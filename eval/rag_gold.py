"""构造 100 题检索评测的 gold：把“概念标签”翻译成语料里真实存在的 citation。

为什么需要（ISSUE-018）：`data/knowledge/100问题.md` 里写的是概念标签
（`CISG-25` / `INC-CIF A5` / `JI-CC-1`），而 `app/services/rag.py` 产出的引用是
`source_id#section`（`CISG-ZH#第二十五条` / `INCOTERMS-2020#s12` /
`SPC-CONTRACT-2023#第一条`）。不先做这层映射，召回率根本无从计算。

口径（与 ADR-011 的报数纪律一致）：
- 一个标签解析出**多条**可接受片段（中文原文 / 英文原文 / 权威解读）；
- `strict` 只算条文原文类来源，`lenient` 再加 `CISG-KEY` 这类解读稿；
- 语料里没有对应文本的标签记入 `gaps`，含该标签且**无任何**可定位片段的题目
  不进召回率分母，单独报“语料未覆盖”，绝不把语料缺口算成检索失败；
- 生成物是 `data/eval/gold_rag.json`，可 diff、可复核；语料变动后用
  `python -m eval.rag_gold --write` 重建，`eval/run_rag_eval.py` 会校验 gold 是否过期。

通用规则（见 `data/eval/rag_label_map.yaml` 里的说明）：
- `CISG-N`（含 `CISG-7(1)` 这类款项标签）→ 中文第 N 条、英文 Article N、解读稿第 N 条；
- `CC-N` → 《民法典》第 N 条；`LAW-N` → 《法律适用法》第 N 条；
- `JI-CC-N` → 《合同编通则解释》第 N 条；`JI-CC` → 该解释前言（施行日期与文号）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:  # 支持 `python eval/rag_gold.py`
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.chinese_numbers import NumberFormatError  # noqa: E402
from app.services.chinese_numbers import to_chinese_number as cn_number  # noqa: E402
from app.services.rag import KnowledgeBase, KnowledgeChunk, load_knowledge_base  # noqa: E402

QUESTIONS_PATH = PROJECT_ROOT / "data" / "knowledge" / "100问题.md"
LABEL_MAP_PATH = PROJECT_ROOT / "data" / "eval" / "rag_label_map.yaml"
GOLD_PATH = PROJECT_ROOT / "data" / "eval" / "gold_rag.json"
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"

#: 只提供“解读”而非条文原文的来源；`strict` 口径下被剔除
COMMENTARY_SOURCES = frozenset({"CISG-KEY"})


class GoldConfigError(RuntimeError):
    """标签映射文件或题目文件不合法；评测数据不能静默降级。"""


@dataclass(frozen=True)
class Question:
    id: int
    group: str
    text: str
    labels: tuple[str, ...]
    section_hint: str


@dataclass(frozen=True)
class LabelMap:
    matchers: dict[str, tuple[tuple[str, str], ...]]
    gaps: dict[str, str]


__all__ = [
    "GOLD_PATH",
    "GoldConfigError",
    "LabelMap",
    "Question",
    "build_gold",
    "cn_number",
    "load_label_map",
    "parse_questions",
    "resolve_label",
]


def _checked_number(raw: str) -> int:
    """把标签里的条号字段转成 int；不合法时统一抛 `GoldConfigError`。"""
    try:
        return int(raw)
    except ValueError as exc:  # 标签里写了非数字，属于配置错误
        raise GoldConfigError(f"条号不是整数：{raw!r}") from exc


def load_label_map(path: Path = LABEL_MAP_PATH) -> LabelMap:
    import yaml

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise GoldConfigError(f"标签映射读取失败：{path}（{exc}）") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise GoldConfigError(f"标签映射必须是 version: 1 的对象：{path}")

    raw_labels = payload.get("labels") or {}
    raw_gaps = payload.get("gaps") or {}
    if not isinstance(raw_labels, dict) or not isinstance(raw_gaps, dict):
        raise GoldConfigError("标签映射的 labels / gaps 必须是对象")

    matchers: dict[str, tuple[tuple[str, str], ...]] = {}
    for label, items in raw_labels.items():
        if not isinstance(items, list) or not items:
            raise GoldConfigError(f"标签 {label!r} 的匹配器必须是非空列表")
        pairs: list[tuple[str, str]] = []
        for item in items:
            if not isinstance(item, dict) or "source" not in item or "heading" not in item:
                raise GoldConfigError(f"标签 {label!r} 的匹配器缺少 source/heading：{item!r}")
            pattern = str(item["heading"])
            try:
                re.compile(pattern)
            except re.error as exc:
                raise GoldConfigError(f"标签 {label!r} 的 heading 正则不合法：{pattern}") from exc
            pairs.append((str(item["source"]), pattern))
        matchers[str(label)] = tuple(pairs)

    overlap = sorted(set(matchers) & set(raw_gaps))
    if overlap:
        raise GoldConfigError(f"标签同时登记为可解析与缺口：{overlap}")
    return LabelMap(matchers, {str(key): str(value) for key, value in raw_gaps.items()})


def parse_questions(path: Path = QUESTIONS_PATH) -> list[Question]:
    """解析 100 题表；只认 4 列且首列是数字的行，分组取自二级标题。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GoldConfigError(f"题目文件读取失败：{path}（{exc}）") from exc

    questions: list[Question] = []
    group = "未分组"
    seen: set[int] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            group = stripped[3:].strip()
            continue
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 4 or not cells[0].isdigit():
            continue
        question_id = int(cells[0])
        if question_id in seen:
            raise GoldConfigError(f"题号重复：{question_id}")
        seen.add(question_id)
        labels = tuple(
            label
            for label in (
                part.strip().strip("*").strip() for part in cells[2].split(";")
            )
            if label
        )
        if not labels:
            raise GoldConfigError(f"第 {question_id} 题没有期望标签")
        questions.append(
            Question(question_id, group, cells[1].strip(), labels, cells[3].strip())
        )
    if len(questions) != 100:
        raise GoldConfigError(f"题目数量应为 100，实际 {len(questions)}")
    return questions


