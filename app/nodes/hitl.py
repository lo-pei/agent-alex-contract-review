"""`human_review` 节点：红色风险的人工确认闸门（ADR-002）。

角色：图里唯一的阻塞点；用 `interrupt()` 真正暂停，等待 `Command(resume=HitlDecision)`。
依赖：`langgraph.types.interrupt`、`app/schemas.py`。
约束：
- `interrupt()` 之前**只读 state + 纯函数构造载荷**：不写报告、不写审计、不调外部服务；
  resume 会让本节点从顶部重跑，任何写操作都必须放在 `interrupt()` 之后；
- 审批载荷不含 LLM 解释与“建议通过/拒绝”，避免人工被模型措辞影响；
- `timeout` 绝不映射为 `approved`；非法决策也 fail-closed 成 `unreviewed_red_risk`；
- `overrides` 只是人工意见，不改写规则等级。
"""

from __future__ import annotations

from time import perf_counter
from typing import Any, Literal

from langgraph.types import interrupt
from pydantic import ValidationError

from app.schemas import (
    ApprovalFinding,
    ApprovalPayload,
    ContractReviewState,
    HitlDecision,
    RuleEvaluation,
    format_citation,
)

#: 审批载荷最多展示的红色风险数（超出部分只给计数，避免载荷过大）
MAX_PAYLOAD_FINDINGS = 20
#: 每条证据展示的原文片段上限（字符）
MAX_QUOTE_CHARS = 300
#: 每个风险最多展示的证据条数
MAX_QUOTES_PER_FINDING = 3

ACTION_TO_STATUS: dict[str, str] = {
    "approve": "approved",
    "reject": "rejected",
    "request_changes": "changes_requested",
    "timeout": "unreviewed_red_risk",
}

TIMEOUT_WARNING = "人工确认超时：红色风险未获确认，报告不得作为通过结论。"


def _red_evaluations(state: ContractReviewState) -> list[RuleEvaluation]:
    return [e for e in state.rule_evaluations if e.risk_level == "red"]


def _approval_finding_of(
    evaluation: RuleEvaluation, filename: str
) -> ApprovalFinding:
    citations: list[str] = []
    quotes: list[str] = []
    for evidence in evaluation.evidence[:MAX_QUOTES_PER_FINDING]:
        citation = format_citation(filename, evidence)
        if citation not in citations:
            citations.append(citation)
        if evidence.grounded and evidence.quote.strip():
            quotes.append(evidence.quote.strip()[:MAX_QUOTE_CHARS])
    return ApprovalFinding(
        rule_id=evaluation.rule_id,
        title=evaluation.title,
        reason=evaluation.reason,
        suggestion=evaluation.suggestion,
        clause_ids=evaluation.clause_ids,
        citations=citations,
        quotes=quotes,
        is_system_finding=evaluation.is_system_finding,
    )


def build_approval_payload(state: ContractReviewState) -> ApprovalPayload:
    """纯函数：由规则结果 + 已校验字段构造审批载荷。"""
    reds = _red_evaluations(state)
    shown = reds[:MAX_PAYLOAD_FINDINGS]
    extraction_summary = {
        key: value for key, value in state.facts.items() if value not in (None, "")
    }
    return ApprovalPayload(
        review_id=state.review_id,
        source_filename=state.source_filename,
        overall_level=state.overall_level,
        findings=[_approval_finding_of(e, state.source_filename) for e in shown],
        findings_total=len(reds),
        truncated=max(0, len(reds) - len(shown)),
        extraction_status=state.extraction_status,
        extraction_summary=extraction_summary,
        to_verify=[f"{item.field}: {item.reason}" for item in state.to_verify],
    )


def _parse_decision(resumed: Any) -> tuple[HitlDecision | None, str | None]:
    """把 resume 值转成 `HitlDecision`；不合法时返回 (None, 错误说明)。"""
    if isinstance(resumed, HitlDecision):
        return resumed, None
    if isinstance(resumed, dict):
        try:
            return HitlDecision.model_validate(resumed), None
        except ValidationError as exc:
            return None, f"人工决策不合法：{exc.errors()[0].get('msg', 'schema 校验失败')}"
    return None, f"人工决策不合法：期望对象，实际收到 {type(resumed).__name__}"


def human_review(state: ContractReviewState) -> dict:
    started = perf_counter()

    # ---- interrupt 之前：只读 + 纯计算 ----
    payload = build_approval_payload(state)
    resumed = interrupt(payload.model_dump(mode="json"))
    decision, error = _parse_decision(resumed)

    warnings = list(state.warnings)
    errors = list(state.errors)
    degraded = list(state.degraded_steps)
    updates: dict[str, Any] = {
        "timings": {
            **state.timings,
            "human_review_ms": round((perf_counter() - started) * 1000, 2),
        }
    }

    if decision is None:
        # fail-closed：非法决策绝不当成 approve
        errors.append(error or "人工决策不合法")
        degraded.append("human_review:invalid_decision")
        warnings.append(TIMEOUT_WARNING)
        updates.update(
            status="unreviewed_red_risk",
            hitl=None,
            warnings=warnings,
            errors=errors,
            degraded_steps=degraded,
        )
        return updates

    status: Literal[
        "approved", "rejected", "changes_requested", "unreviewed_red_risk"
    ] = ACTION_TO_STATUS[decision.action]  # type: ignore[assignment]

    if decision.action == "timeout":
        warnings.append(TIMEOUT_WARNING)
        degraded.append("human_review:timeout")

    known_rules = {e.rule_id for e in state.rule_evaluations}
    unknown_overrides = sorted(set(decision.overrides) - known_rules)
    if unknown_overrides:
        warnings.append(
            "人工意见引用了不存在的规则 ID：" + ", ".join(unknown_overrides) + "（已忽略）"
        )

    updates.update(status=status, hitl=decision, warnings=warnings, degraded_steps=degraded)
    return updates


def route_by_risk(state: ContractReviewState) -> Literal["human_review", "build_report"]:
    """条件边：任何 red（含规则异常产生的系统 red）→ 人工确认；否则快速通道。"""
    if state.status == "failed":
        return "build_report"
    return "human_review" if _red_evaluations(state) else "build_report"
