"""检索评测入口：用 `100问题.md` 的 95 道可评测题跑真实 BM25 检索，出召回率。

角色：第四阶段检索评测（ISSUE-018），不调用 LLM、不需要 Key。
依赖：`app.services.rag`、`eval/rag_gold.py`、`eval/rag_eval.py`。
约束：
- 只评估**检索**（返回的 citation 排在多前），不评估解释质量与判级；
- 两套口径同时报：`ranking`（top-5、不过阈值，用来看排序能力）与
  `production`（`RAG_TOP_K` / `RAG_MIN_SCORE` 实际配置，用来看线上会不会返回空）；
- gold 里的 citation 必须能在当前语料里找到，否则直接失败（语料改了要重建 gold）；
- 结果写 `eval/results/rag-<日期>.json`，含每题的期望、实返 citation 与排名。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:  # 支持 `python eval/run_rag_eval.py` 直接运行
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings  # noqa: E402
from app.services.rag import KnowledgeBase, load_knowledge_base  # noqa: E402
from eval.rag_eval import score  # noqa: E402

DEFAULT_GOLD = PROJECT_ROOT / "data" / "eval" / "gold_rag.json"
DEFAULT_KNOWLEDGE = PROJECT_ROOT / "data" / "knowledge"
DEFAULT_OUTPUT = PROJECT_ROOT / "eval" / "results"


class GoldStaleError(RuntimeError):
    """gold 引用了当前语料里不存在的 citation；必须重建 gold 而不是硬跑。"""


def validate_gold(kb: KnowledgeBase, gold: dict[str, Any]) -> None:
    available = kb.citations()
    stale = sorted(
        {
            citation
            for entry in gold["questions"]
            for citation in entry["expected"]
            if citation not in available
        }
    )
    if stale:
        raise GoldStaleError(
            "gold 与语料不一致（语料已变更？先跑 `python -m eval.rag_gold --write`）："
            + ", ".join(stale[:5])
        )


def _rank(
    kb: KnowledgeBase,
    questions: list[dict[str, Any]],
    *,
    top_k: int,
    min_score: float,
) -> dict[int, list[str]]:
    ranked: dict[int, list[str]] = {}
    for entry in questions:
        hits = kb.search(entry["question"], top_k=top_k, min_score=min_score)
        ranked[entry["id"]] = [chunk.citation for chunk in hits]
    return ranked


def _line(label: str, summary: dict[str, Any]) -> str:
    parts = [
        f"R@{key}={value}"
        for key, value in sorted(summary["recall_at"].items(), key=lambda item: int(item[0]))
    ]
    parts.append(f"MRR={summary['mrr']}")
    parts.append(f"未命中={summary['not_found']}")
    return f"  {label}：" + "  ".join(parts)


def _print_block(name: str, result: dict[str, Any]) -> None:
    lenient = result["overall"]["lenient"]
    strict = result["overall"]["strict"]
    print(f"\n[{name}] 可评测 {result['denominator']} 题"
          f"（语料未覆盖 {result['unresolved_count']} 题）")
    print(_line("lenient（含解读稿）", lenient))
    print(_line("strict（仅条文原文）", strict))
    focus = sorted(lenient["recall_at"], key=int)[-1]
    print(f"  分组 R@{focus}（lenient）：")
    for group, values in result["by_group"].items():
        detail = values["lenient"]
        short = group.split("：", 1)[0]
        print(f"    - {short}：{detail['recall_at'][focus]}（{detail['questions']} 题）")
    if result["misses_beyond_k"]:
        print(f"  前 {focus} 未命中：")
        for item in result["misses_beyond_k"]:
            print(f"    - #{item['id']} {item['question'][:38]} → 期望 {item['expected'][:2]}")


def run(
    gold_path: Path,
    knowledge_dir: Path,
    output_dir: Path,
    *,
    top_k: int = 5,
    tag: str = "",
) -> int:
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    kb = load_knowledge_base(knowledge_dir, enabled=True)
    if kb is None:  # pragma: no cover
        print("知识库加载失败")
        return 2
    validate_gold(kb, gold)

    questions = gold["questions"]
    ranking_ranked = _rank(kb, questions, top_k=top_k, min_score=0.0)
    ranking = score(gold, ranking_ranked)

    prod_k = settings.rag_top_k
    prod_min = settings.rag_min_score
    production_ranked = _rank(kb, questions, top_k=prod_k, min_score=prod_min)
    production = score(gold, production_ranked, ks=(1, prod_k))

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "gold_provenance": gold.get("provenance"),
        "corpus": gold.get("corpus"),
        "question_count": gold.get("question_count"),
        "config": {
            "ranking": {"top_k": top_k, "min_score": 0.0},
            "production": {"top_k": prod_k, "min_score": prod_min},
        },
        "ranking": ranking,
        "production": production,
        "note": (
            "ranking 用来看排序能力（top-5、不过阈值）；production 是线上实际配置，"
            "recall 会因阈值过滤而下降，两者不可混读。"
        ),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"-{tag}" if tag else ""
    target = output_dir / f"rag{suffix}-{datetime.now(UTC):%Y%m%d}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"语料：{len(kb)} 个片段；题：{gold['question_count']} 道")
    _print_block(f"ranking top-{top_k} / 无阈值", ranking)
    _print_block(f"production top-{prod_k} / min_score={prod_min}", production)
    print(f"\n结果：{target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--knowledge", type=Path, default=DEFAULT_KNOWLEDGE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top-k", type=int, default=5, help="排序口径的 k（默认 5）")
    parser.add_argument("--tag", default="", help="结果文件名后缀")
    args = parser.parse_args(argv)
    try:
        return run(args.gold, args.knowledge, args.out, top_k=args.top_k, tag=args.tag)
    except GoldStaleError as exc:
        print(str(exc))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
