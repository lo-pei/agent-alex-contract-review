"""FastAPI 应用：账号 → 上传合同 → 启动审查 → 人工决定 → 下载报告（ADR-002 / ADR-009 / ADR-013）。

角色：把 `ReviewService` 暴露成 HTTP 接口，供原生前端与第三方系统调用。
依赖：`app/review_service.py`、`app/services/checkpointer.py`、`app/services/pending_store.py`、
`app/services/accounts.py`（账号/记录/Skill/模型配置）、`app/report_markdown.py`。
约束：
- **不在 API 层判级或改级**，等级只来自图里的 Python 规则；
- HITL 只通过 `ReviewService.resume()` 恢复，不接受外部拼 `Command`；
- 上传只做类型/大小/空文件校验并落盘到 `.data/uploads/<review_id>/`，不做 OCR/格式转换；
- 报告未生成时返回 409，绝不返回空报告冒充完成；
- 未知 review_id 返回 404，状态冲突返回 409；
- 会话 Cookie 只带 `HttpOnly` 随机 token；API Key 只进不出（响应只有 `has_key`/尾号提示）；
- 未登录可以审查（不记录）；已登录的审查与账号绑定，跨账号读取返回 404。
"""

from __future__ import annotations

import mimetypes
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi import Path as ApiPath
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.graph import build_graph
from app.report_markdown import render_report_markdown
from app.review_service import ReviewRun, ReviewService, ReviewStateError
from app.rules.engine import RULE_ENGINE_VERSION, load_rule_set
from app.schemas import (
    ApprovalPayload,
    DocumentCheck,
    HitlDecision,
    OverallLevel,
    ReviewReport,
    ReviewStatus,
)
from app.services import llm as llm_service
from app.services import secret_box
from app.services.accounts import (
    AccountError,
    AccountsStore,
    LLMSettings,
    ReviewRecord,
    User,
)
from app.services.checkpointer import sqlite_checkpointer
from app.services.llm import LLMNotConfigured, LLMRuntime, probe_llm
from app.services.llm_providers import provider_payload, resolve_provider
from app.services.pending_store import FilePendingStore
from app.services.skill_catalog import Skill, compose_focus

API_TITLE = "Agent Alex · 外贸合同智审助手"
API_VERSION = "1.0.0"

#: 原生前端资源目录（无框架、无 CDN；见 ADR-009 第 2 轮补充）
WEB_DIR = Path(__file__).resolve().parent / "web"
INDEX_FILE = WEB_DIR / "index.html"

# 部分 Windows 环境的 mime.types 不认识 woff2；显式登记，避免静态资源被当作 octet-stream
mimetypes.add_type("font/woff2", ".woff2")

#: 与 `app/nodes/ingest.py` 保持一致；`.doc` 明确拒绝并提示转换
UPLOAD_SUFFIXES = frozenset({".txt", ".md", ".markdown", ".pdf", ".docx"})
MAX_FILENAME_CHARS = 180
CHUNK_SIZE = 1024 * 1024

REVIEW_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
SKILL_ID_PATTERN = r"^[A-Za-z0-9:_-]{1,64}$"

#: 会话 Cookie 名；只存随机 token 的原文，服务端只留 SHA-256（ADR-013）
SESSION_COOKIE = "alex_session"
#: 审查侧栏“参考材料”只收纯文本，避免把第二份合同/扫描件塞进提示词
REFERENCE_SUFFIXES = frozenset({".txt", ".md", ".markdown"})
MAX_REFERENCE_BYTES = 64 * 1024


class ReviewSummary(BaseModel):
    """对外的审查摘要（不含合同原文与完整 state，避免把大文本塞进响应）。"""

    model_config = ConfigDict(extra="forbid")

    review_id: str
    source_filename: str
    status: ReviewStatus
    overall_level: OverallLevel
    awaiting_human: bool = False
    approval: ApprovalPayload | None = None
    report: ReviewReport | None = None
    warnings: list[str] = []
    errors: list[str] = []
    extraction_status: Literal["ok", "degraded", "skipped"] = "skipped"
    explanation_status: Literal["ok", "fallback", "skipped"] = "skipped"
    #: 文档类型闸门：`is_contract=False` 时前端直接展示“不是合同”，不展示风险结论
    document_check: DocumentCheck | None = None
    #: 审查重点与 Skill 名称（只影响解释措辞）
    focus: str | None = None
    skill_name: str | None = None


