"""FastAPI 接口测试：上传 → 暂停 → 人工决定 → 下载报告，以及错误码。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.review_service import ReviewService
from tests.conftest import SAMPLES


@pytest.fixture
def upload_dir(tmp_path: Path) -> Path:
    return tmp_path / "uploads"


@pytest.fixture
def client(upload_dir: Path) -> Iterator[TestClient]:
    app = create_app(ReviewService.in_memory(), upload_dir=upload_dir)
    with TestClient(app) as test_client:
        yield test_client


def _upload(client: TestClient, name: str = "contract.txt", content: bytes | None = None):
    if content is None:
        content = (SAMPLES / "sample_sales_contract.txt").read_bytes()
    return client.post("/api/reviews", files={"file": (name, content, "text/plain")})


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checkpoint_backend"] == "memory"
    assert "rag_enabled" in body


def test_upload_pauses_for_human(client: TestClient, upload_dir: Path) -> None:
    response = _upload(client)
    assert response.status_code == 201
    body = response.json()
    assert body["awaiting_human"] is True
    assert body["status"] == "running"
    assert body["report"] is None
    assert body["approval"]["findings_total"] >= 1
    assert body["approval"]["review_id"] == body["review_id"]

    # 文件落在 uploads/<review_id>/<basename>，不越界
    saved = upload_dir / body["review_id"] / "contract.txt"
    assert saved.is_file()
    assert not (upload_dir / "sample_sales_contract.txt").exists()

    fetched = client.get(f"/api/reviews/{body['review_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["awaiting_human"] is True


def test_approve_then_download_report(client: TestClient) -> None:
    created = _upload(client).json()
    review_id = created["review_id"]

    approved = client.post(
        f"/api/reviews/{review_id}/decisions",
        json={"action": "approve", "reviewer": "alice", "comment": "已核对"},
    )
    assert approved.status_code == 200
    body = approved.json()
    assert body["status"] == "approved"
    assert body["awaiting_human"] is False
    assert body["report"]["status"] == "approved"

    as_json = client.get(f"/api/reviews/{review_id}/report?format=json")
    assert as_json.status_code == 200
    assert as_json.json()["review_id"] == review_id

    as_markdown = client.get(f"/api/reviews/{review_id}/report?format=markdown")
    assert as_markdown.status_code == 200
    assert as_markdown.text.startswith("# 合同审查报告")
    assert "attachment" in as_markdown.headers["content-disposition"]

    # 幂等：终态后再提交拒绝，不重跑图、不改状态
    again = client.post(
        f"/api/reviews/{review_id}/decisions",
        json={"action": "reject", "reviewer": "bob"},
    )
    assert again.status_code == 200
    assert again.json()["status"] == "approved"


def test_non_contract_upload_is_not_reviewed(client: TestClient) -> None:
    """论文/法规等材料：返回可解释的未执行结果，而不是当作合同判级。"""
    paper = (
        "全球比较下的我国人工智能立法\n\n摘要：本文认为，人工智能立法应当兼顾创新与安全。\n"
        "关键词：人工智能；立法；比较法\n\n一、问题的提出\n"
        "本研究采用比较法的方法，梳理欧盟、美国与我国的立法经验。本文提出三层治理框架。\n"
        "参考文献\n[1] 丁晓东. 人工智能与法学研究[J]. 法学研究, 2022.\n"
    ).encode()
    response = _upload(client, "paper.md", paper)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "not_contract"
    assert body["awaiting_human"] is False
    assert body["approval"] is None
    assert body["document_check"]["is_contract"] is False
    assert body["document_check"]["reasons"]
    assert body["document_check"]["hints"]
    assert body["report"]["status"] == "not_contract"
    assert body["report"]["findings"] == []

    # 报告可以下载，但内容明确写“未执行审查”
    markdown = client.get(f"/api/reviews/{body['review_id']}/report?format=markdown")
    assert markdown.status_code == 200
    assert "未执行审查" in markdown.text


def test_report_before_decision_is_conflict(client: TestClient) -> None:
    review_id = _upload(client).json()["review_id"]
    response = client.get(f"/api/reviews/{review_id}/report?format=json")
    assert response.status_code == 409
    assert "报告尚未生成" in response.json()["detail"]


def test_clean_contract_fast_path_and_idempotent_decision(client: TestClient) -> None:
    content = (SAMPLES / "sample_clean_contract.txt").read_bytes()
    created = _upload(client, name="clean.txt", content=content).json()
    assert created["awaiting_human"] is False
    assert created["report"]["status"] == "completed"

    # 快速通道已结束，无需人工确认；再次提交决定是幂等的，不改变状态
    again = client.post(
        f"/api/reviews/{created['review_id']}/decisions",
        json={"action": "approve", "reviewer": "alice"},
    )
    assert again.status_code == 200
    assert again.json()["status"] == "completed"


def test_unknown_review_returns_404(client: TestClient) -> None:
    assert client.get("/api/reviews/doesnotexist").status_code == 404
    assert (
        client.post(
            "/api/reviews/doesnotexist/decisions",
            json={"action": "approve", "reviewer": "alice"},
        ).status_code
        == 404
    )
    assert client.get("/api/reviews/doesnotexist/report").status_code == 404


def test_invalid_review_id_is_rejected(client: TestClient) -> None:
    assert client.get("/api/reviews/bad id").status_code == 422


@pytest.mark.parametrize(
    ("name", "detail"),
    [
        ("legacy.doc", "旧版 .doc"),
        ("scan.pdf.exe", "不支持的文件类型"),
        ("no_extension", "不支持的文件类型"),
    ],
)
def test_bad_suffix_rejected(client: TestClient, name: str, detail: str) -> None:
    response = _upload(client, name=name)
    assert response.status_code == 400
    assert detail in response.json()["detail"]


def test_empty_file_rejected(client: TestClient) -> None:
    response = _upload(client, content=b"")
    assert response.status_code == 400
    assert "为空" in response.json()["detail"]


def test_filename_is_sanitised(client: TestClient, upload_dir: Path) -> None:
    response = _upload(client, name="..\\..\\evil.txt")
    assert response.status_code == 201
    review_id = response.json()["review_id"]
    saved = list((upload_dir / review_id).iterdir())
    assert [item.name for item in saved] == ["evil.txt"]


def test_upload_size_limit(upload_dir: Path) -> None:
    app = create_app(ReviewService.in_memory(), upload_dir=upload_dir, max_upload_mb=0)
    with TestClient(app) as client:
        response = _upload(client)
    assert response.status_code == 413


def test_invalid_decision_payload_is_422(client: TestClient) -> None:
    review_id = _upload(client).json()["review_id"]
    response = client.post(
        f"/api/reviews/{review_id}/decisions",
        json={"action": "maybe", "reviewer": "alice"},
    )
    assert response.status_code == 422


def test_decision_requires_reviewer(client: TestClient) -> None:
    review_id = _upload(client).json()["review_id"]
    response = client.post(
        f"/api/reviews/{review_id}/decisions",
        json={"action": "approve", "reviewer": ""},
    )
    assert response.status_code == 422


def test_rule_catalog_matches_definitions(client: TestClient) -> None:
    """前端规则集页的数据源：只暴露目录信息，不暴露正则/DSL 判定细节。"""
    response = client.get("/api/rules")
    assert response.status_code == 200
    body = response.json()

    assert body["ruleset_version"] == 10
    assert body["count"] == 13
    assert body["red_count"] == 5
    assert body["yellow_count"] == 8
    assert body["rule_engine_version"]
    assert {rule["rule_id"] for rule in body["rules"]} == {
        "R-TRD-001",
        "R-PAY-001",
        "R-PAY-002",
        "R-DLV-001",
        "R-INP-001",
        "R-DIS-001",
        "R-DIS-002",
        "R-DIS-003",
        "R-DIS-004",
        "R-INS-001",
        "R-INC-001",
        "R-INC-002",
        "R-INP-002",
    }
    for rule in body["rules"]:
        assert rule["risk_level"] in {"red", "yellow"}
        assert rule["title"] and rule["reason"] and rule["suggestion"]
        assert "condition" not in rule and "source" not in rule
