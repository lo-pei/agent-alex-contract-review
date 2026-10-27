"""审查运行服务：启动 → 暂停 → 恢复 → 惰性超时（ADR-002 §3.4–3.7）。

角色：API/UI/CLI 共用的薄封装，把 `interrupt()` / `Command(resume=...)` / `get_state`
的细节收在一处，并提供“重复 resume 幂等”“超时绝不通过”两个硬语义。
依赖：`app/graph.py`、`app/services/checkpointer.py`、`app/schemas.py`。
约束：
- 本模块**不生成**风险等级，只搬运图状态与人工决定；
- 幂等：已是终态时再次 resume 直接返回现有结果，不重跑图、不重复写报告；
- 超时：惰性检查，只把状态变为 `unreviewed_red_risk`，**绝不映射为 approved**；
- pending 时间戳通过 `PendingStore` 持久化（`FilePendingStore` 落盘），进程重启后超时判定仍有效；
- 同一 `review_id` 的 `get` / `resume` 加进程内可重入锁，避免并发恢复把图跑两次。
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from langgraph.types import Command
from pydantic import BaseModel, ConfigDict

from app.config import settings
from app.graph import build_graph
from app.schemas import (
    ApprovalPayload,
    ContractReviewState,
    HitlDecision,
    ReviewReport,
    ReviewStatus,
)
from app.services.checkpointer import memory_checkpointer
from app.services.pending_store import MemoryPendingStore, PendingStore, validate_review_id

#: 图已结束的终态；再次 resume 视为幂等请求
FINAL_STATUSES = frozenset(
    {"approved", "rejected", "changes_requested", "unreviewed_red_risk", "completed", "failed"}
)

TIMEOUT_DECISION = HitlDecision(
    action="timeout",
    reviewer="system",
    comment="HITL 超时：未收到人工确认，按未确认处理（不视为通过）。",
)


class ReviewStateError(RuntimeError):
    """审查不存在或当前没有待人工确认的任务。

    `missing=True` 表示 review_id 从未存在过（API 映射为 404），否则为状态冲突（409）。
    """

    def __init__(self, message: str, *, missing: bool = False) -> None:
        super().__init__(message)
        self.missing = missing


class ReviewRun(BaseModel):
    """一次启动/恢复的结果：可能已完成，也可能停在人工确认。"""

    model_config = ConfigDict(extra="forbid")

    review_id: str
    status: ReviewStatus
    awaiting_human: bool = False
    approval: ApprovalPayload | None = None
    report: ReviewReport | None = None
    state: ContractReviewState | None = None


class ReviewService:
    """包一层图，提供 start / resume / get。"""

    def __init__(
        self,
        graph,
        *,
        timeout_minutes: int | None = None,
        clock: Callable[[], datetime] | None = None,
        pending_store: PendingStore | None = None,
    ) -> None:
        self._graph = graph
        self._timeout_minutes = (
            timeout_minutes if timeout_minutes is not None else settings.hitl_timeout_minutes
        )
        self._clock = clock or (lambda: datetime.now(UTC))
        self._pending = pending_store or MemoryPendingStore()
        self._locks: dict[str, threading.RLock] = {}
        self._locks_guard = threading.Lock()

    # ---------- 构造 ----------

    @classmethod
    def in_memory(
        cls,
        *,
        timeout_minutes: int | None = None,
        clock: Callable[[], datetime] | None = None,
        pending_store: PendingStore | None = None,
    ) -> ReviewService:
        """测试/一次性演示：进程内 checkpointer。"""
        return cls(
            build_graph(checkpointer=memory_checkpointer()),
            timeout_minutes=timeout_minutes,
            clock=clock,
            pending_store=pending_store,
        )

    # ---------- 对外接口 ----------

    def start(self, path: Path | str, *, review_id: str | None = None) -> ReviewRun:
        source = Path(path)
        identifier = validate_review_id(review_id or uuid.uuid4().hex)
        with self._lock_for(identifier):
            initial = ContractReviewState(
                review_id=identifier,
                source_filename=source.name,
                source_path=str(source),
            )
            raw = self._graph.invoke(initial.model_dump(), config=self._config(identifier))
            return self._run_from_raw(identifier, raw)

    def get(self, review_id: str) -> ReviewRun:
        """读取当前状态；若停在人工确认且已超时，惰性触发超时决定。"""
        with self._lock_for(review_id):
            snapshot = self._graph.get_state(self._config(review_id))
            if not snapshot.values:
                raise ReviewStateError(f"审查不存在：{review_id}", missing=True)
            run = self._run_from_snapshot(review_id, snapshot)
            if run.awaiting_human and self._timed_out(review_id):
                # RLock 可重入：这里仍持有同一把锁
                return self.resume(review_id, TIMEOUT_DECISION)
            return run

    def resume(self, review_id: str, decision: HitlDecision) -> ReviewRun:
        with self._lock_for(review_id):
            config = self._config(review_id)
            snapshot = self._graph.get_state(config)
            if not snapshot.values:
                raise ReviewStateError(f"审查不存在：{review_id}", missing=True)

            if "human_review" not in snapshot.next:
                state = ContractReviewState.model_validate(snapshot.values)
                if state.status in FINAL_STATUSES:
                    # 幂等：不重复应用决策、不重复生成报告
                    return self._run_from_snapshot(review_id, snapshot)
                raise ReviewStateError(
                    f"审查 {review_id} 当前没有待人工确认的任务（status={state.status}）"
                )

            raw = self._graph.invoke(
                Command(resume=decision.model_dump(mode="json")), config=config
            )
            self._pending.pop(review_id)
            return self._run_from_raw(review_id, raw)

    def get_state(self, review_id: str) -> ContractReviewState:
        snapshot = self._graph.get_state(self._config(review_id))
        if not snapshot.values:
            raise ReviewStateError(f"审查不存在：{review_id}", missing=True)
        return ContractReviewState.model_validate(snapshot.values)

    # ---------- 内部 ----------

    def _lock_for(self, review_id: str) -> threading.RLock:
        with self._locks_guard:
            lock = self._locks.get(review_id)
            if lock is None:
                lock = threading.RLock()
                self._locks[review_id] = lock
            return lock

    @staticmethod
    def _config(review_id: str) -> dict:
        return {"configurable": {"thread_id": review_id}}

    @staticmethod
    def _state_from_raw(raw: dict) -> ContractReviewState:
        # `invoke` 暂停时返回值里带 `__interrupt__`，它不是 state 字段
        payload = {key: value for key, value in raw.items() if not key.startswith("__")}
        return ContractReviewState.model_validate(payload)

    @staticmethod
    def _approval_of(values: object) -> ApprovalPayload | None:
        for interrupt in getattr(values, "interrupts", ()) or ():
            return ApprovalPayload.model_validate(interrupt.value)
        return None

    def _mark_waiting(self, review_id: str) -> None:
        """首次观察到暂停时写入 pending 时间戳（已存在则不覆盖，保证超时起点稳定）。"""
        if self._pending.get(review_id) is None:
            self._pending.put(review_id, self._clock())

    def _run_from_raw(self, review_id: str, raw: dict) -> ReviewRun:
        interrupts = list(raw.get("__interrupt__") or [])
        state = self._state_from_raw(raw)
        if interrupts:
            self._mark_waiting(review_id)
            return ReviewRun(
                review_id=review_id,
                status=state.status,
                awaiting_human=True,
                approval=ApprovalPayload.model_validate(interrupts[0].value),
                state=state,
            )
        return ReviewRun(
            review_id=review_id,
            status=state.status,
            report=state.report,
            state=state,
        )

    def _run_from_snapshot(self, review_id: str, snapshot) -> ReviewRun:
        state = ContractReviewState.model_validate(snapshot.values)
        awaiting = "human_review" in tuple(snapshot.next or ())
        approval = self._approval_of(snapshot) if awaiting else None
        if awaiting:
            self._mark_waiting(review_id)
        return ReviewRun(
            review_id=review_id,
            status=state.status,
            awaiting_human=awaiting,
            approval=approval,
            report=state.report,
            state=state,
        )

    def _timed_out(self, review_id: str) -> bool:
        requested = self._pending.get(review_id)
        if requested is None:
            return False
        return self._clock() - requested >= timedelta(minutes=self._timeout_minutes)
