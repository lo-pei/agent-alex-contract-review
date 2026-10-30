"""规则引擎与条件 DSL 测试：等级、证据、缺失字段、异常 fail-closed、加载校验。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.nodes.ingest import ingest_document
from app.nodes.segment import segment_clauses
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
    assert len(rules) == 13
    assert len({r.rule_id for r in rules}) == len(rules)
    assert [r.risk_level for r in rules if r.rule_id == "R-DIS-001"] == ["red"]

    by_id = {r.rule_id: r for r in rules}
    # 字段规则必须显式声明依赖抽取，才能在抽取降级时被跳过
    assert by_id["R-DLV-001"].requires_extraction
    assert by_id["R-INP-001"].requires_extraction
    assert not by_id["R-PAY-001"].requires_extraction
    # 阶段 4 新增的 6 条都是纯文本规则（不依赖抽取）
    new_rules = {
        "R-DIS-003": "red",
        "R-DIS-004": "red",
        "R-INS-001": "yellow",
        "R-INC-001": "yellow",
        "R-INC-002": "yellow",
        "R-INP-002": "yellow",
    }
    for rule_id, level in new_rules.items():
        assert by_id[rule_id].risk_level == level
        assert not by_id[rule_id].requires_extraction


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
    evaluations = evaluate_rules(
        load_rules(),
        sample_state.clauses,
        sample_state.raw_text,
        extraction_available=False,
    )
    results = _by_rule_id(evaluations)

    assert results["R-TRD-001"].risk_level == "yellow"
    assert results["R-PAY-001"].risk_level == "red"
    assert results["R-PAY-002"].risk_level == "pass"
    assert results["R-DIS-001"].risk_level == "red"
    assert results["R-DIS-002"].risk_level == "red"
    # 无抽取时字段规则跳过：既不算 pass 命中，也不算风险
    assert results["R-DLV-001"].skipped
    assert results["R-INP-001"].skipped
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
    evaluations = evaluate_rules(
        load_rules(),
        clean_state.clauses,
        clean_state.raw_text,
        extraction_available=False,
    )
    assert all(e.risk_level == "pass" for e in evaluations)
    assert {e.rule_id for e in evaluations if e.skipped} == {"R-DLV-001", "R-INP-001"}
    assert overall_level(evaluations) == "pass"


def test_field_rule_skipped_when_extraction_unavailable() -> None:
    rule = RuleDefinition(
        rule_id="R-DLV-001",
        title="未约定交付期限",
        category="delivery",
        risk_level="yellow",
        reason="未抽取到交付期限",
        suggestion="明确交付期限",
        requires_extraction=True,
        condition=FieldMissing(field="delivery_date"),
        source="test",
    )

    evaluations = evaluate_rules([rule], [], "", facts={}, extraction_available=False)

    assert evaluations[0].risk_level == "pass"
    assert evaluations[0].skipped
    assert not evaluations[0].requires_human
    assert "未执行" in evaluations[0].reason


def test_field_rule_triggers_when_field_missing() -> None:
    rule = RuleDefinition(
        rule_id="R-DLV-001",
        title="未约定交付期限",
        category="delivery",
        risk_level="yellow",
        reason="未抽取到交付期限",
        suggestion="明确交付期限",
        requires_extraction=True,
        condition=FieldMissing(field="delivery_date"),
        source="test",
    )

    evaluations = evaluate_rules([rule], [], "", facts={}, extraction_available=True)

    assert evaluations[0].risk_level == "yellow"
    assert not evaluations[0].skipped
    assert evaluations[0].reason == "未抽取到交付期限"


def test_field_rule_passes_when_field_present() -> None:
    rule = RuleDefinition(
        rule_id="R-INP-001",
        title="未约定检验标准",
        category="inspection",
        risk_level="yellow",
        reason="未抽取到检验标准",
        suggestion="明确检验标准",
        requires_extraction=True,
        condition=FieldMissing(field="inspection_standard"),
        source="test",
    )

    evaluations = evaluate_rules(
        [rule], [], "", facts={"inspection_standard": "SGS"}, extraction_available=True
    )

    assert evaluations[0].risk_level == "pass"
    assert not evaluations[0].skipped


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


# ---------- 阶段 4 新增规则 ----------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = PROJECT_ROOT / "data" / "contracts"
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"

#: 新增规则在 50 份模拟合同上的预期命中集合（语料验证基线，误报会立刻让本测试失败）
EXPECTED_CORPUS_HITS: dict[str, set[str]] = {
    "R-DIS-003": {"C47"},
    "R-DIS-004": {"C48"},
    "R-INS-001": {"C04"},
    "R-INC-001": {"C11"},
    "R-INC-002": {"C23"},
    "R-INP-002": {"C09"},
}

NEW_RULE_CASES = [
    pytest.param(
        "R-DIS-003",
        "9.1 任何一方均有权选择：（a）将争议提交上海仲裁委员会仲裁；"
        "或（b）向有管辖权的人民法院提起诉讼。",
        "9.1 争议提交上海仲裁委员会仲裁。9.2 仲裁裁决是终局的，对双方均有约束力。",
        id="or-arbitration-or-litigation",
    ),
    pytest.param(
        "R-DIS-004",
        "9.2 仲裁裁决作出后，任何一方对裁决结果仍有异议的，可在 30 日内向法院提起诉讼。",
        "9.2 仲裁裁决是终局的，对双方均有约束力，任何一方不得再向法院起诉。",
        id="arbitration-then-litigation",
    ),
    pytest.param(
        "R-INS-001",
        "贸易术语：CIF Rotterdam Incoterms® 2020。卖方应自付费用投保一切险。",
        "贸易术语：CIF Rotterdam Incoterms® 2020。卖方按 ICC(C) 投保，保额为合同价的110%。",
        id="cif-insurance-without-amount",
    ),
    pytest.param(
        "R-INC-001",
        "贸易术语：FOB Shanghai Incoterms® 2020。运费由卖方预付至 Antwerp。",
        "贸易术语：FOB Shanghai Incoterms® 2020。运费由买方承担。",
        id="fob-with-seller-freight",
    ),
    pytest.param(
        "R-INC-002",
        "贸易术语：FOB Shenzhen Incoterms® 2020。货物为集装箱整箱（FCL），在堆场交付。",
        "贸易术语：FOB Shanghai Incoterms® 2020。货物为散装钢材，装船后风险转移。",
        id="fob-with-fcl-container",
    ),
    pytest.param(
        "R-INP-002",
        "买方应在货物到达目的港后24小时内完成检验，并在4小时内发出书面通知。",
        "买方应在货物到达目的港后14天内完成检验，并向卖方发出书面通知。",
        id="inspection-within-hours",
    ),
]


def _evaluate_one_rule(rule_id: str, text: str):
    rules = [rule for rule in load_rules() if rule.rule_id == rule_id]
    assert len(rules) == 1, rule_id
    clause = Clause(clause_id="C001", text=text, start=0, end=len(text))
    return evaluate_rules(rules, [clause], text, extraction_available=False)[0]


@pytest.mark.parametrize(("rule_id", "positive", "negative"), NEW_RULE_CASES)
def test_new_rule_matches_only_expected_wording(
    rule_id: str, positive: str, negative: str
) -> None:
    triggered = _evaluate_one_rule(rule_id, positive)
    assert triggered.risk_level != "pass"
    assert triggered.evidence, "触发时必须给出可定位证据"
    evidence = triggered.evidence[0]
    assert evidence.grounded
    assert positive[evidence.start : evidence.end] == evidence.quote

    assert _evaluate_one_rule(rule_id, negative).risk_level == "pass"


#: 英文 / 同义改写用例（ISSUE-021：上一轮留出集暴露英文条款漏报，规则 version 4 补齐）
ENGLISH_RULE_CASES = [
    pytest.param(
        "R-DIS-003",
        "9.2 The claimant may at its option either submit the dispute to arbitration, "
        "or bring an action before the competent court at the defendant's place of business.",
        # 裁决可在法院执行是正常条款，不应判为“或裁或审”
        "9.2 Disputes shall be submitted to arbitration and the award may be enforced "
        "in any court of competent jurisdiction.",
        id="en-or-arbitration-or-court",
    ),
    pytest.param(
        "R-DIS-004",
        "9.2 If either party is dissatisfied with the award, it may bring an action "
        "before the competent court within 30 days.",
        # 终局 + 法定执行，不触发；撤销裁决（set aside）也不触发
        "9.2 The award shall be final and binding, and may be enforced in any court. "
        "Either party may apply to set aside the award on grounds of procedural error.",
        id="en-award-then-court",
    ),
    pytest.param(
        "R-INS-001",
        "Trade term: CIF Genoa Incoterms 2020. Seller shall insure the goods against all risks "
        "for the benefit of Buyer.",
        "Trade term: CIF Genoa Incoterms 2020. Seller shall insure the goods against all risks "
        "for 110% of the invoice value.",
        id="en-cif-insurance-without-amount",
    ),
    pytest.param(
        "R-INC-001",
        "Trade term: FOB Ningbo Incoterms 2020. Ocean freight shall be prepaid by the seller "
        "to the port of destination.",
        "Trade term: FOB Ningbo Incoterms 2020. Freight and insurance shall be for the buyer's "
        "account.",
        id="en-fob-with-seller-freight",
    ),
    pytest.param(
        "R-INC-001",
        # 中文同义改写：费用名被夹在中间，语序与 C11 不同（上一轮 H03 漏报的写法）
        "贸易术语：FOB Qingdao Incoterms 2020。海运费及舱位订舱费用由卖方承担并预付至目的港。",
        # 出口报关费本就由卖方承担，不能算“运费由卖方”
        "贸易术语：FOB Qingdao Incoterms 2020。出口报关费用由卖方承担，主运费由买方承担。",
        id="zh-freight-cost-phrasing",
    ),
    pytest.param(
        "R-INP-002",
        "Buyer shall inspect the goods within 48 hours after discharge and give notice "
        "of any defect within 12 hours.",
        "Buyer shall inspect the goods within 14 days after discharge and give notice "
        "of any defect within a reasonable time.",
        id="en-inspection-within-hours",
    ),
]


@pytest.mark.parametrize(("rule_id", "positive", "negative"), ENGLISH_RULE_CASES)
def test_rules_match_english_and_paraphrased_wording(
    rule_id: str, positive: str, negative: str
) -> None:
    triggered = _evaluate_one_rule(rule_id, positive)
    assert triggered.risk_level != "pass"
    assert triggered.evidence
    for evidence in triggered.evidence:
        assert evidence.grounded
        assert positive[evidence.start : evidence.end] == evidence.quote

    assert _evaluate_one_rule(rule_id, negative).risk_level == "pass"


#: 规则 version 5 的新增写法（holdout3 暴露的 3 类 + 保额邻近判定的回归）
PARAPHRASE_RULE_CASES = [
    pytest.param(
        "R-DIS-003",
        # “既可以…也可以…”：与“或/或者”同义的并列连接词
        "9.2 争议发生后，双方既可以提交新加坡国际仲裁中心仲裁，"
        "也可以向有管辖权的法院提起诉讼。",
        # 仲裁终局 + 仅可申请撤销裁决（法定救济），不应判为“或裁或审”
        "9.2 仲裁裁决为终局裁定，对双方均有约束力；任何一方仅可依据法定情形申请撤销裁决。",
        id="zh-either-or-court",
    ),
    pytest.param(
        "R-INC-001",
        # “卖方须支付…主运费”：情态词插在“卖方”与“支付”之间
        "贸易术语：FCA Zhengzhou Incoterms 2020。卖方须支付自郑州至阿拉木图的主运费及订舱费用。",
        # 出口报关费本就应由卖方承担，且主运费由买方承担
        "贸易术语：FCA Zhengzhou Incoterms 2020。卖方须支付出口报关费用，主运费由买方承担。",
        id="zh-seller-must-pay-freight",
    ),
    pytest.param(
        "R-INP-002",
        "Buyer shall examine the goods within thirty-six (36) hours after discharge at Jeddah.",
        "Buyer shall examine the goods within 30 days after discharge and notify the Seller "
        "within 15 days after inspection.",
        id="en-inspect-before-worded-hours",
    ),
    pytest.param(
        "R-INP-002",
        "Buyer shall notify the Seller of any claim within Twelve (12) hours after delivery.",
        "Buyer shall notify the Seller of any claim within 15 days after delivery.",
        id="en-claim-within-worded-hours",
    ),
    pytest.param(
        "R-INS-001",
        # 保额判定必须是“保险语境邻近”：付款比例 40% 不能压制本规则（holdout3 H27 缺陷）
        "贸易术语：CIF Jebel Ali Incoterms 2020。卖方负责投保一切险，保险单交付买方。\n"
        "7.1 付款方式：40% 合同价电汇预付，剩余 60% 见提单副本后 30 天内支付。",
        "贸易术语：CIF Jebel Ali Incoterms 2020。卖方投保一切险，保险金额为合同价的 110%。\n"
        "7.1 付款方式：40% 合同价电汇预付，剩余 60% 见提单副本后支付。",
        id="zh-payment-percentage-is-not-sum-insured",
    ),
    pytest.param(
        "R-INS-001",
        "Trade term: CIF Antwerp Incoterms 2020. Seller shall insure the goods against all "
        "risks in favour of Buyer.",
        "Trade term: CIF Antwerp Incoterms 2020. Seller shall insure the goods against all "
        "risks with a sum insured of USD 391,600, being 110% of the contract price.",
        id="en-sum-insured-usd",
    ),
]


@pytest.mark.parametrize(("rule_id", "positive", "negative"), PARAPHRASE_RULE_CASES)
def test_rules_match_new_paraphrase_wording(
    rule_id: str, positive: str, negative: str
) -> None:
    triggered = _evaluate_one_rule(rule_id, positive)
    assert triggered.risk_level != "pass"
    assert triggered.evidence
    for evidence in triggered.evidence:
        assert evidence.grounded
        assert positive[evidence.start : evidence.end] == evidence.quote

    assert _evaluate_one_rule(rule_id, negative).risk_level == "pass"


@pytest.mark.parametrize(
    "text",
    [
        # CIF 但合同完全没写保险：由 Incoterms 默认规则补位，不触发本规则（避免噪声）
        "贸易术语：CIF Rotterdam Incoterms® 2020。付款方式：不可撤销即期信用证。",
        # 写了保险但没有金额，但不是 CIF/CIP 术语
        "贸易术语：FOB Shanghai Incoterms® 2020。卖方应自付费用投保一切险。",
        # 英文写法已给出比例
        "CIF Hamburg Incoterms 2020. Seller insures the goods for 110% of the contract price.",
    ],
)
def test_insurance_rule_ignores_non_triggering_context(text: str) -> None:
    assert _evaluate_one_rule("R-INS-001", text).risk_level == "pass"


def _load_state(path: Path) -> ContractReviewState:
    state = ContractReviewState(
        review_id="test-corpus", source_filename=path.name, source_path=str(path)
    )
    state = ContractReviewState.model_validate({**state.model_dump(), **ingest_document(state)})
    return ContractReviewState.model_validate({**state.model_dump(), **segment_clauses(state)})


def test_new_rules_stay_precise_on_simulated_corpus() -> None:
    if not CONTRACTS_DIR.is_dir():
        pytest.skip("缺少 data/contracts 模拟合同目录")
    new_rules = [rule for rule in load_rules() if rule.rule_id in EXPECTED_CORPUS_HITS]
    assert len(new_rules) == len(EXPECTED_CORPUS_HITS)

    hits = {rule_id: set() for rule_id in EXPECTED_CORPUS_HITS}
    for path in sorted(CONTRACTS_DIR.glob("C*.md")):
        state = _load_state(path)
        for evaluation in evaluate_rules(
            new_rules, state.clauses, state.raw_text, extraction_available=False
        ):
            if evaluation.risk_level == "pass":
                continue
            hits[evaluation.rule_id].add(path.stem)
            assert evaluation.evidence, f"{path.stem}:{evaluation.rule_id} 触发但无证据"
            for evidence in evaluation.evidence:
                assert state.raw_text[evidence.start : evidence.end] == evidence.quote
                assert evidence.grounded
    assert hits == EXPECTED_CORPUS_HITS


@pytest.mark.parametrize("name", ["sample_sales_contract.txt", "sample_clean_contract.txt"])
def test_new_rules_do_not_fire_on_samples(name: str) -> None:
    state = _load_state(SAMPLES_DIR / name)
    new_rules = [rule for rule in load_rules() if rule.rule_id in EXPECTED_CORPUS_HITS]
    evaluations = evaluate_rules(
        new_rules, state.clauses, state.raw_text, extraction_available=False
    )
    assert [e.rule_id for e in evaluations if e.risk_level != "pass"] == []


HOLDOUT_DIR = PROJECT_ROOT / "data" / "contracts_holdout"

#: 上一轮独立留出集（H01–H08）在规则 version 4 下的命中集合。
#: 注意：这批合同已被用来定位并修复漏报，**不再是留出集**，只是回归守卫（ADR-011）。
EXPECTED_HOLDOUT_HITS: dict[str, set[str]] = {
    "R-DIS-003": {"H01"},
    "R-INS-001": {"H02"},
    "R-INC-001": {"H03"},
    "R-INP-002": {"H05"},
    "R-DIS-004": {"H06"},
    "R-INC-002": {"H07"},
    "R-PAY-002": {"H08"},
}


def test_previous_holdout_hits_are_stable() -> None:
    if not HOLDOUT_DIR.is_dir():
        pytest.skip("缺少 data/contracts_holdout 目录")
    rules = [rule for rule in load_rules() if rule.rule_id in EXPECTED_HOLDOUT_HITS]
    hits = {rule_id: set() for rule_id in EXPECTED_HOLDOUT_HITS}
    for path in sorted(HOLDOUT_DIR.glob("H*.md")):
        state = _load_state(path)
        for evaluation in evaluate_rules(
            rules, state.clauses, state.raw_text, extraction_available=False
        ):
            if evaluation.risk_level != "pass":
                hits[evaluation.rule_id].add(path.stem)
    assert hits == EXPECTED_HOLDOUT_HITS

    # H04 是干净对照：13 条规则里除字段规则（跳过）外必须全部 pass
    clean = _load_state(HOLDOUT_DIR / "H04.md")
    evaluations = evaluate_rules(
        load_rules(), clean.clauses, clean.raw_text, extraction_available=False
    )
    assert [e.rule_id for e in evaluations if e.risk_level != "pass"] == []


HOLDOUT2_DIR = PROJECT_ROOT / "data" / "contracts_holdout2"

#: holdout2（H09–H20，12 份）在规则 version 4 下的命中集合。
#: 这批合同暴露过“子串误命中（Pacific→CIF）”与“运费窗口截断”两个缺陷，
#: 修复后全对；它同样**不再是留出集**，只作回归守卫（对外报数用 holdout3）。
EXPECTED_HOLDOUT2_HITS: dict[str, set[str]] = {
    "R-DIS-003": {"H09"},
    "R-DIS-004": {"H12"},
    "R-INS-001": {"H14"},
    "R-INC-001": {"H11", "H19"},
    "R-INC-002": {"H16"},
    "R-INP-002": {"H15"},
    "R-PAY-001": {"H18"},
    "R-PAY-002": {"H17"},
}


def test_holdout2_hits_are_stable() -> None:
    if not HOLDOUT2_DIR.is_dir():
        pytest.skip("缺少 data/contracts_holdout2 目录")
    rules = [rule for rule in load_rules() if rule.rule_id in EXPECTED_HOLDOUT2_HITS]
    hits = {rule_id: set() for rule_id in EXPECTED_HOLDOUT2_HITS}
    for path in sorted(HOLDOUT2_DIR.glob("H*.md")):
        state = _load_state(path)
        for evaluation in evaluate_rules(
            rules, state.clauses, state.raw_text, extraction_available=False
        ):
            if evaluation.risk_level != "pass":
                hits[evaluation.rule_id].add(path.stem)
    assert hits == EXPECTED_HOLDOUT2_HITS

    # H10/H13/H20 是干净对照（含“出口报关费用由卖方承担，主运费由买方承担”这类近似句）
    for name in ("H10", "H13", "H20"):
        state = _load_state(HOLDOUT2_DIR / f"{name}.md")
        evaluations = evaluate_rules(
            load_rules(), state.clauses, state.raw_text, extraction_available=False
        )
        assert [e.rule_id for e in evaluations if e.risk_level != "pass"] == [], name


HOLDOUT3_DIR = PROJECT_ROOT / "data" / "contracts_holdout3"

#: holdout3（H21–H28，8 份）在规则 version 5 下的命中集合。
#: 这批合同暴露过“亦可”“卖方负责支付”“thirty-six (36) hours”三类写法，
#: 修复后全对；它同样**不再是留出集**，只作回归守卫（对外报数用 holdout4）。
EXPECTED_HOLDOUT3_HITS: dict[str, set[str]] = {
    "R-DIS-003": {"H21"},
    "R-INC-001": {"H22"},
    "R-INS-001": {"H23"},
    "R-INP-002": {"H24"},
    "R-INC-002": {"H25"},
    "R-PAY-002": {"H26"},
    "R-DIS-004": {"H26"},
}


def test_holdout3_hits_are_stable() -> None:
    if not HOLDOUT3_DIR.is_dir():
        pytest.skip("缺少 data/contracts_holdout3 目录")
    rules = [rule for rule in load_rules() if rule.rule_id in EXPECTED_HOLDOUT3_HITS]
    hits = {rule_id: set() for rule_id in EXPECTED_HOLDOUT3_HITS}
    for path in sorted(HOLDOUT3_DIR.glob("H*.md")):
        state = _load_state(path)
        for evaluation in evaluate_rules(
            rules, state.clauses, state.raw_text, extraction_available=False
        ):
            if evaluation.risk_level != "pass":
                hits[evaluation.rule_id].add(path.stem)
    assert hits == EXPECTED_HOLDOUT3_HITS

    # H27/H28 是干净对照：已写明 110% 保额的 CIF，且付款里还有别的比例（保额邻近判定的回归）
    for name in ("H27", "H28"):
        state = _load_state(HOLDOUT3_DIR / f"{name}.md")
        evaluations = evaluate_rules(
            load_rules(), state.clauses, state.raw_text, extraction_available=False
        )
        assert [e.rule_id for e in evaluations if e.risk_level != "pass"] == [], name


HOLDOUT4_DIR = PROJECT_ROOT / "data" / "contracts_holdout4"

#: holdout4（H29–H40，12 份）的命中集合。
#: 阶段 4 第 5 轮（规则 version 6）修掉了 H39 漏报——英文情态动词与动词之间插入时间状语
#: （“may, within 30 days …, commence proceedings”），因此 H39 已进表；
#: holdout4 自此**降级为回归集**，对外报数改用新写的 data/contracts_holdout5（见下）。
EXPECTED_HOLDOUT4_HITS: dict[str, set[str]] = {
    "R-INS-001": {"H29"},
    "R-INC-001": {"H30", "H40"},
    "R-DIS-003": {"H31", "H38"},
    "R-DIS-004": {"H39"},
    "R-INP-002": {"H33"},
    "R-INC-002": {"H35"},
    "R-PAY-002": {"H37"},
}


def test_holdout4_hits_are_stable() -> None:
    if not HOLDOUT4_DIR.is_dir():
        pytest.skip("缺少 data/contracts_holdout4 目录")
    rules = [rule for rule in load_rules() if rule.rule_id in EXPECTED_HOLDOUT4_HITS]
    hits = {rule_id: set() for rule_id in EXPECTED_HOLDOUT4_HITS}
    for path in sorted(HOLDOUT4_DIR.glob("H*.md")):
        state = _load_state(path)
        for evaluation in evaluate_rules(
            rules, state.clauses, state.raw_text, extraction_available=False
        ):
            if evaluation.risk_level != "pass":
                hits[evaluation.rule_id].add(path.stem)
    assert hits == EXPECTED_HOLDOUT4_HITS

    # H32（仅可申请撤销裁决）/ H34、H36（已写保额）是干净对照
    for name in ("H32", "H34", "H36"):
        state = _load_state(HOLDOUT4_DIR / f"{name}.md")
        evaluations = evaluate_rules(
            load_rules(), state.clauses, state.raw_text, extraction_available=False
        )
        assert [e.rule_id for e in evaluations if e.risk_level != "pass"] == [], name

    # H39 已修复（规则 version 6）：modal 与动词之间插时间状语仍要判 red
    h39 = _load_state(HOLDOUT4_DIR / "H39.md")
    evaluations = evaluate_rules(
        [rule for rule in load_rules() if rule.rule_id == "R-DIS-004"],
        h39.clauses,
        h39.raw_text,
        extraction_available=False,
    )
    assert evaluations[0].risk_level == "red", "H39 回归：时间状语插入后又被漏报"


HOLDOUT5_DIR = PROJECT_ROOT / "data" / "contracts_holdout5"

#: holdout5（H41–H52，12 份）是阶段 4 第 5 轮**修 H39 之前**写下的盲测集，
#: 盲测基线为 P=1.00 / R=0.90 / F1=0.947（唯一漏报 H41，与 H39 同型不同写法）。
#: 修复后本表变成回归守卫；对外报数一律引用基线文件
#: `eval/results/rules-holdout5-baseline-20261028.json`，不引用修复后的 1.0。
EXPECTED_HOLDOUT5_HITS: dict[str, set[str]] = {
    "R-DIS-004": {"H41", "H42"},
    "R-INC-001": {"H44"},
    "R-INS-001": {"H45"},
    "R-DIS-003": {"H46"},
    "R-INP-002": {"H47"},
    "R-DIS-001": {"H48"},
    "R-TRD-001": {"H49"},
    "R-INC-002": {"H50"},
    "R-PAY-001": {"H51"},
}


def test_holdout5_hits_are_stable() -> None:
    if not HOLDOUT5_DIR.is_dir():
        pytest.skip("缺少 data/contracts_holdout5 目录")
    rules = [rule for rule in load_rules() if rule.rule_id in EXPECTED_HOLDOUT5_HITS]
    hits = {rule_id: set() for rule_id in EXPECTED_HOLDOUT5_HITS}
    for path in sorted(HOLDOUT5_DIR.glob("H*.md")):
        state = _load_state(path)
        for evaluation in evaluate_rules(
            rules, state.clauses, state.raw_text, extraction_available=False
        ):
            if evaluation.risk_level != "pass":
                hits[evaluation.rule_id].add(path.stem)
    assert hits == EXPECTED_HOLDOUT5_HITS

    # H43（英文“仅可依法申请撤销裁决”）/ H52（全条款合规）是干净对照：
    # 修复 H39 时不能让“裁决的法定救济”被误判成“先裁后审”。
    for name in ("H43", "H52"):
        state = _load_state(HOLDOUT5_DIR / f"{name}.md")
        evaluations = evaluate_rules(
            load_rules(), state.clauses, state.raw_text, extraction_available=False
        )
        assert [e.rule_id for e in evaluations if e.risk_level != "pass"] == [], name


HOLDOUT6_DIR = PROJECT_ROOT / "data" / "contracts_holdout6"

#: holdout6（H53–H64，12 份**纯英文**）是阶段 4 第 6 轮**改规则之前**写下的盲测集。
#: 盲测基线（规则 version 6）：`TP=8 FP=0 FN=3 TN=121` → P=1.00 / R=0.727 / F1=0.842，
#: 漏报 H53（FOB 下“arrange and pay for the ocean freight”倒装写法）、
#: H55（“or, at the Buyer's option, by proceedings …”连接词后带逗号）、
#: H61（“pay the entire contract price before shipment”未写“in advance”）。
#: 阶段 4 第 6 轮（规则 version 7）已修这三处，本表随之更新 → **holdout6 降级为回归集**；
#: 对外数字只引基线文件 `eval/results/rules-holdout6-baseline-20261028.json`，
#: 修复后的 `rules-holdout6-20261028.json`（11/0/0）只作回归，下一批对外数字须来自 holdout7。
EXPECTED_HOLDOUT6_HITS: dict[str, set[str]] = {
    "R-INS-001": {"H54"},
    "R-DIS-004": {"H56"},
    "R-DIS-001": {"H57"},
    "R-INC-002": {"H58"},
    "R-TRD-001": {"H59"},
    "R-INP-002": {"H60"},
    "R-PAY-002": {"H64"},
    "R-DIS-002": {"H64"},
    "R-INC-001": {"H53"},
    "R-DIS-003": {"H55"},
    "R-PAY-001": {"H61"},
}


def test_holdout6_hits_are_stable() -> None:
    if not HOLDOUT6_DIR.is_dir():
        pytest.skip("缺少 data/contracts_holdout6 目录")
    rules = [rule for rule in load_rules() if rule.rule_id in EXPECTED_HOLDOUT6_HITS]
    hits = {rule_id: set() for rule_id in EXPECTED_HOLDOUT6_HITS}
    for path in sorted(HOLDOUT6_DIR.glob("H*.md")):
        state = _load_state(path)
        for evaluation in evaluate_rules(
            rules, state.clauses, state.raw_text, extraction_available=False
        ):
            if evaluation.risk_level != "pass":
                hits[evaluation.rule_id].add(path.stem)
    assert hits == EXPECTED_HOLDOUT6_HITS

    # H62（CIF + 110% 保额 + 德国法 + DIS 仲裁）/ H63（FCA + 20% 预付 + 10 天检验）
    # 是全条款合规的干净对照：放宽英文写法时不得引入误报。
    for name in ("H62", "H63"):
        state = _load_state(HOLDOUT6_DIR / f"{name}.md")
        evaluations = evaluate_rules(
            load_rules(), state.clauses, state.raw_text, extraction_available=False
        )
        assert [e.rule_id for e in evaluations if e.risk_level != "pass"] == [], name


HOLDOUT7_DIR = PROJECT_ROOT / "data" / "contracts_holdout7"

#: holdout7（H65–H76，12 份**中英混合**）是阶段 4 第 7 轮**改规则之前**写下的盲测集。
#: 盲测基线（规则 version 7）：`TP=7 FP=0 FN=4 TN=121` → P=1.00 / R=0.636 / F1=0.778，
#: 合同级 `TP=6 FP=0 FN=4`，漏报 H65（FOB 下“the ocean freight … shall be for the Seller's account”
#: 的迂回写法）、H66（仲裁句与法院句分属两句的“或裁或审”）、H67（中文“装运前一次性支付…全部价款”）、
#: H69（裁决后“bring the matter before the courts”）。
#: 按 ADR-011 留出纪律，第 7 轮第一步先把四个漏报写成空集合（跑通即基线快照）；第二步
#: （version 8）修完四处写法后本测试果然失败并点名这四份合同，**此时才翻表降级**——
#: 本批自此只作回归守卫，对外数字仍只引基线文件
#: `eval/results/rules-holdout7-baseline-20261029.json`（R=0.636），修后的 11/0/0 不再引用。
EXPECTED_HOLDOUT7_HITS: dict[str, set[str]] = {
    "R-INS-001": {"H68"},
    "R-TRD-001": {"H70"},
    "R-INC-002": {"H71"},
    "R-INP-002": {"H72"},
    "R-PAY-002": {"H73"},
    "R-DIS-002": {"H73"},
    "R-DIS-001": {"H74"},
    # 以下四条是盲测基线漏报，version 8 修好后翻表（修前为空集合，见上）
    "R-INC-001": {"H65"},
    "R-DIS-003": {"H66"},
    "R-PAY-001": {"H67"},
    "R-DIS-004": {"H69"},
}


def test_holdout7_hits_are_stable() -> None:
    if not HOLDOUT7_DIR.is_dir():
        pytest.skip("缺少 data/contracts_holdout7 目录")
    rules = [rule for rule in load_rules() if rule.rule_id in EXPECTED_HOLDOUT7_HITS]
    hits = {rule_id: set() for rule_id in EXPECTED_HOLDOUT7_HITS}
    for path in sorted(HOLDOUT7_DIR.glob("H*.md")):
        state = _load_state(path)
        for evaluation in evaluate_rules(
            rules, state.clauses, state.raw_text, extraction_available=False
        ):
            if evaluation.risk_level != "pass":
                hits[evaluation.rule_id].add(path.stem)
    assert hits == EXPECTED_HOLDOUT7_HITS

    # H75（CIF + 110% + ICC(C) + 荷兰法 + NAI 仲裁）/
    # H76（FCA + 20% 预付 + SGS + 中国法 + 新加坡仲裁）
    # 是全条款合规的干净对照：后续放宽写法时不得引入误报。
    for name in ("H75", "H76"):
        state = _load_state(HOLDOUT7_DIR / f"{name}.md")
        evaluations = evaluate_rules(
            load_rules(), state.clauses, state.raw_text, extraction_available=False
        )
        assert [e.rule_id for e in evaluations if e.risk_level != "pass"] == [], name


HOLDOUT8_DIR = PROJECT_ROOT / "data" / "contracts_holdout8"

#: holdout8（H77–H88，5 份英文 / 7 份中文）是阶段 4 第 7 轮之后**新写**的盲测集，
#: 专攻 `version: 8` 之后仍可能漏的写法（见 `data/eval/gold_holdout8.json` 的
#: `annotation_protocol`）。盲测基线（规则 version 8，**改规则之前跑**）：
#: `TP=6 FP=0 FN=5 TN=121` → P=1.00 / R=0.545 / F1=0.706，合同级 `TP=5 FP=0 FN=5`，
#: 漏报 H77（FOB 下“The ocean freight … is on the Seller's account”的介词短语写法）、
#: H78（裁决终局后又允许 `refer the dispute to the courts`）、H79（中文“付清全部货款”，
#: 不含“一次性/装运前”）、H80（“仲裁庭的裁决”+“收到裁决书之日起…提起上诉”，非“仲裁裁决…后”）、
#: H83（`inspect the Goods immediately upon discharge / on the same day`，无“小时”）。
#: 按 ADR-011 留出纪律，本轮先把这五个漏报写成空集合（跑通即基线快照）；下一步修完
#: 规则后本测试必须失败并点名这五份合同，**此时才翻表降级**——本批自此只作回归守卫，
#: 对外数字仍只引基线文件 `eval/results/rules-holdout8-baseline-20261029.json`（R=0.545）。
EXPECTED_HOLDOUT8_HITS: dict[str, set[str]] = {
    "R-TRD-001": {"H81"},
    "R-INC-002": {"H82"},
    "R-INS-001": {"H84"},
    "R-PAY-002": {"H85"},
    "R-DIS-002": {"H85"},
    "R-DIS-001": {"H86"},
    # 以下五条是盲测基线漏报，已在 `version: 9`（阶段 4 第 9 轮）按基线修好并翻表：
    # 改规则后本测试先失败并把 H77/H78/H79/H80/H83 逐个点名，确认无误后才改成“必须命中”。
    "R-INC-001": {"H77"},
    "R-DIS-003": {"H78"},
    "R-PAY-001": {"H79"},
    "R-DIS-004": {"H80"},
    "R-INP-002": {"H83"},
}


def test_holdout8_hits_are_stable() -> None:
    if not HOLDOUT8_DIR.is_dir():
        pytest.skip("缺少 data/contracts_holdout8 目录")
    rules = [rule for rule in load_rules() if rule.rule_id in EXPECTED_HOLDOUT8_HITS]
    hits = {rule_id: set() for rule_id in EXPECTED_HOLDOUT8_HITS}
    for path in sorted(HOLDOUT8_DIR.glob("H*.md")):
        state = _load_state(path)
        for evaluation in evaluate_rules(
            rules, state.clauses, state.raw_text, extraction_available=False
        ):
            if evaluation.risk_level != "pass":
                hits[evaluation.rule_id].add(path.stem)
    assert hits == EXPECTED_HOLDOUT8_HITS

    # H87（CIF + 110% + ICC(C) + 荷兰法 + NAI 仲裁）/
    # H88（FCA + 20% 预付 + SGS + 中国法 + 上海仲裁）
    # 是全条款合规的干净对照：后续放宽写法时不得引入误报。
    for name in ("H87", "H88"):
        state = _load_state(HOLDOUT8_DIR / f"{name}.md")
        evaluations = evaluate_rules(
            load_rules(), state.clauses, state.raw_text, extraction_available=False
        )
        assert [e.rule_id for e in evaluations if e.risk_level != "pass"] == [], name


HOLDOUT9_DIR = PROJECT_ROOT / "data" / "contracts_holdout9"

#: holdout9（H89–H100，5 份英文 / 7 份中文）是阶段 4 第 9 轮修完 `version: 9` 之后**新写**的
#: 盲测集（见 `data/eval/gold_holdout9.json` 的 `annotation_protocol`）。
#: 盲测基线（规则 version 9，**改规则之前跑**）：`TP=6 FP=0 FN=5 TN=121`
#: → P=1.00 / R=0.545 / F1=0.706，合同级 `TP=5 FP=0 FN=5`，漏报 H89（FOB 下
#: “The price is inclusive of all freight charges up to Jebel Ali”）、H90（“Either party may
#: instead elect to have any dispute decided by the courts …”）、H91（中文“全部合同价款一次性
#: 汇入…确认收款后方可发运”，用“收款”而非“收到/收讫…全部货款”）、H92（“向有管辖权的人民法院
#: 请求重新审理”，动词不是上诉/起诉）、H93（检验期限写成中文数字“二十四小时”，规则只认阿拉伯数字）。
#: 按 ADR-011 留出纪律，本批的五个漏报先写成空集合（跑通即基线快照）；第 10 轮修完规则后
#: 本测试如期失败并点名这五份合同，此时才翻表降级——本批自此只作回归守卫，
#: 对外数字仍只引基线文件 `eval/results/rules-holdout9-baseline-20261029.json`（R=0.545）。
EXPECTED_HOLDOUT9_HITS: dict[str, set[str]] = {
    "R-TRD-001": {"H96"},
    "R-INC-002": {"H95"},
    "R-INS-001": {"H94"},
    "R-PAY-002": {"H97"},
    "R-DIS-002": {"H97"},
    "R-DIS-001": {"H98"},
    # 以下五条原为基线漏报（空集合）；`version: 10` 修好后翻成“必须命中”（第 10 轮）
    "R-INC-001": {"H89"},
    "R-DIS-003": {"H90"},
    "R-PAY-001": {"H91"},
    "R-DIS-004": {"H92"},
    "R-INP-002": {"H93"},
}


def test_holdout9_hits_are_stable() -> None:
    if not HOLDOUT9_DIR.is_dir():
        pytest.skip("缺少 data/contracts_holdout9 目录")
    rules = [rule for rule in load_rules() if rule.rule_id in EXPECTED_HOLDOUT9_HITS]
    hits = {rule_id: set() for rule_id in EXPECTED_HOLDOUT9_HITS}
    for path in sorted(HOLDOUT9_DIR.glob("H*.md")):
        state = _load_state(path)
        for evaluation in evaluate_rules(
            rules, state.clauses, state.raw_text, extraction_available=False
        ):
            if evaluation.risk_level != "pass":
                hits[evaluation.rule_id].add(path.stem)
    assert hits == EXPECTED_HOLDOUT9_HITS

    # H99（CFR + 买方投保 110% ICC(A) + 荷兰法 + NAI 仲裁）/
    # H100（CIP + 110% ICC(A) + 中国法 + 上海仲裁）
    # 是全条款合规的干净对照：后续放宽写法时不得引入误报。
    for name in ("H99", "H100"):
        state = _load_state(HOLDOUT9_DIR / f"{name}.md")
        evaluations = evaluate_rules(
            load_rules(), state.clauses, state.raw_text, extraction_available=False
        )
        assert [e.rule_id for e in evaluations if e.risk_level != "pass"] == [], name


HOLDOUT10_DIR = PROJECT_ROOT / "data" / "contracts_holdout10"

#: holdout10（H101–H112，5 份英文 / 7 份中文）是阶段 4 第 10 轮修完 `version: 10` 之后**新写**
#: 的盲测集（见 `data/eval/gold_holdout10.json` 的 `annotation_protocol`）。
#: 盲测基线（规则 version 10，**改规则之前跑**）：`TP=6 FP=0 FN=5 TN=121`
#: → P=1.00 / R=0.545 / F1=0.706，合同级 `TP=5 FP=0 FN=5`，漏报 H101（FOB 下
#: “all costs of carriage … shall be defrayed by the Seller”，动词在主语之前）、
#: H102（“In lieu of arbitration, the Buyer may … seek a ruling … from the High Court”，
#: 动词是 seek）、H103（中文“合同价款的百分之百 … 款项全额到账后方安排装运”，用“到账”
#: 而非“收到/收讫 + 全部货款”）、H104（“向仲裁地法院申请对裁决的实体问题进行复审”，
#: 动词是“复审”）、H105（检验期限写成“两个工作日”，规则只认小时/立即/当日）。
#: 按 ADR-011 留出纪律，本批的五个漏报先写成空集合（当前跑通即基线快照）；下一步若按本基线
#: 修规则，本测试必须失败并点名这五份合同，**此时才翻表降级**——本批自此只作回归守卫，
#: 对外数字仍只引基线文件 `eval/results/rules-holdout10-baseline-20261030.json`。
EXPECTED_HOLDOUT10_HITS: dict[str, set[str]] = {
    "R-TRD-001": {"H106"},
    "R-INC-002": {"H107"},
    "R-INS-001": {"H108"},
    "R-PAY-002": {"H109"},
    "R-DIS-002": {"H109"},
    "R-DIS-001": {"H110"},
    # 以下五条是 version 10 盲测基线的漏报，先写成空集合；本轮不据基线修规则
    "R-INC-001": set(),
    "R-DIS-003": set(),
    "R-PAY-001": set(),
    "R-DIS-004": set(),
    "R-INP-002": set(),
}


def test_holdout10_hits_are_stable() -> None:
    if not HOLDOUT10_DIR.is_dir():
        pytest.skip("缺少 data/contracts_holdout10 目录")
    rules = [rule for rule in load_rules() if rule.rule_id in EXPECTED_HOLDOUT10_HITS]
    hits = {rule_id: set() for rule_id in EXPECTED_HOLDOUT10_HITS}
    for path in sorted(HOLDOUT10_DIR.glob("H*.md")):
        state = _load_state(path)
        for evaluation in evaluate_rules(
            rules, state.clauses, state.raw_text, extraction_available=False
        ):
            if evaluation.risk_level != "pass":
                hits[evaluation.rule_id].add(path.stem)
    assert hits == EXPECTED_HOLDOUT10_HITS

    # H111（CIF + 110% ICC(A) + 新加坡法 + SIAC）/
    # H112（FCA + 20% 预付 + SGS + 中国法 + 上海仲裁）
    # 是全条款合规的干净对照：后续放宽写法时不得引入误报。
    for name in ("H111", "H112"):
        state = _load_state(HOLDOUT10_DIR / f"{name}.md")
        evaluations = evaluate_rules(
            load_rules(), state.clauses, state.raw_text, extraction_available=False
        )
        assert [e.rule_id for e in evaluations if e.risk_level != "pass"] == [], name
