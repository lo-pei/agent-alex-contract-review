"""规则级评测：在 gold 合同集上跑确定性链路，统计规则命中与（可选）指标。

角色：第四阶段评测入口（ISSUE-005/020），不调用 LLM 做解释，不需要 Key。
依赖：`app.review_service`、`app.rules.engine`、`eval/metrics.py`。
约束：
- 只评估**规则判级**与执行状态，不评估 LLM 抽取/解释质量（那是另一份评测）；
- 结果写 `eval/results/rules-<日期>.json`，包含每份合同的等级、命中规则、跳过规则；
- 若提供 `gold_rules.json`（silver gold），额外写入 rule_level / contract_level /
  coverage 三组指标；
- 不把“未命中任何规则”说成“合同无风险”，报告里必须保留该语义。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:  # 支持 `python eval/run_eval.py` 直接运行
    sys.path.insert(0, str(PROJECT_ROOT))

from app.review_service import ReviewService, ReviewStateError  # noqa: E402
from app.rules.engine import RULE_ENGINE_VERSION, load_rules  # noqa: E402
from eval.metrics import evaluate_results, load_gold  # noqa: E402

DEFAULT_CONTRACTS = PROJECT_ROOT / "data" / "contracts"
DEFAULT_GOLD = PROJECT_ROOT / "data" / "eval" / "gold_contracts.json"
DEFAULT_GOLD_RULES = PROJECT_ROOT / "data" / "eval" / "gold_rules.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "eval" / "results"


def _print_metrics(metrics: dict) -> None:
    rule_level = metrics["rule_level"]["micro"]
    contract_level = metrics["contract_level"]
    coverage = metrics["coverage"]
    print(
        "规则级：TP={tp} FP={fp} FN={fn} TN={tn}  P={p} R={r} F1={f1} 等级一致率={lv}".format(
            tp=rule_level["tp"],
            fp=rule_level["fp"],
            fn=rule_level["fn"],
            tn=rule_level["tn"],
            p=rule_level["precision"],
            r=rule_level["recall"],
            f1=rule_level["f1"],
            lv=rule_level["level_agreement"],
        )
    )
    print(
        "合同级：TP={tp} FP={fp} FN={fn} TN={tn}  P={p} R={r} F1={f1}".format(
            tp=contract_level["tp"],
            fp=contract_level["fp"],
            fn=contract_level["fn"],
            tn=contract_level["tn"],
            p=contract_level["precision"],
            r=contract_level["recall"],
            f1=contract_level["f1"],
        )
    )
    if contract_level["false_negative_contracts"]:
        print("合同级漏报：" + ", ".join(contract_level["false_negative_contracts"]))
    if contract_level["false_positive_contracts"]:
        print("合同级误报：" + ", ".join(contract_level["false_positive_contracts"]))
    print(
        "覆盖率：gold 现象 {total} 个，规则覆盖 {covered} 个（{rate}），缺口 {gap} 个".format(
            total=coverage["phenomena_total"],
            covered=coverage["phenomena_covered"],
            rate=coverage["coverage_rate"],
            gap=coverage["phenomena_uncovered"],
        )
    )
    if coverage["phenomena_uncovered"] == 0:
        print(
            "  ↳ 覆盖率 1.0 只表示“每条现象都有对应规则”（留出集即如此），"
            f"实际识别能力看规则级 recall={rule_level['recall']}。"
        )


def run(
    contracts_dir: Path,
    gold_path: Path,
    output_dir: Path,
    gold_rules_path: Path | None = DEFAULT_GOLD_RULES,
    tag: str = "",
) -> int:
    gold = json.loads(gold_path.read_text(encoding="utf-8")) if gold_path.is_file() else None
    scenarios = {
        item["contract_id"]: item for item in (gold or {}).get("contracts", [])
    }
    rules = load_rules()

    files = sorted(contracts_dir.glob("*.md"))
    if not files:
        print(f"未找到合同：{contracts_dir}")
        return 1

    service = ReviewService.in_memory()
    results: list[dict] = []
    for path in files:
        contract_id = path.stem
        try:
            run_result = service.start(path)
        except ReviewStateError as exc:
            results.append(
                {"contract_id": contract_id, "error": str(exc), "rule_hits": [], "skipped": []}
            )
            continue

        state = run_result.state
        hits = [
            {
                "rule_id": evaluation.rule_id,
                "risk_level": evaluation.risk_level,
                "clause_ids": list(evaluation.clause_ids),
            }
            for evaluation in (state.rule_evaluations if state else [])
            if not evaluation.skipped and evaluation.risk_level in ("red", "yellow")
        ]
        skipped = [
            evaluation.rule_id
            for evaluation in (state.rule_evaluations if state else [])
            if evaluation.skipped
        ]
        results.append(
            {
                "contract_id": contract_id,
                "scenario": scenarios.get(contract_id, {}).get("scenario"),
                "status": run_result.status,
                "awaiting_human": run_result.awaiting_human,
                "overall_level": state.overall_level if state else None,
                "extraction_status": state.extraction_status if state else None,
                "clause_count": len(state.clauses) if state else 0,
                "rule_hits": hits,
                "skipped": skipped,
            }
        )

    hit_counts = Counter(hit["rule_id"] for item in results for hit in item.get("rule_hits", []))
    level_counts = Counter(item.get("overall_level") for item in results)
    with_hits = sum(1 for item in results if item.get("rule_hits"))
    clean = [item["contract_id"] for item in results if not item.get("rule_hits")]

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "rule_engine_version": RULE_ENGINE_VERSION,
        "rule_count": len(rules),
        "contract_count": len(results),
        "contracts_with_hits": with_hits,
        "contracts_without_hits": clean,
        "level_counts": dict(level_counts),
        "hit_counts": dict(hit_counts),
        "note": (
            "规则级评测只反映确定性规则的触发情况；“未命中”不等于无风险，"
            "gold 的 expected_recall 是检索期望，不是规则判级标签。"
        ),
        "contracts": results,
    }

    metrics = None
    if gold_rules_path is not None and Path(gold_rules_path).is_file():
        try:
            gold_rules = load_gold(Path(gold_rules_path))
        except (ValueError, KeyError) as exc:
            print(f"gold 规则文件不可用：{exc}")
            return 2
        metrics = evaluate_results(results, gold_rules)
        payload["metrics"] = metrics
    else:
        payload["metrics"] = None

    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"-{tag}" if tag else ""
    target = output_dir / f"rules{suffix}-{datetime.now(UTC):%Y%m%d}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"合同 {len(results)} 份；命中规则 {with_hits} 份；未命中 {len(clean)} 份")
    print(f"等级分布：{dict(level_counts)}")
    print(f"规则触发次数：{dict(hit_counts)}")
    if metrics is not None:
        _print_metrics(metrics)
    print(f"结果：{target}")
    if clean:
        print("未命中任何规则：" + ", ".join(clean))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--gold-rules",
        type=Path,
        default=DEFAULT_GOLD_RULES,
        help="silver gold（规则级）；传 `none` 可跳过指标计算",
    )
    parser.add_argument("--tag", default="", help="结果文件名后缀，例如 holdout")
    args = parser.parse_args()
    gold_rules = None if str(args.gold_rules).lower() == "none" else args.gold_rules
    return run(args.contracts, args.gold, args.out, gold_rules, args.tag)


if __name__ == "__main__":
    raise SystemExit(main())
