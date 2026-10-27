"""账号、审查记录、Skill 与自带模型配置（ADR-013）的接口测试。

约束：
- 口令与会话只落本地 SQLite，接口不回传哈希/盐/token；
- 模型 API Key 只进不出：响应只有 `has_key` 与尾号提示；
- 审查记录按账号隔离，跨账号读取必须是 404（不是 403，避免泄露存在性）。
"""

from __future__ import annotations

import sqlite3
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


# ---------------------------------------------------------------- 模型配置


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
