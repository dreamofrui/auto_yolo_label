"""In-process task registry shared by desktop and future CLI entry points."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.exceptions import (
    ErrorCode,
    ErrorInfo,
    TaskAlreadyRunningError,
    TaskNotFoundError,
)

_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
_ACTIVE_STATUSES = {"queued", "running"}
_TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "interrupted"}


@dataclass
class TaskHandle:
    """Mutable task state shared by callers and core modules."""

    task_id: str
    task_type: str
    status: str
    progress_current: int
    progress_total: int
    progress_message: str
    logs: list[str]
    result: dict[str, Any] | None
    error: ErrorInfo | None
    created_at: str
    started_at: str | None
    finished_at: str | None
    is_cancel_requested: bool = False


class TaskRegistry:
    """Manage task handles and persist their public state."""

    def __init__(self, task_dir: Path) -> None:
        """Create a registry backed by task JSON files.

        Args:
            task_dir: Directory where task metadata is stored.
        """
        self.task_dir = task_dir
        self._lock = threading.RLock()
        self._tasks: dict[str, TaskHandle] = {}
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self._load_existing_tasks()

    def create_task(self, task_type: str) -> TaskHandle:
        """Create and persist a queued task.

        Args:
            task_type: Logical task type such as scan, train, or infer.

        Returns:
            Newly created task handle.

        Raises:
            TaskAlreadyRunningError: If an active task of the same type exists.
        """
        with self._lock:
            self._ensure_no_active_task(task_type)
            now = _now()
            handle = TaskHandle(
                task_id=_new_task_id(task_type),
                task_type=task_type,
                status="queued",
                progress_current=0,
                progress_total=0,
                progress_message="",
                logs=[],
                result=None,
                error=None,
                created_at=now,
                started_at=None,
                finished_at=None,
            )
            self._tasks[handle.task_id] = handle
            self._persist(handle)
            return handle

    def get(self, task_id: str) -> TaskHandle:
        """Return a task by id.

        Raises:
            TaskNotFoundError: If task_id does not exist.
        """
        with self._lock:
            try:
                return self._tasks[task_id]
            except KeyError as exc:
                raise TaskNotFoundError("任务不存在", details=task_id) from exc

    def list_tasks(self) -> list[TaskHandle]:
        """Return all known tasks sorted by creation time."""
        with self._lock:
            return sorted(self._tasks.values(), key=lambda task: task.created_at)

    def start_task(self, task_id: str, total: int = 0, message: str = "") -> TaskHandle:
        """Mark a task as running."""
        with self._lock:
            handle = self.get(task_id)
            handle.status = "running"
            handle.started_at = handle.started_at or _now()
            handle.progress_total = total
            handle.progress_message = message
            self._persist(handle)
            return handle

    def update_progress(
        self,
        task_id: str,
        current: int,
        total: int | None = None,
        message: str | None = None,
    ) -> TaskHandle:
        """Update task progress fields."""
        with self._lock:
            handle = self.get(task_id)
            if handle.status in _TERMINAL_STATUSES:
                return handle
            handle.progress_current = current
            if total is not None:
                handle.progress_total = total
            if message is not None:
                handle.progress_message = message
            self._persist(handle)
            return handle

    def append_log(self, task_id: str, message: str) -> TaskHandle:
        """Append one log line to a task."""
        with self._lock:
            handle = self.get(task_id)
            if handle.status in _TERMINAL_STATUSES:
                return handle
            handle.logs.append(message)
            self._persist(handle)
            return handle

    def succeed_task(
        self, task_id: str, result: dict[str, Any] | None = None
    ) -> TaskHandle:
        """Mark a task as succeeded."""
        with self._lock:
            handle = self.get(task_id)
            if handle.status in _TERMINAL_STATUSES:
                return handle
            handle.status = "succeeded"
            handle.progress_current = handle.progress_total
            handle.progress_message = "完成"
            handle.result = result
            handle.error = None
            handle.finished_at = _now()
            self._persist(handle)
            return handle

    def fail_task(
        self,
        task_id: str,
        code: ErrorCode,
        message: str,
        details: str | None = None,
        retryable: bool = False,
    ) -> TaskHandle:
        """Mark a task as failed with serializable error info."""
        with self._lock:
            handle = self.get(task_id)
            if handle.status in _TERMINAL_STATUSES:
                return handle
            handle.status = "failed"
            handle.error = ErrorInfo(
                code=code.value,
                message=message,
                details=details,
                retryable=retryable,
            )
            handle.finished_at = _now()
            self._persist(handle)
            return handle

    def cancel(self, task_id: str) -> TaskHandle:
        """Request cancellation and leave active tasks reserved until acknowledged."""
        with self._lock:
            handle = self.get(task_id)
            if handle.status in _TERMINAL_STATUSES:
                return handle
            handle.is_cancel_requested = True
            if handle.status == "queued":
                handle.status = "cancelled"
                handle.finished_at = _now()
            self._persist(handle)
            return handle

    def finish_cancelled_task(
        self, task_id: str, message: str = "已取消"
    ) -> TaskHandle:
        """Mark a cancellation request as fully acknowledged by the core loop."""
        with self._lock:
            handle = self.get(task_id)
            if handle.status in _TERMINAL_STATUSES:
                return handle
            handle.is_cancel_requested = True
            handle.status = "cancelled"
            handle.progress_message = message
            handle.finished_at = _now()
            self._persist(handle)
            return handle

    def _ensure_no_active_task(self, task_type: str) -> None:
        """Raise if an active task of task_type already exists."""
        for task in self._tasks.values():
            if task.task_type == task_type and task.status in _ACTIVE_STATUSES:
                raise TaskAlreadyRunningError("同类型任务已在运行", details=task_type)

    def _load_existing_tasks(self) -> None:
        """Load persisted task files and interrupt unfinished tasks."""
        for path in sorted(self.task_dir.glob("*.json")):
            handle = _task_from_dict(json.loads(path.read_text(encoding="utf-8")))
            if handle.status in _ACTIVE_STATUSES:
                handle.status = "interrupted"
                handle.finished_at = handle.finished_at or _now()
                handle.is_cancel_requested = True
                self._persist(handle)
            self._tasks[handle.task_id] = handle

    def _persist(self, handle: TaskHandle) -> None:
        """Persist one task handle as JSON."""
        path = self.task_dir / f"{handle.task_id}.json"
        path.write_text(
            json.dumps(_task_to_dict(handle), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _new_task_id(task_type: str) -> str:
    """Create a stable task id."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"task_{task_type}_{timestamp}_{suffix}"


