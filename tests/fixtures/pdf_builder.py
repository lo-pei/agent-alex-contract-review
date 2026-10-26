"""测试用 PDF 构造器：不引入 reportlab，直接拼最小合法 PDF。

角色：为 `tests/test_ingest.py` 提供可解析的文本型/无文本层 PDF fixture。
依赖：仅标准库（pypdf 只在被测代码里使用）。
说明：只支持 ASCII 文本（Helvetica 内置字体的 WinAnsi 编码），中文 PDF fixture 暂不构造；
     生成的是单栏文本 PDF，不覆盖复杂版式/表格。
"""

from __future__ import annotations


def _escape_pdf_text(line: str) -> str:
    return line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _content_stream(lines: list[str]) -> bytes:
    if not lines:
        return b"BT ET"
    parts = ["BT", "/F1 12 Tf", "72 720 Td"]
    for index, line in enumerate(lines):
        if index:
            parts.append("0 -16 Td")
        parts.append(f"({_escape_pdf_text(line)}) Tj")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1")


def make_pdf(page_texts: list[list[str]]) -> bytes:
    """生成多页文本 PDF；`page_texts[i]` 是第 i+1 页每行的文本。"""
    if not page_texts:
        raise ValueError("至少需要一页")

    objects: dict[int, bytes] = {}
    page_numbers = [4 + 2 * index for index in range(len(page_texts))]

    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{number} 0 R" for number in page_numbers)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_numbers)} >>".encode()
    objects[3] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )

    for index, lines in enumerate(page_texts):
        page_number = page_numbers[index]
        content_number = page_number + 1
        objects[page_number] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_number} 0 R >>"
        ).encode()
        stream = _content_stream(lines)
        objects[content_number] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )

    buffer = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(buffer)
        buffer += f"{number} 0 obj\n".encode("ascii") + objects[number] + b"\nendobj\n"

    max_number = max(objects)
    xref_offset = len(buffer)
    buffer += f"xref\n0 {max_number + 1}\n".encode("ascii")
    buffer += b"0000000000 65535 f \n"
    for number in range(1, max_number + 1):
        buffer += f"{offsets[number]:010d} 00000 n \n".encode("ascii")
    buffer += (
        f"trailer\n<< /Size {max_number + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    return bytes(buffer)
