"""账号、审查记录、Skill 与自带模型配置（ADR-013）的接口测试。

约束：
- 口令与会话只落本地 SQLite，接口不回传哈希/盐/token；
- 模型 API Key 只进不出：响应只有 `has_key` 与尾号提示；
- 审查记录按账号隔离，跨账号读取必须是 404（不是 403，避免泄露存在性）。
"""

from __future__ import annotations

import io
import sqlite3
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.review_service import ReviewService
from app.services.accounts import AccountError, AccountsStore
from app.services.secret_box import SecretBoxError, decrypt, encrypt, load_or_create_master_key

CONTRACT = (
    "国际货物销售合同\n\n"
    "第一条 付款方式\n买方应在合同签订后 30 日内支付合同总价的 100% 预付款。\n\n"
    "第二条 争议解决\n因本合同引起的争议，双方可以提交仲裁，也可以向法院起诉。\n"
)


@pytest.fixture
def store(tmp_path: Path) -> AccountsStore:
    return AccountsStore(tmp_path / "app.sqlite", tmp_path / "secret.key")


@pytest.fixture
def client(tmp_path: Path, store: AccountsStore) -> Iterator[TestClient]:
    app = create_app(
        ReviewService.in_memory(),
        upload_dir=tmp_path / "uploads",
        accounts=store,
        user_db_path=tmp_path / "app.sqlite",
    )
    with TestClient(app) as test_client:
        yield test_client


