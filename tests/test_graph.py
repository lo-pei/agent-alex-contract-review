"""最小图端到端测试：编译、调用、报告、失败降级、checkpointer。"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from app.graph import build_graph
from app.graph_demo import run_review
from app.schemas import ContractReviewState


def test_graph_runs_on_sample(sample_path: Path) -> None:
    state = run_review(sample_path)

    assert state.status == "completed"
    assert state.overall_level == "red"
    # 7 条规则：5 条文本规则 + 2 条字段规则（无 Key 时字段规则 skipped）
    assert len(state.rule_evaluations) == 7
    assert state.extraction_status == "degraded"
    assert len(state.clauses) >= 5
    assert state.report is not None

    report = state.report
    assert report.status == "completed"
    assert report.overall_level == "red"
    assert report.review_id == state.review_id
    assert report.source_filename == "sample_sales_contract.txt"

    rule_ids = {f.rule_id for f in report.findings}
    assert {"R-PAY-001", "R-DIS-001", "R-DIS-002"} <= rule_ids
    assert all(f.risk_level in ("red", "yellow") for f in report.findings)
    # 红色在前
    levels = [f.risk_level for f in report.findings]
    assert levels == sorted(levels, key=lambda x: 0 if x == "red" else 1)
    # 报告必须包含免责声明
    assert any("不构成法律意见" in item for item in report.limitations)


def test_citations_are_traceable(sample_path: Path) -> None:
    state = run_review(sample_path)
    assert state.report is not None

    pattern = re.compile(r"^sample_sales_contract\.txt:p1:\d+-\d+$")
    citations = [c for f in state.report.findings for c in f.citations]
    assert citations, "红色/黄色风险至少应有一条原文引用"
    for citation in citations:
        assert pattern.match(citation), citation


def test_no_crash_when_contract_missing(tmp_path: Path) -> None:
    state = run_review(tmp_path / "missing.txt")
    assert state.status == "failed"
    assert state.overall_level == "unknown"
    assert state.report is not None
    assert state.report.status == "failed"
    assert "审查未完成" in state.report.summary
    assert state.report.findings == []


def test_clean_contract_fast_path(clean_sample_path: Path) -> None:
    state = run_review(clean_sample_path)
    assert state.status == "completed"
    assert state.overall_level == "pass"
    assert state.report is not None
    assert state.report.findings == []
    assert "未命中" in state.report.summary


def test_graph_is_deterministic(sample_path: Path) -> None:
    first = run_review(sample_path)
    second = run_review(sample_path)
    first_report = first.report.model_dump() if first.report else {}
    second_report = second.report.model_dump() if second.report else {}
    assert first_report["findings"] == second_report["findings"]
    assert first_report["overall_level"] == second_report["overall_level"]


def test_checkpointer_persists_state(sample_path: Path) -> None:
    graph = build_graph(checkpointer=InMemorySaver())
    initial = ContractReviewState(
        review_id=uuid.uuid4().hex,
        source_filename=sample_path.name,
        source_path=str(sample_path),
    )
    config = {"configurable": {"thread_id": initial.review_id}}

    graph.invoke(initial.model_dump(), config=config)

    snapshot = graph.get_state(config)
    assert snapshot.values["status"] == "completed"
    assert snapshot.values["overall_level"] == "red"


def test_timings_recorded_for_every_node(sample_path: Path) -> None:
    state = run_review(sample_path)
    assert {
        "ingest_document_ms",
        "segment_clauses_ms",
        "extract_fields_ms",
        "validate_extraction_ms",
        "evaluate_rules_ms",
        "build_report_ms",
    } <= set(state.timings)
