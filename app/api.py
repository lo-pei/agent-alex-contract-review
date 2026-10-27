"""FastAPI 应用：上传合同 → 启动审查 → 人工决定 → 下载报告（ADR-002 / ADR-009）。

角色：把 `ReviewService` 暴露成 HTTP 接口，供 Streamlit 与第三方系统调用。
依赖：`app/review_service.py`、`app/services/checkpointer.py`、`app/services/pending_store.py`、
`app/report_markdown.py`。
约束：
- **不在 API 层判级或改级**，等级只来自图里的 Python 规则；
- HITL 只通过 `ReviewService.resume()` 恢复，不接受外部拼 `Command`；
- 上传只做类型/大小/空文件校验并落盘到 `.data/uploads/<review_id>/`，不做 OCR/格式转换；
- 报告未生成时返回 409，绝不返回空报告冒充完成；
- 未知 review_id 返回 404，状态冲突返回 409。
"""

from __future__ import annotations

import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi import Path as ApiPath
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict

from app.config import settings
from app.graph import build_graph
from app.report_markdown import render_report_markdown
from app.review_service import ReviewRun, ReviewService, ReviewStateError
from app.schemas import (
    ApprovalPayload,
    HitlDecision,
    OverallLevel,
    ReviewReport,
    ReviewStatus,
)
from app.services.checkpointer import sqlite_checkpointer
from app.services.pending_store import FilePendingStore

API_TITLE = "Agent Alex · 外贸合同智审助手"
API_VERSION = "0.6.0"

#: 与 `app/nodes/ingest.py` 保持一致；`.doc` 明确拒绝并提示转换
UPLOAD_SUFFIXES = frozenset({".txt", ".md", ".markdown", ".pdf", ".docx"})
MAX_FILENAME_CHARS = 180
CHUNK_SIZE = 1024 * 1024

REVIEW_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class ReviewSummary(BaseModel):
    """对外的审查摘要（不含合同原文与完整 state，避免把大文本塞进响应）。"""

    model_config = ConfigDict(extra="forbid")

    review_id: str
    source_filename: str
    status: ReviewStatus
    overall_level: OverallLevel
    awaiting_human: bool = False
    approval: ApprovalPayload | None = None
    report: ReviewReport | None = None
    warnings: list[str] = []
    errors: list[str] = []
    extraction_status: Literal["ok", "degraded", "skipped"] = "skipped"
    explanation_status: Literal["ok", "fallback", "skipped"] = "skipped"


def _summary_of(run: ReviewRun) -> ReviewSummary:
    state = run.state
    if state is None:  # pragma: no cover - ReviewRun 始终带 state
        raise HTTPException(status_code=500, detail="审查状态缺失")
    return ReviewSummary(
        review_id=run.review_id,
        source_filename=state.source_filename,
        status=run.status,
        overall_level=state.overall_level,
        awaiting_human=run.awaiting_human,
        approval=run.approval,
        report=run.report,
        warnings=list(state.warnings),
        errors=list(state.errors),
        extraction_status=state.extraction_status,
        explanation_status=state.explanation_status,
    )


def _safe_filename(name: str | None) -> str:
    """只取 basename，去掉控制字符与路径分隔符（兼容 Windows/Unix 写法）。"""
    if not name:
        return ""
    candidate = name.replace("\\", "/").split("/")[-1]
    candidate = "".join(ch for ch in candidate if ch.isprintable()).strip()
    if candidate in {"", ".", ".."}:
        return ""
    if len(candidate) > MAX_FILENAME_CHARS:
        candidate = candidate[-MAX_FILENAME_CHARS:]
    return candidate


def _service_of(request: Request) -> ReviewService:
    service = getattr(request.app.state, "service", None)
    if service is None:  # pragma: no cover - lifespan 保证已初始化
        raise HTTPException(status_code=503, detail="审查服务未初始化")
    return service


