"""账号、审查记录、Skill 与模型配置的本地 SQLite 存储（ADR-013）。

角色：给原生前端提供“登录 / 注册 / 我的审查记录 / 自建 Skill / 自带模型 Key”的后端。
依赖：标准库 `sqlite3`（WAL）、`app/services/secret_box.py`、`app/services/skill_catalog.py`、
`app/services/llm_providers.py`、`app/services/llm.py`（`LLMRuntime`）。
约束：
- 口令只存 PBKDF2-HMAC-SHA256（随机盐、210k 次迭代），任何接口都不回传口令/哈希/盐；
- 会话只存 token 的 SHA-256，Cookie 由 API 层设置（HttpOnly / SameSite=Lax）；
- 第三方 API Key 只以密文入库，接口只回 `has_key` 与后 4 位提示；
- 审查记录只记录登录用户；匿名审查不入库（`/api/reviews` 列表需要登录）；
- 判级不受本模块影响：这里只存“谁上传了什么、结论是什么、用了哪个 Skill”。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.config import settings
from app.services import secret_box
from app.services.llm import LLMRuntime
from app.services.llm_providers import resolve_provider
from app.services.skill_catalog import (
    MAX_SKILL_ASSET_CHARS,
    MAX_SKILL_ASSETS,
    MAX_SKILL_INSTRUCTION_CHARS,
    MAX_USER_FOCUS_CHARS,
    SKILL_ASSET_SUFFIXES,
    TOOL_BY_ID,
    Skill,
    SkillAsset,
    builtin_skills,
)

PBKDF2_ITERATIONS = 210_000
SALT_BYTES = 16
MAX_PASSWORD_CHARS = 128
MIN_PASSWORD_CHARS = 8
MAX_DISPLAY_NAME_CHARS = 40
MAX_BASE_URL_CHARS = 300
MAX_MODEL_CHARS = 120
MAX_API_KEY_CHARS = 256
MAX_FILENAME_CHARS = 200
MAX_TITLE_CHARS = 60
#: 头像以 data URL 存库；前端会先压到 128px，正常只有几十 KB
MAX_AVATAR_CHARS = 400_000

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,185}\.[^@\s]{2,63}$")
BASE_URL_RE = re.compile(r"^https?://[^\s]+$")
AVATAR_RE = re.compile(r"^data:image/(png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+$")


class AccountError(RuntimeError):
    """账号/配置类错误；`code` 由 API 映射成 HTTP 状态码。"""

    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


MAX_SKILL_NAME_CHARS = 40
MAX_SKILL_DESCRIPTION_CHARS = 160


def _clean_skill_tools(tools: list[str] | None) -> list[str]:
    """只保留目录里的工具 id，去重并保序；未知 id 直接忽略（不报错，避免前端升级不同步）。"""
    cleaned: list[str] = []
    for tool_id in tools or []:
        key = (tool_id or "").strip()
        if key and key in TOOL_BY_ID and key not in cleaned:
            cleaned.append(key)
    return cleaned


def _clean_skill_assets(assets: list[dict] | None) -> list[dict]:
    """校验 Skill 附件（Python / Markdown 文本）。

    附件**只作为文本资料**参与解释，任何情况下都不会被执行；因此这里只做
    数量、后缀、单条长度与总长度的限制，不做语法检查。
    """
    cleaned: list[dict] = []
    total = 0
    for raw in assets or []:
        if not isinstance(raw, dict):
            raise AccountError("附件格式不正确", code="invalid")
        name = str(raw.get("name") or "").strip()
        content = str(raw.get("content") or "")
        if not name:
            raise AccountError("附件缺少文件名", code="invalid")
        if len(name) > 120:
            raise AccountError("附件名最多 120 个字符", code="invalid")
        lowered = name.casefold()
        if not lowered.endswith(SKILL_ASSET_SUFFIXES):
            raise AccountError(
                "附件只支持 .py / .md / .markdown / .txt 文本", code="invalid"
            )
        if not content.strip():
            raise AccountError(f"附件《{name}》内容为空", code="invalid")
        if len(content) > MAX_SKILL_ASSET_CHARS:
            raise AccountError(
                f"附件《{name}》超过 {MAX_SKILL_ASSET_CHARS} 个字符", code="invalid"
            )
        total += len(content)
        if total > MAX_SKILL_ASSET_CHARS * MAX_SKILL_ASSETS:
            raise AccountError("附件总长度超出上限", code="invalid")
        kind = "python" if lowered.endswith(".py") else "markdown"
        cleaned.append(
            {"name": name, "kind": kind, "size": len(content), "content": content}
        )
    if len(cleaned) > MAX_SKILL_ASSETS:
        raise AccountError(f"最多 {MAX_SKILL_ASSETS} 个附件", code="invalid")
    return cleaned


def _clean_skill_fields(
    name: str,
    description: str,
    instruction: str,
    tools: list[str] | None = None,
    assets: list[dict] | None = None,
) -> tuple[str, str, str, list[str], list[dict]]:
    """名称/说明/指令/工具/附件的统一校验（新建与编辑共用，前端上限与此一致）。"""
    cleaned_name = (name or "").strip()
    cleaned_description = (description or "").strip()
    cleaned_instruction = (instruction or "").strip()
    if not cleaned_name:
        raise AccountError("Skill 名称不能为空", code="invalid")
    if len(cleaned_name) > MAX_SKILL_NAME_CHARS:
        raise AccountError(
            f"Skill 名称最多 {MAX_SKILL_NAME_CHARS} 个字符", code="invalid"
        )
    if len(cleaned_description) > MAX_SKILL_DESCRIPTION_CHARS:
        raise AccountError(
            f"Skill 说明最多 {MAX_SKILL_DESCRIPTION_CHARS} 个字符", code="invalid"
        )
    if not cleaned_instruction:
        raise AccountError("请写一句审查重点说明，模型才能理解你的关注方向", code="invalid")
    if len(cleaned_instruction) > MAX_SKILL_INSTRUCTION_CHARS:
        raise AccountError(
            f"审查重点最多 {MAX_SKILL_INSTRUCTION_CHARS} 个字符", code="invalid"
        )
    return (
        cleaned_name,
        cleaned_description,
        cleaned_instruction,
        _clean_skill_tools(tools),
        _clean_skill_assets(assets),
    )


class User(BaseModel):
    """对外可见的账号信息（不含口令与盐）。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    email: str
    display_name: str
    #: 头像 data URL（空串 = 用昵称首字母）
    avatar: str = ""
    created_at: datetime


