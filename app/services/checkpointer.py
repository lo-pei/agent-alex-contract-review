"""checkpointer 工厂：运行用 SQLite，测试/演示用内存（ADR-002 §3.6、ADR-004）。

角色：HITL 的前提是持久化 checkpoint；没有 checkpointer 时图必须拒绝编译（见 `app/graph.py`）。
依赖：`langgraph-checkpoint-sqlite`、`app/config.py`。
约束：backend=memory 只用于测试与本地演示；生产入口（API/UI）必须用 sqlite。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

from app import schemas
from app.config import settings


def _allowed_schema_types() -> list[tuple[str, str]]:
    """状态里会出现本项目 Pydantic 类型；显式登记，避免 msgpack 反序列化被未来版本阻断。"""
    return [
        ("app.schemas", name)
        for name, value in vars(schemas).items()
        if isinstance(value, type)
        and issubclass(value, BaseModel)
        and getattr(value, "__module__", "") == "app.schemas"
    ]


def _serde():
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    return JsonPlusSerializer(allowed_msgpack_modules=_allowed_schema_types())


def memory_checkpointer() -> InMemorySaver:
    """进程内 checkpointer：测试与一次性演示用。"""
    return InMemorySaver(serde=_serde())


@contextmanager
def sqlite_checkpointer(path: str | Path | None = None) -> Iterator[object]:
    """SQLite checkpointer：进程重启后仍能 `get_state` 并 resume。"""
    from langgraph.checkpoint.sqlite import SqliteSaver

    target = Path(path or settings.checkpoint_sqlite_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(target), check_same_thread=False)
    try:
        yield SqliteSaver(connection, serde=_serde())
    finally:
        connection.close()


@contextmanager
def open_checkpointer(backend: str | None = None) -> Iterator[object]:
    """按配置打开 checkpointer；`memory` 仅供测试。"""
    chosen = (backend or settings.checkpoint_backend).strip().lower()
    if chosen == "memory":
        yield memory_checkpointer()
        return
    if chosen == "sqlite":
        with sqlite_checkpointer() as saver:
            yield saver
        return
    raise ValueError(f"未知 CHECKPOINT_BACKEND：{chosen!r}（可选 sqlite / memory）")