def create_app(
    service: ReviewService | None = None,
    *,
    upload_dir: Path | str | None = None,
    pending_dir: Path | str | None = None,
    max_upload_mb: int | None = None,
) -> FastAPI:
    """构造应用。传入 `service` 时使用该实例（测试用内存 checkpointer），否则使用 SQLite。"""
    upload_root = Path(upload_dir or settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    limit_bytes = (max_upload_mb if max_upload_mb is not None else settings.max_upload_mb) * (
        1024 * 1024
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if service is not None:
            app.state.service = service
            yield
            return
        with sqlite_checkpointer() as saver:
            app.state.service = ReviewService(
                build_graph(checkpointer=saver),
                pending_store=FilePendingStore(pending_dir),
            )
            yield

    app = FastAPI(title=API_TITLE, version=API_VERSION, lifespan=lifespan)
    if service is not None:
        app.state.service = service

    @app.exception_handler(ReviewStateError)
    def _review_state_handler(_request: Request, exc: ReviewStateError) -> JSONResponse:
        return JSONResponse(
            status_code=404 if exc.missing else 409,
            content={"detail": str(exc)},
        )

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "version": API_VERSION,
            "checkpoint_backend": settings.checkpoint_backend if service is None else "memory",
            "rag_enabled": settings.rag_enabled,
            "time": datetime.now(UTC).isoformat(),
        }

    @app.post("/api/reviews", status_code=201, response_model=ReviewSummary)
    def create_review(
        request: Request,
        file: Annotated[UploadFile, File(description="合同文件（txt/md/pdf/docx）")],
    ) -> ReviewSummary:
        filename = _safe_filename(file.filename)
        if not filename:
            raise HTTPException(status_code=400, detail="缺少文件名")
        suffix = Path(filename).suffix.casefold()
        if suffix == ".doc":
            raise HTTPException(
                status_code=400,
                detail="不支持旧版 .doc，请另存为 .docx 或 .txt/.md 后重新上传",
            )
        if suffix not in UPLOAD_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型 {suffix or '(无扩展名)'}；"
                "支持 .txt/.md/.pdf/.docx",
            )

        review_id = uuid.uuid4().hex
        target_dir = upload_root / review_id
        target = target_dir / filename
        total = 0
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("wb") as handle:
                while True:
                    chunk = file.file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > limit_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"文件超过 {limit_bytes // (1024 * 1024)} MB 上限",
                        )
                    handle.write(chunk)
            if total == 0:
                raise HTTPException(status_code=400, detail="文件为空")
        except HTTPException:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise
        except OSError as exc:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail=f"文件保存失败：{exc}") from exc
        finally:
            file.file.close()

        run = _service_of(request).start(target, review_id=review_id)
        return _summary_of(run)

    @app.get("/api/reviews/{review_id}", response_model=ReviewSummary)
    def get_review(
        request: Request,
        review_id: str = ApiPath(pattern=REVIEW_ID_PATTERN),
    ) -> ReviewSummary:
        return _summary_of(_service_of(request).get(review_id))

    @app.post("/api/reviews/{review_id}/decisions", response_model=ReviewSummary)
    def submit_decision(
        request: Request,
        decision: HitlDecision,
        review_id: str = ApiPath(pattern=REVIEW_ID_PATTERN),
    ) -> ReviewSummary:
        return _summary_of(_service_of(request).resume(review_id, decision))

    @app.get("/api/reviews/{review_id}/report")
    def get_report(
        request: Request,
        review_id: str = ApiPath(pattern=REVIEW_ID_PATTERN),
        format: Literal["json", "markdown"] = "json",
    ) -> Response:
        run = _service_of(request).get(review_id)
        report = run.report
        if report is None:
            raise HTTPException(
                status_code=409,
                detail="报告尚未生成：请先完成人工确认（或等待审查结束）",
            )
        if format == "markdown":
            content = render_report_markdown(report)
            return Response(
                content=content,
                media_type="text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="{review_id}-report.md"'
                },
            )
        return JSONResponse(content=report.model_dump(mode="json"))

    return app
