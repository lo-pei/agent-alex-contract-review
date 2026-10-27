"""证据定位：把 LLM 给出的 quote 映射回原文偏移（ADR-005 §3.4）。

角色：validate 节点、解释 Quality Gate、规则引擎共享的唯一定位实现。
依赖：仅标准库（`unicodedata`）。
约束：
- 先精确匹配；失败后**只允许** NFC 规范化 + 连续空白折叠；
- 禁止模糊相似度、标点删除、数字转写、否定词删除；
- 找不到就返回 None，由调用方决定降级（不伪造偏移）。

实现说明：NFC 必须按“基字符 + 组合符”整簇规范化（逐字符规范化无法合成
`e` + `´` → `é`），因此下面用簇缓冲 + 两张索引表把规范化字符映射回原文区间。
"""

from __future__ import annotations

import unicodedata


def _is_combining(char: str) -> bool:
    return unicodedata.combining(char) != 0


def _normalize_with_index(text: str) -> tuple[str, list[int], list[int]]:
    """返回 `(规范化文本, 每个字符的原文起始索引, 原文结束索引)`。

    空白折叠规则：任意连续空白（含换行）压成一个空格；文本首部空白丢弃，
    末尾空白丢弃（不在末尾留空格）。
    """
    chars: list[str] = []
    starts: list[int] = []
    ends: list[int] = []

    pending_space = False
    space_start = 0
    space_end = 0
    cluster: list[str] = []
    cluster_start = 0
    cluster_end = 0

    def flush_cluster() -> None:
        nonlocal cluster
        if not cluster:
            return
        for normalized in unicodedata.normalize("NFC", "".join(cluster)):
            chars.append(normalized)
            starts.append(cluster_start)
            ends.append(cluster_end)
        cluster = []

    for position, raw_char in enumerate(text):
        if raw_char.isspace():
            flush_cluster()
            if chars:
                if not pending_space:
                    space_start = position
                pending_space = True
                space_end = position + 1
            continue

        if pending_space:
            chars.append(" ")
            starts.append(space_start)
            ends.append(space_end)
            pending_space = False

        if not cluster:
            cluster_start = position
        elif not _is_combining(raw_char):
            flush_cluster()
            cluster_start = position

        cluster.append(raw_char)
        cluster_end = position + 1

    flush_cluster()
    return "".join(chars), starts, ends


def normalize(text: str) -> str:
    return _normalize_with_index(text)[0]


def locate_quote(text: str, quote: str) -> tuple[int, int] | None:
    """在 `text` 中定位 `quote`，返回 `(start, end)`；失败返回 None。

    返回区间可跨行/跨空白，但起止都是原文真实字符索引，可直接用于
    `text[start:end]` 与 `文件:页:start-end` citation。
    """
    if not quote or not quote.strip():
        return None

    exact = text.find(quote)
    if exact >= 0:
        return exact, exact + len(quote)

    normalized_text, starts, ends = _normalize_with_index(text)
    normalized_quote = normalize(quote)
    if not normalized_quote:
        return None

    position = normalized_text.find(normalized_quote)
    if position < 0:
        return None

    start = starts[position]
    end = ends[position + len(normalized_quote) - 1]
    if start >= end or text[start:end].strip() == "":
        return None
    return start, end
