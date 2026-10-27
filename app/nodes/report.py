"""`build_report` 节点：把规则结果与人工决定汇总成可追溯报告。

角色：图的终点，报告只展示非 pass 结果，并给出 `文件名:p页:start-end` 引用。
依赖：`app/schemas.py`、`app/rules/engine.py`（引擎版本号）。
约束：
- 抽取降级/跳过不影响报告生成，但必须在 `limitations` 里显式说明；
- 报告 `extracted_fields` 只来自 `state.facts`（已通过 Python 引文校验）；
- 人工决定只写进 `hitl`，**不改写规则等级**；超时状态必须在摘要与 limitation 中显著提示。
"""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

from app.rules.engine import RULE_ENGINE_VERSION
from app.schemas import (
    ContractReviewState,
    ExplanationResult,
    ReportFinding,
    ReviewReport,
    ReviewStatus,
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
UNREVIEWED_LIMITATION = (
    "红色风险未获人工确认（审批超时或决策无效）：本报告不得作为通过结论，"
    "也不得用于对外承诺；请重新提交人工复核。"
)
REJECTED_LIMITATION = "复核人已拒绝本版本合同：需修改后重新提交审查，本报告仅作为修改依据。"
CHANGES_REQUESTED_LIMITATION = (
    "复核人要求修改：本报告只反映当前版本的问题清单，修改后必须重新审查。"
)
EXPLANATION_FALLBACK_LIMITATION = (
    "部分或全部风险解释未通过质量门/模型不可用，已回退为规则理由；解释仅供参考，"
    "不得作为法律结论。"
)
KNOWLEDGE_NOT_USED_LIMITATION = (
    "本次风险解释未使用知识库（RAG 未启用或未命中），仅依据规则理由与合同原文。"
)

#: 人工决定产生的终态；其余状态在报告里统一记为 `completed`
HUMAN_FINAL_STATUSES = ("approved", "rejected", "changes_requested", "unreviewed_red_risk")


def _finding_of(
    evaluation: RuleEvaluation,
    filename: str,
    explanation: ExplanationResult | None = None,
) -> ReportFinding:
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
        explanation_summary=explanation.summary if explanation else None,
        explanation_quote=explanation.quote if explanation else None,
        explanation_grounded=explanation.grounded if explanation else False,
        explanation_citation=explanation.citation if explanation else None,
        explanation_source=explanation.source if explanation else "none",
        knowledge_citations=explanation.knowledge_citations if explanation else [],
        is_system_finding=evaluation.is_system_finding,
    )


def _human_sentence(state: ContractReviewState) -> str:
    decision = state.hitl
    if decision is None:
        return ""
    reviewer = decision.reviewer
    comment = f"，意见：{decision.comment}" if decision.comment else ""
    if decision.action == "approve":
        return f"红色风险已经人工确认（复核人 {reviewer}{comment}）。"
    if decision.action == "reject":
        return f"复核人 {reviewer} 已拒绝本版本合同{comment}。"
    if decision.action == "request_changes":
        return f"复核人 {reviewer} 要求修改{comment}。"
    return "红色风险未获人工确认（审批超时），报告不得作为通过结论。"


def _explanation_note(state: ContractReviewState) -> str:
    if state.explanation_status == "ok":
        return "风险解释由模型生成，引用已核验。"
    if state.explanation_status == "fallback":
        return "风险解释已回退为规则理由（模型不可用或未通过质量门）。"
    return ""


def _summary(state: ContractReviewState, findings: list[ReportFinding]) -> str:
    if state.status == "failed":
        details = "；".join(state.errors) if state.errors else "未知错误"
        return f"审查未完成：{details}"
    reds = sum(1 for f in findings if f.risk_level == "red")
    yellows = sum(1 for f in findings if f.risk_level == "yellow")
    skipped = sum(1 for e in state.rule_evaluations if e.skipped)
    suffix = f"另有 {skipped} 条字段规则因抽取不可用被跳过。" if skipped else ""
    prefix = _human_sentence(state)
    note = _explanation_note(state)
    if not findings:
        return f"{prefix}规则执行完成，未命中任何风险规则。{suffix}{note}"
    base = f"{prefix}规则执行完成：{reds} 条红色风险，{yellows} 条黄色风险。{suffix}"
    return f"{base}{note}"


def _limitations(state: ContractReviewState) -> list[str]:
    limitations = list(LIMITATIONS)
    if state.status == "failed":
        return limitations
    if state.extraction_status == "degraded":
        limitations.append(EXTRACTION_DEGRADED_LIMITATION)
    elif state.extraction_status == "skipped":
        limitations.append(EXTRACTION_SKIPPED_LIMITATION)
    if state.explanation_status == "fallback":
        limitations.append(EXPLANATION_FALLBACK_LIMITATION)
    elif state.explanation_status == "ok" and not any(
        explanation.knowledge_citations for explanation in state.explanations
    ):
        limitations.append(KNOWLEDGE_NOT_USED_LIMITATION)
    if state.status == "unreviewed_red_risk":
        limitations.append(UNREVIEWED_LIMITATION)
    elif state.status == "rejected":
        limitations.append(REJECTED_LIMITATION)
    elif state.status == "changes_requested":
        limitations.append(CHANGES_REQUESTED_LIMITATION)
    return limitations


def _report_status(state: ContractReviewState) -> ReviewStatus:
    if state.status == "failed":
        return "failed"
    if state.status in HUMAN_FINAL_STATUSES:
        return state.status  # type: ignore[return-value]
    return "completed"


def build_report(state: ContractReviewState) -> dict:
    started = perf_counter()

    explanations = {item.rule_id: item for item in state.explanations}
    evaluations = state.rule_evaluations
    findings = [
        _finding_of(e, state.source_filename, explanations.get(e.rule_id))
        for e in evaluations
        if e.risk_level in ("red", "yellow")
    ]
    # 红色在前，保持规则执行顺序稳定
    findings.sort(key=lambda f: 0 if f.risk_level == "red" else 1)

    report_status = _report_status(state)
    report = ReviewReport(
        review_id=state.review_id,
        source_filename=state.source_filename,
        generated_at=datetime.now(UTC),
        overall_level=state.overall_level,
        status=report_status,
        summary=_summary(state, findings),
        findings=findings,
        extracted_fields=state.facts,
        to_verify=state.to_verify,
        hitl=state.hitl,
        limitations=_limitations(state),
        rule_engine_version=RULE_ENGINE_VERSION,
        prompt_version=state.prompt_version,
        model_id=state.extraction_model,
        explanation_status=state.explanation_status,
        explanation_model=state.explanation_model,
        explanation_prompt_version=state.explanation_prompt_version,
    )
    return {
        "report": report,
        "status": report_status,
        "timings": {
            **state.timings,
            "build_report_ms": round((perf_counter() - started) * 1000, 2),
        },
    }
