"""逐条审查与修订稿导出：条款聚合、示例条款、DOCX/PDF 字节与接口鉴权。

约束（ADR-003 / ADR-013）：
- 条款等级只沿用规则结果（red/yellow/pass），这里不做任何重新判级；
- 修订文本是示例条款（带 `___` 占位），导出文件必须同时带审查意见与免责声明；
- 待人工确认时也能预览逐条意见，但报告仍要等确认后才生成。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.review_service import ReviewService
from app.schemas import (
    Clause,
    ContractReviewState,
    Evidence,
    ExplanationResult,
    RuleEvaluation,
)
from app.services.clause_export import ExportError, export_clause_review
from app.services.clause_review import (
    REVISION_NOTE,
    REVISION_TEMPLATES,
    build_clause_reviews,
)
from tests.conftest import SAMPLES

# --------------------------------------------------------------- 纯服务层


def _state() -> ContractReviewState:
    """两条条款：c1 命中红色 + 一条黄色，c2 只命中黄色；另有一条合同级问题。"""
    return ContractReviewState(
        review_id="rv-0001",
        source_filename="sales-contract.txt",
        status="approved",
        overall_level="red",
        extraction_status="ok",
        clauses=[
            Clause(
                clause_id="c1",
                title="2. Price and Payment",
                text="Payment shall be made by T/T as 100% advance payment.",
                page=1,
            ),
            Clause(
                clause_id="c2",
                title="3. Delivery",
                text="Shipment shall be effected within 45 days after receipt.",
                page=2,
            ),
            Clause(
                clause_id="c3",
                title="4. Notices",
                text="All notices shall be in writing.",
                page=2,
            ),
        ],
        rule_evaluations=[
            RuleEvaluation(
                rule_id="R-PAY-001",
                title="全额预付导致收款风险",
                risk_level="red",
                reason="约定 100% 预付，买方违约时卖方无收款保障。",
                suggestion="改为 30% 预付 + 70% 见提单副本付款。",
                clause_ids=["c1"],
                evidence=[
                    Evidence(
                        quote="100% advance payment",
                        start=12,
                        end=32,
                        page=1,
                        clause_id="c1",
                        grounded=True,
                    )
                ],
                requires_human=True,
            ),
            RuleEvaluation(
                rule_id="R-PAY-002",
                title="付款方式未明确",
                risk_level="yellow",
                reason="未写电汇路径与逾期利息。",
                clause_ids=["c1"],
            ),
            RuleEvaluation(
                rule_id="R-DLV-001",
                title="交付期未与付款节点挂钩",
                risk_level="yellow",
                reason="装运期以收到预付款起算，未限定最迟装运日。",
                clause_ids=["c2"],
            ),
            RuleEvaluation(
                rule_id="R-INP-001",
                title="检验标准缺失",
                risk_level="pass",
                reason="未触发。",
                clause_ids=["c2"],
            ),
            RuleEvaluation(
                rule_id="R-TRD-001",
                title="贸易术语版本缺失",
                risk_level="pass",
                reason="抽取不可用，跳过。",
                clause_ids=["c1"],
                skipped=True,
            ),
            RuleEvaluation(
                rule_id="R-DIS-001",
                title="未约定适用法律",
                risk_level="red",
                reason="全文没有适用法律条款。",
                clause_ids=[],
            ),
        ],
        explanations=[
            ExplanationResult(
                rule_id="R-PAY-001",
                summary="全额预付把资金风险全部转移给买方，卖方可要求分批付款。",
                quote="100% advance payment",
                citation="sales-contract.txt:p1:12-32",
                grounded=True,
                source="llm",
                knowledge_citations=["《联合国国际货物销售合同公约》第 53 条"],
            )
        ],
    )


def test_clauses_are_grouped_without_rejudging() -> None:
    view = build_clause_reviews(_state())

    assert [clause.index for clause in view.clauses] == [1, 2, 3]
    by_id = {clause.clause_id: clause for clause in view.clauses}

    # c1：红色优先；同一条款的两条规则都保留
    assert by_id["c1"].risk_level == "red"
    assert [finding.rule_id for finding in by_id["c1"].findings] == [
        "R-PAY-001",
        "R-PAY-002",
    ]
    red = by_id["c1"].findings[0]
    assert red.risk_level == "red"
    assert red.quotes == ["100% advance payment"]
    assert red.explanation_summary.startswith("全额预付")
    assert red.knowledge_citations == ["《联合国国际货物销售合同公约》第 53 条"]

    # c2：只有黄色；pass 的规则不进入视图，skipped 更不进入
    assert by_id["c2"].risk_level == "yellow"
    assert [finding.rule_id for finding in by_id["c2"].findings] == ["R-DLV-001"]

    # c3：没有命中 → pass，且没有可套用的修订文本
    assert by_id["c3"].risk_level == "pass"
    assert by_id["c3"].findings == []
    assert by_id["c3"].revised_text is None


def test_findings_are_displayed_red_before_yellow() -> None:
    """展示顺序统一“红在前、黄在后”，输入顺序反过来也一样（等级本身不变）。"""
    state = _state()
    # 把黄色规则排到红色之前
    state.rule_evaluations[0], state.rule_evaluations[1] = (
        state.rule_evaluations[1],
        state.rule_evaluations[0],
    )
    clause = next(
        item for item in build_clause_reviews(state).clauses if item.clause_id == "c1"
    )
    assert [finding.rule_id for finding in clause.findings] == [
        "R-PAY-001",
        "R-PAY-002",
    ]
    assert [finding.risk_level for finding in clause.findings] == ["red", "yellow"]


def test_revision_templates_are_red_first_and_deduplicated() -> None:
    state = _state()
    view = build_clause_reviews(state)
    by_id = {clause.clause_id: clause for clause in view.clauses}

    expected = "\n\n".join(
        [REVISION_TEMPLATES["R-PAY-001"], REVISION_TEMPLATES["R-PAY-002"]]
    )
    assert by_id["c1"].revised_text == expected
    assert by_id["c1"].revision_note == REVISION_NOTE
    # 黄色规则单独也生成示例条款
    assert by_id["c2"].revised_text == REVISION_TEMPLATES["R-DLV-001"]

    # 同一条规则命中两条条款：每条都能看到，但同一份修订文本不重复拼接
    dup = _state()
    dup.rule_evaluations[0] = dup.rule_evaluations[0].model_copy(
        update={"clause_ids": ["c1", "c2"]}
    )
    dup_view = build_clause_reviews(dup)
    dup_by_id = {clause.clause_id: clause for clause in dup_view.clauses}
    assert [finding.rule_id for finding in dup_by_id["c2"].findings] == [
        "R-PAY-001",
        "R-DLV-001",
    ]
    assert dup_by_id["c2"].revised_text == "\n\n".join(
        [REVISION_TEMPLATES["R-PAY-001"], REVISION_TEMPLATES["R-DLV-001"]]
    )

    # 同一条规则出现两次（重跑/合并）：意见都保留，但示例条款只拼一次
    twice = _state()
    twice.rule_evaluations.append(twice.rule_evaluations[0].model_copy())
    twice_view = build_clause_reviews(twice)
    clause1 = next(clause for clause in twice_view.clauses if clause.clause_id == "c1")
    assert len(clause1.findings) == 3
    assert clause1.revised_text.count(REVISION_TEMPLATES["R-PAY-001"]) == 1


def test_contract_level_findings_are_separated() -> None:
    view = build_clause_reviews(_state())

    assert [finding.rule_id for finding in view.contract_findings] == ["R-DIS-001"]
    assert view.contract_revised_text == REVISION_TEMPLATES["R-DIS-001"]
    assert view.contract_revision_note == REVISION_NOTE
    # 两条条款 + 一条“建议新增条款”
    assert view.revised_count == 3
    assert any("只展示规则覆盖到的问题" in line for line in view.limitations)
    assert not any("抽取未完全成功" in line for line in view.limitations)


def test_degraded_extraction_is_disclosed() -> None:
    state = _state().model_copy(update={"extraction_status": "degraded"})
    view = build_clause_reviews(state, awaiting_human=True)
    assert view.awaiting_human is True
    assert any("抽取未完全成功" in line for line in view.limitations)


def test_export_builds_docx_and_pdf_bytes() -> None:
    view = build_clause_reviews(_state())
    accepted = {"c1": "买方应于合同生效后 10 个工作日内支付 30% 预付款。"}

    docx, docx_name, docx_mime = export_clause_review(view, accepted, "docx")
    assert docx.startswith(b"PK")
    assert docx_name.endswith(".docx") and "审查稿" in docx_name
    assert docx_mime.endswith("wordprocessingml.document")

    pdf, pdf_name, pdf_mime = export_clause_review(view, accepted, "pdf")
    assert pdf.startswith(b"%PDF")
    assert pdf_name.endswith(".pdf") and "审查稿" in pdf_name
    assert pdf_mime == "application/pdf"


def test_export_rejects_unknown_format_and_empty_clauses() -> None:
    view = build_clause_reviews(_state())
    with pytest.raises(ExportError):
        export_clause_review(view, {}, "markdown")

    empty = view.model_copy(update={"clauses": []})
    with pytest.raises(ExportError):
        export_clause_review(empty, {}, "docx")


# ------------------------------------------------------------------- 接口层


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(
        ReviewService.in_memory(),
        upload_dir=tmp_path / "uploads",
        user_db_path=tmp_path / "users.db",
    )
    with TestClient(app) as test_client:
        yield test_client


def _upload(
    client: TestClient,
    name: str = "contract.txt",
    content: bytes | None = None,
):
    if content is None:
        content = (SAMPLES / "sample_sales_contract.txt").read_bytes()
    return client.post("/api/reviews", files={"file": (name, content, "text/plain")})


def test_clauses_endpoint_previews_rules_before_confirmation(client: TestClient) -> None:
    created = _upload(client).json()
    assert created["awaiting_human"] is True
    assert created["report"] is None

    response = client.get(f"/api/reviews/{created['review_id']}/clauses")
    assert response.status_code == 200
    body = response.json()

    assert body["review_id"] == created["review_id"]
    assert body["awaiting_human"] is True
    assert body["status"] == "running"
    assert len(body["clauses"]) >= 5
    assert {clause["risk_level"] for clause in body["clauses"]} <= {
        "red",
        "yellow",
        "pass",
    }
    # 条款视图里必须能看到真实的规则命中与示例条款
    assert any(clause["findings"] for clause in body["clauses"])
    assert any(clause["revised_text"] for clause in body["clauses"])
    assert body["limitations"]


def test_clauses_endpoint_is_404_for_unknown_and_other_users(client: TestClient) -> None:
    assert client.get("/api/reviews/doesnotexist/clauses").status_code == 404

    client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "password": "longpassword123",
            "display_name": "Owner",
        },
    )
    review_id = _upload(client).json()["review_id"]
    assert client.get(f"/api/reviews/{review_id}/clauses").status_code == 200

    # 换一个未登录的浏览器：已入册的审查只对归属账号可见
    client.cookies.clear()
    assert client.get(f"/api/reviews/{review_id}/clauses").status_code == 404


def test_export_endpoint_returns_docx_and_pdf(client: TestClient) -> None:
    review_id = _upload(client).json()["review_id"]
    clauses = client.get(f"/api/reviews/{review_id}/clauses").json()["clauses"]
    target = next(clause for clause in clauses if clause["revised_text"])
    payload = {
        "format": "docx",
        "clauses": [{"clause_id": target["clause_id"], "text": "修改后的条款……"}],
    }

    docx = client.post(f"/api/reviews/{review_id}/export", json=payload)
    assert docx.status_code == 200
    assert docx.content.startswith(b"PK")
    assert "filename*=UTF-8''" in docx.headers["content-disposition"]
    assert docx.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument"
    )

    pdf = client.post(
        f"/api/reviews/{review_id}/export",
        json={**payload, "format": "pdf"},
    )
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert pdf.headers["content-type"] == "application/pdf"

    # 不传 clauses 也能导出：保留原文 + 审查意见
    whole = client.post(
        f"/api/reviews/{review_id}/export",
        json={"format": "pdf", "clauses": []},
    )
    assert whole.status_code == 200


def test_export_endpoint_validates_format_and_review_id(client: TestClient) -> None:
    review_id = _upload(client).json()["review_id"]
    unsupported = client.post(
        f"/api/reviews/{review_id}/export",
        json={"format": "markdown", "clauses": []},
    )
    assert unsupported.status_code == 422

    missing = client.post(
        "/api/reviews/doesnotexist/export",
        json={"format": "pdf", "clauses": []},
    )
    assert missing.status_code == 404
