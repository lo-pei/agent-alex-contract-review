"""`segment_clauses` 节点：把 canonical_text 切成 Clause[]（保留全局偏移）。

角色：图的第二站（ADR-001 / ADR-005 §3.4）。
依赖：`app/schemas.py`。
实现（确定性，不调用 LLM）：
1. 标题识别（界面轮 12 加强）：
   - 中文序号（`第X条` / `一、` / `（一）`）、英文（`ARTICLE N`）；
   - 数字编号 `1.` / `12.`：允许“编号 + 主题词 + 冒号 + 正文”写在同一行
     （中文合同常见 `13. 争议解决：凡因……`），也允许短句标题以句号结尾；
   - 无编号的主题行：`违约责任：……`、`Force Majeure: ……` 这类“主题词 + 冒号”
     形式，仅当主题词命中 `_TOPIC_KEYWORDS` 时才认标题（避免把“装运港：”当成条款）；
2. 同一主题的相邻段落（中文条款紧跟英文译本）合并回一条，避免一条拆成两条；
3. 标题前内容 → `C000` 前言（空则跳过）；标题只保留“编号 + 主题词”短标签，
   方便左侧目录展示（正文仍在 `text` 里）；
4. 只有“非标题开头”的小段落才并入前一条款（有标题的小条款保留，保住条款边界）；
5. 单条款 > 4000 字符按段落/句号/分号拆分，`clause_id` 追加 `-1/-2`；
6. 无标题 → 空行段落聚合（目标 300–2000 字符），仍无内容 → 单条款；
7. 条款数 > 200 → 明确报错（不静默截断）。
约束：切分失败不崩溃，写 `status="failed"` + `errors`，报告仍可产出“审查未完成”。
"""

from __future__ import annotations

import re
from time import perf_counter

from app.schemas import Clause, ContractReviewState

MAX_CLAUSES = 200
MAX_CLAUSE_CHARS = 4000
MIN_CLAUSE_CHARS = 80
MAX_TITLE_CHARS = 120
#: “编号 + 主题词 + 冒号 + 正文”写在同一行时，整行可能很长（正文就在标题行里）
MAX_NUMBERED_LINE_CHARS = 600
#: “违约责任：……”这类无编号主题行，正文同样可能在标题行里
MAX_LABEL_LINE_CHARS = 800

_CLAUSE_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "trade_term": ("fob", "cif", "cfr", "exw", "ddp", "dap", "fca", "incoterms", "贸易术语"),
    "payment": ("payment", "付款", "t/t", "l/c", "信用证"),
    "delivery": ("delivery", "shipment", "交货", "装运"),
    "inspection": ("inspection", "检验"),
    "warranty": ("warranty", "质保", "保证期"),
    "liability": ("liability", "indemnif", "赔偿", "违约责任"),
    "dispute": ("arbitration", "jurisdiction", "governing law", "仲裁", "管辖", "适用法律"),
    "force_majeure": ("force majeure", "不可抗力"),
    "confidentiality": ("confidential", "保密"),
}

_HEADING_PATTERNS = (
    re.compile(r"^第[一二三四五六七八九十百零〇\d]+[条章节]"),
    re.compile(r"^[一二三四五六七八九十]+、"),
    re.compile(r"^（[一二三四五六七八九十]+）"),
    re.compile(r"^(ARTICLE|Article|SECTION|Section|CLAUSE|Clause)\s+[0-9IVXLC]+"),
)
# 纯数字编号：要求「短行 + 不以句末标点结尾 + 标题词数少」，避免把正文 “30 days after...” 当标题
_NUMBERED_HEADING = re.compile(r"^\d{1,2}(?:\.\d{1,2})*[.)、．]?\s+(.+)$")
# “主题词 + 冒号”：中文合同里经常不写编号（如 `违约责任：如果卖方……`）
_LABEL_HEADING = re.compile(r"^([^:：]{1,32})[:：]")

#: 主题词 → 归一键；用于两件事：判断“主题词行”是不是条款标题、把中英双语段落并回一条。
_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "payment": ("payment", "付款", "支付"),
    "price": ("unit price", "price", "价格", "单价", "总价"),
    "goods": ("commodity", "goods", "货物名称"),
    "quantity": ("quantity", "数量", "溢短装"),
    "packing": ("packing", "包装"),
    "trade_terms": ("trade term", "incoterms", "贸易术语"),
    "delivery": ("delivery", "shipment", "交货", "装运"),
    "insurance": ("insurance", "保险"),
    "inspection": ("inspection", "quality standard", "检验", "质量标准", "质量", "品质"),
    "liability": ("liquidated damages", "liability", "违约责任", "赔偿"),
    "force_majeure": ("force majeure", "不可抗力"),
    "ip": ("intellectual property", "知识产权"),
    "governing_law": ("governing law", "适用法律"),
    "dispute": ("dispute resolution", "arbitration", "争议解决", "仲裁"),
    "notices": ("notices", "通知"),
    "confidentiality": ("confidential", "保密"),
}

