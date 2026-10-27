"""评测指标与 silver gold 的单元测试（不需要 Key、不跑 LangGraph）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.metrics import (
    GoldSet,
    Phenomenon,
    evaluate_results,
    load_gold,
    predictions_from_results,
    score_contract_level,
    score_coverage,
    score_rule_level,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_RULES = PROJECT_ROOT / "data" / "eval" / "gold_rules.json"
GOLD_HOLDOUT = PROJECT_ROOT / "data" / "eval" / "gold_holdout.json"
HOLDOUT_DIR = PROJECT_ROOT / "data" / "contracts_holdout"
CONTRACTS_DIR = PROJECT_ROOT / "data" / "contracts"


def _gold(
    phenomena: list[Phenomenon],
    contracts: tuple[str, ...] = ("C01", "C02"),
    scored: dict[str, str] | None = None,
) -> GoldSet:
    return GoldSet(
        version=1,
        provenance="test",
        scored_rules=scored or {"R-X": "yellow"},
        unscored_rules={},
        contract_ids=contracts,
        phenomena=tuple(phenomena),
    )


def test_predictions_from_results_reads_only_firing_levels() -> None:
    results = [
        {
            "contract_id": "C01",
            "rule_hits": [
                {"rule_id": "R-X", "risk_level": "yellow"},
                {"rule_id": "R-Y", "risk_level": "red"},
            ],
        },
        {"contract_id": "C02", "rule_hits": []},
    ]
    predictions = predictions_from_results(results)
    assert predictions == {("C01", "R-X"): "yellow", ("C01", "R-Y"): "red"}


def test_rule_level_perfect_match() -> None:
    gold = _gold([Phenomenon("C01", "x", "yellow", "R-X", "e")])
    metrics = score_rule_level({("C01", "R-X"): "yellow"}, gold)
    assert metrics["micro"] == {
        "tp": 1,
        "fp": 0,
        "fn": 0,
        "tn": 1,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "level_agreement": 1.0,
    }


def test_rule_level_counts_false_positives_and_negatives() -> None:
    gold = _gold(
        [
            Phenomenon("C01", "应报", "yellow", "R-X", "e"),
            Phenomenon("C02", "应报", "red", "R-X", "e"),
        ]
    )
    # C01 漏报、C02 报成 yellow（等级不一致），另有一个 gold 未声明的合同误报
    gold = GoldSet(
        version=1,
        provenance="test",
        scored_rules={"R-X": "yellow"},
        unscored_rules={},
        contract_ids=("C01", "C02", "C03"),
        phenomena=gold.phenomena,
    )
    metrics = score_rule_level({("C02", "R-X"): "yellow", ("C03", "R-X"): "red"}, gold)
    micro = metrics["micro"]
    assert (micro["tp"], micro["fp"], micro["fn"], micro["tn"]) == (1, 1, 1, 0)
    assert micro["precision"] == 0.5
    assert micro["recall"] == 0.5
    assert micro["level_agreement"] == 0.0
    assert metrics["false_positives"] == [
        {"contract_id": "C03", "rule_id": "R-X", "level": "red"}
    ]
    assert metrics["false_negatives"] == [
        {"contract_id": "C01", "rule_id": "R-X", "gold_level": "yellow"}
    ]


def test_rule_level_returns_none_when_no_positive_denominator() -> None:
    gold = _gold([])
    metrics = score_rule_level({}, gold)
    assert metrics["micro"]["tn"] == 2
    assert metrics["micro"]["precision"] is None
    assert metrics["micro"]["recall"] is None
    assert metrics["micro"]["f1"] is None
    assert metrics["micro"]["level_agreement"] is None


def test_contract_level_lists_missed_contracts() -> None:
    gold = _gold(
        [
            Phenomenon("C01", "a", "yellow", "R-X", "e"),
            Phenomenon("C02", "b", "yellow", None, "e"),
        ]
    )
    metrics = score_contract_level({("C01", "R-X"): "yellow"}, gold)
    assert (metrics["tp"], metrics["fp"], metrics["fn"], metrics["tn"]) == (1, 0, 1, 0)
    assert metrics["false_negative_contracts"] == ["C02"]


def test_coverage_separates_rule_gaps() -> None:
    gold = _gold(
        [
            Phenomenon("C01", "有规则", "yellow", "R-X", "e"),
            Phenomenon("C02", "无规则", "yellow", None, "e"),
        ]
    )
    coverage = score_coverage(gold)
    assert coverage["phenomena_total"] == 2
    assert coverage["phenomena_covered"] == 1
    assert coverage["coverage_rate"] == 0.5
    assert coverage["covered_by_rule"] == {"R-X": 1}
    assert coverage["uncovered"][0]["phenomenon"] == "无规则"


def test_evaluate_results_bundles_three_views() -> None:
    gold = _gold([Phenomenon("C01", "a", "yellow", "R-X", "e")])
    metrics = evaluate_results([{"contract_id": "C01", "rule_hits": []}], gold)
    assert set(metrics) >= {
        "rule_level",
        "contract_level",
        "coverage",
        "scored_rules",
        "unscored_rules",
        "note",
    }
    assert metrics["contract_level"]["recall"] == 0.0


def test_gold_conflict_detected() -> None:
    gold = _gold(
        [
            Phenomenon("C01", "a", "yellow", "R-X", "e"),
            Phenomenon("C01", "b", "red", "R-X", "e"),
        ]
    )
    with pytest.raises(ValueError, match="gold 冲突"):
        _ = gold.positives


def test_load_gold_rejects_unknown_contract_and_rule(tmp_path: Path) -> None:
    payload = {
        "version": 1,
        "provenance": "test",
        "scored_rules": {"R-X": "yellow"},
        "contract_ids": ["C01"],
        "phenomena": [
            {"contract_id": "C09", "phenomenon": "x", "level": "yellow", "rule_id": "R-X"},
        ],
    }
    path = tmp_path / "gold.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="未声明的合同"):
        load_gold(path)

    payload["phenomena"][0]["contract_id"] = "C01"
    payload["phenomena"][0]["rule_id"] = "R-UNKNOWN"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="未评分的规则"):
        load_gold(path)

    payload["phenomena"][0]["rule_id"] = None
    payload["phenomena"][0]["level"] = "orange"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="等级非法"):
        load_gold(path)


def test_gold_rules_file_covers_all_contracts_and_text_rules() -> None:
    gold = load_gold(GOLD_RULES)
    assert len(gold.contract_ids) == 50
    assert len(set(gold.contract_ids)) == 50
    assert set(gold.contract_ids) == {p.stem for p in CONTRACTS_DIR.glob("*.md")}
    assert all(item.evidence for item in gold.phenomena)
    # 只有文本规则参与判级；两条字段规则必须显式声明为不评分
    assert set(gold.unscored_rules) == {"R-DLV-001", "R-INP-001"}
    scored = gold.positives
    assert set(rule_id for _cid, rule_id in scored) <= set(gold.scored_rules)
    # 已知的确定性命中必须出现在 gold 中，否则评测会静默失真
    for contract_id, rule_id in (
        ("C04", "R-INS-001"),
        ("C09", "R-INP-002"),
        ("C11", "R-INC-001"),
        ("C23", "R-INC-002"),
        ("C47", "R-DIS-003"),
        ("C48", "R-DIS-004"),
    ):
        assert (contract_id, rule_id) in scored
    for contract_id in ("C39", "C40", "C41", "C42", "C43"):
        assert (contract_id, "R-PAY-002") in scored


def test_holdout_gold_is_self_consistent() -> None:
    gold = load_gold(GOLD_HOLDOUT)
    assert set(gold.contract_ids) == {p.stem for p in HOLDOUT_DIR.glob("*.md")}
    assert all(item.evidence for item in gold.phenomena)
    # 清洁合同 H04 不得出现在 gold 现象中，否则无法验证误报
    assert "H04" not in gold.gold_positive_contracts
