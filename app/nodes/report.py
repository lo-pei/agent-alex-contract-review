"""`build_report` 节点：把规则结果汇总成可追溯报告。

角色：图的终点（当前阶段），报告只展示非 pass 结果，并给出 `文件名:p页:start-end` 引用。
依赖：`app/schemas.py`、`app/rules/engine.py`（引擎版本号）。
后续：LLM 解释结果、HITL 决策、抽取字段会在各自节点完成后并入报告。
"""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

from app.rules.engine import RULE_ENGINE_VERSION
from app.schemas import (
    ContractReviewState,
    ReportFinding,
    ReviewReport,
    RuleEvaluation,
    format_citation,
)

LIMITATIONS = [
    "本报告由确定性规则自动生成，属于合同预审辅助材料，不构成法律意见。",
    "规则覆盖范围有限：未命中的条款不代表不存在风险，签署前仍需专业律师复核。",
]


def _finding_of(evaluation: RuleEvaluation, filename: str) -> ReportFinding:
    citations: list[str] = []
    for evidence in evaluation.evidence:
        citation = format_citation(filename, evidence)
        if citation not in citations:
            citations.append(citation)
    return ReportFinding(
        rule_id=evaluation.rule_id,
        risk_level="red" if evaluation.risk_level == "red" else "yellow",
        reason=evaluation.reason,
        suggestion=evaluation.suggestion,
        clause_ids=evaluation.clause_ids,
        citations=citations,
        is_system_finding=evaluation.is_system_finding,
    )


def _summary(state: ContractReviewState, findings: list[ReportFinding]) -> str:
    if state.status == "failed":
        details = "；".join(state.errors) if state.errors else "未知错误"
        return f"审查未完成：{details}"
    reds = sum(1 for f in findings if f.risk_level == "red")
    yellows = sum(1 for f in findings if f.risk_level == "yellow")
    if not findings:
        return "规则执行完成，未命中任何风险规则。"
    return f"规则执行完成：{reds} 条红色风险，{yellows} 条黄色风险。"


def build_report(state: ContractReviewState) -> dict:
    started = perf_counter()

    evaluations = state.rule_evaluations
    findings = [
        _finding_of(e, state.source_filename)
        for e in evaluations
        if e.risk_level in ("red", "yellow")
    ]
    # 红色在前，保持规则执行顺序稳定
    findings.sort(key=lambda f: 0 if f.risk_level == "red" else 1)

    report = ReviewReport(
        review_id=state.review_id,
        source_filename=state.source_filename,
        generated_at=datetime.now(UTC),
        overall_level=state.overall_level,
        status="failed" if state.status == "failed" else "completed",
        summary=_summary(state, findings),
        findings=findings,
        extracted_fields={},
        to_verify=state.to_verify,
        hitl=state.hitl,
        limitations=LIMITATIONS,
        rule_engine_version=RULE_ENGINE_VERSION,
    )
    return {
        "report": report,
        "status": "failed" if state.status == "failed" else "completed",
        "timings": {
            **state.timings,
            "build_report_ms": round((perf_counter() - started) * 1000, 2),
        },
    }