def _match(
    label: str,
    matchers: tuple[tuple[str, str], ...],
    by_source: dict[str, list[KnowledgeChunk]],
) -> list[str]:
    hits: list[str] = []
    for source_id, pattern in matchers:
        regex = re.compile(pattern)
        for chunk in by_source.get(source_id, []):
            if regex.search(chunk.heading) and chunk.citation not in hits:
                hits.append(chunk.citation)
    return hits


def _generic(label: str) -> tuple[tuple[str, str], ...] | None:
    """通用条号标签 → 匹配器；不认识返回 None。"""
    cisg = re.fullmatch(r"CISG-(\d+)(?:\([^)]*\))*", label)
    if cisg:
        number = _checked_number(cisg.group(1))
        return (
            ("CISG-ZH", rf"^第{_cn(number)}条$"),
            ("CISG-EN", rf"^Article {number}$"),
            ("CISG-KEY", rf"^第{number}条｜"),
        )
    civil = re.fullmatch(r"CC-(\d+)(?:\([^)]*\))*", label)
    if civil:
        return (("CN-CIVIL-CODE", rf"^第{_cn(_checked_number(civil.group(1)))}条$"),)
    law = re.fullmatch(r"LAW-(\d+)", label)
    if law:
        return (("CN-LAW-APPLICATION", rf"^第{_cn(_checked_number(law.group(1)))}条$"),)
    jicc = re.fullmatch(r"JI-CC-(\d+)", label)
    if jicc:
        return (("SPC-CONTRACT-2023", rf"^第{_cn(_checked_number(jicc.group(1)))}条$"),)
    if label == "JI-CC":
        return (("SPC-CONTRACT-2023", r"^前言$"),)
    return None