class Credentials(BaseModel):
    """注册/登录请求体。"""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    display_name: str = Field(default="", max_length=40)


class ProfileUpdate(BaseModel):
    """个人账户：昵称 / 头像（avatar 传空串表示移除）。"""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=40)
    avatar: str | None = Field(default=None, max_length=400_000)


class SessionInfo(BaseModel):
    """当前登录态：未登录时 `authenticated=false`，其余字段为空。"""

    model_config = ConfigDict(extra="forbid")

    authenticated: bool
    user: User | None = None
    llm: LLMSettings | None = None
    #: 环境默认模型是否可用（未登录用户也能看到“是否已配置模型”）
    env_llm: bool = False


class SkillList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: list[Skill]
    builtin_count: int


class SkillCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=160)
    instruction: str = Field(min_length=1, max_length=1000)


class LLMUpdate(BaseModel):
    """BYOK 写入请求：`api_key` 留空表示沿用已保存的 Key。"""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=40)
    base_url: str = Field(default="", max_length=300)
    model: str = Field(min_length=1, max_length=120)
    api_key: str = Field(default="", max_length=256)


class LLMProbeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    provider: str
    model: str
    detail: str = ""


class ReviewHistory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviews: list[ReviewRecord]
    total: int


class ReviewPatch(BaseModel):
    """审查记录的改名 / 置顶（字段缺省表示不改）。"""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=60)
    pinned: bool | None = None


class RuleSummary(BaseModel):
    """规则集目录项：只读展示用，不含正则/DSL（避免把判定细节泄露给客户端）。"""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title: str
    category: str
    risk_level: Literal["red", "yellow"]
    reason: str
    suggestion: str
    requires_extraction: bool


class RuleCatalog(BaseModel):
    """规则集目录 + 集合版本，供前端“规则集”页与工作台摘要展示。"""

    model_config = ConfigDict(extra="forbid")

    ruleset_version: int
    rule_engine_version: str
    count: int
    red_count: int
    yellow_count: int
    rules: list[RuleSummary]


def _summary_of(run: ReviewRun) -> ReviewSummary:
    state = run.state
    if state is None:  # pragma: no cover - ReviewRun 始终带 state
        raise HTTPException(status_code=500, detail="审查状态缺失")
    return ReviewSummary(
        review_id=run.review_id,
        source_filename=state.source_filename,
        status=run.status,
        overall_level=state.overall_level,
        awaiting_human=run.awaiting_human,
        approval=run.approval,
        report=run.report,
        warnings=list(state.warnings),
        errors=list(state.errors),
        extraction_status=state.extraction_status,
        explanation_status=state.explanation_status,
        document_check=state.document_check,
        focus=state.focus or None,
        skill_name=state.skill_name,
    )


def _level_counts(state) -> tuple[int, int]:
    reds = sum(1 for e in state.rule_evaluations if e.risk_level == "red" and not e.skipped)
    yellows = sum(
        1 for e in state.rule_evaluations if e.risk_level == "yellow" and not e.skipped
    )
    return reds, yellows


def _safe_filename(name: str | None) -> str:
    """只取 basename，去掉控制字符与路径分隔符（兼容 Windows/Unix 写法）。"""
    if not name:
        return ""
    candidate = name.replace("\\", "/").split("/")[-1]
    candidate = "".join(ch for ch in candidate if ch.isprintable()).strip()
    if candidate in {"", ".", ".."}:
        return ""
    if len(candidate) > MAX_FILENAME_CHARS:
        candidate = candidate[-MAX_FILENAME_CHARS:]
    return candidate


def _service_of(request: Request) -> ReviewService:
    service = getattr(request.app.state, "service", None)
    if service is None:  # pragma: no cover - lifespan 保证已初始化
        raise HTTPException(status_code=503, detail="审查服务未初始化")
    return service


def _set_session(response: Response, token: str, ttl_days: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=ttl_days * 24 * 3600,
        httponly=True,
        samesite="lax",
        path="/",
    )