#: 明确是“字段行”而不是条款标题的前缀（`装运港：` / 目的港：` / 卖方：` 等）。
#: 这些行留在原条款里：它们是条款正文的一部分，单独成条会让审查失去上下文。
_FIELD_LABELS = (
    "装运港",
    "目的港",
    "卖方",
    "买方",
    "地址",
    "电话",
    "传真",
    "电子邮箱",
    "邮箱",
    "签署日期",
    "签订日期",
    "合同编号",
    "开户行",
    "账号",
    "port of shipment",
    "port of destination",
    "the seller",
    "the buyer",
    "address",
    "tel",
    "fax",
    "e-mail",
    "email",
    "contract no",
    "signing date",
)


class SegmentError(Exception):
    """可读的切分失败原因；由节点转成 `status="failed"`。"""


def classify_clause(text: str) -> str | None:
    """确定性关键词分类：先看标题行，再看全文；未命中返回 None（不猜）。"""
    title = text.split("\n", 1)[0]
    for candidate in (title, text):
        lowered = candidate.casefold()
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


def _topics_of_line(line: str) -> set[str]:
    """命中的主题归一键集合；未命中返回空集（不猜）。"""
    lowered = line.casefold()
    return {
        topic
        for topic, keywords in _TOPIC_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    }


def _is_label_heading(stripped: str) -> bool:
    """`违约责任：……` / `Force Majeure: ……` 这类“主题词 + 冒号”的标题行。

    只认命中主题词的前缀：`装运港：`、`卖方：` 等字段行仍留在原条款里。
    """
    match = _LABEL_HEADING.match(stripped)
    if not match:
        return False
    label = match.group(1).strip()
    if not label:
        return False
    if any(label.casefold().startswith(field) for field in _FIELD_LABELS):
        return False
    return bool(_topics_of_line(label))


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _is_numbered_heading(stripped: str) -> bool:
    """数字编号标题：兼容“编号 + 主题词 + 冒号 + 正文同一行”的写法。"""
    if len(stripped) > MAX_NUMBERED_LINE_CHARS or "|" in stripped:
        return False
    match = _NUMBERED_HEADING.match(stripped)
    if not match:
        return False
    rest = match.group(1).strip()
    if not rest:
        return False

    label_match = _LABEL_HEADING.match(rest)
    if label_match:
        label = label_match.group(1).strip()
        # 冒号前必须是短标签（≤16 字），避免把 “30 days after receipt: ...” 当标题
        if label and len(label) <= 16:
            return True

    if len(rest) <= 30:
        # 短标题可以以句号结尾（如 `14. 本合同由中、英文写成，两种文本具有同等效力。`）
        return True
    if len(rest) <= 60 and _has_cjk(rest):
        # 中文短条款常一句话成条（`12. 通知：……`），仍算标题；英文正文行不会命中
        return True
    if rest.endswith((".", "。", ";", "；", ",", "，")):
        return False
    return len(rest.split()) <= 6


def _starts_numbered(title: str) -> bool:
    """该行是否自带编号（`第X条` / `1.` / `一、`）——自带编号的条款不参与译本合并。"""
    stripped = title.strip()
    if not stripped:
        return False
    if _NUMBERED_HEADING.match(stripped):
        return True
    return any(pattern.match(stripped) for pattern in _HEADING_PATTERNS)


def is_heading(line: str) -> bool:
    """判断一行是否为条款标题。"""
    stripped = line.strip()
    if not stripped:
        return False
    if _NUMBERED_HEADING.match(stripped):
        return _is_numbered_heading(stripped)
    if _is_label_heading(stripped):
        return len(stripped) <= MAX_LABEL_LINE_CHARS
    if len(stripped) > MAX_TITLE_CHARS:
        return False
    return any(pattern.match(stripped) for pattern in _HEADING_PATTERNS)


#: “特别提示 / 注意事项”这类说明块：块内的 `1. 2. 3.` 是提示条目，不是合同条款
_NOTICE_START = re.compile(r"^(?:特别提示|重要提示|注意事项|敬请注意|温馨提示)[:：]?$")
_NOTICE_END = re.compile(
    r"^(?:销售合同书|SALES CONTRACT|SALES AGREEMENT|CONTRACT|合同编号|"
    r"第[一二三四五六七八九十百零〇\d]+[条章节]|ARTICLE\s+[0-9IVXLC])"
)


