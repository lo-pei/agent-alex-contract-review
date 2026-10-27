"""本地知识检索（RAG MVP）：BM25 + 字符 n-gram，零网络依赖（ADR-007 / ADR-008）。

角色：为 `explain_risks` 提供可追溯的知识片段，引用格式 `source_id#section`。
依赖：`app/config.py`、`PyYAML`、标准库；**不引入**向量库/embedding 服务。
约束：
- 默认关闭（`RAG_ENABLED=false`），关闭时返回 `None`，不报错；
- 只做检索，不做判级、不改写规则结果；
- 检索不到就返回空列表，绝不编造知识；
- 语料必须有 `manifest.yaml`（`source_id/title/publisher/version/jurisdiction/
  effective_date/language/file/license`），缺字段直接报错，避免无授权/无版本文本入库；
- 文件必须在语料目录内（拒绝 `..`/绝对路径）。

语料格式示例见 `data/knowledge/manifest.yaml` 与 `docs/devlog/06_RAG与多智能体资料清单.md`。

支持的语料格式：Markdown / 纯文本（按 Markdown 标题与 `***Article N***` 等结构行切分）、
DOCX（按 `第X条` 条文切分，无法按标题样式切分时退化）。旧版 `.doc` 明确拒绝，请先转换。
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

import yaml

from app.config import settings

MANIFEST_FILENAME = "manifest.yaml"
MANIFEST_VERSION = 1

#: manifest 每条文档的必填字段（顺序即错误提示顺序）
REQUIRED_FIELDS: tuple[str, ...] = (
    "source_id",
    "title",
    "publisher",
    "version",
    "jurisdiction",
    "effective_date",
    "language",
    "file",
    "license",
)

ALLOWED_SUFFIXES = frozenset({".md", ".markdown", ".txt", ".docx"})
REJECTED_SUFFIXES = frozenset({".doc"})

#: 片段上限（字符）；超过则按段落/句子边界再切，避免单条 59KB 大段污染 BM25 与提示词
MAX_SECTION_CHARS = 1600

_SOURCE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,63}$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
#: 英文 CISG 原文用 `***Article N***` 作为条文标题
_STRONG_HEADING_RE = re.compile(r"^\*\*\*\s*(.+?)\s*\*\*\*$")
#: 仅把结构性加粗行（Preamble / PART / Chapter / Article）当标题，避免把强调句切成段
_BOLD_HEADING_RE = re.compile(
    r"^\*\*\s*((?:Preamble|PART|Part|Chapter|Section|Article|ARTICLE)\b.*?)\s*\*\*$"
)
_WORD_RE = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")

#: docx 条文/编章节行（中文法律文本常见“第X条”开头）
_NUMBER = r"[一二三四五六七八九十百千零〇两0-9]+"
_DOCX_ARTICLE_RE = re.compile(rf"^(第{_NUMBER}条)")
_DOCX_STRUCTURE_RE = re.compile(rf"^(第{_NUMBER}(?:编|分编|章|节))")
_DOCX_TOC_RE = re.compile(r"^目\s*录$")
_DOCX_APPENDIX_RE = re.compile(r"^附\s*则$")

#: BM25 参数（业界常用默认值；语料变化时通过评测调整，不在代码里“调参到过拟合”）
BM25_K1 = 1.5
BM25_B = 0.75

#: 相对阈值：只保留得分不低于最高分 25% 的片段，避免长尾噪声混入提示词
RELATIVE_SCORE_RATIO = 0.25


class KnowledgeConfigError(RuntimeError):
    """知识库目录/manifest/文件不合法；调用方应告警并退化为纯规则解释。"""


@dataclass(frozen=True)
class KnowledgeDocument:
    """`manifest.yaml` 中的一条文档元数据（可追溯来源与授权）。"""

    source_id: str
    title: str
    publisher: str
    version: str
    jurisdiction: str
    effective_date: str
    language: str
    file: str
    license: str


@dataclass(frozen=True)
class KnowledgeChunk:
    """一个可检索片段；`citation` 是唯一对外引用格式。"""

    source_id: str
    title: str
    heading: str
    section: str
    text: str
    citation: str
    score: float = 0.0


def tokenize(text: str) -> list[str]:
    """英文按词、中文按“单字 + 二元组”切分；不依赖分词库。

    中文二元组能保留“付款/交付/仲裁”等术语信号；单字用于兜底召回。
    这是词法检索，不做语义向量化，因此可离线、可测试、可解释。
    """
    lowered = text.casefold()
    tokens = _WORD_RE.findall(lowered)
    for run in _CJK_RE.findall(lowered):
        tokens.extend(run)
        tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
    return [token for token in tokens if token]


def _heading_of(line: str) -> str | None:
    """识别一行是否为结构标题（Markdown 标题 / `***Article N***` / 结构性加粗）。"""
    match = _HEADING_RE.match(line)
    if match:
        return match.group(2).strip() or "未命名"
    for pattern in (_STRONG_HEADING_RE, _BOLD_HEADING_RE):
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip() or "未命名"
    return None


def _split_sections(text: str) -> list[tuple[str, str]]:
    """按 Markdown 标题切段；返回 `[(标题, 正文)]`，空正文丢弃。"""
    sections: list[tuple[str, str]] = []
    heading = "概述"
    lines: list[str] = []

    def flush() -> None:
        body = "\n".join(lines).strip()
        if body:
            sections.append((heading, body))

    for line in text.splitlines():
        title = _heading_of(line)
        if title is not None:
            flush()
            heading = title
            lines = []
        else:
            lines.append(line)
    flush()
    return sections


def _chunk_text(body: str, limit: int = MAX_SECTION_CHARS) -> list[str]:
    """把超长正文按段落/句子边界切成不超过 `limit` 的片段；尽力保持语义完整。"""
    if len(body) <= limit:
        return [body]

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
    if len(paragraphs) == 1:
        paragraphs = [line.strip() for line in body.splitlines() if line.strip()]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n{paragraph}" if current else paragraph
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        # 单段本身超长：按句末标点硬切
        while len(paragraph) > limit:
            cut = max(
                paragraph.rfind("。", 0, limit),
                paragraph.rfind("；", 0, limit),
                paragraph.rfind(". ", 0, limit),
                paragraph.rfind("! ", 0, limit),
                paragraph.rfind("? ", 0, limit),
            )
            if cut <= 0:
                cut = limit
            else:
                cut += 1
            chunks.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        current = paragraph
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk]


def _text_sections(text: str) -> list[tuple[str, str]]:
    """文本语料：先按结构标题切，再对超长片段二次切分（标题不变，段落后缀编号）。"""
    sections: list[tuple[str, str]] = []
    for heading, body in _split_sections(text):
        for part in _chunk_text(body):
            sections.append((heading, part))
    return sections


def _docx_paragraphs(path: Path) -> list[str]:
    """读取 DOCX 段落文本；python-docx 仅在此处按需导入。"""
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - 依赖缺失时给出明确提示
        raise KnowledgeConfigError("读取 .docx 需要 python-docx：pip install python-docx") from exc
    try:
        document = Document(str(path))
    except Exception as exc:  # python-docx 抛出的异常类型较多，统一包装
        raise KnowledgeConfigError(f"DOCX 读取失败：{path.name}（{exc}）") from exc
    return [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]


def _docx_sections(path: Path) -> list[tuple[str, str]]:
    """DOCX 语料：按“第X条”切分条文，编/章/节只作为上下文，目录行丢弃。

    DOCX 无法依赖标题样式（法律文本通常全部是 `Normal`），因此用条文号正则。
    条文之间的段落（如款项、但书）归入所属条文，避免把一条拆散。
    """
    paragraphs = _docx_paragraphs(path)
    sections: list[tuple[str, str]] = []
    preamble: list[str] = []
    context = ""
    heading = ""
    body: list[str] = []

    def flush() -> None:
        text = "\n".join(body).strip()
        if not text:
            return
        if context:
            text = f"〔{context}〕\n{text}"
        for part in _chunk_text(text):
            sections.append((heading or "前言", part))

    for paragraph in paragraphs:
        if _DOCX_TOC_RE.match(paragraph):
            # 目录之后到第一个结构标题之前的内容不作为正文
            continue
        article = _DOCX_ARTICLE_RE.match(paragraph)
        if article:
            flush()
            heading = article.group(1)
            body = [paragraph]
            continue
        structure = _DOCX_STRUCTURE_RE.match(paragraph)
        if structure or _DOCX_APPENDIX_RE.match(paragraph):
            flush()
            if heading:
                heading = ""
            context = paragraph
            body = []
            continue
        if heading:
            body.append(paragraph)
        else:
            preamble.append(paragraph)

    flush()

    if preamble:
        text = "\n".join(preamble).strip()
        # 目录条目（如“第一编　总　则”）已在上面被当作结构行，这里只保留真实正文
        if text and not all(_DOCX_STRUCTURE_RE.match(line) for line in preamble):
            for part in _chunk_text(text):
                sections.insert(0, ("前言", part))
    return sections


def _require_text(mapping: dict, key: str, where: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeConfigError(f"{where} 缺少或为空的字段：{key}")
    return value.strip()


def _validate_document(raw: object, index: int, root: Path) -> tuple[KnowledgeDocument, Path]:
    where = f"manifest 第 {index + 1} 条"
    if not isinstance(raw, dict):
        raise KnowledgeConfigError(f"{where} 必须是对象")
    unknown = sorted(set(raw) - set(REQUIRED_FIELDS))
    if unknown:
        raise KnowledgeConfigError(f"{where} 含未定义字段：{', '.join(unknown)}")

    values = {key: _require_text(raw, key, where) for key in REQUIRED_FIELDS}
    source_id = values["source_id"]
    if not _SOURCE_ID_RE.fullmatch(source_id):
        raise KnowledgeConfigError(
            f"{where} 的 source_id 不合法（需字母开头、仅字母数字下划线和连字符）：{source_id!r}"
        )
    try:
        date.fromisoformat(values["effective_date"])
    except ValueError as exc:
        raise KnowledgeConfigError(
            f"{where} 的 effective_date 必须是 YYYY-MM-DD：{values['effective_date']!r}"
        ) from exc

    file_value = values["file"]
    if Path(file_value).is_absolute():
        raise KnowledgeConfigError(f"{where} 的 file 必须相对语料目录：{file_value!r}")
    target = (root / file_value).resolve()
    if not target.is_relative_to(root):
        raise KnowledgeConfigError(f"{where} 的 file 越出语料目录：{file_value!r}")
    if target.suffix.casefold() in REJECTED_SUFFIXES:
        raise KnowledgeConfigError(
            f"{where} 的文件是旧版 .doc（python-docx 不支持）：{file_value!r}，"
            "请先转换为 .docx 或 .md 再登记"
        )
    if target.suffix.casefold() not in ALLOWED_SUFFIXES:
        raise KnowledgeConfigError(
            f"{where} 的文件类型不支持（仅 md/markdown/txt/docx）：{file_value!r}"
        )
    if not target.is_file():
        raise KnowledgeConfigError(f"{where} 的文件不存在：{file_value!r}")
    return KnowledgeDocument(**values), target


def _read_document(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise KnowledgeConfigError(f"知识文件不是 UTF-8：{path.name}") from exc
    except OSError as exc:
        raise KnowledgeConfigError(f"知识文件读取失败：{path.name}（{exc}）") from exc


def _sections_of(path: Path) -> list[tuple[str, str]]:
    """按后缀选择切分策略：DOCX 走条文号，其余按 Markdown/文本结构标题。"""
    if path.suffix.casefold() == ".docx":
        return _docx_sections(path)
    return _text_sections(_read_document(path))


class KnowledgeBase:
    """BM25 词法检索；语料小，加载一次并缓存（缓存键含文件 mtime/size）。"""

    def __init__(
        self,
        documents: list[KnowledgeDocument],
        chunks: list[KnowledgeChunk],
    ) -> None:
        self.documents = tuple(documents)
        self.chunks = tuple(chunks)
        self._tokens = [
            tokenize(f"{chunk.title} {chunk.heading} {chunk.text}") for chunk in chunks
        ]
        self._df: Counter[str] = Counter()
        for tokens in self._tokens:
            self._df.update(set(tokens))
        self._avgdl = (
            sum(len(tokens) for tokens in self._tokens) / len(self._tokens)
            if self._tokens
            else 0.0
        )

    def __len__(self) -> int:
        return len(self.chunks)

    def citations(self) -> frozenset[str]:
        return frozenset(chunk.citation for chunk in self.chunks)

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> list[KnowledgeChunk]:
        """返回得分最高的片段；没有命中或全部低于阈值时返回空列表。"""
        if not self.chunks:
            return []
        query_tokens = set(tokenize(query))
        if not query_tokens:
            return []

        limit = settings.rag_top_k if top_k is None else top_k
        threshold = settings.rag_min_score if min_score is None else min_score
        if limit <= 0:
            return []

        count = len(self._tokens)
        scores = [0.0] * count
        for term in sorted(query_tokens):
            frequency = self._df.get(term, 0)
            if frequency == 0:
                continue
            idf = math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for index, tokens in enumerate(self._tokens):
                term_frequency = tokens.count(term)
                if term_frequency == 0:
                    continue
                norm = 1 - BM25_B + BM25_B * len(tokens) / self._avgdl
                scores[index] += (
                    idf * term_frequency * (BM25_K1 + 1) / (term_frequency + BM25_K1 * norm)
                )

        ranked = sorted(
            (
                (score, chunk)
                for score, chunk in zip(scores, self.chunks, strict=True)
                if score > 0 and score >= threshold
            ),
            key=lambda item: (-item[0], item[1].citation),
        )
        if ranked:
            cutoff = max(threshold, ranked[0][0] * RELATIVE_SCORE_RATIO)
            ranked = [item for item in ranked if item[0] >= cutoff]
        return [replace(chunk, score=round(score, 4)) for score, chunk in ranked[:limit]]


def _section_ids(
    sections: list[tuple[str, str]], *, by_heading: bool
) -> list[tuple[str, str, str]]:
    """为每个片段分配稳定且唯一的 section 标识，返回 `[(heading, section, body)]`。

    - Markdown/文本：`s1, s2, ...`；同一标题被超长切分时依次为 `s2`、`s2-2`、`s2-3`；
    - DOCX：直接用条文号（如 `第577条`），重复出现时后缀 `-2`。
    """
    numbered: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    if by_heading:
        counters: Counter[str] = Counter()
        for heading, body in sections:
            counters[heading] += 1
            occurrence = counters[heading]
            base = heading
            section = base if occurrence == 1 else f"{base}-{occurrence}"
            while section in seen:  # 极端情况下避免引用重复
                counters[heading] += 1
                section = f"{base}-{counters[heading]}"
            seen.add(section)
            numbered.append((heading, section, body))
        return numbered

    index = 0
    previous: str | None = None
    part = 0
    for heading, body in sections:
        if heading != previous:
            index += 1
            previous = heading
            part = 1
        else:
            part += 1
        section = f"s{index}" if part == 1 else f"s{index}-{part}"
        numbered.append((heading, section, body))
    return numbered


#: 进程内缓存：API/UI 每次请求都重载 500KB 语料会很慢；键含 manifest 与各文件 mtime/size
_CACHE: dict[tuple[str, tuple[tuple[str, int, int], ...]], KnowledgeBase] = {}
_CACHE_LIMIT = 4


def _fingerprint(
    root: Path, manifest: Path, paths: list[Path]
) -> tuple[str, tuple[tuple[str, int, int], ...]]:
    stats = tuple(
        (path.name, path.stat().st_mtime_ns, path.stat().st_size)
        for path in [manifest, *paths]
    )
    return str(root), stats


def load_knowledge_base(
    corpus_dir: Path | str | None = None,
    *,
    enabled: bool | None = None,
) -> KnowledgeBase | None:
    """加载语料。默认跟随 `RAG_ENABLED`；关闭返回 `None`，开启但配置错误抛异常。

    加载结果按 `(目录, 文件 mtime/size)` 缓存，语料变更后自动重建。
    """
    if enabled is None:
        enabled = settings.rag_enabled
    if not enabled:
        return None

    root = Path(corpus_dir) if corpus_dir is not None else Path(settings.rag_knowledge_dir)
    if not root.is_dir():
        raise KnowledgeConfigError(f"知识库目录不存在：{root}（先按资料清单准备语料）")
    root = root.resolve()

    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise KnowledgeConfigError(f"缺少 {MANIFEST_FILENAME}：{manifest_path}")
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise KnowledgeConfigError(f"manifest 读取失败：{exc}") from exc

    if not isinstance(manifest, dict):
        raise KnowledgeConfigError("manifest 顶层必须是对象")
    if manifest.get("version") != MANIFEST_VERSION:
        raise KnowledgeConfigError(
            f"manifest.version 必须是 {MANIFEST_VERSION}，当前：{manifest.get('version')!r}"
        )
    raw_documents = manifest.get("documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise KnowledgeConfigError("manifest.documents 必须是非空列表")

    validated: list[tuple[KnowledgeDocument, Path]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_documents):
        document, path = _validate_document(raw, index, root)
        if document.source_id in seen:
            raise KnowledgeConfigError(f"source_id 重复：{document.source_id}")
        seen.add(document.source_id)
        validated.append((document, path))

    key = _fingerprint(root, manifest_path, [path for _, path in validated])
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    documents: list[KnowledgeDocument] = []
    chunks: list[KnowledgeChunk] = []
    for document, path in validated:
        sections = _sections_of(path)
        if not sections:
            raise KnowledgeConfigError(f"知识文件没有可用内容：{document.file}")
        documents.append(document)
        for heading, section, body in _section_ids(
            sections, by_heading=path.suffix.casefold() == ".docx"
        ):
            chunks.append(
                KnowledgeChunk(
                    source_id=document.source_id,
                    title=document.title,
                    heading=heading,
                    section=section,
                    text=body,
                    citation=f"{document.source_id}#{section}",
                )
            )

    knowledge = KnowledgeBase(documents, chunks)
    if len(_CACHE) >= _CACHE_LIMIT:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = knowledge
    return knowledge