def register(client: TestClient, email: str = "buyer@example.com") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "secret123", "display_name": "采购"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _skill_zip(files: dict[str, str]) -> bytes:
    """构造内存 zip：键为包内路径，值为 UTF-8 文本。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return buffer.getvalue()


# ---------------------------------------------------------------- 账号


def test_register_creates_session_and_hides_secrets(client: TestClient) -> None:
    body = register(client)
    assert body["authenticated"] is True
    assert body["user"]["email"] == "buyer@example.com"
    assert body["user"]["display_name"] == "采购"
    # 响应里不能出现口令相关字段
    assert "password" not in body["user"]
    assert "salt" not in body["user"]
    assert client.cookies.get("alex_session")

    me = client.get("/api/auth/me").json()
    assert me["authenticated"] is True
    assert me["user"]["id"] == body["user"]["id"]


def test_password_is_hashed_with_salt(store: AccountsStore) -> None:
    user, _token = store.register("buyer@example.com", "secret123")
    with sqlite3.connect(store._path) as connection:  # noqa: SLF001 - 测试需要看落库内容
        row = connection.execute(
            "SELECT password_hash, salt FROM users WHERE id = ?", (user.id,)
        ).fetchone()
    assert row is not None
    assert row[0] != "secret123"
    assert len(row[1]) == 32


def test_duplicate_email_conflicts(client: TestClient) -> None:
    register(client)
    response = client.post(
        "/api/auth/register", json={"email": "buyer@example.com", "password": "secret123"}
    )
    assert response.status_code == 409
    assert "已经注册" in response.json()["detail"]


def test_login_wrong_password_is_401(client: TestClient) -> None:
    register(client)
    response = client.post(
        "/api/auth/login", json={"email": "buyer@example.com", "password": "wrongpass"}
    )
    assert response.status_code == 401


def test_invalid_email_and_short_password_are_rejected(client: TestClient) -> None:
    bad_email = client.post(
        "/api/auth/register", json={"email": "not-an-email", "password": "secret123"}
    )
    assert bad_email.status_code == 400
    short = client.post(
        "/api/auth/register", json={"email": "a@example.com", "password": "1234567"}
    )
    assert short.status_code == 400
    assert "8 位" in short.json()["detail"]


def test_logout_revokes_session(client: TestClient) -> None:
    register(client)
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").json()["authenticated"] is False


# ---------------------------------------------------------------- Skill


def test_builtin_skills_are_available_without_login(client: TestClient) -> None:
    body = client.get("/api/skills").json()
    assert body["builtin_count"] >= 5
    names = {skill["name"] for skill in body["skills"]}
    assert {"全量体检", "付款与结算", "争议解决"} <= names
    assert all(skill["builtin"] for skill in body["skills"])


def test_user_can_create_and_delete_own_skill(client: TestClient) -> None:
    register(client)
    created = client.post(
        "/api/skills",
        json={
            "name": "信用证付款",
            "description": "看信用证节点",
            "instruction": "重点核对开证时间与最迟装运期",
        },
    )
    assert created.status_code == 201
    skill = created.json()
    assert skill["builtin"] is False
    assert skill["owner_id"]

    after = client.get("/api/skills").json()
    assert any(item["id"] == skill["id"] for item in after["skills"])
    assert not any(item["id"] == skill["id"] for item in after["skills"] if item["builtin"])

    assert client.delete(f"/api/skills/{skill['id']}").status_code == 204
    assert not any(
        item["id"] == skill["id"] for item in client.get("/api/skills").json()["skills"]
    )


def test_builtin_skill_cannot_be_deleted(client: TestClient) -> None:
    register(client)
    response = client.delete("/api/skills/builtin:full")
    assert response.status_code == 400
    assert "不能删除" in response.json()["detail"]


def test_skill_write_requires_login(client: TestClient) -> None:
    response = client.post(
        "/api/skills", json={"name": "x", "description": "", "instruction": "看付款"}
    )
    assert response.status_code == 401


def test_other_users_skill_is_not_visible(client: TestClient) -> None:
    register(client)
    created = client.post(
        "/api/skills", json={"name": "私有", "description": "", "instruction": "只看付款"}
    ).json()
    client.post("/api/auth/logout")
    register(client, "seller@example.com")
    ids = {item["id"] for item in client.get("/api/skills").json()["skills"]}
    assert created["id"] not in ids


def test_skill_can_be_edited_but_builtin_is_read_only(client: TestClient) -> None:
    """仓库页支持“查看并修改”：自建 Skill 用 PATCH，推荐 Skill 只读（可另存为我的）。"""
    register(client)
    skill = client.post(
        "/api/skills",
        json={"name": "旧名字", "description": "旧说明", "instruction": "看付款节点"},
    ).json()

    updated = client.patch(
        f"/api/skills/{skill['id']}",
        json={
            "name": "新名字",
            "description": "新说明",
            "instruction": "重点看预付款比例与交付期限是否挂钩",
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["id"] == skill["id"]
    assert body["name"] == "新名字"
    assert body["description"] == "新说明"
    assert "预付款比例" in body["instruction"]
    # 列表里同步更新（页面“使用”下拉也读同一份数据）
    listed = {item["id"]: item for item in client.get("/api/skills").json()["skills"]}
    assert listed[skill["id"]]["name"] == "新名字"

    builtin = client.patch(
        "/api/skills/builtin:full",
        json={"name": "改内置", "description": "", "instruction": "随便"},
    )
    assert builtin.status_code == 400
    assert "另存为" in builtin.json()["detail"]

    too_long = client.patch(
        f"/api/skills/{skill['id']}",
        json={"name": "字" * 41, "description": "", "instruction": "看付款"},
    )
    # Pydantic 的 max_length 先拦下（422），服务层还有同样的 400 兜底
    assert too_long.status_code == 422


def test_skill_tool_catalog_is_read_only_and_stable(client: TestClient) -> None:
    """Skill 能声明“调用哪些已实现的能力”，但目录只读、不能新增可执行代码。"""
    body = client.get("/api/skills/tools").json()
    tools = body["tools"]
    assert len(tools) >= 5
    ids = [tool["id"] for tool in tools]
    assert ids == [
        "rules_scan",
        "field_extract",
        "clause_split",
        "knowledge_lookup",
        "negotiation_hint",
    ]
    assert all(tool["name"] and tool["description"] and tool["effect"] for tool in tools)
    # 推荐 Skill 自带工具声明，方便用户理解“全量体检”到底做了什么
    full = next(
        item for item in client.get("/api/skills").json()["skills"] if item["id"] == "builtin:full"
    )
    assert full["tools"]
    assert set(full["tools"]) <= set(ids)


def test_skill_tools_and_assets_are_saved(client: TestClient) -> None:
    """Skill 不只是一段提示词：可勾选工具、附加 .py / .md 文本资料（只读、不执行）。"""
    register(client)
    created = client.post(
        "/api/skills",
        json={
            "name": "信用证 + 自查脚本",
            "description": "带检查清单",
            "instruction": "先看开证时间，再看最迟装运期",
            "tools": ["rules_scan", "negotiation_hint", "no_such_tool"],
            "assets": [
                {"name": "checks.py", "content": "EXPECTED = ['开证时间', '装运期']\n"},
                {"name": "notes.md", "content": "# 关注点\n- 信用证有效期要晚于装运期\n"},
            ],
        },
    )
    assert created.status_code == 201, created.text
    skill = created.json()
    # 未知工具被忽略（不报错，也不落库）
    assert skill["tools"] == ["rules_scan", "negotiation_hint"]
    assets = {asset["name"]: asset for asset in skill["assets"]}
    assert set(assets) == {"checks.py", "notes.md"}
    assert assets["checks.py"]["kind"] == "python"
    assert assets["notes.md"]["kind"] == "markdown"
    assert assets["checks.py"]["size"] == len("EXPECTED = ['开证时间', '装运期']\n")
    assert "EXPECTED" in assets["checks.py"]["content"]

    # 编辑后仍能改工具与附件
    updated = client.patch(
        f"/api/skills/{skill['id']}",
        json={
            "name": skill["name"],
            "description": skill["description"],
            "instruction": skill["instruction"],
            "tools": ["field_extract"],
            "assets": [{"name": "checklist.txt", "content": "1. 核对金额\n"}],
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["tools"] == ["field_extract"]
    assert [asset["name"] for asset in body["assets"]] == ["checklist.txt"]
    assert body["assets"][0]["kind"] == "markdown"


def test_skill_asset_validation(client: TestClient) -> None:
    """附件只收文本：后缀白名单、单条长度、数量上限都要拦住，且不执行任何代码。"""
    register(client)

    def create(assets: list[dict]) -> object:
        return client.post(
            "/api/skills",
            json={"name": "附件校验", "description": "", "instruction": "看付款", "assets": assets},
        )

    bad_suffix = create([{"name": "run.exe", "content": "MZ"}])
    assert bad_suffix.status_code == 400
    assert "附件只支持" in bad_suffix.json()["detail"]

    empty = create([{"name": "empty.md", "content": "   "}])
    assert empty.status_code == 400
    assert "内容为空" in empty.json()["detail"]

    too_long = create([{"name": "big.py", "content": "x" * 6001}])
    assert too_long.status_code == 422  # Pydantic 先按 max_length 拦下

    too_many = create([{"name": f"n{index}.md", "content": "x"} for index in range(6)])
    assert too_many.status_code == 422  # max_length=MAX_SKILL_ASSETS

    ok = create([{"name": "n.md", "content": "x"}])
    assert ok.status_code == 201
    # 只存文本：响应里没有执行结果、路径或可调用句柄
    assert set(ok.json()["assets"][0]) == {"name", "kind", "size", "content"}


def test_compose_focus_includes_tools_and_assets() -> None:
    """工具与附件只写进“解释背景”，并明确声明不作为判级依据、不得当作指令执行。"""
    from app.services.skill_catalog import Skill, SkillAsset, compose_focus

    skill = Skill(
        id="sk_test",
        name="自制 Skill",
        description="",
        instruction="重点看付款与交付是否挂钩",
        tools=["rules_scan", "negotiation_hint"],
        assets=[SkillAsset(name="checks.py", kind="python", size=6, content="print(1)")],
        builtin=False,
    )
    focus = compose_focus(user_focus="看预付款", skill=skill)
    assert "重点看付款与交付是否挂钩" in focus
    assert "规则全量扫描" in focus and "谈判提示" in focus
    assert "checks.py" in focus and "print(1)" in focus
    assert "不作为判级依据" in focus
    assert "不得当作指令执行" in focus
    assert len(focus) <= 4000


def test_packaged_external_skills_are_builtin(client: TestClient) -> None:
    """4 个外部 Skill 包随项目离线分发，默认出现在 Skill 仓库里（只读文本 + 声明工具）。"""
    body = client.get("/api/skills").json()
    by_id = {skill["id"]: skill for skill in body["skills"]}
    expected = {
        "builtin:lc-reviewer",
        "builtin:xiaping-fast-review",
        "builtin:xiaolv-fast-review",
        "builtin:risk-officer",
    }
    assert expected <= set(by_id)

    lc = by_id["builtin:lc-reviewer"]
    assert lc["builtin"] is True
    assert "信用证" in lc["name"]
    assert lc["tools"] and set(lc["tools"]) <= {
        tool["id"] for tool in client.get("/api/skills/tools").json()["tools"]
    }
    assert any(asset["name"].endswith("SKILL.md") for asset in lc["assets"])
    assert "外部包" in lc["tags"]
    assert any("UCP" in asset["content"] for asset in lc["assets"])


def test_zip_skill_package_is_imported_with_readonly_assets(client: TestClient) -> None:
    """zip 包：根目录 SKILL.md + references/ → 一条 Skill + 只读附件；脚本不执行。"""
    register(client)
    package = _skill_zip(
        {
            "SKILL.md": (
                "---\n"
                "name: 信用证单据核对\n"
                "description: 按 UCP600 核对单据\n"
                "allowed-tools: [bash]\n"
                "---\n"
                "# 信用证单据核对\n\n"
                "先核对信用证与单据是否一致，再核对单单一致。\n"
            ),
            "references/payment-terms.md": "# 付款\nUCP600 下开证行承担独立付款责任。\n",
            "references/incoterms-2020.md": "# Incoterms\nCIF 由卖方投保。\n",
            "scripts/check.py": "raise SystemExit('这个脚本绝不能被执行')\n",
            "notes.txt": "备注：只读文本\n",
        }
    )
    response = client.post(
        "/api/skills/import",
        files={"file": ("skill.zip", package, "application/zip")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    skill = body["skill"]
    assert skill["name"] == "信用证单据核对"
    assert skill["builtin"] is False
    assert "信用证与单据" in skill["instruction"]
    assets = {asset["name"]: asset for asset in skill["assets"]}
    assert "references/payment-terms.md" in assets
    assert "scripts/check.py" in assets
    assert assets["scripts/check.py"]["kind"] == "python"
    # 脚本只被当作文本存着，进程没有退出
    assert "绝不能被执行" in assets["scripts/check.py"]["content"]
    # 包内 allowed-tools 不映射为项目能力，只给提示
    assert skill["tools"] == []
    assert any("allowed-tools" in warning for warning in body["warnings"])
    assert body["files"] == 5


def test_zip_skill_package_rejects_missing_skill_md(client: TestClient) -> None:
    register(client)
    response = client.post(
        "/api/skills/import",
        files={"file": ("skill.zip", _skill_zip({"references/a.md": "# A\n"}), "application/zip")},
    )
    assert response.status_code == 400
    assert "SKILL.md" in response.json()["detail"]


def test_zip_skill_import_requires_login(client: TestClient) -> None:
    response = client.post(
        "/api/skills/import",
        files={
            "file": (
                "skill.zip",
                _skill_zip({"SKILL.md": "# 标题\n审查付款\n"}),
                "application/zip",
            )
        },
    )
    assert response.status_code == 401


def test_skill_edit_is_scoped_to_owner(client: TestClient) -> None:
    register(client)
    skill = client.post(
        "/api/skills", json={"name": "私有", "description": "", "instruction": "只看付款"}
    ).json()
    client.post("/api/auth/logout")
    register(client, "seller@example.com")
    response = client.patch(
        f"/api/skills/{skill['id']}",
        json={"name": "抢过来", "description": "", "instruction": "改掉"},
    )
    assert response.status_code == 404


def test_skill_edit_requires_login(client: TestClient) -> None:
    response = client.patch(
        "/api/skills/sk_missing",
        json={"name": "x", "description": "", "instruction": "看付款"},
    )
    assert response.status_code == 401


def test_profile_updates_display_name_and_avatar(client: TestClient) -> None:
    """个人账户弹窗：昵称与头像走 PATCH /api/auth/profile，头像只回 data URL。"""
    account = register(client)
    user_id = account["user"]["id"]

    renamed = client.patch("/api/auth/profile", json={"display_name": "  张三  "})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["display_name"] == "张三"
    assert renamed.json()["id"] == user_id
    assert "password" not in renamed.json()

    avatar = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="
    with_avatar = client.patch("/api/auth/profile", json={"avatar": avatar})
    assert with_avatar.status_code == 200
    assert with_avatar.json()["avatar"] == avatar
    # /api/auth/me 也要带上，页面刷新后仍显示头像
    assert client.get("/api/auth/me").json()["user"]["avatar"] == avatar

    removed = client.patch("/api/auth/profile", json={"avatar": ""})
    assert removed.status_code == 200
    assert removed.json()["avatar"] == ""


def test_profile_rejects_bad_input(client: TestClient) -> None:
    register(client)
    assert client.patch("/api/auth/profile", json={"display_name": "  "}).status_code == 400
    # 超长昵称先被 Pydantic 的 max_length 拦下（422）
    assert client.patch("/api/auth/profile", json={"display_name": "字" * 41}).status_code == 422
    bad_avatar = client.patch("/api/auth/profile", json={"avatar": "https://example.com/a.png"})
    assert bad_avatar.status_code == 400
    # extra="forbid"：只允许昵称与头像，避免夹带邮箱/口令
    assert client.patch("/api/auth/profile", json={"email": "x@y.com"}).status_code == 422
    client.post("/api/auth/logout")
    assert client.patch("/api/auth/profile", json={"display_name": "x"}).status_code == 401


def test_legacy_users_table_gets_avatar_column(tmp_path: Path) -> None:
    """老库没有 avatar 列时自动 ALTER，不用删库重建。"""
    db_path = tmp_path / "legacy.sqlite"
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE users ("
        "id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL, "
        "password_hash TEXT NOT NULL, salt TEXT NOT NULL, created_at TEXT NOT NULL)"
    )
    connection.commit()
    connection.close()

    store = AccountsStore(db_path, tmp_path / "secret.key")
    user, _ = store.register("old@example.com", "secret123", "老用户")
    assert user.avatar == ""
    assert store.update_profile(user.id, avatar="data:image/png;base64,AAAA").avatar


# ---------------------------------------------------------------- 模型配置


def test_provider_catalog_covers_major_vendors(client: TestClient) -> None:
    """厂商目录扩容后仍只给“默认值”，不暴露 Key；用户可自由改地址与模型。"""
    providers = client.get("/api/llm/providers").json()["providers"]
    ids = {item["id"] for item in providers}
    assert {
        "openai",
        "deepseek",
        "moonshot",
        "zhipu",
        "dashscope",
        "siliconflow",
        "openrouter",
        "gemini",
        "xai",
        "groq",
        "mistral",
        "together",
        "volcano",
        "qianfan",
        "hunyuan",
        "minimax",
        "stepfun",
        "lmstudio",
        "ollama",
        "custom",
    } <= ids
    assert len(providers) >= 20
    by_id = {item["id"]: item for item in providers}
    assert by_id["volcano"]["base_url"].endswith("/api/v3")
    assert by_id["gemini"]["base_url"].endswith("/v1beta/openai")
    assert by_id["lmstudio"]["key_optional"] is True
    # 自定义端点同样允许不填 Key（部分内网代理不需要）
    assert by_id["custom"]["key_optional"] is True


def test_provider_catalog_has_no_secrets(client: TestClient) -> None:
    providers = client.get("/api/llm/providers").json()["providers"]
    ids = {item["id"] for item in providers}
    assert {"openai", "deepseek", "ollama", "custom"} <= ids
    for item in providers:
        assert "api_key" not in item
        assert not any("key" in field for field in item if field != "key_optional")


def test_llm_key_is_encrypted_and_never_returned(client: TestClient, store: AccountsStore) -> None:
    register(client)
    response = client.put(
        "/api/llm",
        json={
            "provider": "deepseek",
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "api_key": "sk-test-1234567890",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["has_key"] is True
    assert body["key_hint"].endswith("7890")
    assert "sk-test-1234567890" not in response.text

    with sqlite3.connect(store._path) as connection:  # noqa: SLF001
        row = connection.execute("SELECT api_key_cipher FROM llm_configs").fetchone()
    assert row is not None
    assert "sk-test-1234567890" not in row[0]
    assert row[0].startswith("v1:")

    # 读取配置同样不回传明文
    read = client.get("/api/llm")
    assert read.status_code == 200
    assert "sk-test-1234567890" not in read.text


def test_saved_key_can_be_reused_and_cleared(client: TestClient) -> None:
    register(client)
    client.put(
        "/api/llm",
        json={
            "provider": "openai",
            "base_url": "",
            "model": "gpt-4.1-mini",
            "api_key": "sk-abcdefghijkl",
        },
    )
    # Key 留空表示沿用已保存的 Key
    again = client.put(
        "/api/llm",
        json={"provider": "openai", "base_url": "", "model": "gpt-4o-mini", "api_key": ""},
    )
    assert again.status_code == 200
    assert again.json()["model"] == "gpt-4o-mini"
    assert again.json()["has_key"] is True

    assert client.delete("/api/llm").status_code == 204
    assert client.get("/api/llm").json() is None


def test_missing_key_for_hosted_provider_is_rejected(client: TestClient) -> None:
    register(client)
    response = client.put(
        "/api/llm",
        json={"provider": "openai", "base_url": "", "model": "gpt-4.1-mini", "api_key": ""},
    )
    assert response.status_code == 400
    assert "API Key" in response.json()["detail"]


def test_local_provider_allows_empty_key(store: AccountsStore) -> None:
    user, _ = store.register("local@example.com", "secret123")
    saved = store.save_llm_settings(
        user.id, provider="ollama", base_url="http://localhost:11434/v1", model="qwen2.5"
    )
    assert saved.has_key is False
    runtime = store.resolve_llm_runtime(user.id)
    assert runtime is not None
    # 本地推理服务不需要真 Key，但 SDK 需要一个非空占位符
    assert runtime.api_key == "EMPTY"


def test_invalid_base_url_is_rejected(client: TestClient) -> None:
    register(client)
    response = client.put(
        "/api/llm",
        json={"provider": "custom", "base_url": "ftp://x", "model": "m", "api_key": ""},
    )
    assert response.status_code == 400


def test_rotated_master_key_reports_actionable_error(store: AccountsStore, tmp_path: Path) -> None:
    user, _ = store.register("rot@example.com", "secret123")
    store.save_llm_settings(
        user.id, provider="openai", model="gpt-4.1-mini", api_key="sk-rotate-1234"
    )
    with pytest.raises(AccountError) as error:
        AccountsStore(tmp_path / "app.sqlite", tmp_path / "other.key").resolve_llm_runtime(user.id)
    assert "重新填写" in str(error.value)


# ---------------------------------------------------------------- 审查记录


def test_review_is_recorded_for_logged_in_user(client: TestClient) -> None:
    register(client)
    created = client.post(
        "/api/reviews",
        files={"file": ("contract.txt", CONTRACT.encode("utf-8"), "text/plain")},
        data={"focus": "重点看预付款", "skill_id": "builtin:payment"},
    )
    assert created.status_code == 201, created.text
    review_id = created.json()["review_id"]

    history = client.get("/api/reviews").json()
    assert history["total"] == 1
    record = history["reviews"][0]
    assert record["review_id"] == review_id
    assert record["source_filename"] == "contract.txt"
    assert record["skill_name"] == "付款与结算"
    assert "预付款" in (record["focus"] or "")


def test_history_requires_login(client: TestClient) -> None:
    assert client.get("/api/reviews").status_code == 401


def _record_one(client: TestClient) -> str:
    created = client.post(
        "/api/reviews",
        files={"file": ("contract.txt", CONTRACT.encode("utf-8"), "text/plain")},
    )
    assert created.status_code == 201, created.text
    return created.json()["review_id"]


def test_review_record_can_be_renamed_and_pinned(client: TestClient) -> None:
    """历史列表支持改标签名与置顶；置顶排在最前，改名不影响等级。"""
    register(client)
    first = _record_one(client)
    second = _record_one(client)

    renamed = client.patch(f"/api/reviews/{first}", json={"title": "  亚洲客户·2026  "})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["title"] == "亚洲客户·2026"

    pinned = client.patch(f"/api/reviews/{first}", json={"pinned": True})
    assert pinned.status_code == 200
    assert pinned.json()["pinned"] is True

    listed = client.get("/api/reviews").json()["reviews"]
    assert [item["review_id"] for item in listed] == [first, second]
    assert listed[0]["title"] == "亚洲客户·2026"

    # 传空标签 = 恢复显示文件名
    cleared = client.patch(f"/api/reviews/{first}", json={"title": ""})
    assert cleared.json()["title"] is None

    # 改名/置顶不改等级：记录里的等级仍来自规则（停待确认时是 unknown）
    assert listed[0]["overall_level"] in {"red", "yellow", "green", "unknown"}


def test_review_record_can_be_deleted_and_then_is_missing(client: TestClient) -> None:
    register(client)
    review_id = _record_one(client)
    assert client.get(f"/api/reviews/{review_id}").status_code == 200

    removed = client.delete(f"/api/reviews/{review_id}")
    assert removed.status_code == 204
    assert client.get("/api/reviews").json()["total"] == 0
    assert client.get(f"/api/reviews/{review_id}").status_code == 404


def test_record_edit_and_delete_are_scoped_to_owner(client: TestClient) -> None:
    register(client)
    review_id = _record_one(client)
    client.post("/api/auth/logout")
    register(client, "seller@example.com")

    assert client.patch(f"/api/reviews/{review_id}", json={"pinned": True}).status_code == 404
    assert client.delete(f"/api/reviews/{review_id}").status_code == 404


def test_history_edit_requires_login(client: TestClient) -> None:
    assert client.patch("/api/reviews/r-1", json={"pinned": True}).status_code == 401
    assert client.delete("/api/reviews/r-1").status_code == 401


def test_clearing_history_is_single_request_and_scoped_to_owner(client: TestClient) -> None:
    """清空审查记录：一次 DELETE /api/reviews 只删本账号，另一账号的记录保持不动。"""
    register(client)
    _record_one(client)
    _record_one(client)
    client.post("/api/auth/logout")

    register(client, "seller@example.com")
    other = _record_one(client)

    # 未登录不能清空
    client.post("/api/auth/logout")
    assert client.delete("/api/reviews").status_code == 401

    # 回到 buyer 账号清空：只删自己的 2 条
    login = client.post(
        "/api/auth/login",
        json={"email": "buyer@example.com", "password": "secret123"},
    )
    assert login.status_code == 200, login.text
    cleared = client.delete("/api/reviews")
    assert cleared.status_code == 200, cleared.text
    assert cleared.json() == {"deleted": 2}
    assert client.get("/api/reviews").json()["total"] == 0

    # 另一个账号的记录仍在，且仍能按 id 读到
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/login",
        json={"email": "seller@example.com", "password": "secret123"},
    )
    assert client.get("/api/reviews").json()["total"] == 1
    assert client.get(f"/api/reviews/{other}").status_code == 200

    # 再清一次是幂等的：返回 0，不报错
    assert client.delete("/api/reviews").json() == {"deleted": 1}


def test_other_account_cannot_read_review(client: TestClient) -> None:
    register(client)
    review_id = client.post(
        "/api/reviews",
        files={"file": ("c.txt", CONTRACT.encode("utf-8"), "text/plain")},
    ).json()["review_id"]
    client.post("/api/auth/logout")
    register(client, "seller@example.com")
    assert client.get(f"/api/reviews/{review_id}").status_code == 404
    assert client.get("/api/reviews").json()["total"] == 0


def test_anonymous_review_is_not_recorded(client: TestClient) -> None:
    created = client.post(
        "/api/reviews",
        files={"file": ("c.txt", CONTRACT.encode("utf-8"), "text/plain")},
    )
    assert created.status_code == 201
    register(client)
    assert client.get("/api/reviews").json()["total"] == 0


def test_focus_and_skill_reach_the_report(client: TestClient) -> None:
    register(client)
    body = client.post(
        "/api/reviews",
        files={"file": ("c.txt", CONTRACT.encode("utf-8"), "text/plain")},
        data={"focus": "先讲收款保障", "skill_id": "builtin:seller"},
    ).json()
    assert body["skill_name"] == "卖方视角"
    report = body["report"]
    if report is not None:
        assert report["skill"] == "卖方视角"
        assert "先讲收款保障" in (report["focus"] or "")


# ---------------------------------------------------------------- 密文盒


def test_secret_box_roundtrip_and_tamper_detection(tmp_path: Path) -> None:
    key = load_or_create_master_key(tmp_path / "k.key")
    token = encrypt("sk-abc", key)
    assert token.startswith("v1:")
    assert decrypt(token, key) == "sk-abc"

    tampered = token[:-4] + ("AAAA" if token[-4:] != "AAAA" else "BBBB")
    with pytest.raises(SecretBoxError):
        decrypt(tampered, key)

    other = load_or_create_master_key(tmp_path / "k2.key")
    with pytest.raises(SecretBoxError):
        decrypt(token, other)
