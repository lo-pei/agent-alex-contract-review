"""图片 PDF 的 OCR 降级路径（界面轮 13）。

约束：
- OCR 只为“没有文本层”的 PDF 提供文本，**不参与判级**；
- OCR 组件缺失/单页失败都不能让整个审查崩溃，只能降级成可读错误或 warning；
- 真实模型推理慢，单元测试用 monkeypatch 替换识别调用。
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from app.config import settings
from app.nodes import ingest as ingest_module
from app.nodes.ingest import ingest_document
from app.schemas import ContractReviewState
from app.services.ocr import OcrError, ocr_pdf_pages
from tests.fixtures.pdf_builder import make_pdf


def _state(path: Path) -> ContractReviewState:
    return ContractReviewState(
        review_id="t", source_filename=path.name, source_path=str(path)
    )


def _use_settings(monkeypatch, **overrides) -> None:
    """`Settings` 是 frozen dataclass，用 replace 生成副本再替换 ingest 模块里的引用。"""
    monkeypatch.setattr(ingest_module, "settings", replace(settings, **overrides))


def test_image_only_pdf_uses_ocr(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "scan.pdf"
    path.write_bytes(make_pdf([[""], [""]]))
    calls: list[list[int]] = []

    def fake_ocr(raw: bytes, pages) -> dict[int, str]:
        calls.append(list(pages))
        return {number: "PAYMENT TERMS\n100% T/T IN ADVANCE" for number in pages}

    _use_settings(monkeypatch, ocr_enabled=True)
    monkeypatch.setattr(ingest_module, "ocr_pdf_pages", fake_ocr)
    update = ingest_document(_state(path))

    assert update.get("status") != "failed"
    assert calls == [[1, 2]]
    assert "100% T/T IN ADVANCE" in update["raw_text"]
    assert any("OCR" in warning for warning in update["warnings"])
    # 页码偏移仍可回溯
    for page in update["pages"]:
        segment = update["raw_text"][page.start_offset : page.end_offset]
        assert "PAYMENT TERMS" in segment


def test_text_pdf_does_not_call_ocr(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "text.pdf"
    path.write_bytes(
        make_pdf([["SALES CONTRACT", "1. Payment: 100% T/T in advance before shipment."]])
    )

    def explode(*args, **kwargs):  # pragma: no cover - 不应被调用
        raise AssertionError("文本型 PDF 不应触发 OCR")

    _use_settings(monkeypatch, ocr_enabled=True)
    monkeypatch.setattr(ingest_module, "ocr_pdf_pages", explode)
    update = ingest_document(_state(path))

    assert update.get("status") != "failed"
    assert "100% T/T" in update["raw_text"]


def test_ocr_failure_degrades_to_readable_error(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "scan.pdf"
    path.write_bytes(make_pdf([[""]]))

    def fake_ocr(raw: bytes, pages) -> dict[int, str]:
        raise OcrError("缺少 PDF 渲染组件")

    _use_settings(monkeypatch, ocr_enabled=True)
    monkeypatch.setattr(ingest_module, "ocr_pdf_pages", fake_ocr)
    update = ingest_document(_state(path))

    assert update["status"] == "failed"
    assert "未检测到文本层" in update["errors"][0]
    assert any("OCR 未执行" in warning for warning in update["warnings"])


def test_ocr_can_be_disabled(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "scan.pdf"
    path.write_bytes(make_pdf([[""]]))
    _use_settings(monkeypatch, ocr_enabled=False)
    update = ingest_document(_state(path))

    assert update["status"] == "failed"
    assert "OCR 不可用或已关闭" in update["errors"][0]


def test_ocr_requires_its_dependencies(monkeypatch) -> None:
    monkeypatch.setattr("app.services.ocr.ocr_available", lambda: False)
    with pytest.raises(OcrError, match="OCR 组件"):
        ocr_pdf_pages(b"not a pdf", [1])

