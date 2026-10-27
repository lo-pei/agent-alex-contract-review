"""把 `data/knowledge/模拟合同*.md` 拆成单份合同，并抽取“条款—问题映射摘要”为 gold。

角色：第四阶段评测的数据准备（ISSUE-005 / ISSUE-018）。
依赖：标准库；不修改用户原始文件。
约束：
- 原始文件中的每份合同以 `## Cxx · 场景` 开头，末尾是 `> **条款—问题映射摘要（Cxx）**` 引用块；
- 合同正文写入 `data/contracts/Cxx.md`（保留 `### 第X条` 标题，供 segment 切分）；
- 映射摘要写入 `data/eval/gold_contracts.json`（保留原始 Markdown 表格 + 解析出的行）；
- 同一 contract_id 出现两次视为数据错误（不静默覆盖）。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "knowledge"
DEFAULT_CONTRACTS = PROJECT_ROOT / "data" / "contracts"
DEFAULT_GOLD = PROJECT_ROOT / "data" / "eval" / "gold_contracts.json"

CONTRACT_HEADING_RE = re.compile(r"^##\s+(C\d{2})\s*·\s*(.+?)\s*$")
SUMMARY_HEADING_RE = re.compile(r"^>\s*\*\*条款—问题映射摘要（(C\d{2})）\*\*")
TABLE_ROW_RE = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")
SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|$")


def split_source(path: Path) -> list[dict]:
    """按 `## Cxx · 场景` 切分；返回正文与映射摘要。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[dict] = []
    current: dict | None = None
    body: list[str] = []
    summary: list[str] = []

    def flush() -> None:
        if current is None:
            return
        while body and not body[-1].strip():
            body.pop()
        blocks.append(
            {
                "contract_id": current["contract_id"],
                "scenario": current["scenario"],
                "source_file": path.name,
                "body": "\n".join(body).strip(),
                "mapping_markdown": "\n".join(summary).strip(),
            }
        )

    for line in lines:
        heading = CONTRACT_HEADING_RE.match(line)
        if heading:
            flush()
            current = {"contract_id": heading.group(1), "scenario": heading.group(2)}
            body = []
            summary = []
            continue
        if current is None:
            continue  # 文件开头的说明文字
        summary_heading = SUMMARY_HEADING_RE.match(line)
        if summary_heading:
            summary = [line]
            continue
        if summary:
            if line.startswith(">") or not line.strip():
                summary.append(line)
            continue
        body.append(line)
    flush()
    return [block for block in blocks if block["body"]]


def parse_mapping(markdown: str) -> list[dict]:
    """把映射摘要里的 Markdown 表格解析成行；格式不符时只保留原文。"""
    expectations: list[dict] = []
    for line in markdown.splitlines():
        stripped = line.lstrip(">").strip()
        if not stripped.startswith("|") or SEPARATOR_RE.match(stripped):
            continue
        match = TABLE_ROW_RE.match(stripped)
        if not match:
            continue
        clause, questions, recall, distractors = (cell.strip() for cell in match.groups())
        if clause in {"合同条款", ""}:
            continue
        expectations.append(
            {
                "clause": clause,
                "questions": [q.strip() for q in re.split(r"[,，、]", questions) if q.strip()],
                "expected_recall": recall,
                "distractors": distractors,
            }
        )
    return expectations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    args = parser.parse_args()

    sources = sorted(args.source.glob("模拟合同*.md"))
    if not sources:
        print(f"未找到模拟合同：{args.source}")
        return 1

    args.contracts.mkdir(parents=True, exist_ok=True)
    args.gold.parent.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    records: list[dict] = []
    for source in sources:
        for block in split_source(source):
            contract_id = block["contract_id"]
            if contract_id in seen:
                print(f"合同编号重复：{contract_id}（{source.name}）")
                return 1
            seen.add(contract_id)
            target = args.contracts / f"{contract_id}.md"
            target.write_text(block["body"] + "\n", encoding="utf-8")
            records.append(
                {
                    "contract_id": contract_id,
                    "scenario": block["scenario"],
                    "source_file": block["source_file"],
                    "contract_file": f"data/contracts/{contract_id}.md",
                    "mapping_markdown": block["mapping_markdown"],
                    "expectations": parse_mapping(block["mapping_markdown"]),
                }
            )

    records.sort(key=lambda item: item["contract_id"])
    payload = {
        "version": 1,
        "note": (
            "gold 来自模拟合同自带的“条款—问题映射摘要”；"
            "questions 指向 data/knowledge/100问题.md 的编号，"
            "expected_recall 是检索期望，不是规则判级 gold。"
        ),
        "contract_count": len(records),
        "contracts": records,
    }
    args.gold.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with_expectations = sum(1 for item in records if item["expectations"])
    print(f"合同 {len(records)} 份 → {args.contracts}")
    print(f"含映射行 {with_expectations} 份 → {args.gold}")
    missing = [item["contract_id"] for item in records if not item["expectations"]]
    if missing:
        print("无映射行：" + ", ".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