def _cn(value: int) -> str:
    """条号转中文；越界属于标签配置错误，转成 `GoldConfigError` 统一提示。"""
    try:
        return cn_number(value)
    except NumberFormatError as exc:
        raise GoldConfigError(str(exc)) from exc


def resolve_label(
    label: str,
    mapping: LabelMap,
    by_source: dict[str, list[KnowledgeChunk]],
) -> tuple[list[str], str]:
    """返回 `(可接受 citation 列表, 无法定位的原因)`；两者互斥。"""
    if label in mapping.gaps:
        return [], mapping.gaps[label]
    matchers = mapping.matchers.get(label) or _generic(label)
    if matchers is None:
        return [], "标签未登记且无法按通用条号规则解析"
    hits = _match(label, matchers, by_source)
    if not hits:
        return [], "匹配器未命中任何片段（可能语料已变更）"
    return hits, ""


def build_gold(
    kb: KnowledgeBase,
    questions: list[Question],
    mapping: LabelMap,
) -> dict[str, Any]:
    by_source: dict[str, list[KnowledgeChunk]] = {}
    for chunk in kb.chunks:
        by_source.setdefault(chunk.source_id, []).append(chunk)

    entries: list[dict[str, Any]] = []
    for question in questions:
        expected: list[str] = []
        unresolved: list[dict[str, str]] = []
        for label in question.labels:
            hits, reason = resolve_label(label, mapping, by_source)
            if hits:
                expected.extend(citation for citation in hits if citation not in expected)
            else:
                unresolved.append({"label": label, "reason": reason})
        strict = [
            citation
            for citation in expected
            if citation.split("#", 1)[0] not in COMMENTARY_SOURCES
        ]
        entries.append(
            {
                "id": question.id,
                "group": question.group,
                "question": question.text,
                "section_hint": question.section_hint,
                "labels": list(question.labels),
                "expected": expected,
                "strict": strict,
                "unresolved": unresolved,
            }
        )

    resolved = [entry for entry in entries if entry["expected"]]
    return {
        "version": 1,
        "provenance": (
            "AI 构造、可复核：标签→语料映射登记在 data/eval/rag_label_map.yaml，"
            "通用条号（CISG/CC/LAW/JI-CC）由 eval/rag_gold.py 解析；"
            "strict=条文原文，lenient=再含 CISG-KEY 解读稿"
        ),
        "generated_at": datetime.now(UTC).isoformat(),
        "corpus": {
            "chunk_count": len(kb.chunks),
            "sources": sorted({chunk.source_id for chunk in kb.chunks}),
        },
        "question_count": len(entries),
        "resolved_count": len(resolved),
        "unresolved_count": len(entries) - len(resolved),
        "questions": entries,
    }


def _print_summary(gold: dict[str, Any]) -> None:
    print(f"题目 {gold['question_count']} 道；可评测 {gold['resolved_count']} 道；"
          f"语料未覆盖 {gold['unresolved_count']} 道")
    for entry in gold["questions"]:
        if entry["expected"]:
            continue
        labels = "、".join(item["label"] for item in entry["unresolved"])
        print(f"  未评测 #{entry['id']}：{labels}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=QUESTIONS_PATH)
    parser.add_argument("--labels", type=Path, default=LABEL_MAP_PATH)
    parser.add_argument("--gold", type=Path, default=GOLD_PATH)
    parser.add_argument("--write", action="store_true", help="写入 gold_rag.json")
    args = parser.parse_args(argv)

    kb = load_knowledge_base(KNOWLEDGE_DIR, enabled=True)
    if kb is None:  # pragma: no cover - enabled=True 时不会返回 None
        print("知识库加载失败（RAG_ENABLED 关闭？）")
        return 2
    gold = build_gold(kb, parse_questions(args.questions), load_label_map(args.labels))
    _print_summary(gold)
    if args.write:
        args.gold.parent.mkdir(parents=True, exist_ok=True)
        args.gold.write_text(
            json.dumps(gold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"已写入：{args.gold}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
