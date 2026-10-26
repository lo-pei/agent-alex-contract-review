"""`ingest_document` 节点：读取合同文件 → canonical_text + 页码/偏移 + sha256。

角色：图的第一站（ADR-001 / ADR-005）。
依赖：`app/config.py`（上限）、`app/schemas.py`（Page/State）、`pypdf`、`python-docx`。
支持：TXT / Markdown / 文本型 PDF / DOCX（扫描件、加密 PDF 明确报错，不做 OCR）。
约束：
- 所有偏移都是 **canonical_text 的字符索引**，不是 PDF 字节偏移；
- 本节点任何失败都写入 `errors` 且 `status="failed"`，不抛异常中断图；
- 报告只暴露 basename，不暴露服务器绝对路径。
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from time import perf_counter

from app.config import settings
from app.schemas import ContractReviewState, Page

SUPPORTED_SUFFIXES = {".txt": "text", ".md": "text", ".pdf": "pdf", ".docx": "docx"}
KNOWN_UNSUPPORTED_SUFFIXES = {".doc": "旧版 Word (.doc)"}

PAGE_SEPARATOR = "\n\n"
MIN_PDF_TEXT_CHARS = 50  # 少于此字符数视为无文本层（扫描件）


class IngestError(Exception):
    """可读的解析失败原因；由节点转成 `status="failed"`，不向上冒泡。"""


def canonicalize(text: str) -> str:
    """统一换行符、去掉 BOM 与 NUL；其余字符保持原样（保证偏移可回查）。"""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\x00", "")
    return normalized[1:] if normalized.startswith("\ufeff") else normalized


def _safe_filename(name: str) -> str:
    """只保留 basename 并去掉控制字符，避免报告/日志泄漏路径或注入换行。"""
    cleaned = "".join(ch for ch in Path(name).name if ch.isprintable())
    return cleaned or "contract"


def _decode_text(raw: bytes) -> tuple[str, list[str]]:
    """UTF-8 → GB18030 → Latin-1 依次尝试；中文合同常见 GB18030。"""
    warnings: list[str] = []
    try:
        return raw.decode("utf-8-sig"), warnings
    except UnicodeDecodeError:
        warnings.append("文件不是 UTF-8 编码，已按 GB18030 解码，请核对原文。")
    try:
        return raw.decode("gb18030"), warnings
    except UnicodeDecodeError:
        warnings.append("文件编码无法识别，已按 Latin-1 兜底解码，可能包含乱码，请核对原文。")
        return raw.decode("latin-1"), warnings


def _extract_pdf(raw: bytes, warnings: list[str]) -> list[str]:
    """按页提取文本；扫描件/加密/超页数都抛 `IngestError`。"""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(raw))
    except (PdfReadError, ValueError, TypeError) as exc:
        raise IngestError(f"PDF 无法解析：{exc}") from exc

    if reader.is_encrypted:
        try:
            decrypted = reader.decrypt("")
        except Exception as exc:  # noqa: BLE001 - pypdf 的解密异常类型不统一
            raise IngestError(f"PDF 解密失败：{exc}，请移除密码后上传。") from exc
        if not decrypted:
            raise IngestError("PDF 已加密，无法用空密码解密；请移除密码后上传。")
        warnings.append("PDF 已用空密码解密，文本提取可能受权限限制，请核对原文。")

    page_count = len(reader.pages)
    if page_count > settings.max_pages:
        raise IngestError(
            f"PDF 页数过多（{page_count} 页），超过上限 {settings.max_pages} 页。"
        )

    page_texts: list[str] = []
    empty_pages: list[int] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001 - 单页损坏不应拖垮整个文件
            raise IngestError(f"第 {index} 页文本提取失败：{exc}") from exc
        page_texts.append(canonicalize(text).strip("\n"))
        if not text.strip():
            empty_pages.append(index)

    total_chars = sum(len(text.strip()) for text in page_texts)
    if page_count and total_chars < MIN_PDF_TEXT_CHARS:
        raise IngestError(
            "未检测到文本层（可能是扫描件/图片 PDF）；"
            "请提供可复制文本的 PDF 或 DOCX，本项目不做 OCR。"
        )

    if empty_pages:
        preview = ", ".join(str(number) for number in empty_pages[:10])
        warnings.append(
            f"第 {preview} 页未提取到文本，可能是空白页或图片页，需人工核对。"
        )
    warnings.append("PDF 文本由 pypdf 提取；表格/多栏版式可能打乱列顺序，重要条款请人工核对。")
    return page_texts


def _iter_docx_blocks(document):
    """按 body 顺序产出段落与表格（避免“先段落再表格”打乱原文顺序）。"""
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _extract_docx(raw: bytes) -> str:
    """段落 + 表格按顺序拼成单页文本；表格行用 ` | ` 分隔单元格。"""
    from docx import Document

    try:
        document = Document(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001 - python-docx 抛出的异常类型不稳定
        raise IngestError(f"DOCX 无法解析：{exc}") from exc

    parts: list[str] = []
    for block in _iter_docx_blocks(document):
        if hasattr(block, "rows"):  # Table
            for row in block.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                if any(cells):
                    parts.append(" | ".join(cells))
        else:  # Paragraph
            text = block.text.strip()
            if text:
                parts.append(text)
    return "\n\n".join(parts)


def _assemble_pages(page_texts: list[str]) -> tuple[list[Page], str]:
    """拼接 canonical_text 并计算每页全局偏移；页间分隔符 `\\n\\n` 不属于任何页。"""
    pages: list[Page] = []
    cursor = 0
    for number, text in enumerate(page_texts, start=1):
        start = cursor
        end = start + len(text)
        pages.append(Page(page_number=number, text=text, start_offset=start, end_offset=end))
        cursor = end + len(PAGE_SEPARATOR)
    canonical = PAGE_SEPARATOR.join(page_texts)
    return pages, canonical


def ingest_document(state: ContractReviewState) -> dict:
    started = perf_counter()

    def finish(**updates: object) -> dict:
        elapsed_ms = round((perf_counter() - started) * 1000, 2)
        timings = {**state.timings, "ingest_document_ms": elapsed_ms}
        return {**updates, "timings": timings}

    def fail(message: str) -> dict:
        return finish(
            status="failed",
            errors=[*state.errors, message],
            pages=[],
            raw_text="",
            clauses=[],
        )

    if not state.source_path:
        return fail("未提供合同文件路径（source_path 为空）。")

    path = Path(state.source_path)
    if not path.is_file():
        return fail(f"合同文件不存在：{path}")

    suffix = path.suffix.lower()
    if suffix in KNOWN_UNSUPPORTED_SUFFIXES:
        return fail(
            f"暂不支持 {KNOWN_UNSUPPORTED_SUFFIXES[suffix]} 文件；"
            "请上传 TXT / Markdown / 文本型 PDF / DOCX。"
        )
    if suffix not in SUPPORTED_SUFFIXES:
        return fail(
            f"不支持的文件类型 {suffix or '(无扩展名)'}；"
            "当前支持 TXT / Markdown / 文本型 PDF / DOCX。"
        )

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        return fail(f"文件过大（{size_mb:.1f} MB），超过上限 {settings.max_upload_mb} MB。")

    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    warnings: list[str] = []

    try:
        if SUPPORTED_SUFFIXES[suffix] == "pdf":
            if not raw.startswith(b"%PDF-"):
                raise IngestError("文件内容不是有效的 PDF（缺少 %PDF- 头）。")
            page_texts = _extract_pdf(raw, warnings)
        elif SUPPORTED_SUFFIXES[suffix] == "docx":
            if not raw.startswith(b"PK\x03\x04"):
                raise IngestError("文件内容不是有效的 DOCX（不是 ZIP 容器）。")
            page_texts = [_extract_docx(raw)]
        else:
            text, decode_warnings = _decode_text(raw)
            warnings.extend(decode_warnings)
            page_texts = [canonicalize(text)]
    except IngestError as exc:
        return fail(str(exc))

    pages, canonical = _assemble_pages(page_texts)
    if not canonical.strip():
        return fail("合同文本为空（去除空白后无内容）。")
    if len(canonical) > settings.max_contract_chars:
        return fail(
            f"合同文本过长（{len(canonical)} 字符），"
            f"超过上限 {settings.max_contract_chars} 字符。"
        )

    return finish(
        source_filename=_safe_filename(path.name),
        source_sha256=sha256,
        media_type=SUPPORTED_SUFFIXES[suffix],
        pages=pages,
        raw_text=canonical,
        warnings=[*state.warnings, *warnings],
        clauses=[],
    )
