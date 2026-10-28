"""检索评测指标：把“gold 可接受 citation 集合”与“实际返回的前 k 条”对齐。

角色：第四阶段检索评测（ISSUE-018）的纯计算层，被 `eval/run_rag_eval.py` 调用。
依赖：仅标准库（不依赖 pytest / numpy），便于直接跑。

口径：
- 一道题命中，指其**任一**可接受 citation 出现在前 k 条里（k=1/3/5）；
- `strict` 只认条文原文（剔除 `CISG-KEY` 这类解读稿），`lenient` 连解读稿一起认；
  两个数一起报，避免“命中解读稿也算回到条文”的误读；
- `MRR`（平均倒数排名）反映“正确答案排得多靠前”，不是命中率的替代品；
- 语料未覆盖的题（gold 里 `expected` 为空）不进分母，单独计数。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

DEFAULT_KS: tuple[int, ...] = (1, 3, 5)


def _first_rank(ranked: Sequence[str], expected: Iterable[str]) -> int | None:
    targets = set(expected)
    for index, citation in enumerate(ranked, start=1):
        if citation in targets:
            return index
    return None


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _summarize(ranks: Sequence[int | None], ks: Sequence[int]) -> dict[str, Any]:
    total = len(ranks)
    hits = {str(k): sum(1 for rank in ranks if rank is not None and rank <= k) for k in ks}
    reciprocal = sum(1.0 / rank for rank in ranks if rank is not None)
    return {
        "questions": total,
        "hits": hits,
        "recall_at": {key: _ratio(value, total) for key, value in hits.items()},
        "mrr": round(reciprocal / total, 4) if total else None,
        "not_found": sum(1 for rank in ranks if rank is None),
        "rank_histogram": {
            str(k): sum(1 for rank in ranks if rank == k) for k in range(1, 6)
        },
    }


def score(
    gold: Mapping[str, Any],
    ranked: Mapping[int, Sequence[str]],
    ks: Sequence[int] = DEFAULT_KS,
) -> dict[str, Any]:
    """按 gold 的 100 题（去掉语料未覆盖的）计算命中率、MRR 与分组明细。"""
    entries = list(gold["questions"])
    resolved = [entry for entry in entries if entry["expected"]]
    unresolved = [entry for entry in entries if not entry["expected"]]

    detail: list[dict[str, Any]] = []
    lenient_ranks: list[int | None] = []
    strict_ranks: list[int | None] = []
    by_group: dict[str, dict[str, list[int | None]]] = {}

    for entry in resolved:
        returned = list(ranked.get(entry["id"], []))
        lenient_rank = _first_rank(returned, entry["expected"])
        strict_rank = _first_rank(returned, entry["strict"]) if entry["strict"] else None
        lenient_ranks.append(lenient_rank)
        strict_ranks.append(strict_rank)
        group = str(entry["group"])
        bucket = by_group.setdefault(group, {"lenient": [], "strict": []})
        bucket["lenient"].append(lenient_rank)
        bucket["strict"].append(strict_rank)
        detail.append(
            {
                "id": entry["id"],
                "group": group,
                "question": entry["question"],
                "expected": entry["expected"],
                "rank": lenient_rank,
                "strict_rank": strict_rank,
                "returned": returned,
            }
        )

    overall = {
        "lenient": _summarize(lenient_ranks, ks),
        "strict": _summarize(strict_ranks, ks),
    }
    misses = [
        {
            "id": item["id"],
            "group": item["group"],
            "question": item["question"],
            "expected": item["expected"],
            "strict_rank": item["strict_rank"],
            "returned": item["returned"],
        }
        for item in detail
        if item["rank"] is None or item["rank"] > max(ks)
    ]
    weak = [
        {
            "id": item["id"],
            "question": item["question"],
            "rank": item["rank"],
            "strict_rank": item["strict_rank"],
        }
        for item in detail
        if item["rank"] is not None and item["rank"] > 1
    ]

    return {
        "denominator": len(resolved),
        "unresolved_count": len(unresolved),
        "unresolved": [
            {
                "id": entry["id"],
                "labels": [item["label"] for item in entry["unresolved"]],
                "reasons": [item["reason"] for item in entry["unresolved"]],
            }
            for entry in unresolved
        ],
        "overall": overall,
        "by_group": {
            group: {
                "lenient": _summarize(values["lenient"], ks),
                "strict": _summarize(values["strict"], ks),
            }
            for group, values in by_group.items()
        },
        "misses_beyond_k": misses,
        "not_top1": weak,
        "questions": detail,
        "note": (
            "lenient=条文原文或 CISG-KEY 解读稿；strict=仅条文原文；"
            "语料未覆盖的题不进分母（见 unresolved）。"
        ),
    }
