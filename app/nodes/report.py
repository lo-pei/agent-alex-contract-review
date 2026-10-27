"""`build_report` 节点：把规则结果汇总成可追溯报告。

角色：图的终点（当前阶段），报告只展示非 pass 结果，并给出 `文件名:p页:start-end` 引用。
依赖：`app/schemas.py`、`app/rules/engine.py`（引擎版本号）。
约束：抽取降级/跳过不影响报告生成，但必须在 `limitations` 里显式说明；
报告中的 `extracted_fields` 只来自 `state.facts`（已通过 Python 引文校验）。
后续：LLM 解释结果、HITL 决策会在各自节点完成后并入报告。
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

EXTRACTION_DEGRADED_LIMITATION = (
    "要素抽取未完整执行（降级/未配置 LLM），依赖抽取字段的规则已跳过；"
    "报告中未列出的字段缺失类风险需人工核对。"
)
EXTRACTION_SKIPPED_LIMITATION = (
    "本次审查未执行要素抽取（合同解析失败或无可抽取条款），仅运行文本规则。"
)


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
    skipped = sum(1 for e in state.rule_evaluations if e.skipped)
    suffix = f"另有 {skipped} 条字段规则因抽取不可用被跳过。" if skipped else ""
    if not findings:
        return f"规则执行完成，未命中任何风险规则。{suffix}"
    return f"规则执行完成：{reds} 条红色风险，{yellows} 条黄色风险。{suffix}"


def _limitations(state: ContractReviewState) -> list[str]:
    limitations = list(LIMITATIONS)
    if state.status == "failed":
        return limitations
    if state.extraction_status == "degraded":
        limitations.append(EXTRACTION_DEGRADED_LIMITATION)
    elif state.extraction_status == "skipped":
        limitations.append(EXTRACTION_SKIPPED_LIMITATION)
    return limitations


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
        extracted_fields=state.facts,
        to_verify=state.to_verify,
        hitl=state.hitl,
        limitations=_limitations(state),
        rule_engine_version=RULE_ENGINE_VERSION,
        prompt_version=state.prompt_version,
        model_id=state.extraction_model,
    )
    return {
        "report": report,
        "status": "failed" if state.status == "failed" else "completed",
        "timings": {
            **state.timings,
            "build_report_ms": round((perf_counter() - started) * 1000, 2),
        },
    }
