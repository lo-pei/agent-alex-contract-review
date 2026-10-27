"""HITL 待审批时间戳持久化（ADR-002 §3.5，ISSUE-017）。

角色：记录“某次审查从何时开始等待人工确认”，供惰性超时判定。
依赖：标准库；**不引入**数据库/缓存服务。
约束：
- 时间戳必须可跨进程读取（API/UI 重启后超时判定仍然有效）；
- 写入原子化（临时文件 + `os.replace`），避免半个 JSON；
- `review_id` 只允许字母数字/下划线/连字符，防止路径穿越；
- 读取到损坏文件时返回 `None`（相当于“本次未记录开始时间”），绝不伪造超时。
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.config import settings

#: 只允许安全字符，避免 `review_id` 被用作路径
_REVIEW_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_review_id(review_id: str) -> str:
    if not _REVIEW_ID_RE.fullmatch(review_id):
        raise ValueError(f"非法 review_id（仅字母数字下划线连字符，1-64 位）：{review_id!r}")
    return review_id


def _parse(raw: str) -> datetime | None:
    try:
        value = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class PendingStore(Protocol):
    """待审批时间戳存取协议（测试可注入内存实现）。"""

    def put(self, review_id: str, requested_at: datetime) -> None: ...

    def get(self, review_id: str) -> datetime | None: ...

    def pop(self, review_id: str) -> None: ...


class MemoryPendingStore:
    """进程内实现；仅用于测试与一次性演示（重启即丢失，ISSUE-017 不适用于它）。"""

    def __init__(self) -> None:
        self._items: dict[str, datetime] = {}
        self._lock = threading.Lock()

    def put(self, review_id: str, requested_at: datetime) -> None:
        validate_review_id(review_id)
        with self._lock:
            self._items[review_id] = requested_at.astimezone(UTC)

    def get(self, review_id: str) -> datetime | None:
        validate_review_id(review_id)
        with self._lock:
            return self._items.get(review_id)

    def pop(self, review_id: str) -> None:
        validate_review_id(review_id)
        with self._lock:
            self._items.pop(review_id, None)


class FilePendingStore:
    """落盘实现：每次审查一个 JSON 文件，原子写入。

    文件内容：`{"requested_at": "2026-10-27T09:00:00+00:00"}`。
    """

    def __init__(self, directory: Path | str | None = None) -> None:
        self._directory = Path(directory or settings.pending_dir)
        self._directory.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._directory

    def _path(self, review_id: str) -> Path:
        return self._directory / f"{validate_review_id(review_id)}.json"

    def put(self, review_id: str, requested_at: datetime) -> None:
        path = self._path(review_id)
        payload = json.dumps(
            {"requested_at": requested_at.astimezone(UTC).isoformat()},
            ensure_ascii=False,
        )
        # 先写同目录临时文件，再原子替换，避免读到半个文件
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{path.stem}-", suffix=".tmp", dir=self._directory
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise

    def get(self, review_id: str) -> datetime | None:
        path = self._path(review_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        raw = payload.get("requested_at")
        return _parse(raw) if isinstance(raw, str) else None

    def pop(self, review_id: str) -> None:
        self._path(review_id).unlink(missing_ok=True)
