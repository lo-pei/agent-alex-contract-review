"""pending 时间戳持久化测试（ISSUE-017）：跨进程超时判定、原子写、非法 ID。"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.graph import build_graph
from app.review_service import ReviewService
from app.schemas import HitlDecision
from app.services.checkpointer import memory_checkpointer
from app.services.pending_store import (
    FilePendingStore,
    MemoryPendingStore,
    validate_review_id,
)

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)


def test_memory_store_roundtrip() -> None:
    store = MemoryPendingStore()
    assert store.get("abc") is None
    store.put("abc", NOW)
    assert store.get("abc") == NOW
    store.pop("abc")
    assert store.get("abc") is None


def test_file_store_persists_across_instances(tmp_path: Path) -> None:
    store = FilePendingStore(tmp_path)
    store.put("abc", NOW)

    # 新实例模拟进程重启
    restarted = FilePendingStore(tmp_path)
    assert restarted.get("abc") == NOW
    payload = json.loads((tmp_path / "abc.json").read_text(encoding="utf-8"))
    assert payload["requested_at"] == NOW.isoformat()

    restarted.pop("abc")
    assert restarted.get("abc") is None
    assert not (tmp_path / "abc.json").exists()


def test_file_store_ignores_corrupted_file(tmp_path: Path) -> None:
    (tmp_path / "abc.json").write_text("{not json", encoding="utf-8")
    assert FilePendingStore(tmp_path).get("abc") is None


def test_file_store_accepts_naive_timestamp(tmp_path: Path) -> None:
    (tmp_path / "abc.json").write_text(
        json.dumps({"requested_at": "2026-10-27T09:00:00"}), encoding="utf-8"
    )
    assert FilePendingStore(tmp_path).get("abc") == NOW


@pytest.mark.parametrize("review_id", ["../escape", "a/b", "a b", "", "x" * 65])
def test_invalid_review_id_rejected(tmp_path: Path, review_id: str) -> None:
    with pytest.raises(ValueError):
        validate_review_id(review_id)
    with pytest.raises(ValueError):
        FilePendingStore(tmp_path).put(review_id, NOW)


def test_lazy_timeout_survives_service_restart(tmp_path: Path, sample_path: Path) -> None:
    """ISSUE-017：pending 时间戳落盘后，新进程/新 service 仍能触发超时。"""
    saver = memory_checkpointer()
    graph = build_graph(checkpointer=saver)
    clock = {"now": NOW}

    first = ReviewService(
        graph,
        timeout_minutes=30,
        clock=lambda: clock["now"],
        pending_store=FilePendingStore(tmp_path),
    )
    run = first.start(sample_path)
    assert run.awaiting_human
    assert (tmp_path / f"{run.review_id}.json").is_file()

    restarted = ReviewService(
        graph,
        timeout_minutes=30,
        clock=lambda: clock["now"],
        pending_store=FilePendingStore(tmp_path),
    )
    clock["now"] = clock["now"] + timedelta(minutes=31)
    expired = restarted.get(run.review_id)

    assert not expired.awaiting_human
    assert expired.status == "unreviewed_red_risk"
    assert expired.report is not None
    # 超时后清理 pending 文件，避免残留
    assert not (tmp_path / f"{run.review_id}.json").exists()


def test_pending_removed_after_decision(tmp_path: Path, sample_path: Path) -> None:
    service = ReviewService(
        build_graph(checkpointer=memory_checkpointer()),
        pending_store=FilePendingStore(tmp_path),
    )
    run = service.start(sample_path)
    assert (tmp_path / f"{run.review_id}.json").is_file()

    service.resume(run.review_id, HitlDecision(action="approve", reviewer="alice"))
    assert not (tmp_path / f"{run.review_id}.json").exists()
