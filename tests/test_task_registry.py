"""Tests for shared task registry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from utils.exceptions import ErrorCode, TaskAlreadyRunningError, TaskNotFoundError
from utils.task_registry import TaskRegistry


def test_create_task_initializes_and_persists_handle(tmp_path: Path) -> None:
    """Created tasks start queued and are persisted as JSON."""
    registry = TaskRegistry(task_dir=tmp_path)

    handle = registry.create_task("scan")

    assert handle.task_id.startswith("task_scan_")
    assert handle.task_type == "scan"
    assert handle.status == "queued"
    assert handle.progress_current == 0
    assert handle.progress_total == 0
    assert handle.progress_message == ""
    assert handle.logs == []
    assert handle.result is None
    assert handle.error is None
    assert handle.created_at
    assert handle.started_at is None
    assert handle.finished_at is None
    assert handle.is_cancel_requested is False

    payload = json.loads(
        (tmp_path / f"{handle.task_id}.json").read_text(encoding="utf-8")
    )
    assert payload["taskId"] == handle.task_id
    assert payload["taskType"] == "scan"


def test_lifecycle_methods_update_status_and_timestamps(tmp_path: Path) -> None:
    """Task lifecycle helpers update state and persist results."""
    registry = TaskRegistry(task_dir=tmp_path)
    handle = registry.create_task("sample")

    registry.start_task(handle.task_id, total=10, message="开始")
    registry.update_progress(handle.task_id, current=5, total=10, message="一半")
    registry.append_log(handle.task_id, "log line")
    registry.succeed_task(handle.task_id, result={"ok": True})

    updated = registry.get(handle.task_id)
    assert updated.status == "succeeded"
    assert updated.progress_current == 10
    assert updated.progress_total == 10
    assert updated.progress_message == "完成"
    assert updated.logs == ["log line"]
    assert updated.result == {"ok": True}
    assert updated.started_at is not None
    assert updated.finished_at is not None


def test_fail_task_stores_error_info(tmp_path: Path) -> None:
    """Failed tasks store serializable error info."""
    registry = TaskRegistry(task_dir=tmp_path)
    handle = registry.create_task("train")

    registry.fail_task(
        handle.task_id, code=ErrorCode.INTERNAL_ERROR, message="失败", details="boom"
    )

    failed = registry.get(handle.task_id)
    assert failed.status == "failed"
    assert failed.error is not None
    assert failed.error.code == "INTERNAL_ERROR"
    assert failed.error.message == "失败"
    assert failed.error.details == "boom"


def test_cancel_requests_core_loop_stop_without_finishing_task(tmp_path: Path) -> None:
    """Cancellation requests keep active tasks reserved until core acknowledges."""
    registry = TaskRegistry(task_dir=tmp_path)
    handle = registry.create_task("infer")
    registry.start_task(handle.task_id)

    registry.cancel(handle.task_id)

    requested = registry.get(handle.task_id)
    assert requested.status == "running"
    assert requested.is_cancel_requested is True
    assert requested.finished_at is None

    with pytest.raises(TaskAlreadyRunningError):
        registry.create_task("infer")


def test_finish_cancelled_task_terminal_state_blocks_late_success(
    tmp_path: Path,
) -> None:
    """Cancelled tasks stay cancelled after core acknowledges cancellation."""
    registry = TaskRegistry(task_dir=tmp_path)
    handle = registry.create_task("restore")
    registry.start_task(handle.task_id, total=3)
    registry.cancel(handle.task_id)

    registry.finish_cancelled_task(handle.task_id, message="用户取消")
    registry.succeed_task(handle.task_id, result={"ok": True})

    cancelled = registry.get(handle.task_id)
    assert cancelled.status == "cancelled"
    assert cancelled.progress_message == "用户取消"
    assert cancelled.result is None
    assert cancelled.finished_at is not None


def test_get_missing_task_raises_business_error(tmp_path: Path) -> None:
    """Missing tasks raise TaskNotFoundError."""
    registry = TaskRegistry(task_dir=tmp_path)

    with pytest.raises(TaskNotFoundError):
        registry.get("task_missing")


def test_duplicate_running_task_type_is_rejected(tmp_path: Path) -> None:
    """Only one running task of the same type is allowed."""
    registry = TaskRegistry(task_dir=tmp_path)
    first = registry.create_task("train")
    registry.start_task(first.task_id)

    with pytest.raises(TaskAlreadyRunningError):
        registry.create_task("train")


def test_startup_marks_running_tasks_interrupted(tmp_path: Path) -> None:
    """Persisted queued/running tasks become interrupted when registry restarts."""
    registry = TaskRegistry(task_dir=tmp_path)
    queued = registry.create_task("scan")
    running = registry.create_task("train")
    registry.start_task(running.task_id)

    reloaded = TaskRegistry(task_dir=tmp_path)

    assert reloaded.get(queued.task_id).status == "interrupted"
    assert reloaded.get(running.task_id).status == "interrupted"
    assert reloaded.get(running.task_id).finished_at is not None
