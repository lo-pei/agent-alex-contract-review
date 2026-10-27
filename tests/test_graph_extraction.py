"""图端到端（LLM 抽取）测试：Fake LLM 成功、无 Key 降级、部分失败仍降级。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.graph_demo import run_review
from app.nodes import extract as extract_module
from app.nodes.report import EXTRACTION_DEGRADED_LIMITATION
from app.schemas import ExtractedFieldSet
from tests.fakes import FakeLLM, by_clause, clause_id_of, field, field_set

FIELDS = {
    "C000": field_set(
        seller=field("ABC Trading Co., Ltd.", "Seller: ABC Trading Co., Ltd."),
        buyer=field("Global Import LLC", "Buyer: Global Import LLC"),
    ),
    "C002": field_set(
        unit_price=field("620", "USD 620 per metric ton"),
        total_amount=field("3,100,000", "The total contract price is USD 3,100,000."),
        currency=field("USD", "USD 620 per metric ton"),
        payment_method=field("T/T", "by T/T as 100% advance payment"),
    ),
    "C003": field_set(
        delivery_date=field(
            "within 45 days after receipt of the advance payment",
            "Shipment shall be effected within 45 days after receipt of the advance payment.",
        )
    ),
    "C004": field_set(
        inspection_standard=field(
            "SGS", "Inspection shall be carried out by SGS at the port of loading."
        )
    ),
}


def _evaluations(state) -> dict:
    return {e.rule_id: e for e in state.rule_evaluations}


def test_graph_extracts_fields_with_fake_llm(
    sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(extract_module, "get_llm", lambda: by_clause(FIELDS))

    state = run_review(sample_path)
    assert state.report is not None

    assert state.status == "completed"
    assert state.extraction_status == "ok"
    assert state.extraction_model == "fake-llm"
    assert state.prompt_version == "extract-v1"

    assert state.facts["total_amount"] == 3_100_000.0
    assert state.facts["currency"] == "USD"
    assert state.facts["seller"] == "ABC Trading Co., Ltd."
    assert state.fact_evidence["total_amount"].grounded

    report = state.report
    assert report.extracted_fields == state.facts
    assert report.model_id == "fake-llm"
    assert report.prompt_version == "extract-v1"

    evaluations = _evaluations(state)
    # 字段就位后，两条字段规则正常判定为 pass（不是 skipped）
    assert evaluations["R-DLV-001"].risk_level == "pass"
    assert evaluations["R-INP-001"].risk_level == "pass"
    assert not evaluations["R-DLV-001"].skipped
    assert not evaluations["R-INP-001"].skipped

    # 文本规则结果不因抽取而改变
    assert evaluations["R-PAY-001"].risk_level == "red"
    assert evaluations["R-DIS-001"].risk_level == "red"
    assert evaluations["R-DIS-002"].risk_level == "red"
    assert state.overall_level == "red"
    assert {f.rule_id for f in report.findings} == {
        "R-PAY-001",
        "R-DIS-001",
        "R-DIS-002",
        "R-TRD-001",
    }


def test_graph_without_key_degrades_and_skips_field_rules(sample_path: Path) -> None:
    state = run_review(sample_path)
    assert state.report is not None

    assert state.extraction_status == "degraded"
    assert state.facts == {}
    assert state.report.extracted_fields == {}
    assert state.report.prompt_version == "n/a"
    assert state.report.model_id is None

    evaluations = _evaluations(state)
    assert evaluations["R-DLV-001"].skipped
    assert evaluations["R-INP-001"].skipped
    assert evaluations["R-DLV-001"].risk_level == "pass"
    # 文本规则照常执行
    assert evaluations["R-PAY-001"].risk_level == "red"
    assert state.overall_level == "red"

    assert EXTRACTION_DEGRADED_LIMITATION in state.report.limitations
    assert "跳过" in state.report.summary
    assert state.status == "completed"


def test_partial_failure_degrades_and_skips_field_rules(
    sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(schema, system, user):
        clause_id = clause_id_of(user)
        if clause_id == "C004":
            return RuntimeError("timeout")
        return FIELDS.get(clause_id or "", ExtractedFieldSet())

    monkeypatch.setattr(extract_module, "get_llm", lambda: FakeLLM(handler))

    state = run_review(sample_path)
    assert state.report is not None

    assert state.extraction_status == "degraded"
    assert "extract_fields:C004" in state.degraded_steps
    # 已抽取字段仍保留（可追溯），但字段规则因整体降级被跳过
    assert state.facts["total_amount"] == 3_100_000.0
    assert _evaluations(state)["R-DLV-001"].skipped
    assert state.report.extracted_fields["total_amount"] == 3_100_000.0
    assert state.report.status == "completed"


def test_graph_timings_include_llm_nodes(
    sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(extract_module, "get_llm", lambda: by_clause(FIELDS))

    state = run_review(sample_path)

    assert {"extract_fields_ms", "validate_extraction_ms"} <= set(state.timings)