class ReviewRecord(BaseModel):
    """一次审查的索引（列表用；正文与证据仍在 checkpoint / 报告接口里）。"""

    model_config = ConfigDict(extra="forbid")

    review_id: str
    source_filename: str
    status: str
    overall_level: str
    reds: int = 0
    yellows: int = 0
    focus: str | None = None
    skill_name: str | None = None
    #: 用户给这条记录起的标签名；为空时前端显示 `source_filename`
    title: str | None = None
    #: 置顶（历史列表按 pinned desc, created_at desc 排序）
    pinned: bool = False
    created_at: datetime
    updated_at: datetime


class LLMSettings(BaseModel):
    """模型配置的只读视图：**不包含** API Key 明文。"""

    model_config = ConfigDict(extra="forbid")

    provider: str
    base_url: str
    model: str
    has_key: bool
    key_hint: str = ""
    updated_at: datetime | None = None


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _normalize_email(email: str) -> str:
    candidate = (email or "").strip().lower()
    if not EMAIL_RE.match(candidate):
        raise AccountError("请填写有效的邮箱地址", code="invalid")
    return candidate


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_CHARS:
        raise AccountError(f"密码至少 {MIN_PASSWORD_CHARS} 位", code="invalid")
    if len(password) > MAX_PASSWORD_CHARS:
        raise AccountError(f"密码最多 {MAX_PASSWORD_CHARS} 位", code="invalid")