def create_app(
    service: ReviewService | None = None,
    *,
    upload_dir: Path | str | None = None,
    pending_dir: Path | str | None = None,
    max_upload_mb: int | None = None,
    accounts: AccountsStore | None = None,
    user_db_path: Path | str | None = None,
) -> FastAPI:
    """构造应用。

    传入 `service` 时使用该实例（测试用内存 checkpointer），否则使用 SQLite；
    `accounts` 可注入账号存储（测试用 `tmp_path`），否则按 `user_db_path` 建在 `.data/`。
    """
    upload_root = Path(upload_dir or settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    limit_bytes = (max_upload_mb if max_upload_mb is not None else settings.max_upload_mb) * (
        1024 * 1024
    )
    db_path = Path(user_db_path or settings.user_db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        owns_store = accounts is None
        store = accounts or AccountsStore(db_path)
        app.state.accounts = store
        try:
            if service is not None:
                app.state.service = service
                yield
                return
            with sqlite_checkpointer() as saver:
                app.state.service = ReviewService(
                    build_graph(checkpointer=saver),
                    pending_store=FilePendingStore(pending_dir),
                )
                yield
        finally:
            if owns_store:
                store.close()

    app = FastAPI(title=API_TITLE, version=API_VERSION, lifespan=lifespan)
    app.state.accounts = accounts
    if service is not None:
        app.state.service = service

    # 前端：原生 HTML/CSS/JS（无框架、无 CDN、无构建步骤），由 FastAPI 直接托管
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        """浏览器入口：单页应用（上传 → 审查 → 人工确认 → 报告）。"""
        return FileResponse(
            INDEX_FILE,
            media_type="text/html; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )

    @app.exception_handler(ReviewStateError)
    def _review_state_handler(_request: Request, exc: ReviewStateError) -> JSONResponse:
        return JSONResponse(
            status_code=404 if exc.missing else 409,
            content={"detail": str(exc)},
        )

    @app.exception_handler(AccountError)
    def _account_error_handler(_request: Request, exc: AccountError) -> JSONResponse:
        status = {
            "invalid": 400,
            "unauthorized": 401,
            "not_found": 404,
            "conflict": 409,
        }.get(exc.code, 400)
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    @app.exception_handler(secret_box.SecretBoxError)
    def _secret_error_handler(_request: Request, exc: secret_box.SecretBoxError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"本地密钥不可用：{exc}；请删除 .data/secret.key 后重新配置 API Key。"
            },
        )

    def store_of(request: Request) -> AccountsStore:
        store = getattr(request.app.state, "accounts", None)
        if store is None:  # pragma: no cover - lifespan 总会设置
            raise HTTPException(status_code=503, detail="账号存储未初始化")
        return store

    def current_user(request: Request) -> User | None:
        return store_of(request).resolve_session(request.cookies.get(SESSION_COOKIE))

    def require_user(request: Request) -> User:
        user = current_user(request)
        if user is None:
            raise HTTPException(status_code=401, detail="请先登录或注册")
        return user

    def llm_runtime_for(request: Request) -> LLMRuntime | None:
        """登录用户自带模型配置；未登录/未配置返回 None（回落到环境默认模型）。"""
        user = current_user(request)
        if user is None:
            return None
        return store_of(request).resolve_llm_runtime(user.id)

    def authorize(request: Request, review_id: str) -> User | None:
        """已入册的审查只有归属账号能读；匿名审查凭不可猜的 id 可读。"""
        owner = store_of(request).owner_of(review_id)
        if owner is None:
            return current_user(request)
        user = current_user(request)
        if user is None or user.id != owner:
            raise HTTPException(status_code=404, detail=f"审查不存在：{review_id}")
        return user

    def record(request: Request, run: ReviewRun, user: User | None) -> None:
        state = run.state
        if user is None or state is None:
            return
        reds, yellows = _level_counts(state)
        # 图暂停在人工确认时 `state.status` 仍是 running；历史列表要显示“待确认”
        status = "awaiting_human" if run.awaiting_human else run.status
        store_of(request).record_review(
            review_id=run.review_id,
            owner_id=user.id,
            source_filename=state.source_filename,
            status=status,
            overall_level=state.overall_level,
            reds=reds,
            yellows=yellows,
            focus=state.focus,
            skill_name=state.skill_name,
        )

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "version": API_VERSION,
            "checkpoint_backend": settings.checkpoint_backend if service is None else "memory",
            "rag_enabled": settings.rag_enabled,
            "accounts": True,
            "time": datetime.now(UTC).isoformat(),
        }

    # ---------- 账号 ----------

    @app.post("/api/auth/register", response_model=SessionInfo, status_code=201)
    def register(payload: Credentials, response: Response, request: Request) -> SessionInfo:
        store = store_of(request)
        user, token = store.register(payload.email, payload.password, payload.display_name)
        _set_session(response, token, settings.session_ttl_days)
        return SessionInfo(
            authenticated=True,
            user=user,
            llm=store.get_llm_settings(user.id),
            env_llm=bool(settings.llm_api_key.strip()),
        )

    @app.post("/api/auth/login", response_model=SessionInfo)
    def login(payload: Credentials, response: Response, request: Request) -> SessionInfo:
        store = store_of(request)
        user, token = store.login(payload.email, payload.password)
        _set_session(response, token, settings.session_ttl_days)
        return SessionInfo(
            authenticated=True,
            user=user,
            llm=store.get_llm_settings(user.id),
            env_llm=bool(settings.llm_api_key.strip()),
        )

    @app.post("/api/auth/logout", status_code=204)
    def logout(response: Response, request: Request) -> Response:
        store_of(request).revoke_session(request.cookies.get(SESSION_COOKIE))
        response.delete_cookie(SESSION_COOKIE, path="/")
        response.status_code = 204
        return response

    @app.patch("/api/auth/profile", response_model=User)
    def update_profile(payload: ProfileUpdate, request: Request) -> User:
        """改昵称或头像；只传了的字段才更新（头像传空串 = 移除）。"""
        user = require_user(request)
        return store_of(request).update_profile(
            user.id,
            display_name=payload.display_name,
            avatar=payload.avatar,
        )

    @app.get("/api/auth/me", response_model=SessionInfo)
    def me(request: Request) -> SessionInfo:
        user = current_user(request)
        store = store_of(request)
        return SessionInfo(
            authenticated=user is not None,
            user=user,
            llm=store.get_llm_settings(user.id) if user is not None else None,
            env_llm=bool(settings.llm_api_key.strip()),
        )

    @app.get("/api/reviews", response_model=ReviewHistory)
    def list_reviews(request: Request, limit: int = 20) -> ReviewHistory:
        user = require_user(request)
        items = store_of(request).list_reviews(user.id, limit=limit)
        return ReviewHistory(reviews=items, total=len(items))

    @app.patch("/api/reviews/{review_id}", response_model=ReviewRecord)
    def patch_review(
        payload: ReviewPatch,
        request: Request,
        review_id: str = ApiPath(pattern=REVIEW_ID_PATTERN),
    ) -> ReviewRecord:
        """改标签名 / 置顶：只动 `review_records`，不重跑审查、不改任何等级。"""
        user = require_user(request)
        store = store_of(request)
        if payload.pinned is not None:
            record = store.set_review_pinned(user.id, review_id, payload.pinned)
            if payload.title is None:
                return record
        return store.rename_review(user.id, review_id, payload.title or "")

    @app.delete("/api/reviews/{review_id}", status_code=204)
    def delete_review(
        request: Request,
        review_id: str = ApiPath(pattern=REVIEW_ID_PATTERN),
    ) -> Response:
        """删除历史记录：只有归属账号能删；同时清掉本机 checkpoint 与上传文件。"""
        user = require_user(request)
        store_of(request).delete_review(user.id, review_id)
        _service_of(request).discard(review_id)
        shutil.rmtree(upload_root / review_id, ignore_errors=True)
        return Response(status_code=204)

    # ---------- Skill ----------

    @app.get("/api/skills", response_model=SkillList)
    def list_skills(request: Request) -> SkillList:
        user = current_user(request)
        skills = store_of(request).list_skills(user.id if user is not None else None)
        return SkillList(
            skills=skills,
            builtin_count=sum(1 for skill in skills if skill.builtin),
        )

    @app.post("/api/skills", response_model=Skill, status_code=201)
    def create_skill(payload: SkillCreate, request: Request) -> Skill:
        user = require_user(request)
        return store_of(request).create_skill(
            user.id,
            name=payload.name,
            description=payload.description,
            instruction=payload.instruction,
        )

    @app.patch("/api/skills/{skill_id}", response_model=Skill)
    def update_skill(
        payload: SkillCreate,
        request: Request,
        skill_id: str = ApiPath(pattern=SKILL_ID_PATTERN),
    ) -> Skill:
        """改自建 Skill；推荐 Skill 只读（会返回 400，前端提示另存为我的）。"""
        user = require_user(request)
        return store_of(request).update_skill(
            user.id,
            skill_id,
            name=payload.name,
            description=payload.description,
            instruction=payload.instruction,
        )

    @app.delete("/api/skills/{skill_id}", status_code=204)
    def delete_skill(
        request: Request,
        skill_id: str = ApiPath(pattern=SKILL_ID_PATTERN),
    ) -> Response:
        user = require_user(request)
        store_of(request).delete_skill(user.id, skill_id)
        return Response(status_code=204)

    # ---------- 模型配置（BYOK） ----------

    @app.get("/api/llm/providers")
    def llm_providers() -> dict:
        """厂商目录：只给默认地址与模型名，不含任何 Key。"""
        return {"providers": provider_payload()}

    @app.get("/api/llm", response_model=LLMSettings | None)
    def get_llm_settings(request: Request) -> LLMSettings | None:
        user = require_user(request)
        return store_of(request).get_llm_settings(user.id)

    @app.put("/api/llm", response_model=LLMSettings)
    def save_llm_settings(payload: LLMUpdate, request: Request) -> LLMSettings:
        user = require_user(request)
        settings_out = store_of(request).save_llm_settings(
            user.id,
            provider=payload.provider,
            base_url=payload.base_url,
            model=payload.model,
            api_key=payload.api_key,
        )
        # 换了 Key/地址后旧客户端不能复用
        llm_service.clear_llm_cache()
        return settings_out

    @app.delete("/api/llm", status_code=204)
    def clear_llm_settings(request: Request) -> Response:
        user = require_user(request)
        store_of(request).clear_llm_settings(user.id)
        return Response(status_code=204)

    @app.post("/api/llm/test", response_model=LLMProbeResult)
    def test_llm_settings(payload: LLMUpdate, request: Request) -> LLMProbeResult:
        """用表单里填的值做一次真实连通性探测（不保存、不落盘）。"""
        user = require_user(request)
        catalog = resolve_provider(payload.provider)
        if catalog is None:
            raise HTTPException(status_code=400, detail="未知的模型厂商")

        key = payload.api_key.strip()
        runtime: LLMRuntime | None
        if not key:
            saved = store_of(request).get_llm_settings(user.id)
            if saved is None:
                raise HTTPException(status_code=400, detail="请先填写 API Key 再测试")
            runtime = store_of(request).resolve_llm_runtime(user.id)
            if runtime is None:  # pragma: no cover - saved 存在时 runtime 必存在
                raise HTTPException(status_code=400, detail="保存的配置不完整，请重新填写")
        else:
            address = payload.base_url.strip() or catalog.base_url
            if not address.startswith(("http://", "https://")):
                raise HTTPException(status_code=400, detail="服务地址必须以 http(s):// 开头")
            runtime = LLMRuntime(
                provider=catalog.id,
                base_url=address,
                model=payload.model,
                api_key=key,
                timeout_seconds=settings.llm_timeout_seconds,
            )
        try:
            result = probe_llm(runtime)
        except LLMNotConfigured as exc:  # pragma: no cover - runtime 已给全字段
            return LLMProbeResult(
                ok=False, provider=runtime.provider, model=runtime.model, detail=str(exc)
            )
        except Exception as exc:  # noqa: BLE001 - 探测失败要让用户看到原因
            return LLMProbeResult(
                ok=False,
                provider=runtime.provider,
                model=runtime.model,
                detail=f"{type(exc).__name__}: {exc}"[:400],
            )
        return LLMProbeResult(
            ok=bool(result.ok),
            provider=runtime.provider,
            model=runtime.model,
            detail="接口可用" if result.ok else "接口返回了非预期结果",
        )

    @app.get("/api/rules", response_model=RuleCatalog)
    def list_rules() -> RuleCatalog:
        """规则集目录（只读）。等级仍只由规则引擎在服务端判定，前端只展示。"""
        try:
            rule_set = load_rule_set()
        except (FileNotFoundError, ValueError) as exc:  # 启动期问题，运行期不静默
            raise HTTPException(status_code=500, detail=f"规则集加载失败：{exc}") from exc
        rules = [
            RuleSummary(
                rule_id=rule.rule_id,
                title=rule.title,
                category=rule.category,
                risk_level=rule.risk_level,
                reason=rule.reason,
                suggestion=rule.suggestion,
                requires_extraction=rule.requires_extraction,
            )
            for rule in rule_set.rules
        ]
        return RuleCatalog(
            ruleset_version=rule_set.version,
            rule_engine_version=RULE_ENGINE_VERSION,
            count=len(rules),
            red_count=sum(1 for rule in rules if rule.risk_level == "red"),
            yellow_count=sum(1 for rule in rules if rule.risk_level == "yellow"),
            rules=rules,
        )

    @app.post("/api/reviews", status_code=201, response_model=ReviewSummary)
    def create_review(
        request: Request,
        file: Annotated[UploadFile, File(description="合同文件（txt/md/pdf/docx）")],
        focus: Annotated[str, Form(description="审查重点（用户指令）")] = "",
        skill_id: Annotated[str, Form(description="选用的 Skill id（可空）")] = "",
        reference: Annotated[
            UploadFile | None, File(description="参考材料（txt/md，可选）")
        ] = None,
    ) -> ReviewSummary:
        filename = _safe_filename(file.filename)
        if not filename:
            raise HTTPException(status_code=400, detail="缺少文件名")
        suffix = Path(filename).suffix.casefold()
        if suffix == ".doc":
            raise HTTPException(
                status_code=400,
                detail="不支持旧版 .doc，请另存为 .docx 或 .txt/.md 后重新上传",
            )
        if suffix not in UPLOAD_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型 {suffix or '(无扩展名)'}；"
                "支持 .txt/.md/.pdf/.docx",
            )

        user = current_user(request)
        store = store_of(request)
        skill = store.resolve_skill(user.id if user is not None else None, skill_id or None)

        reference_name: str | None = None
        reference_text = ""
        if reference is not None and reference.filename:
            reference_name = _safe_filename(reference.filename)
            if Path(reference_name).suffix.casefold() not in REFERENCE_SUFFIXES:
                raise HTTPException(
                    status_code=400,
                    detail="参考材料只支持 .txt/.md；图片或扫描件请直接放进合同正文",
                )
            raw_reference = reference.file.read(MAX_REFERENCE_BYTES + 1)
            reference.file.close()
            if len(raw_reference) > MAX_REFERENCE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"参考材料超过 {MAX_REFERENCE_BYTES // 1024} KB 上限",
                )
            reference_text = raw_reference.decode("utf-8", errors="replace")

        review_id = uuid.uuid4().hex
        target_dir = upload_root / review_id
        target = target_dir / filename
        total = 0
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("wb") as handle:
                while True:
                    chunk = file.file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > limit_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"文件超过 {limit_bytes // (1024 * 1024)} MB 上限",
                        )
                    handle.write(chunk)
            if total == 0:
                raise HTTPException(status_code=400, detail="文件为空")
        except HTTPException:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise
        except OSError as exc:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail=f"文件保存失败：{exc}") from exc
        finally:
            file.file.close()

        composed = compose_focus(
            user_focus=focus,
            skill=skill,
            reference_name=reference_name,
            reference_text=reference_text,
        )
        run = _service_of(request).start(
            target,
            review_id=review_id,
            focus=composed,
            skill_id=skill.id if skill is not None else None,
            skill_name=skill.name if skill is not None else None,
            llm_runtime=llm_runtime_for(request),
        )
        record(request, run, user)
        return _summary_of(run)

    @app.get("/api/reviews/{review_id}", response_model=ReviewSummary)
    def get_review(
        request: Request,
        review_id: str = ApiPath(pattern=REVIEW_ID_PATTERN),
    ) -> ReviewSummary:
        user = authorize(request, review_id)
        run = _service_of(request).get(review_id)
        record(request, run, user)
        return _summary_of(run)

    @app.post("/api/reviews/{review_id}/decisions", response_model=ReviewSummary)
    def submit_decision(
        request: Request,
        decision: HitlDecision,
        review_id: str = ApiPath(pattern=REVIEW_ID_PATTERN),
    ) -> ReviewSummary:
        user = authorize(request, review_id)
        run = _service_of(request).resume(review_id, decision)
        record(request, run, user)
        return _summary_of(run)

    @app.get("/api/reviews/{review_id}/report")
    def get_report(
        request: Request,
        review_id: str = ApiPath(pattern=REVIEW_ID_PATTERN),
        format: Literal["json", "markdown"] = "json",
    ) -> Response:
        authorize(request, review_id)
        run = _service_of(request).get(review_id)
        report = run.report
        if report is None:
            raise HTTPException(
                status_code=409,
                detail="报告尚未生成：请先完成人工确认（或等待审查结束）",
            )
        if format == "markdown":
            content = render_report_markdown(report)
            return Response(
                content=content,
                media_type="text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="{review_id}-report.md"'
                },
            )
        return JSONResponse(content=report.model_dump(mode="json"))

    return app