def _now() -> str:
    """Return the current wall-clock timestamp."""
    return datetime.now().strftime(_TIME_FORMAT)


def _task_to_dict(handle: TaskHandle) -> dict[str, Any]:
    """Convert TaskHandle to JSON-compatible camelCase dict."""
    return {
        "taskId": handle.task_id,
        "taskType": handle.task_type,
        "status": handle.status,
        "progressCurrent": handle.progress_current,
        "progressTotal": handle.progress_total,
        "progressMessage": handle.progress_message,
        "logs": handle.logs,
        "result": handle.result,
        "error": None if handle.error is None else handle.error.__dict__,
        "createdAt": handle.created_at,
        "startedAt": handle.started_at,
        "finishedAt": handle.finished_at,
        "isCancelRequested": handle.is_cancel_requested,
    }


def _task_from_dict(raw: dict[str, Any]) -> TaskHandle:
    """Convert a persisted camelCase dict to TaskHandle."""
    error_raw = raw.get("error")
    error = ErrorInfo(**error_raw) if isinstance(error_raw, dict) else None
    return TaskHandle(
        task_id=str(raw["taskId"]),
        task_type=str(raw["taskType"]),
        status=str(raw["status"]),
        progress_current=int(raw.get("progressCurrent", 0)),
        progress_total=int(raw.get("progressTotal", 0)),
        progress_message=str(raw.get("progressMessage", "")),
        logs=[str(item) for item in raw.get("logs", [])],
        result=dict(raw["result"]) if isinstance(raw.get("result"), dict) else None,
        error=error,
        created_at=str(raw["createdAt"]),
        started_at=None if raw.get("startedAt") is None else str(raw["startedAt"]),
        finished_at=None if raw.get("finishedAt") is None else str(raw["finishedAt"]),
        is_cancel_requested=bool(raw.get("isCancelRequested", False)),
    )