def _hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        PBKDF2_ITERATIONS,
    ).hex()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AccountsStore:
    """单文件 SQLite 存储；进程内加锁（多 worker 部署见 ISSUE-019）。"""

    def __init__(
        self,
        db_path: str | Path | None = None,
        secret_path: str | Path | None = None,
        *,
        session_ttl_days: int | None = None,
    ) -> None:
        self._path = Path(db_path or settings.user_db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(str(self._path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        with self._lock:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._init_schema()
        # 延迟到 schema 之后：schema 失败时不必先生成密钥
        self._master_key = secret_box.load_or_create_master_key(
            secret_path or settings.user_secret_path
        )
        ttl = session_ttl_days if session_ttl_days is not None else settings.session_ttl_days
        self._session_ttl = timedelta(days=max(1, ttl))

    # ---------- 生命周期 ----------

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _init_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                avatar TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                instruction TEXT NOT NULL,
                tools TEXT NOT NULL DEFAULT '[]',
                assets TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_skills_owner ON skills(owner_id, created_at);

            CREATE TABLE IF NOT EXISTS llm_configs (
                user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                base_url TEXT NOT NULL,
                model TEXT NOT NULL,
                api_key_cipher TEXT NOT NULL,
                key_hint TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS review_records (
                review_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                source_filename TEXT NOT NULL,
                status TEXT NOT NULL,
                overall_level TEXT NOT NULL,
                reds INTEGER NOT NULL DEFAULT 0,
                yellows INTEGER NOT NULL DEFAULT 0,
                focus TEXT,
                skill_name TEXT,
                title TEXT,
                pinned INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_review_records_owner
                ON review_records(owner_id, created_at DESC);
            """
        )
        self._ensure_review_columns()
        self._ensure_user_columns()
        self._ensure_skill_columns()
        self._connection.commit()

    def _ensure_skill_columns(self) -> None:
        """老库平滑升级：`tools` / `assets` 是界面轮 12 新增列（Skill 可带工具与附件）。"""
        existing = {
            row["name"] for row in self._connection.execute("PRAGMA table_info(skills)")
        }
        if "tools" not in existing:
            self._connection.execute(
                "ALTER TABLE skills ADD COLUMN tools TEXT NOT NULL DEFAULT '[]'"
            )
        if "assets" not in existing:
            self._connection.execute(
                "ALTER TABLE skills ADD COLUMN assets TEXT NOT NULL DEFAULT '[]'"
            )

    def _ensure_user_columns(self) -> None:
        """老库平滑升级：`avatar` 是界面轮 9 新增列（个人账户头像）。"""
        existing = {
            row["name"] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        if "avatar" not in existing:
            self._connection.execute(
                "ALTER TABLE users ADD COLUMN avatar TEXT NOT NULL DEFAULT ''"
            )

    def _ensure_review_columns(self) -> None:
        """老库平滑升级：`title` / `pinned` 是本轮新增列（ADR-013 第 2 轮）。"""
        existing = {
            row["name"]
            for row in self._connection.execute("PRAGMA table_info(review_records)")
        }
        if "title" not in existing:
            self._connection.execute("ALTER TABLE review_records ADD COLUMN title TEXT")
        if "pinned" not in existing:
            self._connection.execute(
                "ALTER TABLE review_records ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0"
            )

    # ---------- 账号 ----------

    def register(
        self, email: str, password: str, display_name: str | None = None
    ) -> tuple[User, str]:
        """注册并直接登录；返回 `(用户, 会话 token)`（token 只出现这一次）。"""
        normalized = _normalize_email(email)
        _validate_password(password)
        display = (display_name or "").strip() or normalized.split("@")[0]
        if len(display) > MAX_DISPLAY_NAME_CHARS:
            raise AccountError(f"昵称最多 {MAX_DISPLAY_NAME_CHARS} 个字符", code="invalid")

        salt = secrets.token_bytes(SALT_BYTES).hex()
        digest = _hash_password(password, salt)
        user_id = "u_" + uuid.uuid4().hex[:16]
        created = _now()
        with self._lock:
            try:
                self._connection.execute(
                    "INSERT INTO users (id, email, display_name, password_hash, salt, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, normalized, display, digest, salt, _iso(created)),
                )
                self._connection.commit()
            except sqlite3.IntegrityError as exc:
                raise AccountError("这个邮箱已经注册过了", code="conflict") from exc
        token = self._create_session(user_id)
        return self.get_user(user_id), token

    def login(self, email: str, password: str) -> tuple[User, str]:
        normalized = (email or "").strip().lower()
        row = self._fetchone("SELECT * FROM users WHERE email = ?", (normalized,))
        if row is None:
            raise AccountError("邮箱或密码不正确", code="unauthorized")
        digest = _hash_password(password, row["salt"])
        if not hmac.compare_digest(digest, row["password_hash"]):
            raise AccountError("邮箱或密码不正确", code="unauthorized")
        user = self._user_from_row(row)
        return user, self._create_session(user.id)

    def get_user(self, user_id: str) -> User:
        row = self._fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        if row is None:
            raise AccountError("账号不存在", code="not_found")
        return self._user_from_row(row)

    def update_profile(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        avatar: str | None = None,
    ) -> User:
        """改昵称 / 头像；两个参数都是“给了才改”，传空串头像表示移除。"""
        updates: dict[str, str] = {}
        if display_name is not None:
            cleaned = display_name.strip()
            if not cleaned:
                raise AccountError("昵称不能为空", code="invalid")
            if len(cleaned) > MAX_DISPLAY_NAME_CHARS:
                raise AccountError(
                    f"昵称最多 {MAX_DISPLAY_NAME_CHARS} 个字符", code="invalid"
                )
            updates["display_name"] = cleaned
        if avatar is not None:
            cleaned_avatar = avatar.strip()
            if cleaned_avatar:
                if len(cleaned_avatar) > MAX_AVATAR_CHARS:
                    raise AccountError("头像太大，请换一张小一点的图片", code="invalid")
                if not AVATAR_RE.match(cleaned_avatar):
                    raise AccountError("头像格式不支持，请上传 PNG/JPG 图片", code="invalid")
            updates["avatar"] = cleaned_avatar
        if not updates:
            return self.get_user(user_id)
        assignments = ", ".join(f"{column} = ?" for column in updates)
        with self._lock:
            cursor = self._connection.execute(
                f"UPDATE users SET {assignments} WHERE id = ?",  # noqa: S608 - 列名来自闭集
                (*updates.values(), user_id),
            )
            self._connection.commit()
        if cursor.rowcount == 0:
            raise AccountError("账号不存在", code="not_found")
        return self.get_user(user_id)

    def resolve_session(self, token: str | None) -> User | None:
        """token → 用户；过期/未知/超长一律返回 None，不抛异常。"""
        if not token or len(token) > 200:
            return None
        digest = _token_hash(token)
        with self._lock:
            row = self._connection.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
                " WHERE s.token_hash = ? AND s.expires_at > ?",
                (digest, _iso(_now())),
            ).fetchone()
            self._connection.execute(
                "DELETE FROM sessions WHERE expires_at <= ?", (_iso(_now()),)
            )
            self._connection.commit()
        return self._user_from_row(row) if row is not None else None

    def revoke_session(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            self._connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),)
            )
            self._connection.commit()

    def _create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = _now()
        with self._lock:
            self._connection.execute(
                "INSERT INTO sessions (token_hash, user_id, created_at, expires_at)"
                " VALUES (?, ?, ?, ?)",
                (_token_hash(token), user_id, _iso(now), _iso(now + self._session_ttl)),
            )
            self._connection.execute(
                "DELETE FROM sessions WHERE expires_at <= ?", (_iso(now),)
            )
            self._connection.commit()
        return token

    # ---------- Skill ----------

    def list_skills(self, owner_id: str | None = None) -> list[Skill]:
        skills = builtin_skills()
        if not owner_id:
            return skills
        rows = self._fetchall(
            "SELECT * FROM skills WHERE owner_id = ? ORDER BY created_at DESC", (owner_id,)
        )
        skills.extend(self._skill_from_row(row) for row in rows)
        return skills

    def resolve_skill(self, owner_id: str | None, skill_id: str | None) -> Skill | None:
        """按 ID 取 Skill：先查内置，再查该用户名下的自建 Skill。"""
        if not skill_id:
            return None
        for skill in builtin_skills():
            if skill.id == skill_id:
                return skill
        if not owner_id:
            return None
        row = self._fetchone(
            "SELECT * FROM skills WHERE id = ? AND owner_id = ?", (skill_id, owner_id)
        )
        return self._skill_from_row(row) if row is not None else None

    def create_skill(
        self,
        owner_id: str,
        *,
        name: str,
        description: str = "",
        instruction: str,
        tools: list[str] | None = None,
        assets: list[dict] | None = None,
    ) -> Skill:
        (
            cleaned_name,
            cleaned_description,
            cleaned_instruction,
            cleaned_tools,
            cleaned_assets,
        ) = _clean_skill_fields(name, description, instruction, tools, assets)

        skill_id = "sk_" + uuid.uuid4().hex[:16]
        created = _now()
        tools_json = json.dumps(cleaned_tools, ensure_ascii=False)
        assets_json = json.dumps(cleaned_assets, ensure_ascii=False)
        with self._lock:
            self._connection.execute(
                "INSERT INTO skills"
                " (id, owner_id, name, description, instruction, tools, assets, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    skill_id,
                    owner_id,
                    cleaned_name,
                    cleaned_description,
                    cleaned_instruction,
                    tools_json,
                    assets_json,
                    _iso(created),
                ),
            )
            self._connection.commit()
        return Skill(
            id=skill_id,
            name=cleaned_name,
            description=cleaned_description,
            instruction=cleaned_instruction,
            tags=[],
            builtin=False,
            tools=cleaned_tools,
            assets=[SkillAsset.model_validate(item) for item in cleaned_assets],
            owner_id=owner_id,
            created_at=created,
        )

    def update_skill(
        self,
        owner_id: str,
        skill_id: str,
        *,
        name: str,
        description: str = "",
        instruction: str,
        tools: list[str] | None = None,
        assets: list[dict] | None = None,
    ) -> Skill:
        """改自建 Skill；内置推荐 Skill 是代码常量，只读（另存为自建即可）。"""
        if skill_id.startswith("builtin:"):
            raise AccountError("推荐 Skill 不能直接改，请另存为我的 Skill", code="invalid")
        (
            cleaned_name,
            cleaned_description,
            cleaned_instruction,
            cleaned_tools,
            cleaned_assets,
        ) = _clean_skill_fields(name, description, instruction, tools, assets)
        with self._lock:
            cursor = self._connection.execute(
                "UPDATE skills"
                " SET name = ?, description = ?, instruction = ?, tools = ?, assets = ?"
                " WHERE id = ? AND owner_id = ?",
                (
                    cleaned_name,
                    cleaned_description,
                    cleaned_instruction,
                    json.dumps(cleaned_tools, ensure_ascii=False),
                    json.dumps(cleaned_assets, ensure_ascii=False),
                    skill_id,
                    owner_id,
                ),
            )
            self._connection.commit()
        if cursor.rowcount == 0:
            raise AccountError("没有找到这个 Skill（或不属于当前账号）", code="not_found")
        row = self._fetchone(
            "SELECT * FROM skills WHERE id = ? AND owner_id = ?", (skill_id, owner_id)
        )
        if row is None:  # pragma: no cover - rowcount 已保证存在
            raise AccountError("没有找到这个 Skill（或不属于当前账号）", code="not_found")
        return self._skill_from_row(row)

    def delete_skill(self, owner_id: str, skill_id: str) -> None:
        if skill_id.startswith("builtin:"):
            raise AccountError("内置推荐 Skill 不能删除", code="invalid")
        with self._lock:
            cursor = self._connection.execute(
                "DELETE FROM skills WHERE id = ? AND owner_id = ?", (skill_id, owner_id)
            )
            self._connection.commit()
        if cursor.rowcount == 0:
            raise AccountError("没有找到这个 Skill（或不属于当前账号）", code="not_found")

    # ---------- 模型配置（BYOK） ----------

    def save_llm_settings(
        self,
        user_id: str,
        *,
        provider: str,
        base_url: str = "",
        model: str,
        api_key: str | None = None,
    ) -> LLMSettings:
        catalog = resolve_provider((provider or "").strip())
        if catalog is None:
            raise AccountError("未知的模型厂商", code="invalid")
        address = (base_url or "").strip() or catalog.base_url
        model_name = (model or "").strip()
        if not address:
            raise AccountError("请填写服务地址（例如 https://api.openai.com/v1）", code="invalid")
        if not BASE_URL_RE.match(address) or len(address) > MAX_BASE_URL_CHARS:
            raise AccountError("服务地址必须以 http:// 或 https:// 开头", code="invalid")
        if not model_name or len(model_name) > MAX_MODEL_CHARS:
            raise AccountError("请填写模型名称", code="invalid")

        new_key = (api_key or "").strip()
        if new_key and (len(new_key) < 8 or len(new_key) > MAX_API_KEY_CHARS):
            raise AccountError("API Key 长度看起来不对（应在 8-256 字符之间）", code="invalid")

        with self._lock:
            existing = self._connection.execute(
                "SELECT api_key_cipher, key_hint FROM llm_configs WHERE user_id = ?", (user_id,)
            ).fetchone()
            if new_key:
                cipher = secret_box.encrypt(new_key, self._master_key)
                hint = "••••" + new_key[-4:]
            elif existing is not None:
                cipher = existing["api_key_cipher"]
                hint = existing["key_hint"]
            elif catalog.key_optional:
                cipher = secret_box.encrypt("", self._master_key)
                hint = ""
            else:
                raise AccountError("请填写该厂商的 API Key", code="invalid")

            self._connection.execute(
                "INSERT INTO llm_configs"
                " (user_id, provider, base_url, model, api_key_cipher, key_hint, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(user_id) DO UPDATE SET"
                " provider = excluded.provider, base_url = excluded.base_url,"
                " model = excluded.model, api_key_cipher = excluded.api_key_cipher,"
                " key_hint = excluded.key_hint, updated_at = excluded.updated_at",
                (
                    user_id,
                    catalog.id,
                    address,
                    model_name,
                    cipher,
                    hint,
                    _iso(_now()),
                ),
            )
            self._connection.commit()
        return self.get_llm_settings(user_id)  # type: ignore[return-value]

    def get_llm_settings(self, user_id: str) -> LLMSettings | None:
        row = self._fetchone("SELECT * FROM llm_configs WHERE user_id = ?", (user_id,))
        if row is None:
            return None
        return LLMSettings(
            provider=row["provider"],
            base_url=row["base_url"],
            model=row["model"],
            has_key=bool(row["key_hint"]),
            key_hint=row["key_hint"],
            updated_at=_parse_time(row["updated_at"]),
        )

    def resolve_llm_runtime(self, user_id: str | None) -> LLMRuntime | None:
        """按用户取出可用的模型运行时（含解密后的 Key）；没配置返回 None。"""
        if not user_id:
            return None
        row = self._fetchone("SELECT * FROM llm_configs WHERE user_id = ?", (user_id,))
        if row is None:
            return None
        try:
            api_key = secret_box.decrypt(row["api_key_cipher"], self._master_key)
        except secret_box.SecretBoxError as exc:
            raise AccountError(
                f"保存的 API Key 无法解密（{exc}）；请在“API 配置”里重新填写。",
                code="invalid",
            ) from exc
        return LLMRuntime(
            provider=row["provider"],
            base_url=row["base_url"],
            model=row["model"],
            # 本地推理服务允许空 Key，SDK 仍需要一个非空占位符
            api_key=api_key or "EMPTY",
            timeout_seconds=settings.llm_timeout_seconds,
        )

    def clear_llm_settings(self, user_id: str) -> None:
        with self._lock:
            self._connection.execute("DELETE FROM llm_configs WHERE user_id = ?", (user_id,))
            self._connection.commit()

    # ---------- 审查记录 ----------

    def record_review(
        self,
        *,
        review_id: str,
        owner_id: str,
        source_filename: str,
        status: str,
        overall_level: str,
        reds: int = 0,
        yellows: int = 0,
        focus: str | None = None,
        skill_name: str | None = None,
    ) -> None:
        now = _iso(_now())
        filename = (source_filename or "")[:MAX_FILENAME_CHARS]
        note = (focus or "").strip()[:MAX_USER_FOCUS_CHARS] or None
        with self._lock:
            self._connection.execute(
                "INSERT INTO review_records"
                " (review_id, owner_id, source_filename, status, overall_level, reds,"
                "  yellows, focus, skill_name, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(review_id) DO UPDATE SET"
                " status = excluded.status, overall_level = excluded.overall_level,"
                " reds = excluded.reds, yellows = excluded.yellows,"
                " focus = excluded.focus, skill_name = excluded.skill_name,"
                " updated_at = excluded.updated_at",
                (
                    review_id,
                    owner_id,
                    filename,
                    status,
                    overall_level,
                    max(0, reds),
                    max(0, yellows),
                    note,
                    (skill_name or "").strip()[:40] or None,
                    now,
                    now,
                ),
            )
            self._connection.commit()

    def owner_of(self, review_id: str) -> str | None:
        row = self._fetchone(
            "SELECT owner_id FROM review_records WHERE review_id = ?", (review_id,)
        )
        return None if row is None else row["owner_id"]

    def list_reviews(self, owner_id: str, limit: int = 20) -> list[ReviewRecord]:
        rows = self._fetchall(
            "SELECT * FROM review_records WHERE owner_id = ?"
            " ORDER BY pinned DESC, created_at DESC LIMIT ?",
            (owner_id, max(1, min(limit, 50))),
        )
        return [self._record_from_row(row) for row in rows]

    def rename_review(self, owner_id: str, review_id: str, title: str) -> ReviewRecord:
        """改标签名；传空字符串表示恢复成文件名。"""
        cleaned = (title or "").strip()[:MAX_TITLE_CHARS] or None
        self._update_review(
            owner_id, review_id, "UPDATE review_records SET title = ? WHERE review_id = ?",
            (cleaned, review_id),
        )
        return self._get_record(owner_id, review_id)

    def set_review_pinned(
        self, owner_id: str, review_id: str, pinned: bool
    ) -> ReviewRecord:
        self._update_review(
            owner_id,
            review_id,
            "UPDATE review_records SET pinned = ? WHERE review_id = ?",
            (1 if pinned else 0, review_id),
        )
        return self._get_record(owner_id, review_id)

    def delete_review(self, owner_id: str, review_id: str) -> None:
        self._update_review(
            owner_id, review_id, "DELETE FROM review_records WHERE review_id = ?", (review_id,)
        )

    def delete_reviews(self, owner_id: str) -> list[str]:
        """清空该账号的全部历史记录，返回被删的 `review_id`（供调用方清本机文件）。

        只删本账号的行：另一个账号的记录不会被碰到，也不需要逐个 `DELETE` 请求。
        """
        with self._lock:
            rows = self._connection.execute(
                "SELECT review_id FROM review_records WHERE owner_id = ?", (owner_id,)
            ).fetchall()
            review_ids = [row["review_id"] for row in rows]
            if review_ids:
                self._connection.execute(
                    "DELETE FROM review_records WHERE owner_id = ?", (owner_id,)
                )
                self._connection.commit()
        return review_ids

    def _update_review(
        self, owner_id: str, review_id: str, statement: str, params: tuple
    ) -> None:
        """只有归属账号能改/删；不存在与越权都按 not_found 处理（不泄露存在性）。"""
        with self._lock:
            row = self._connection.execute(
                "SELECT owner_id FROM review_records WHERE review_id = ?", (review_id,)
            ).fetchone()
            if row is None or row["owner_id"] != owner_id:
                raise AccountError("审查记录不存在", code="not_found")
            self._connection.execute(statement, params)
            self._connection.commit()

    def _get_record(self, owner_id: str, review_id: str) -> ReviewRecord:
        row = self._fetchone(
            "SELECT * FROM review_records WHERE review_id = ? AND owner_id = ?",
            (review_id, owner_id),
        )
        if row is None:
            raise AccountError("审查记录不存在", code="not_found")
        return self._record_from_row(row)

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> ReviewRecord:
        return ReviewRecord(
            review_id=row["review_id"],
            source_filename=row["source_filename"],
            status=row["status"],
            overall_level=row["overall_level"],
            reds=row["reds"],
            yellows=row["yellows"],
            focus=row["focus"],
            skill_name=row["skill_name"],
            title=row["title"] if "title" in row.keys() else None,
            pinned=bool(row["pinned"]) if "pinned" in row.keys() else False,
            created_at=_parse_time(row["created_at"]),
            updated_at=_parse_time(row["updated_at"]),
        )

    # ---------- 内部 ----------

    def _fetchone(self, query: str, params: tuple) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(query, params).fetchone()

    def _fetchall(self, query: str, params: tuple) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(query, params).fetchall())

    @staticmethod
    def _user_from_row(row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            display_name=row["display_name"],
            avatar=row["avatar"] if "avatar" in row.keys() else "",
            created_at=_parse_time(row["created_at"]),
        )

    @staticmethod
    def _skill_from_row(row: sqlite3.Row) -> Skill:
        assets: list[SkillAsset] = []
        raw_assets = row["assets"] if "assets" in row.keys() else "[]"
        try:
            for item in json.loads(raw_assets or "[]"):
                assets.append(SkillAsset.model_validate(item))
        except (ValueError, TypeError):
            assets = []
        try:
            tools = [str(item) for item in json.loads(row["tools"])]
        except (ValueError, TypeError, KeyError):
            tools = []
        return Skill(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            instruction=row["instruction"],
            tags=[],
            builtin=False,
            tools=[tool for tool in tools if tool in TOOL_BY_ID],
            assets=assets,
            owner_id=row["owner_id"],
            created_at=_parse_time(row["created_at"]),
        )
