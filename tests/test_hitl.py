"""HITL 测试：真暂停、审批前零业务写入、恢复、幂等、超时不通过（ADR-002 §5）。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from langgraph.types import Command

from app.graph import build_graph
from app.nodes.hitl import MAX_PAYLOAD_FINDINGS, build_approval_payload, route_by_risk
from app.nodes.report import REJECTED_LIMITATION, UNREVIEWED_LIMITATION
from app.review_service import ReviewService, ReviewStateError
from app.schemas import (
    ContractReviewState,
    Evidence,
    HitlDecision,
    RuleEvaluation,
)
from app.services.checkpointer import memory_checkpointer

APPROVE = HitlDecision(action="approve", reviewer="alice")
REJECT = HitlDecision(action="reject", reviewer="alice", comment="付款条件不可接受")


def _final_state(raw: dict) -> ContractReviewState:
    payload = {key: value for key, value in raw.items() if not key.startswith("__")}
    return ContractReviewState.model_validate(payload)


# ---------- 编译期强制 checkpointer ----------


def test_checkpointer_required() -> None:
    with pytest.raises(ValueError, match="checkpointer"):
        build_graph()


# ---------- 暂停 ----------


def test_hitl_pauses(sample_path: Path) -> None:
    service = ReviewService.in_memory()
    run = service.start(sample_path)

    assert run.awaiting_human
    # interrupt 在节点返回前抛出，state.status 仍是 running（ADR-002 §3.4）
    assert run.status == "running"
    assert run.report is None
    assert run.approval is not None
    assert run.approval.type == "red_risk_approval"
    assert run.approval.findings_total >= 3
    assert len(run.approval.findings) == min(
        run.approval.findings_total, MAX_PAYLOAD_FINDINGS
    )
    assert all(f.risk_level == "red" for f in run.approval.findings)
    assert "绝不自动通过" in run.approval.instructions
    # 审批载荷不含时间戳/LLM 解释，保证节点重跑时载荷稳定
    dumped = run.approval.model_dump()
    assert "requested_at" not in dumped
    assert "explanation" not in str(dumped)

    # 规则已经跑完，只是没写报告
    state = service.get_state(run.review_id)
    assert state.overall_level == "red"
    assert {e.rule_id for e in state.rule_evaluations} >= {"R-PAY-001", "R-DIS-001"}


def test_no_business_write_before_approval(sample_path: Path) -> None:
    service = ReviewService.in_memory()
    run = service.start(sample_path)

    state = service.get_state(run.review_id)
    assert state.report is None  # 审批前不写最终报告
    assert state.hitl is None  # 没有人工决定
    assert state.status == "running"
    # 只有 pending 载荷可读
    assert run.approval is not None and run.approval.findings


# ---------- 快速通道 ----------


def test_no_red_fast_path(clean_sample_path: Path) -> None:
    service = ReviewService.in_memory()
    run = service.start(clean_sample_path)

    assert not run.awaiting_human
    assert run.status == "completed"
    assert run.report is not None
    assert run.report.status == "completed"
    assert run.report.hitl is None


# ---------- 恢复 ----------


def test_approve_resumes_and_writes_once(sample_path: Path) -> None:
    service = ReviewService.in_memory()
    run = service.start(sample_path)

    approved = service.resume(run.review_id, APPROVE)

    assert approved.status == "approved"
    assert approved.report is not None
    assert approved.report.status == "approved"
    assert approved.report.hitl is not None
    assert approved.report.hitl.reviewer == "alice"
    assert "人工确认" in approved.report.summary

    # 幂等：第二个决定不再生效、不重跑图、不重新生成报告
    again = service.resume(run.review_id, REJECT)
    assert again.status == "approved"
    assert again.report is not None and approved.report is not None
    assert again.report.generated_at == approved.report.generated_at
    assert again.report.hitl is not None
    assert again.report.hitl.reviewer == "alice"


def test_reject_skips_explanation(sample_path: Path) -> None:
    service = ReviewService.in_memory()
    run = service.start(sample_path)

    rejected = service.resume(run.review_id, REJECT)

    assert rejected.status == "rejected"
    assert rejected.report is not None
    assert rejected.report.status == "rejected"
    assert rejected.state is not None
    # 被拒绝时不生成 LLM 解释，直接出报告
    assert rejected.state.explanation_status == "skipped"
    assert "拒绝" in rejected.report.summary
    assert REJECTED_LIMITATION in rejected.report.limitations
    # 规则等级不被人工决定改写
    assert rejected.report.overall_level == "red"
    assert rejected.report.hitl is not None
    assert rejected.report.hitl.action == "reject"


def test_request_changes_status(sample_path: Path) -> None:
    service = ReviewService.in_memory()
    run = service.start(sample_path)

    changed = service.resume(
        run.review_id,
        HitlDecision(action="request_changes", reviewer="bob", comment="补充不可抗力条款"),
    )

    assert changed.status == "changes_requested"
    assert changed.report is not None
    assert changed.report.status == "changes_requested"
    assert "要求修改" in changed.report.summary


def test_timeout_never_approves(sample_path: Path) -> None:
    service = ReviewService.in_memory()
    run = service.start(sample_path)

    timed_out = service.resume(
        run.review_id, HitlDecision(action="timeout", reviewer="system")
    )

    assert timed_out.status == "unreviewed_red_risk"
    assert timed_out.report is not None
    assert timed_out.report.status == "unreviewed_red_risk"
    assert "未获人工确认" in timed_out.report.summary
    assert "不得作为通过结论" in timed_out.report.summary
    assert UNREVIEWED_LIMITATION in timed_out.report.limitations
    assert timed_out.report.hitl is not None
    assert timed_out.report.hitl.action == "timeout"
    # 绝不出现“已通过”
    assert "已通过" not in timed_out.report.summary


# ---------- 惰性超时 ----------


def test_lazy_timeout_marks_unreviewed(sample_path: Path) -> None:
    clock = {"now": datetime(2026, 10, 27, 9, 0, tzinfo=UTC)}
    service = ReviewService.in_memory(
        timeout_minutes=30, clock=lambda: clock["now"]
    )
    run = service.start(sample_path)

    fresh = service.get(run.review_id)
    assert fresh.awaiting_human

    clock["now"] = clock["now"] + timedelta(minutes=31)
    expired = service.get(run.review_id)

    assert not expired.awaiting_human
    assert expired.status == "unreviewed_red_risk"
    assert expired.report is not None
    assert UNREVIEWED_LIMITATION in expired.report.limitations


# ---------- 非法决策 fail-closed ----------


def test_invalid_decision_fails_closed(sample_path: Path) -> None:
    graph = build_graph(checkpointer=memory_checkpointer())
    review_id = "hitl-invalid-decision"
    config = {"configurable": {"thread_id": review_id}}
    initial = ContractReviewState(
        review_id=review_id,
        source_filename=sample_path.name,
        source_path=str(sample_path),
    )
    graph.invoke(initial.model_dump(), config=config)

    raw = graph.invoke(Command(resume={"action": "approve"}), config)
    state = _final_state(raw)

    # 缺 reviewer → 不是合法决定，绝不当作 approve
    assert state.status == "unreviewed_red_risk"
    assert any("不合法" in error for error in state.errors)
    assert state.report is not None
    assert state.report.status == "unreviewed_red_risk"


def test_resume_completed_review_is_idempotent(clean_sample_path: Path) -> None:
    service = ReviewService.in_memory()
    run = service.start(clean_sample_path)

    again = service.resume(run.review_id, APPROVE)

    # 已完成（无待审任务）→ 直接返回现有结果，不重跑、不改状态
    assert again.status == "completed"
    assert again.report is not None and run.report is not None
    assert again.report.generated_at == run.report.generated_at


def test_resume_unknown_review_raises() -> None:
    service = ReviewService.in_memory()
    with pytest.raises(ReviewStateError):
        service.resume("not-exists", APPROVE)


def test_get_unknown_review_raises() -> None:
    service = ReviewService.in_memory()
    with pytest.raises(ReviewStateError):
        service.get("not-exists")


# ---------- 条件边与载荷构造 ----------


def test_route_by_risk() -> None:
    red = RuleEvaluation(
        rule_id="R-PAY-001", title="t", risk_level="red", reason="r"
    )
    yellow = RuleEvaluation(
        rule_id="R-TRD-001", title="t", risk_level="yellow", reason="r"
    )
    assert route_by_risk(ContractReviewState(review_id="a", source_filename="c.txt")) == (
        "build_report"
    )
    assert (
        route_by_risk(
            ContractReviewState(
                review_id="a", source_filename="c.txt", rule_evaluations=[yellow]
            )
        )
        == "build_report"
    )
    assert (
        route_by_risk(
            ContractReviewState(
                review_id="a", source_filename="c.txt", rule_evaluations=[yellow, red]
            )
        )
        == "human_review"
    )


def test_payload_truncates_many_findings() -> None:
    evaluations = [
        RuleEvaluation(
            rule_id=f"R-PAY-{index:03d}",
            title=f"规则 {index}",
            risk_level="red",
            reason="原因",
            evidence=[Evidence(quote="原文", start=0, end=2, page=1, grounded=True)],
        )
        for index in range(1, MAX_PAYLOAD_FINDINGS + 6)
    ]
    state = ContractReviewState(
        review_id="many",
        source_filename="contract.txt",
        overall_level="red",
        rule_evaluations=evaluations,
    )

    payload = build_approval_payload(state)

    assert payload.findings_total == MAX_PAYLOAD_FINDINGS + 5
    assert len(payload.findings) == MAX_PAYLOAD_FINDINGS
    assert payload.truncated == 5
    # 引用格式可回溯
    assert payload.findings[0].citations == ["contract.txt:p1:0-2"]
    assert payload.findings[0].quotes == ["原文"]


def test_unknown_override_produces_warning(sample_path: Path) -> None:
    service = ReviewService.in_memory()
    run = service.start(sample_path)

    result = service.resume(
        run.review_id,
        HitlDecision(action="approve", reviewer="alice", overrides={"R-FAKE-001": "接受"}),
    )

    assert result.state is not None
    assert any("R-FAKE-001" in warning for warning in result.state.warnings)
