"""逐条审查结果的导出：修订稿 DOCX / PDF。

输入是前端“逐条审查”里用户确认过的条款文本（`clause_id -> 最终文本`），
输出是**审查意见汇总 + 修订稿**；等级沿用规则结果，不在导出层重新判定。

依赖：`python-docx`（已在 requirements）+ `reportlab`（纯 Python，用于中文 PDF）。
两条路径都不联网、不写临时文件，直接返回 `bytes` 交给 FastAPI 的 `Response`。
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from xml.sax.saxutils import escape

from app.schemas import ClauseReviewList

LEVEL_LABEL = {"red": "高风险", "yellow": "中风险", "pass": "未见问题"}

DISCLAIMER = (
    "本文件由外贸合同智审助手生成：风险等级只由规则引擎判定，"
    "修订条款为示例文本，签署前请专业人士复核。"
)


class ExportError(ValueError):
    """导出参数不合法（未知格式 / 没有任何条款）。"""


def _now() -> str:
    return datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M")


def _final_text(clause_text: str, applied: str | None) -> tuple[str, bool]:
    """返回 (最终文本, 是否应用了修订)。空字符串视为未修订。"""
    if applied and applied.strip():
        return applied.strip(), True
    return clause_text, False


def _ordered_clauses(payload: ClauseReviewList, accepted: dict[str, str]):
    for clause in payload.clauses:
        final, revised = _final_text(clause.text, accepted.get(clause.clause_id))
        yield clause, final, revised


def _finding_line(finding) -> str:
    """一条规则的导出文本：`[等级] 标题（规则号）：原因 + 建议`。"""
    line = (
        f"[{LEVEL_LABEL[finding.risk_level]}] {finding.title}"
        f"（{finding.rule_id}）：{finding.reason}"
    )
    if finding.suggestion:
        line += f" 建议：{finding.suggestion}"
    return line


def _findings_text(clause) -> str:
    if not clause.findings:
        return "未见规则命中。"
    return "\n".join(_finding_line(finding) for finding in clause.findings)


def _clause_heading(clause) -> str:
    """条款标题：前言不编号，其余用“序号. 标题”。"""
    if clause.is_preamble:
        return "前言"
    return f"{clause.index}. {clause.title or '（无标题）'}"


# --------------------------------------------------------------------------- DOCX


def _build_docx(payload: ClauseReviewList, accepted: dict[str, str]) -> bytes:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Microsoft YaHei"
    style.font.size = Pt(10.5)

    title = document.add_heading("合同逐条审查报告", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    meta = document.add_paragraph()
    meta.add_run(
        f"文件：{payload.source_filename}\n"
        f"审查编号：{payload.review_id}\n"
        f"总体等级：{LEVEL_LABEL.get(payload.overall_level, payload.overall_level)}\n"
        f"生成时间：{_now()}"
    )

    document.add_heading("一、逐条审查意见", level=2)
    for clause, _final, _revised in _ordered_clauses(payload, accepted):
        head = document.add_heading(
            f"{_clause_heading(clause)} — {LEVEL_LABEL[clause.risk_level]}",
            level=3,
        )
        head.paragraph_format.space_before = Pt(8)
        document.add_paragraph(clause.text)
        for line in _findings_text(clause).split("\n"):
            document.add_paragraph(line)

    if payload.contract_findings:
        document.add_heading("二、全合同问题", level=2)
        for finding in payload.contract_findings:
            document.add_paragraph(_finding_line(finding))
        if payload.contract_revised_text:
            document.add_paragraph("建议新增条款：")
            document.add_paragraph(payload.contract_revised_text)

    document.add_heading("三、修订稿", level=2)
    for clause, final, revised in _ordered_clauses(payload, accepted):
        mark = "（已修订）" if revised else ""
        document.add_heading(f"{_clause_heading(clause)}{mark}", level=3)
        for line in final.split("\n"):
            document.add_paragraph(line)

    note = document.add_paragraph(DISCLAIMER)
    note.runs[0].font.size = Pt(9)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------- PDF

_PDF_FONT = "STSong-Light"


def _build_pdf(payload: ClauseReviewList, accepted: dict[str, str]) -> bytes:
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    if _PDF_FONT not in pdfmetrics.getRegisteredFontNames():
        # 标准 14 字体里的中文 CID 字体，无需携带字体文件
        pdfmetrics.registerFont(UnicodeCIDFont(_PDF_FONT))

    base = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CJKTitle",
        parent=base["Title"],
        fontName=_PDF_FONT,
        fontSize=17,
        leading=22,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        "CJKHeading",
        parent=base["Heading2"],
        fontName=_PDF_FONT,
        fontSize=12.5,
        leading=17,
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "CJKBody",
        parent=base["BodyText"],
        fontName=_PDF_FONT,
        fontSize=10,
        leading=15,
    )
    note_style = ParagraphStyle(
        "CJKNote",
        parent=body_style,
        fontSize=8.5,
        leading=12,
        textColor="#666666",
    )

    def para(text: str, style=body_style) -> Paragraph:
        return Paragraph(escape(text).replace("\n", "<br/>"), style)

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="合同逐条审查报告",
    )
    flowable: list = [para("合同逐条审查报告", title_style), Spacer(1, 8)]
    flowable.append(
        para(
            f"文件：{payload.source_filename}\n"
            f"审查编号：{payload.review_id}\n"
            f"总体等级：{LEVEL_LABEL.get(payload.overall_level, payload.overall_level)}\n"
            f"生成时间：{_now()}",
            note_style,
        )
    )
    flowable.append(para("一、逐条审查意见", heading_style))
    for clause, _final, _revised in _ordered_clauses(payload, accepted):
        flowable.append(
            para(
                f"{_clause_heading(clause)}"
                f" — {LEVEL_LABEL[clause.risk_level]}",
                body_style,
            )
        )
        flowable.append(para(clause.text, note_style))
        flowable.append(para(_findings_text(clause), note_style))
        flowable.append(Spacer(1, 6))

    if payload.contract_findings:
        flowable.append(para("二、全合同问题", heading_style))
        for finding in payload.contract_findings:
            flowable.append(
                para(
                    f"[{LEVEL_LABEL[finding.risk_level]}] {finding.title}"
                    f"（{finding.rule_id}）：{finding.reason}",
                    note_style,
                )
            )
        if payload.contract_revised_text:
            flowable.append(para("建议新增条款：", body_style))
            flowable.append(para(payload.contract_revised_text, note_style))

    flowable.append(para("三、修订稿", heading_style))
    for clause, final, revised in _ordered_clauses(payload, accepted):
        mark = "（已修订）" if revised else ""
        flowable.append(para(f"{_clause_heading(clause)}{mark}", body_style))
        flowable.append(para(final))
        flowable.append(Spacer(1, 6))

    flowable.append(Spacer(1, 10))
    flowable.append(para(DISCLAIMER, note_style))
    document.build(flowable)
    return buffer.getvalue()


def export_clause_review(
    payload: ClauseReviewList,
    accepted: dict[str, str],
    fmt: str,
) -> tuple[bytes, str, str]:
    """返回 (字节流, 文件名, MIME)。`accepted` 是用户点过“一键更正”的条款。"""
    if not payload.clauses:
        raise ExportError("这次审查没有可导出的条款")
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    stem = payload.source_filename.rsplit(".", 1)[0] or "contract"
    stem = "".join(ch for ch in stem if ch not in '\\/:*?"<>|').strip() or "contract"
    if fmt == "docx":
        return (
            _build_docx(payload, accepted),
            f"{stem}-审查稿-{stamp}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    if fmt == "pdf":
        return _build_pdf(payload, accepted), f"{stem}-审查稿-{stamp}.pdf", "application/pdf"
    # 未知格式在 API 层已被拦截；这里兜底
    raise ExportError("只支持 docx 或 pdf")
