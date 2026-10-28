"""PDF 图片页 OCR：渲染 + 本地识别（RapidOCR，中文/英文）。

角色：`app/nodes/ingest.py` 在 PDF 没有文本层、或个别页只有图片时调用。
依赖：`pypdfium2`（PDF → 图片，Apache/BSD 许可）+ `rapidocr-onnxruntime`
（内置 PP-OCR 模型，离线推理）。**不联网、不训练、不修改原文件**。
约束：
- 只读取上传文件的内存字节，不落临时图片；
- 最多处理 `settings.ocr_max_pages` 页，超出部分明确写 warning；
- OCR 结果只作为合同文本进入后续流程，**不参与判级**（等级仍只由规则决定）；
- 缺依赖 / 单页失败都抛 `OcrError`，由调用方降级为“请上传文本型 PDF”。
"""

from __future__ import annotations

import threading
from collections.abc import Sequence

from app.config import settings


class OcrError(Exception):
    """OCR 不可用或识别失败的可读原因。"""


#: 进程内复用同一个识别器（首次加载模型较慢，之后每页约 1–3 秒）
_engine = None
_engine_lock = threading.Lock()


def ocr_available() -> bool:
    """依赖是否装好；仅做 import 检查，不加载模型。"""
    try:
        import pypdfium2  # noqa: F401
        import rapidocr_onnxruntime  # noqa: F401
    except Exception:  # noqa: BLE001 - 缺依赖/二进制不兼容都算不可用
        return False
    return True


def _engine_instance():
    global _engine
    with _engine_lock:
        if _engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
            except Exception as exc:  # noqa: BLE001
                raise OcrError(f"OCR 组件加载失败：{exc}") from exc
            _engine = RapidOCR()
        return _engine


def _recognize(image) -> str:
    """PIL 图片 → 按行拼接的文本；识别不到返回空串。"""
    import numpy as np

    engine = _engine_instance()
    with _engine_lock:
        try:
            result, _ = engine(np.asarray(image.convert("RGB")))
        except Exception as exc:  # noqa: BLE001 - onnxruntime 异常类型不稳定
            raise OcrError(f"OCR 识别失败：{exc}") from exc
    lines: list[str] = []
    for item in result or []:
        if len(item) < 2:
            continue
        text = str(item[1]).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def ocr_pdf_pages(
    raw: bytes,
    page_numbers: Sequence[int],
    *,
    scale: float | None = None,
) -> dict[int, str]:
    """把指定页（1 起）渲染成图片并 OCR；返回 `{页码: 文本}`。

    单页识别失败不会拖垮整份文件：该页跳过，其余页继续。
    依赖缺失 / PDF 打不开才抛 `OcrError`。
    """
    try:
        import pypdfium2 as pdfium
    except Exception as exc:  # noqa: BLE001
        raise OcrError(
            "缺少 PDF 渲染组件（pypdfium2），无法识别图片页。"
        ) from exc
    if not ocr_available():
        raise OcrError(
            "本机未安装 OCR 组件（rapidocr-onnxruntime / pypdfium2），"
            "无法识别图片 PDF。"
        )

    try:
        document = pdfium.PdfDocument(raw)
    except Exception as exc:  # noqa: BLE001
        raise OcrError(f"PDF 无法渲染为图片：{exc}") from exc

    render_scale = scale if scale is not None else settings.ocr_render_scale
    texts: dict[int, str] = {}
    try:
        total_pages = len(document)
        for number in page_numbers:
            if number < 1 or number > total_pages:
                continue
            try:
                bitmap = document[number - 1].render(scale=render_scale)
                image = bitmap.to_pil()
                text = _recognize(image)
            except OcrError:
                raise
            except Exception:  # noqa: BLE001 - 单页损坏/渲染失败只跳过该页
                continue
            if text.strip():
                texts[number] = text.strip()
    finally:
        document.close()
    return texts


__all__ = ["OcrError", "ocr_available", "ocr_pdf_pages"]
