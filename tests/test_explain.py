"""解释节点测试：质量门、引用定位、RAG 引用白名单、降级与跳过（ADR-003 §3.8）。"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import settings
from app.graph_demo import run_review
from app.nodes import explain as explain_module
from app.nodes.report import EXPLANATION_FALLBACK_LIMITATION, KNOWLEDGE_NOT_USED_LIMITATION
from app.schemas import HitlDecision, RiskExplanation
from app.services.llm import LLMNotConfigured
from tests.fakes import FakeLLM, rule_id_of

PROJECT_ROOT = Path(__file__).resolve().parent.parent
#: 测试固定使用项目自拟示例语料，避免受用户真实语料变动影响
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge" / "examples"

APPROVE = HitlDecision(action="approve", reviewer="test-reviewer")
REJECT = HitlDecision(action="reject", reviewer="test-reviewer", comment="不接受")

#: 与样例合同真实文本一致的引文（R-PAY-001 / R-TRD-001 有条款，争议规则没有条款）
QUOTES = {
    "R-PAY-001": "by T/T as 100% advance payment",
    "R-TRD-001": "FOB Shanghai",
}

SUMMARIES = {
    "R-PAY-001": "合同要求买方在发货前全额电汇付款，资金风险集中在买方。",
    "R-TRD-001": "合同使用 FOB 但未注明 Incoterms 版本，风险转移与费用划分可能有歧义。",
    "R-DIS-001": "合同未约定适用法律，争议发生时准据法不确定。",
    "R-DIS-002": "合同未约定仲裁或管辖，争议解决路径不明确。",
}

RECOMMENDATIONS = {
    "R-PAY-001": "改为信用证或按交付节点分期付款。",
    "R-TRD-001": "补充 Incoterms 2020 版本与具体装运港。",
    "R-DIS-001": "补充适用法律条款。",
    "R-DIS-002": "明确仲裁机构与仲裁地。",
}

_KNOWLEDGE_REF_RE = re.compile(r"\[(EX-[A-Z0-9-]+#s\d+)\]")


def _valid_explanation(user: str, **overrides: object) -> RiskExplanation:
    rule_id = rule_id_of(user) or "R-UNKNOWN"
    payload: dict[str, object] = {
        "rule_id": rule_id,
        "clause_id": "C002" if rule_id in QUOTES else None,
        "summary": SUMMARIES.get(rule_id, f"{rule_id} 的解释。"),
        "quote": QUOTES.get(rule_id),
        "recommendation": RECOMMENDATIONS.get(rule_id),
        "knowledge_refs": [],
    }
    payload.update(overrides)
    return RiskExplanation(**payload)


def _valid_handler(schema, system, user):  # noqa: ANN001 - FakeLLM 协议
    return _valid_explanation(user)


def _run(
    monkeypatch: pytest.MonkeyPatch,
    path: Path,
    handler=_valid_handler,
    *,
    decision: HitlDecision | None = APPROVE,
):
    monkeypatch.setattr(explain_module, "get_llm", lambda: FakeLLM(handler))
    return run_review(path, decision=decision)


# ---------- 正常路径 ----------


def test_explanation_generated_and_grounded(
    sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _run(monkeypatch, sample_path)
    assert state.report is not None

    assert state.status == "approved"
    assert state.explanation_status == "ok"
    assert state.explanation_model == "fake-llm"
    assert state.explanation_prompt_version == explain_module.EXPLANATION_PROMPT_VERSION
    assert len(state.explanations) == 4
    assert "explain_risks_ms" in state.timings

    report = state.report
    assert report.explanation_status == "ok"
    assert report.explanation_model == "fake-llm"
    assert report.explanation_prompt_version == "explain-v1"
    assert "风险解释由模型生成" in report.summary

    findings = {finding.rule_id: finding for finding in report.findings}
    pay = findings["R-PAY-001"]
    # 解释不改等级
    assert pay.risk_level == "red"
    assert pay.explanation_source == "llm"
    assert pay.explanation_grounded
    assert pay.explanation_quote and "advance payment" in pay.explanation_quote
    assert pay.explanation_citation is not None
    assert pay.explanation_citation.startswith(f"{sample_path.name}:p1:")

    # 无条款的规则（未约定适用法律）不伪造引文
    dispute = findings["R-DIS-001"]
    assert dispute.explanation_source == "llm"
    assert not dispute.explanation_grounded
    assert dispute.explanation_citation is None

    # RAG 默认关闭：解释可用，但必须显式说明未使用知识库
    assert KNOWLEDGE_NOT_USED_LIMITATION in report.limitations


def test_prompt_marks_contract_and_knowledge_as_untrusted(
    sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    llm = FakeLLM(_valid_handler)
    monkeypatch.setattr(explain_module, "get_llm", lambda: llm)

    run_review(sample_path, decision=APPROVE)

    assert llm.calls
    first = llm.calls[0]
    assert "<untrusted_contract>" in first["user"]
    assert "<untrusted_knowledge>" in first["user"]
    assert "规则等级（只读，不得更改）" in first["user"]
    assert "risk_level" in first["system"]  # 只出现在“不要输出”的约束里


# ---------- 质量门 ----------


def test_quality_gate_blocks_impersonated_legal_conclusion(
    sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(schema, system, user):  # noqa: ANN001
        if rule_id_of(user) == "R-PAY-001":
            return _valid_explanation(
                user, summary="该条款导致合同无效，应立即停止交易。"
            )
        return _valid_explanation(user)

    state = _run(monkeypatch, sample_path, handler)
    assert state.report is not None

    assert state.explanation_status == "fallback"
    assert any("forbidden:void" in step for step in state.degraded_steps)
    findings = {finding.rule_id: finding for finding in state.report.findings}
    pay = findings["R-PAY-001"]
    assert pay.explanation_source == "rule"
    assert pay.explanation_summary == pay.reason
    # 越权文本必须完全消失，不能进入报告
    assert "合同无效" not in json.dumps(
        state.report.model_dump(mode="json"), ensure_ascii=False
    )
    assert EXPLANATION_FALLBACK_LIMITATION in state.report.limitations
    assert any("未通过质量门" in warning for warning in state.warnings)


def test_quality_gate_rejects_unlocatable_quote(
    sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(schema, system, user):  # noqa: ANN001
        if rule_id_of(user) == "R-PAY-001":
            return _valid_explanation(user, quote="THIS QUOTE DOES NOT EXIST")
        return _valid_explanation(user)

    state = _run(monkeypatch, sample_path, handler)
    assert state.explanation_status == "fallback"
    assert any("quote_not_found" in step for step in state.degraded_steps)
    findings = {f.rule_id: f for f in state.report.findings}  # type: ignore[union-attr]
    pay = findings["R-PAY-001"]
    assert pay.explanation_source == "rule"
    # 回退时使用规则自带、已定位的证据，不伪造
    assert pay.explanation_quote == "100% advance payment"


def test_quality_gate_rejects_other_rule_id(
    sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(schema, system, user):  # noqa: ANN001
        return _valid_explanation(user, rule_id="R-UNKNOWN-999")

    state = _run(monkeypatch, sample_path, handler)
    assert state.explanation_status == "fallback"
    assert any(":rule_id" in step for step in state.degraded_steps)
    assert all(item.source == "rule" for item in state.explanations)


def test_quality_gate_rejects_clause_outside_rule(
    sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(schema, system, user):  # noqa: ANN001
        if rule_id_of(user) == "R-PAY-001":
            return _valid_explanation(user, clause_id="C007")
        return _valid_explanation(user)

    state = _run(monkeypatch, sample_path, handler)
    assert state.explanation_status == "fallback"
    assert any(":clause_id" in step for step in state.degraded_steps)


def test_explanation_schema_forbids_risk_level() -> None:
    with pytest.raises(ValidationError):
        RiskExplanation(rule_id="R-PAY-001", summary="解释", risk_level="red")


# ---------- 降级与跳过 ----------


def test_llm_not_configured_falls_back_but_report_is_complete(
    sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom():
        raise LLMNotConfigured("未配置测试 Key")

    monkeypatch.setattr(explain_module, "get_llm", boom)
    state = run_review(sample_path, decision=APPROVE)

    assert state.status == "approved"
    assert state.report is not None
    assert state.explanation_status == "fallback"
    assert "explain:not_configured" in state.degraded_steps
    assert all(item.source == "rule" for item in state.explanations)
    assert all(item.summary for item in state.explanations)
    assert any("风险解释未生成" in warning for warning in state.warnings)
    assert state.report.explanation_status == "fallback"
    assert EXPLANATION_FALLBACK_LIMITATION in state.report.limitations


def test_reject_does_not_call_llm(
    sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom():
        raise AssertionError("被拒绝时不得调用解释 LLM")

    monkeypatch.setattr(explain_module, "get_llm", boom)
    state = run_review(sample_path, decision=REJECT)

    assert state.status == "rejected"
    assert state.explanation_status == "skipped"
    assert state.explanations == []
    assert state.report is not None
    assert state.report.explanation_status == "skipped"


def test_clean_contract_skips_explanation_without_llm(
    clean_sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom():
        raise AssertionError("无可解释风险时不得调用解释 LLM")

    monkeypatch.setattr(explain_module, "get_llm", boom)
    state = run_review(clean_sample_path, decision=None)

    assert state.status == "completed"
    assert state.explanation_status == "skipped"
    assert state.explanations == []
    assert state.report is not None
    assert state.report.findings == []
    assert state.report.explanation_status == "skipped"


# ---------- RAG 引用 ----------


def test_rag_citations_must_be_retrieved_and_registered(
    sample_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patched = replace(
        settings,
        rag_enabled=True,
        rag_knowledge_dir=str(KNOWLEDGE_DIR),
    )
    monkeypatch.setattr(explain_module, "settings", patched)

    def handler(schema, system, user):  # noqa: ANN001
        match = _KNOWLEDGE_REF_RE.search(user)
        refs = [match.group(1), "FAKE#s1"] if rule_id_of(user) == "R-PAY-001" else []
        return _valid_explanation(user, knowledge_refs=refs)

    state = _run(monkeypatch, sample_path, handler)
    assert state.report is not None
    assert state.explanation_status == "ok"

    findings = {finding.rule_id: finding for finding in state.report.findings}
    pay = findings["R-PAY-001"]
    # 只保留“本条风险实际检索到”的引用；编造的引用被丢弃并告警
    assert len(pay.knowledge_citations) == 1
    assert pay.knowledge_citations[0].startswith("EX-")
    assert any("FAKE#s1" in warning for warning in state.warnings)
    # 使用了知识库 → 不再写“未使用知识库”的 limitation
    assert KNOWLEDGE_NOT_USED_LIMITATION not in state.report.limitations


def test_rag_misconfigured_degrades_to_rules(
    sample_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patched = replace(
        settings,
        rag_enabled=True,
        rag_knowledge_dir=str(tmp_path / "missing"),
    )
    monkeypatch.setattr(explain_module, "settings", patched)

    state = _run(monkeypatch, sample_path, _valid_handler)

    assert state.explanation_status == "ok"
    assert "explain:knowledge_unavailable" in state.degraded_steps
    assert any("知识库不可用" in warning for warning in state.warnings)
    assert state.report is not None
    # 知识库不可用时，解释仍来自模型，但引用列表必须为空（不许编造）
    assert all(not item.knowledge_citations for item in state.explanations)


def test_rag_no_hit_warns(
    sample_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 空语料：manifest 合法但没有任何知识文件 → 不命中，仍应生成解释
    (tmp_path / "manifest.yaml").write_text(
        'version: 1\ndocuments:\n  - source_id: T1\n    title: 空\n'
        '    publisher: 项目\n    version: "1"\n    jurisdiction: 中国\n'
        '    effective_date: "2026-01-01"\n    language: zh\n    file: doc.md\n'
        '    license: internal\n',
        encoding="utf-8",
    )
    (tmp_path / "doc.md").write_text("## 完全无关\nzzzz qqqq\n", encoding="utf-8")
    patched = replace(settings, rag_enabled=True, rag_knowledge_dir=str(tmp_path))
    monkeypatch.setattr(explain_module, "settings", patched)

    state = _run(monkeypatch, sample_path, _valid_handler)

    assert state.explanation_status == "ok"
    assert "explain:knowledge_no_hit" in state.degraded_steps
    assert any("知识库未命中" in warning for warning in state.warnings)
    assert state.report is not None
    assert KNOWLEDGE_NOT_USED_LIMITATION in state.report.limitations
