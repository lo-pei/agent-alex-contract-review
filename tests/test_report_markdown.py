"""报告 Markdown 渲染测试：结构完整、等级只读、表格转义、限制必出现。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.report_markdown import render_report_markdown
from app.review_service import ReviewService
from app.schemas import (
    HitlDecision,
    ReportFinding,
    ReviewReport,
    ToVerifyItem,
)


def _report(finding: ReportFinding | None = None) -> ReviewReport:
    return ReviewReport(
        review_id="abc123",
        source_filename="合同A.txt",
        generated_at=datetime(2026, 10, 27, 9, 30, tzinfo=UTC),
        overall_level="red",
        status="approved",
        summary="红色风险已经人工确认（复核人 alice）。",
        findings=[finding] if finding else [],
        extracted_fields={"seller": "甲公司", "note": "含|竖线\n换行"},
        to_verify=[ToVerifyItem(field="currency", reason="币种未标注")],
        hitl=HitlDecision(action="approve", reviewer="alice", comment="已核对"),
        limitations=["本报告不构成法律意见。"],
        rule_engine_version="2",
        prompt_version="extract-v2",
        model_id="fake-model",
        explanation_status="ok",
        explanation_model="fake-model",
        explanation_prompt_version="explain-v1",
    )


def test_render_contains_required_sections() -> None:
    finding = ReportFinding(
        rule_id="R-PAY-001",
        risk_level="red",
        reason="100% 预付款",
        suggestion="改为 30% 预付款",
        clause_ids=["c2"],
        citations=["合同A.txt:p1:10-30"],
        explanation_summary="预付款比例过高。",
        explanation_quote="100% advance payment",
        explanation_grounded=True,
        explanation_citation="合同A.txt:p1:10-30",
        explanation_source="llm",
        knowledge_citations=["CISG-ZH#第十二条"],
    )
    markdown = render_report_markdown(_report(finding))

    assert markdown.startswith("# 合同审查报告 · 合同A.txt")
    headings = (
        "## 摘要",
        "## 风险清单",
        "## 抽取要素",
        "## 待人工核对",
        "## 人工复核",
        "## 限制与免责",
        "## 版本信息",
    )
    for heading in headings:
        assert heading in markdown
    assert "**红色**" in markdown
    assert "R-PAY-001" in markdown
    assert "`合同A.txt:p1:10-30`" in markdown
    assert "`CISG-ZH#第十二条`" in markdown
    assert "规则理由兜底" not in markdown
    assert "人工决定只记录复核结论，不改写规则判定的风险等级" in markdown
    assert "本报告不构成法律意见。" in markdown
    assert "`explain-v1`" in markdown


def test_render_escapes_table_and_newlines() -> None:
    markdown = render_report_markdown(_report())
    assert r"含\|竖线 换行" in markdown
    assert "| seller | 甲公司 |" in markdown
    # 未命中风险时给显式说明，而不是空白
    assert "未命中任何风险规则" in markdown


def test_render_from_real_review(sample_path: Path) -> None:
    service = ReviewService.in_memory()
    run = service.start(sample_path)
    approved = service.resume(run.review_id, HitlDecision(action="approve", reviewer="bob"))
    assert approved.report is not None

    markdown = render_report_markdown(approved.report)

    assert f"`{run.review_id}`" in markdown
    assert "已人工确认（approve）" in markdown
    assert "R-PAY-001" in markdown
    assert "审查未完成" not in markdown
    assert approved.report.summary.split("。")[0] in markdown