def _notice_spans(text: str) -> list[tuple[int, int]]:
    """说明块区间；无结束标记时以 2000 字符为上限，避免吞掉整篇。"""
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for line, line_start, line_end in _line_offsets(text):
        stripped = line.strip()
        if _NOTICE_START.match(stripped):
            start = line_start
            continue
        if start is not None and (
            _NOTICE_END.match(stripped) or line_end - start > 2000
        ):
            spans.append((start, line_start))
            start = None
    if start is not None:
        spans.append((start, len(text)))
    return spans


def _line_offsets(text: str):
    """产出 (line, start, end)，end 不含换行符，start 为行首全局偏移。"""
    offset = 0
    for line in text.splitlines(keepends=True):
        start = offset
        offset += len(line)
        yield line.rstrip("\n"), start, offset


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start] in " \t\n\r":
        start += 1
    while end > start and text[end - 1] in " \t\n\r":
        end -= 1
    return start, end


def heading_starts(text: str) -> list[int]:
    notices = _notice_spans(text)
    return [
        start
        for line, start, _ in _line_offsets(text)
        if is_heading(line)
        and not any(begin <= start < stop for begin, stop in notices)
    ]


def split_by_headings(text: str) -> list[dict]:
    """按标题切分；返回 [{start, end, title, is_preamble}]，坐标已去首尾空白。"""
    starts = heading_starts(text)
    if not starts:
        return []

    drafts: list[dict] = []
    preamble = _trim_span(text, 0, starts[0])
    if preamble[1] > preamble[0] and text[preamble[0] : preamble[1]].strip():
        drafts.append(
            {
                "start": preamble[0],
                "end": preamble[1],
                "title": "",
                "is_preamble": True,
            }
        )

    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        trimmed_start, trimmed_end = _trim_span(text, start, end)
        title_line = text[start:].split("\n", 1)[0].strip()
        drafts.append(
            {
                "start": trimmed_start,
                "end": trimmed_end,
                "title": _short_title(title_line),
                "is_preamble": False,
            }
        )
    return drafts


def _merge_translations(drafts: list[dict], text: str) -> list[dict]:
    """无编号的同主题段（中英对照合同的译本）并入上一条款；自带编号的条目不参与。"""
    merged: list[dict] = []
    for draft in drafts:
        if (
            merged
            and not draft["is_preamble"]
            and not merged[-1]["is_preamble"]
            and not _starts_numbered(draft["title"])
        ):
            previous_topics = _topics_of_line(merged[-1]["title"])
            current_topics = _topics_of_line(draft["title"])
            if previous_topics and current_topics and previous_topics & current_topics:
                merged[-1]["end"] = draft["end"]
                continue
        merged.append(dict(draft))
    return merged


def _merge_small(drafts: list[dict], text: str) -> list[dict]:
    """只有“非标题开头”的小段才并入上一条款；带标题的小条款保留（守住条款边界）。"""
    merged: list[dict] = []
    for draft in drafts:
        content = text[draft["start"] : draft["end"]]
        first_line = content.strip().split("\n", 1)[0]
        headed = bool(draft["title"]) or is_heading(first_line)
        if (
            merged
            and not merged[-1]["is_preamble"]
            and not draft["is_preamble"]
            and not headed
            and len(content.strip()) < MIN_CLAUSE_CHARS
        ):
            merged[-1]["end"] = draft["end"]
            continue
        merged.append(dict(draft))
    return merged


