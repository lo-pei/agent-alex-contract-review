"""`segment_clauses` 节点：把 canonical_text 切成 Clause[]（保留全局偏移）。

角色：图的第二站（ADR-001 / ADR-005 §3.2）。
依赖：`app/schemas.py`。
当前实现：**空行分段 fallback**（标题识别、条款类型、超长拆分在下一阶段补齐）。
约束：不调用 LLM；切分失败不崩溃，退化为整篇一个条款并写 warning。
"""

from __future__ import annotations

import re
from time import perf_counter

from app.schemas import Clause, ContractReviewState

_CLAUSE_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "payment": ("payment", "付款", "t/t", "l/c", "信用证"),
    "delivery": ("delivery", "shipment", "交货", "装运"),
    "inspection": ("inspection", "检验"),
    "warranty": ("warranty", "质保", "保证期"),
    "trade_term": ("fob", "cif", "cfr", "exw", "ddp", "dap", "fca", "incoterms", "贸易术语"),
    "dispute": ("arbitration", "jurisdiction", "governing law", "仲裁", "管辖", "适用法律"),
    "force_majeure": ("force majeure", "不可抗力"),
}


def classify_clause(text: str) -> str | None:
    """确定性关键词分类；未命中返回 None（不猜）。"""
    lowered = text.casefold()
    for clause_type, keywords in _CLAUSE_TYPE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return clause_type
    return None


def split_blocks(text: str) -> list[tuple[str, int, int]]:
    """按空行分块，返回 (block_text, start, end)，坐标与 canonical_text 一致。"""
    blocks: list[tuple[str, int, int]] = []
    current: list[str] = []
    current_start = 0
    offset = 0

    for line in text.splitlines(keepends=True):
        if line.strip():
            if not current:
                current_start = offset
            current.append(line)
        elif current:
            block = "".join(current).rstrip()
            blocks.append((block, current_start, current_start + len(block)))
            current = []
        offset += len(line)

    if current:
        block = "".join(current).rstrip()
        blocks.append((block, current_start, current_start + len(block)))
    return blocks


def _title_of(block: str) -> str:
    first_line = block.split("\n", 1)[0].strip()
    return first_line if 0 < len(first_line) <= 120 else ""


def segment_clauses(state: ContractReviewState) -> dict:
    started = perf_counter()

    if state.status == "failed" or not state.raw_text.strip():
        return {
            "clauses": [],
            "timings": {
                **state.timings,
                "segment_clauses_ms": round((perf_counter() - started) * 1000, 2),
            },
        }

    warnings = list(state.warnings)
    blocks = split_blocks(state.raw_text)
    if not blocks:
        blocks = [(state.raw_text.strip(), 0, len(state.raw_text.strip()))]
        warnings.append("未识别出任何段落，已将整篇合同作为一个条款处理。")

    clauses = [
        Clause(
            clause_id=f"C{index:03d}",
            title=_title_of(block),
            text=block,
            page=_page_of(state, start),
            start=start,
            end=end,
            clause_type=classify_clause(block),
        )
        for index, (block, start, end) in enumerate(blocks, start=1)
    ]
    return {
        "clauses": clauses,
        "warnings": warnings,
        "timings": {
            **state.timings,
            "segment_clauses_ms": round((perf_counter() - started) * 1000, 2),
        },
    }


def _page_of(state: ContractReviewState, offset: int) -> int:
    for page in state.pages:
        if page.start_offset <= offset < page.end_offset:
            return page.page_number
    return state.pages[0].page_number if state.pages else 1


# 供下一阶段的标题式切分复用：英文/中文条款标题模式（ADR-005 §3.2）
HEADING_PATTERNS = (
    re.compile(r"^第[一二三四五六七八九十百零〇\d]+条"),
    re.compile(r"^[一二三四五六七八九十]+、"),
    re.compile(r"^(ARTICLE|Article|SECTION|Section|CLAUSE|Clause)\s+[0-9IVXLC]+"),
)
