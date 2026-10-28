"""多智能体专家节点测试（ADR-007 §3.2、ADR-015）。

覆盖：默认关闭、确定性路由、引文定位、专家不能改等级、失败降级、轨迹透出。
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import settings
from app.graph_demo import run_review
from app.nodes import experts as experts_module
from app.schemas import (
    Clause,
    ContractReviewState,
    ExpertDraft,
    ExpertFinding,
    ExpertOpinion,
    HitlDecision,
)
from tests.fakes import FakeLLM

APPROVE = HitlDecision(action="approve", reviewer="test-reviewer")

#: 样例合同里的真实引文（与 test_explain 一致）
QUOTE = "by T/T as 100% advance payment"
_BLOCK_RE = re.compile(
    r"\[(C\d+)\][^\n]*\n(.*?)(?=\n\n\[C\d+\]|\n</untrusted_contract>|\Z)", re.S
)


def _enable(
    monkeypatch: pytest.MonkeyPatch,
    *,
    agents: bool = True,
    tools: bool = False,
) -> None:
    """把 settings 换成“专家/工具已开启”的副本；只影响被测模块的绑定。"""
    enabled = replace(settings, agents_enabled=agents, tools_enabled=tools)
    monkeypatch.setattr(experts_module, "settings", enabled)


def _quote_clause(user: str, quote: str) -> str | None:
    """挑出确实包含该引文的条款编号（没有就返回 None）。"""
    for clause_id, text in _BLOCK_RE.findall(user):
        if quote in text:
            return clause_id
    return None


def _first_clause(user: str) -> str | None:
    match = _BLOCK_RE.search(user)
    return match.group(1) if match else None


def _expert_llm() -> FakeLLM:
    """只在 prompt 里真有这段原文时才给意见（模拟“看得到才说”）。"""

    def handler(schema, system, user):  # noqa: ANN001 - FakeLLM 协议
        clause_id = _quote_clause(user, QUOTE)
        if clause_id is None:
            return ExpertOpinion(summary="本专业没有需要提示的点。", findings=[])
        return ExpertOpinion(
            summary="提示一条付款安排上的注意点。",
            findings=[
                ExpertDraft(
                    topic="付款时点偏早",
                    clause_id=clause_id,
                    quote=QUOTE,
                    detail="合同要求发货前全额电汇，买方资金压力集中在最前端。",
                    suggestion="考虑改为信用证或按装运节点分期付款。",
                )
            ],
        )

    return FakeLLM(handler)


def _bad_quote_llm() -> FakeLLM:
    """给一个真实条款 + 合同里不存在的引文：应被丢弃。"""

    def handler(schema, system, user):  # noqa: ANN001 - FakeLLM 协议
        return ExpertOpinion(
            summary="编了一段原文。",
            findings=[
                ExpertDraft(
                    topic="付款时点偏早",
                    clause_id=_first_clause(user),
                    quote="this sentence is not in the contract",
                    detail="合同要求发货前全额电汇。",
                )
            ],
        )

    return FakeLLM(handler)


def _state_with_clauses() -> ContractReviewState:
    return ContractReviewState(
        review_id="r1",
        source_filename="contract.txt",
        raw_text="dummy",
        clauses=[
            Clause(
                clause_id="C001",
                title="付款条件",
                text="T/T 100% advance",
                clause_type="payment",
            ),
            Clause(clause_id="C002", title="装运", text="FOB Shanghai", clause_type="delivery"),
            Clause(
                clause_id="C003",
                title="仲裁",
                text="CIETAC arbitration",
                clause_type="dispute",
            ),
        ],
    )


# ---------- 默认关闭 ----------


def test_experts_are_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch, agents=False)
    assert experts_module.route_experts(_state_with_clauses()) == "evaluate_rules"


def test_disabled_graph_has_no_expert_findings(
    monkeypatch: pytest.MonkeyPatch, sample_path: Path
) -> None:
    _enable(monkeypatch, agents=False)
    state = run_review(sample_path, decision=APPROVE)
    assert state.expert_findings == []
    assert state.expert_route == []
    assert state.expert_status == "skipped"


# ---------- 路由 ----------


def test_router_picks_experts_by_clause_type_and_keyword() -> None:
    selected = experts_module.select_experts(_state_with_clauses().clauses)
    assert selected == ["payment", "delivery", "dispute"]

    only_dispute = ContractReviewState(
        review_id="r2",
        source_filename="contract.txt",
        raw_text="dummy",
        clauses=[
            Clause(
                clause_id="C001",
                title="杂项",
                text="争议提交中国国际经济贸易仲裁委员会仲裁。",
                clause_type="other",
            )
        ],
    )
    assert experts_module.select_experts(only_dispute.clauses) == ["dispute"]


def test_router_falls_back_to_all_experts_when_nothing_matches() -> None:
    state = ContractReviewState(
        review_id="r3",
        source_filename="contract.txt",
        raw_text="dummy",
        clauses=[Clause(clause_id="C001", title="其他", text="zzz", clause_type="other")],
    )
    assert experts_module.select_experts(state.clauses) == list(experts_module.EXPERT_ORDER)


def test_router_skips_failed_state(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    state = _state_with_clauses().model_copy(update={"status": "failed"})
    assert experts_module.route_experts(state) == "evaluate_rules"


# ---------- 边界：专家不能有等级 ----------


def test_expert_draft_schema_forbids_risk_level() -> None:
    with pytest.raises(ValidationError):
        ExpertDraft(topic="付款", detail="说明", risk_level="red")  # type: ignore[call-arg]


def test_expert_opinion_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ExpertOpinion(summary="x", findings=[], risk_level="red")  # type: ignore[call-arg]


# ---------- 正常路径 ----------


def test_expert_findings_are_grounded_and_do_not_change_level(
    monkeypatch: pytest.MonkeyPatch, sample_path: Path
) -> None:
    _enable(monkeypatch, agents=False)
    baseline = run_review(sample_path, decision=APPROVE)

    _enable(monkeypatch)
    monkeypatch.setattr(experts_module, "get_llm", lambda: _expert_llm())
    state = run_review(sample_path, decision=APPROVE)

    assert state.expert_route
    assert state.expert_findings, "专家意见应被保留"
    finding = state.expert_findings[0]
    assert finding.expert in experts_module.EXPERT_ORDER
    assert finding.grounded is True
    assert finding.citation and sample_path.name in finding.citation
    # 等级仍只来自规则：与关闭专家时完全一致
    assert state.overall_level == baseline.overall_level
    assert [e.rule_id for e in state.rule_evaluations] == [
        e.rule_id for e in baseline.rule_evaluations
    ]
    assert state.status == baseline.status


def test_expert_quote_not_found_is_dropped(
    monkeypatch: pytest.MonkeyPatch, sample_path: Path
) -> None:
    _enable(monkeypatch)
    monkeypatch.setattr(experts_module, "get_llm", lambda: _bad_quote_llm())

    state = run_review(sample_path, decision=APPROVE)

    assert state.expert_findings == []
    assert any(note.endswith(":quote_not_found") for note in state.degraded_steps)
    assert state.expert_status == "degraded"
    # 降级不影响审查结论
    assert state.report is not None
    assert state.status == "approved"


def test_expert_failure_degrades_without_breaking(
    monkeypatch: pytest.MonkeyPatch, sample_path: Path
) -> None:
    _enable(monkeypatch)
    monkeypatch.setattr(
        experts_module,
        "get_llm",
        lambda: FakeLLM(lambda schema, system, user: RuntimeError("upstream 500")),
    )

    state = run_review(sample_path, decision=APPROVE)

    assert state.expert_findings == []
    assert state.expert_status == "degraded"
    assert any(
        note.startswith("expert:") and note.endswith(":failed")
        for note in state.degraded_steps
    )
    assert state.report is not None


def test_expert_without_llm_records_not_configured(
    monkeypatch: pytest.MonkeyPatch, sample_path: Path
) -> None:
    _enable(monkeypatch)  # 不替换 get_llm：真实实现会抛 LLMNotConfigured

    state = run_review(sample_path, decision=APPROVE)

    assert state.expert_findings == []
    assert state.expert_status == "degraded"
    assert any(note.endswith(":not_configured") for note in state.degraded_steps)


# ---------- 轨迹透出 ----------


def test_clause_review_exposes_agent_trace(
    monkeypatch: pytest.MonkeyPatch, sample_path: Path
) -> None:
    from app.services import clause_review as clause_review_module

    _enable(monkeypatch)
    monkeypatch.setattr(
        clause_review_module, "settings", replace(settings, agents_enabled=True)
    )
    monkeypatch.setattr(experts_module, "get_llm", lambda: _expert_llm())

    state = run_review(sample_path, decision=APPROVE)
    view = clause_review_module.build_clause_reviews(state)

    assert view.agent_trace.agents_enabled is True
    # 并行分支的 append 顺序不稳定；轨迹按固定专家顺序归一
    assert view.agent_trace.experts == [
        expert_id
        for expert_id in experts_module.EXPERT_ORDER
        if expert_id in set(state.expert_route)
    ]
    assert view.agent_trace.expert_findings
    assert isinstance(view.agent_trace.expert_findings[0], ExpertFinding)
    # 专家意见不进入 findings（等级来源不变）
    assert all(
        item.risk_level in ("red", "yellow")
        for clause in view.clauses
        for item in clause.findings
    )
