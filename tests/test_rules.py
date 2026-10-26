"""规则引擎与条件 DSL 测试：等级、证据、缺失字段、异常 fail-closed、加载校验。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.rules.dsl import (
    AllOf,
    AnyOf,
    ContainsAll,
    ContainsAny,
    DateAfter,
    DateBefore,
    FieldEquals,
    FieldIn,
    FieldMissing,
    FieldPresent,
    NoneOf,
    NumericGt,
    NumericLt,
    RegexMatch,
    evaluate_condition,
)
from app.rules.engine import (
    RuleDefinition,
    RuleSet,
    evaluate_rules,
    load_rules,
    overall_level,
)
from app.schemas import Clause, ContractReviewState

# ---------- 条件 DSL ----------


def test_contains_any_case_insensitive() -> None:
    result = evaluate_condition(ContainsAny(keywords=["FOB"]), "sold on fob Shanghai")
    assert result.triggered
    assert result.spans[0].start == 8


def test_contains_all_requires_every_keyword() -> None:
    condition = ContainsAll(keywords=["payment", "advance"])
    assert evaluate_condition(condition, "payment in advance").triggered
    assert not evaluate_condition(condition, "payment by L/C").triggered


def test_regex_match() -> None:
    condition = RegexMatch(pattern=r"Incoterms\s*(19|20)\d{2}")
    assert evaluate_condition(condition, "CIF Rotterdam, Incoterms 2020").triggered
    assert not evaluate_condition(condition, "CIF Rotterdam").triggered


def test_all_of_and_none_of_combination() -> None:
    condition = AllOf(
        conditions=[
            ContainsAny(keywords=["FOB", "CIF"]),
            NoneOf(conditions=[RegexMatch(pattern=r"Incoterms\s*20\d{2}")]),
        ]
    )
    assert evaluate_condition(condition, "FOB Shanghai").triggered
    assert not evaluate_condition(condition, "FOB Shanghai, Incoterms 2020").triggered


def test_any_of() -> None:
    condition = AnyOf(
        conditions=[
            ContainsAny(keywords=["仲裁"]),
            ContainsAny(keywords=["arbitration"]),
        ]
    )
    assert evaluate_condition(condition, "arbitration in Shanghai").triggered
    assert not evaluate_condition(condition, "courts in Hamburg").triggered


def test_field_conditions() -> None:
    facts = {"currency": "USD", "total_amount": 100}
    assert evaluate_condition(FieldEquals(field="currency", value="usd"), "", facts).triggered
    assert evaluate_condition(FieldIn(field="currency", values=["USD", "EUR"]), "", facts).triggered
    assert evaluate_condition(FieldMissing(field="governing_law"), "", facts).triggered
    assert evaluate_condition(FieldPresent(field="currency"), "", facts).triggered
    assert not evaluate_condition(FieldPresent(field="governing_law"), "", facts).triggered


def test_numeric_conditions() -> None:
    facts = {"total_amount": 50}
    assert evaluate_condition(NumericLt(field="total_amount", value=100), "", facts).triggered
    assert not evaluate_condition(NumericGt(field="total_amount", value=100), "", facts).triggered


def test_date_conditions() -> None:
    facts = {"delivery_date": "2026-12-01"}
    before = DateBefore(field="delivery_date", value=date(2027, 1, 1))
    after = DateAfter(field="delivery_date", value=date(2027, 1, 1))
    assert evaluate_condition(before, "", facts).triggered
    assert not evaluate_condition(after, "", facts).triggered


def test_missing_numeric_fact_raises() -> None:
    with pytest.raises(TypeError):
        evaluate_condition(NumericLt(field="total_amount", value=100), "", {})


def test_invalid_regex_rejected_at_load() -> None:
    with pytest.raises(ValidationError):
        RegexMatch(pattern="([unclosed")


# ---------- 规则加载 ----------


def test_load_default_rules() -> None:
    rules = load_rules()
    assert len(rules) >= 5
    assert [r.risk_level for r in rules if r.rule_id == "R-DIS-001"] == ["red"]


def test_load_rejects_duplicate_ids(tmp_path: Path) -> None:
    rule = {
        "rule_id": "R-PAY-001",
        "title": "t",
        "category": "payment",
        "risk_level": "red",
        "reason": "r",
        "suggestion": "s",
        "condition": {"type": "contains_any", "keywords": ["x"]},
        "source": "src",
    }
    path = tmp_path / "rules.yaml"
    payload = {"version": 1, "rules": [rule, {**rule, "title": "t2"}]}
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="重复"):
        load_rules(path)


def test_load_rejects_empty_rules(tmp_path: Path) -> None:
    path = tmp_path / "rules.yaml"
    path.write_text(yaml.safe_dump({"version": 1, "rules": []}), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_rules(path)


def test_load_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_rules(tmp_path / "nope.yaml")


def test_rule_id_pattern_enforced() -> None:
    with pytest.raises(ValidationError):
        RuleSet.model_validate(
            {
                "version": 1,
                "rules": [
                    {
                        "rule_id": "BAD-1",
                        "title": "t",
                        "category": "payment",
                        "risk_level": "red",
                        "reason": "r",
                        "suggestion": "s",
                        "condition": {"type": "contains_any", "keywords": ["x"]},
                        "source": "src",
                    }
                ],
            }
        )


# ---------- 规则求值 ----------


def _by_rule_id(evaluations):
    return {e.rule_id: e for e in evaluations}


def test_sample_contract_levels(sample_state: ContractReviewState) -> None:
    evaluations = evaluate_rules(load_rules(), sample_state.clauses, sample_state.raw_text)
    results = _by_rule_id(evaluations)

    assert results["R-TRD-001"].risk_level == "yellow"
    assert results["R-PAY-001"].risk_level == "red"
    assert results["R-PAY-002"].risk_level == "pass"
    assert results["R-DIS-001"].risk_level == "red"
    assert results["R-DIS-002"].risk_level == "red"
    assert overall_level(evaluations) == "red"
    assert len(evaluations) == len(load_rules())


def test_triggered_rule_has_grounded_evidence(sample_state: ContractReviewState) -> None:
    evaluations = evaluate_rules(load_rules(), sample_state.clauses, sample_state.raw_text)
    advance = _by_rule_id(evaluations)["R-PAY-001"]
    assert advance.evidence, "触发规则必须带证据"
    evidence = advance.evidence[0]
    assert evidence.grounded
    assert evidence.quote == "100% advance payment"
    assert sample_state.raw_text[evidence.start : evidence.end] == evidence.quote
    assert advance.clause_ids == [evidence.clause_id]
    assert advance.requires_human


def test_clean_contract_all_pass(clean_state: ContractReviewState) -> None:
    evaluations = evaluate_rules(load_rules(), clean_state.clauses, clean_state.raw_text)
    assert all(e.risk_level == "pass" for e in evaluations)
    assert overall_level(evaluations) == "pass"


def test_missing_required_field_yields_yellow() -> None:
    rule = RuleDefinition(
        rule_id="R-LAW-001",
        title="适用法律缺失",
        category="dispute",
        risk_level="red",
        reason="未约定适用法律",
        suggestion="补充适用法律条款",
        requires_fields=["governing_law"],
        condition=FieldPresent(field="governing_law"),
        source="test",
    )
    evaluations = evaluate_rules([rule], [], "", facts={})
    assert evaluations[0].risk_level == "yellow"
    assert evaluations[0].requires_human
    assert "缺少字段" in evaluations[0].reason


def test_rule_execution_error_becomes_system_red() -> None:
    rule = RuleDefinition(
        rule_id="R-NUM-001",
        title="金额阈值",
        category="payment",
        risk_level="yellow",
        reason="金额过低",
        suggestion="核对金额",
        condition=NumericGt(field="total_amount", value=1_000_000),
        source="test",
    )
    evaluations = evaluate_rules([rule], [], "", facts={})
    assert evaluations[0].risk_level == "red"
    assert evaluations[0].is_system_finding
    assert evaluations[0].requires_human
    assert "规则执行异常" in evaluations[0].reason


def test_empty_rule_set_rejected() -> None:
    with pytest.raises(ValueError, match="规则集为空"):
        evaluate_rules([], [], "")


def test_overall_level_aggregation() -> None:
    clause = Clause(clause_id="C001", text="x", start=0, end=1)
    rule_yellow = RuleDefinition(
        rule_id="R-PAY-001",
        title="t",
        category="payment",
        risk_level="yellow",
        reason="r",
        suggestion="s",
        condition=ContainsAny(keywords=["x"]),
        source="test",
    )
    evaluations = evaluate_rules([rule_yellow], [clause], "x")
    assert overall_level(evaluations) == "yellow"
