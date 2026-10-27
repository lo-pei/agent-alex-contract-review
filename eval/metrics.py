"""规则评测指标：把「规则预测」与「silver gold」对齐，算出可复核的指标。

角色：第四阶段评测（ISSUE-005/020）的纯计算层，被 `eval/run_eval.py` 调用。
依赖：仅标准库（不依赖 pytest / numpy），便于在无虚拟环境的机器上直接跑。

口径（与 ADR-010 / ADR-011 一致）：
- 只评**文本规则**在**合同级**上的触发情况：gold 为 red/yellow 视为“应触发”，pass 视为“不应触发”；
- 规则级（rule × contract）：TP/FP/FN/TN + precision/recall/F1 + 等级一致率；
- 合同级（contract）：合同是否至少存在一项 gold 风险 vs 是否被规则标记；
- 覆盖率：gold 现象中有多少映射到规则，未映射部分即规则缺口（不是“无风险”）。
- 单侧分母为 0 时指标返回 `None`，不返回 0.0，避免“无正例=差”的误导。
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LEVELS = ("red", "yellow")


@dataclass(frozen=True)
class Phenomenon:
    """一条 gold 风险现象：合同里确实存在该问题，且预期被判为 level。"""

    contract_id: str
    phenomenon: str
    level: str
    rule_id: str | None
    evidence: str


@dataclass(frozen=True)
class GoldSet:
    version: int
    provenance: str
    scored_rules: Mapping[str, str]
    unscored_rules: Mapping[str, str]
    contract_ids: tuple[str, ...]
    phenomena: tuple[Phenomenon, ...] = field(default_factory=tuple)

    @property
    def positives(self) -> dict[tuple[str, str], str]:
        """(contract_id, rule_id) → 期望等级；未出现即视为 pass。"""
        result: dict[tuple[str, str], str] = {}
        for item in self.phenomena:
            if item.rule_id is None:
                continue
            key = (item.contract_id, item.rule_id)
            if key in result and result[key] != item.level:
                raise ValueError(f"gold 冲突：{key} 同时标注为 {result[key]} 与 {item.level}")
            result[key] = item.level
        return result

    @property
    def gold_positive_contracts(self) -> set[str]:
        return {item.contract_id for item in self.phenomena}


def load_gold(path: Path) -> GoldSet:
    """读取 gold JSON。结构错误直接抛异常：评测数据不能静默降级。"""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    phenomena = tuple(
        Phenomenon(
            contract_id=str(item["contract_id"]),
            phenomenon=str(item["phenomenon"]),
            level=str(item["level"]),
            rule_id=item.get("rule_id"),
            evidence=str(item.get("evidence", "")),
        )
        for item in payload.get("phenomena", [])
    )
    for item in phenomena:
        if item.level not in LEVELS:
            raise ValueError(f"gold 等级非法：{item}")
    gold = GoldSet(
        version=int(payload.get("version", 1)),
        provenance=str(payload.get("provenance", "unknown")),
        scored_rules=dict(payload.get("scored_rules", {})),
        unscored_rules=dict(payload.get("unscored_rules", {})),
        contract_ids=tuple(str(cid) for cid in payload.get("contract_ids", [])),
        phenomena=phenomena,
    )
    unknown = {item.contract_id for item in phenomena} - set(gold.contract_ids)
    if unknown:
        raise ValueError(f"gold 现象引用了未声明的合同：{sorted(unknown)}")
    unknown_rules = {
        item.rule_id for item in phenomena if item.rule_id and item.rule_id not in gold.scored_rules
    }
    if unknown_rules:
        raise ValueError(f"gold 现象引用了未评分的规则：{sorted(unknown_rules)}")
    return gold


def predictions_from_results(results: Iterable[Mapping[str, Any]]) -> dict[tuple[str, str], str]:
    """把 `run_eval` 的 results 转成 (contract_id, rule_id) → 预测等级。"""
    predictions: dict[tuple[str, str], str] = {}
    for item in results:
        contract_id = str(item["contract_id"])
        for hit in item.get("rule_hits", []):
            predictions[(contract_id, str(hit["rule_id"]))] = str(hit["risk_level"])
    return predictions


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None or precision + recall == 0:
        return None
    return round(2 * precision * recall / (precision + recall), 4)


def _empty_counts() -> dict[str, int]:
    return {"tp": 0, "fp": 0, "fn": 0, "tn": 0}


def _summarize(counts: Mapping[str, int], level_matches: int) -> dict[str, Any]:
    precision = _ratio(counts["tp"], counts["tp"] + counts["fp"])
    recall = _ratio(counts["tp"], counts["tp"] + counts["fn"])
    return {
        **counts,
        "precision": precision,
        "recall": recall,
        "f1": _f1(precision, recall),
        "level_agreement": _ratio(level_matches, counts["tp"]),
    }


def score_rule_level(
    predictions: Mapping[tuple[str, str], str],
    gold: GoldSet,
    rule_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """规则级混淆矩阵：只统计 gold.scored_rules 中的规则，缺失预测视为 pass。"""
    rules = list(rule_ids if rule_ids is not None else gold.scored_rules.keys())
    expected = gold.positives
    totals = _empty_counts()
    level_matches = 0
    per_rule: dict[str, dict[str, Any]] = {}
    false_positives: list[dict[str, str]] = []
    false_negatives: list[dict[str, str]] = []
    true_positives: list[dict[str, str]] = []

    for rule_id in rules:
        counts = _empty_counts()
        matches = 0
        for contract_id in gold.contract_ids:
            gold_level = expected.get((contract_id, rule_id))
            predicted_level = predictions.get((contract_id, rule_id))
            predicted_fires = predicted_level in LEVELS
            gold_fires = gold_level in LEVELS
            if predicted_fires and gold_fires:
                counts["tp"] += 1
                matches += int(predicted_level == gold_level)
                true_positives.append(
                    {
                        "contract_id": contract_id,
                        "rule_id": rule_id,
                        "gold_level": str(gold_level),
                        "predicted_level": str(predicted_level),
                    }
                )
            elif predicted_fires:
                counts["fp"] += 1
                false_positives.append(
                    {"contract_id": contract_id, "rule_id": rule_id, "level": str(predicted_level)}
                )
            elif gold_fires:
                counts["fn"] += 1
                false_negatives.append(
                    {"contract_id": contract_id, "rule_id": rule_id, "gold_level": str(gold_level)}
                )
            else:
                counts["tn"] += 1
        per_rule[rule_id] = _summarize(counts, matches)
        for key in totals:
            totals[key] += counts[key]
        level_matches += matches

    return {
        "scored_rule_count": len(rules),
        "micro": _summarize(totals, level_matches),
        "per_rule": per_rule,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "true_positives": true_positives,
    }


def score_contract_level(
    predictions: Mapping[tuple[str, str], str],
    gold: GoldSet,
) -> dict[str, Any]:
    """合同级：gold 有任一风险 vs 规则是否标记了该合同。"""
    predicted_positive = {
        contract_id for (contract_id, _rule), level in predictions.items() if level in LEVELS
    }
    gold_positive = gold.gold_positive_contracts
    universe = set(gold.contract_ids)
    tp = len(predicted_positive & gold_positive)
    fp = len(predicted_positive - gold_positive)
    fn = len(gold_positive - predicted_positive)
    tn = len(universe - predicted_positive - gold_positive)
    summary = _summarize({"tp": tp, "fp": fp, "fn": fn, "tn": tn}, tp)
    return {
        **summary,
        "false_positive_contracts": sorted(predicted_positive - gold_positive),
        "false_negative_contracts": sorted(gold_positive - predicted_positive),
    }


def score_coverage(gold: GoldSet) -> dict[str, Any]:
    """覆盖率：gold 现象中多少映射到规则；未映射即规则缺口（下一轮规则待办）。"""
    covered = [item for item in gold.phenomena if item.rule_id]
    uncovered = [item for item in gold.phenomena if not item.rule_id]
    by_rule = Counter(item.rule_id for item in covered)
    return {
        "phenomena_total": len(gold.phenomena),
        "phenomena_covered": len(covered),
        "phenomena_uncovered": len(uncovered),
        "coverage_rate": _ratio(len(covered), len(gold.phenomena)),
        "covered_by_rule": dict(sorted(by_rule.items())),
        "uncovered": [
            {
                "contract_id": item.contract_id,
                "phenomenon": item.phenomenon,
                "level": item.level,
                "evidence": item.evidence,
            }
            for item in uncovered
        ],
    }


def evaluate_results(results: Iterable[Mapping[str, Any]], gold: GoldSet) -> dict[str, Any]:
    """一次性产出三组指标，供 run_eval 写进结果文件。"""
    results = list(results)
    predictions = predictions_from_results(results)
    return {
        "gold_provenance": gold.provenance,
        "gold_version": gold.version,
        "scored_rules": dict(gold.scored_rules),
        "unscored_rules": dict(gold.unscored_rules),
        "rule_level": score_rule_level(predictions, gold),
        "contract_level": score_contract_level(predictions, gold),
        "coverage": score_coverage(gold),
        "note": (
            "silver gold（AI 初标、待人工复核），规则与 gold 同源阅读，"
            "rule_level 指标主要用于回归守卫，不代表独立准确率；"
            "contract_level 与 coverage 用于暴露规则覆盖缺口。"
        ),
    }
