"""处理过程事件流的测试：节点级事件、客户端 review_id、轮询端点（ADR-017）。

约束：过程事件只描述“做了什么”，不含任何风险等级；过程丢了不影响结论。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.review_service import ReviewService
from app.services.accounts import AccountsStore
from app.services.progress import ProgressStore, progress_store
from tests.conftest import SAMPLES


@pytest.fixture
def store(tmp_path: Path) -> AccountsStore:
    return AccountsStore(tmp_path / "app.sqlite", tmp_path / "secret.key")


@pytest.fixture
def client(tmp_path: Path, store: AccountsStore) -> Iterator[TestClient]:
    # 删除历史记录需要登录（ADR-013），这里带上账号库，否则 DELETE 会 401
    app = create_app(
        ReviewService.in_memory(),
        upload_dir=tmp_path / "uploads",
        accounts=store,
        user_db_path=tmp_path / "app.sqlite",
    )
    with TestClient(app) as test_client:
        yield test_client


def _upload(client: TestClient, review_id: str = ""):
    content = (SAMPLES / "sample_sales_contract.txt").read_bytes()
    data = {"focus": "", "skill_id": "builtin:full"}
    if review_id:
        data["review_id"] = review_id
    return client.post(
        "/api/reviews",
        files={"file": ("contract.txt", content, "text/plain")},
        data=data,
    )


def test_store_records_begin_and_finish() -> None:
    store = ProgressStore()
    store.begin("r1", "ingest_document")
    assert store.any_running("r1") is True
    store.finish("r1", "ingest_document", detail="3 页 · 1234 字符")
    events = store.events("r1")

    assert len(events) == 1
    event = events[0]
    assert event["label"] == "读取文件"
    assert event["status"] == "done"
    assert event["detail"] == "3 页 · 1234 字符"
    assert event["duration_ms"] >= 0
    assert "_started" not in event
    assert "risk_level" not in event
    assert store.any_running("r1") is False

    store.clear("r1")
    assert store.events("r1") == []


def test_store_marks_interrupt_as_waiting() -> None:
    store = ProgressStore()
    store.begin("r2", "human_review")
    store.finish("r2", "human_review", status="waiting", detail="等待人工确认")
    [event] = store.events("r2")
    assert event["status"] == "waiting"
    assert store.any_running("r2") is False


def test_progress_endpoint_lists_nodes(client: TestClient) -> None:
    review_id = "progress-endpoint-1"
    progress_store().clear(review_id)
    created = _upload(client, review_id)
    assert created.status_code == 201
    assert created.json()["review_id"] == review_id

    response = client.get(f"/api/reviews/{review_id}/progress")
    assert response.status_code == 200
    body = response.json()
    assert body["review_id"] == review_id
    assert body["running"] is False  # 已停在人工确认，没有节点在跑
    labels = [event["label"] for event in body["events"]]
    assert "读取文件" in labels
    assert "切分条款" in labels
    assert "人工确认" in labels
    assert all("risk_level" not in event for event in body["events"])
    progress_store().clear(review_id)


def test_client_review_id_must_be_safe(client: TestClient) -> None:
    response = _upload(client, "bad id!")
    assert response.status_code == 400
    assert "review_id" in response.json()["detail"]


def test_duplicate_client_review_id_is_rejected(client: TestClient) -> None:
    review_id = "progress-duplicate-1"
    progress_store().clear(review_id)
    first = _upload(client, review_id)
    assert first.status_code == 201
    again = _upload(client, review_id)
    assert again.status_code == 409
    assert review_id in again.json()["detail"]
    progress_store().clear(review_id)


def test_progress_is_cleared_with_review(client: TestClient) -> None:
    review_id = "progress-cleared-1"
    progress_store().clear(review_id)
    client.post(
        "/api/auth/register",
        json={"email": "progress@example.com", "password": "secret123"},
    )
    assert _upload(client, review_id).status_code == 201
    assert progress_store().events(review_id)

    # 删除历史记录时同一份过程表也要清掉，避免 id 复用后读到旧步骤
    assert client.delete(f"/api/reviews/{review_id}").status_code == 204
    assert progress_store().events(review_id) == []