def split_long_span(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """把超长区间按段落 → 句号/分号切成 ≤4000 字符的片段（坐标连续、去首尾空白）。"""
    pieces: list[tuple[int, int]] = []
    cursor = start
    while end - cursor > MAX_CLAUSE_CHARS:
        window = text[cursor : cursor + MAX_CLAUSE_CHARS]
        cut = window.rfind("\n\n")
        if cut < MAX_CLAUSE_CHARS // 2:
            candidates = [window.rfind(mark) for mark in ("。", "；", ". ", "; ")]
            best = max(candidates)
            cut = best + 1 if best >= MAX_CLAUSE_CHARS // 2 else MAX_CLAUSE_CHARS
        piece_start, piece_end = _trim_span(text, cursor, cursor + cut)
        if piece_end > piece_start:
            pieces.append((piece_start, piece_end))
        cursor += cut

    piece_start, piece_end = _trim_span(text, cursor, end)
    if piece_end > piece_start:
        pieces.append((piece_start, piece_end))
    return pieces


def split_by_paragraphs(text: str) -> list[tuple[int, int]]:
    """无标题 fallback：空行段落聚合成约 300–2000 字符的块；超长块再按句子拆。"""
    blocks = split_blocks(text)
    if not blocks:
        span = _trim_span(text, 0, len(text))
        return [span] if span[1] > span[0] else []

    spans: list[tuple[int, int]] = []
    for _, start, end in blocks:
        if end - start > MAX_CLAUSE_CHARS:
            spans.extend(split_long_span(text, start, end))
        else:
            spans.append((start, end))

    groups: list[list[int]] = []
    for start, end in spans:
        if not groups:
            groups.append([start, end])
            continue
        current_len = groups[-1][1] - groups[-1][0]
        if current_len >= 300 or (current_len + (end - start)) > 2000:
            groups.append([start, end])
        else:
            groups[-1][1] = end
    return [tuple(group) for group in groups]


def _short_title(line: str) -> str:
    """目录用的短标题：只留“编号 + 主题词”，去掉标题行里的正文与占位空格。

    `5. 付款条件：                      Payment:` → `5. 付款条件`
    `违约责任：如果卖方未能按约定交货……` → `违约责任`
    """
    stripped = " ".join(line.split())
    if not stripped:
        return ""

    number = ""
    rest = stripped
    match = _NUMBERED_HEADING.match(stripped)
    if match:
        number = stripped[: match.start(1)].strip()
        rest = match.group(1)

    label_match = _LABEL_HEADING.match(rest)
    if label_match:
        label = " ".join(label_match.group(1).split())
        if label and len(label) <= 16 and len(number) + 1 + len(label) <= MAX_TITLE_CHARS:
            return f"{number} {label}".strip()

    if len(stripped) <= MAX_TITLE_CHARS:
        return stripped
    return stripped[:MAX_TITLE_CHARS].rstrip() + "…"


def _title_of(text: str, start: int, end: int) -> str:
    first_line = text[start:end].split("\n", 1)[0].strip()
    return _short_title(first_line) if first_line else ""


def _build_clauses(
    text: str, drafts: list[dict], page_of
) -> list[Clause]:
    clauses: list[Clause] = []
    body_index = 0

    for draft in drafts:
        start, end = draft["start"], draft["end"]
        if end <= start:
            continue

        if draft["is_preamble"]:
            clauses.append(
                Clause(
                    clause_id="C000",
                    title="",
                    text=text[start:end],
                    page=page_of(start),
                    start=start,
                    end=end,
                    clause_type="preamble",
                )
            )
            continue

        body_index += 1
        base_id = f"C{body_index:03d}"
        pieces = (
            split_long_span(text, start, end)
            if end - start > MAX_CLAUSE_CHARS
            else [(start, end)]
        )
        for piece_index, (piece_start, piece_end) in enumerate(pieces, start=1):
            clause_id = base_id if len(pieces) == 1 else f"{base_id}-{piece_index}"
            piece_text = text[piece_start:piece_end]
            clauses.append(
                Clause(
                    clause_id=clause_id,
                    title=draft["title"] or _title_of(text, piece_start, piece_end),
                    text=piece_text,
                    page=page_of(piece_start),
                    start=piece_start,
                    end=piece_end,
                    clause_type=classify_clause(piece_text),
                )
            )
    return clauses


def segment_clauses(state: ContractReviewState) -> dict:
    started = perf_counter()

    def finish(**updates: object) -> dict:
        return {
            **updates,
            "timings": {
                **state.timings,
                "segment_clauses_ms": round((perf_counter() - started) * 1000, 2),
            },
        }

    if state.status == "failed" or not state.raw_text.strip():
        return finish(clauses=[])

    text = state.raw_text
    warnings = list(state.warnings)

    drafts = split_by_headings(text)
    if drafts:
        drafts = _merge_translations(drafts, text)
        drafts = _merge_small(drafts, text)
    else:
        spans = split_by_paragraphs(text)
        drafts = [
            {
                "start": start,
                "end": end,
                "title": _title_of(text, start, end),
                "is_preamble": False,
            }
            for start, end in spans
        ]
        warnings.append(
            "未识别到条款标题，已按段落聚合（目标 300–2000 字符），重要条款请人工核对。"
        )

    if not drafts:
        drafts = [{"start": 0, "end": len(text), "title": "", "is_preamble": False}]
        warnings.append("未识别出任何段落，已将整篇合同作为一个条款处理。")

    try:
        clauses = _build_clauses(text, drafts, lambda offset: _page_of(state, offset))
        if len(clauses) > MAX_CLAUSES:
            raise SegmentError(
                f"条款数过多（{len(clauses)} 条），超过上限 {MAX_CLAUSES} 条；"
                "请拆分合同或调整上限。"
            )
    except SegmentError as exc:
        return finish(
            status="failed",
            clauses=[],
            errors=[*state.errors, str(exc)],
            warnings=warnings,
        )

    return finish(clauses=clauses, warnings=warnings)


def _page_of(state: ContractReviewState, offset: int) -> int:
    """偏移所在页；页间分隔符归入前一页（ADR-005 §3.2 规则 6）。"""
    for page in reversed(state.pages):
        if page.start_offset <= offset:
            return page.page_number
    return state.pages[0].page_number if state.pages else 1
