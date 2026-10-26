"""`ingest_document` 节点：读取合同文件 → canonical_text + 页码/偏移 + sha256。

角色：图的第一站（ADR-001），当前阶段只支持 TXT / Markdown。
依赖：`app/config.py`（上限）、`app/schemas.py`（Page/State）。
后续：PDF（pypdf）、DOCX（python-docx）在 ADR-005 第 2 步接入；
      本节点任何失败都写入 `errors` 且 `status="failed"`，不抛异常中断图。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from time import perf_counter

from app.config import settings
from app.schemas import ContractReviewState, Page

SUPPORTED_SUFFIXES = {".txt": "text", ".md": "text"}
KNOWN_UNSUPPORTED_SUFFIXES = {".pdf": "pdf", ".docx": "docx"}


def canonicalize(text: str) -> str:
    """统一换行符并去掉 BOM；其余字符保持原样（保证偏移可回查）。"""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized[1:] if normalized.startswith("\ufeff") else normalized


def _decode(raw: bytes) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        return raw.decode("utf-8-sig"), warnings
    except UnicodeDecodeError:
        # 中文合同常见 GB18030；解不出来时显式失败，而不是替换成乱码
        warnings.append("文件不是 UTF-8 编码，已按 GB18030 解码，请核对原文。")
        return raw.decode("gb18030"), warnings


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
            f"暂不支持 {suffix} 文件（PDF/DOCX 解析将在下一阶段接入）；"
            "当前请上传 TXT 或 Markdown 合同。"
        )
    if suffix not in SUPPORTED_SUFFIXES:
        return fail(f"不支持的文件类型 {suffix or '(无扩展名)'}；当前支持 TXT / Markdown。")

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        return fail(f"文件过大（{size_mb:.1f} MB），超过上限 {settings.max_upload_mb} MB。")

    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    try:
        decoded, decode_warnings = _decode(raw)
    except UnicodeDecodeError as exc:
        return fail(f"文件编码无法识别：{exc}")

    text = canonicalize(decoded)
    if not text.strip():
        return fail("合同文本为空（去除空白后无内容）。")
    if len(text) > settings.max_contract_chars:
        return fail(
            f"合同文本过长（{len(text)} 字符），超过上限 {settings.max_contract_chars} 字符。"
        )

    page = Page(page_number=1, text=text, start_offset=0, end_offset=len(text))
    return finish(
        source_filename=path.name,
        source_sha256=sha256,
        media_type=SUPPORTED_SUFFIXES[suffix],
        pages=[page],
        raw_text=text,
        warnings=[*state.warnings, *decode_warnings],
        clauses=[],
    )
