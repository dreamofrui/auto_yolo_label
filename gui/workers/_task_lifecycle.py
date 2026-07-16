"""Shared task lifecycle helpers for desktop workers."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from utils.exceptions import AutoLabelerError, ErrorCode, ErrorInfo
from utils.task_registry import TaskHandle, TaskRegistry

_CANCELLATION_CODES = {ErrorCode.TASK_CANCELLED, ErrorCode.TRAIN_INTERRUPTED}


def default_task_registry() -> TaskRegistry:
    """Return the default desktop task registry."""
    return TaskRegistry(Path.home() / ".autolabeler" / "tasks")


def start_worker_task(
    registry: TaskRegistry, task_type: str, message: str
) -> TaskHandle:
    """Create and start a worker task."""
    task = registry.create_task(task_type)
    registry.start_task(task.task_id, message=message)
    return task


def finish_worker_success(
    registry: TaskRegistry,
    task: TaskHandle,
    result: object,
    payload: dict[str, Any] | None = None,
) -> None:
    """Mark a worker task as succeeded with a serializable result payload."""
    registry.succeed_task(
        task.task_id,
        result=_task_payload(result) if payload is None else _json_value(payload),
    )


def finish_worker_error(
    registry: TaskRegistry, task: TaskHandle, exc: AutoLabelerError
) -> ErrorInfo:
    """Mark a worker task as failed or cancelled and return GUI error info."""
    if exc.code in _CANCELLATION_CODES:
        registry.finish_cancelled_task(task.task_id, message=exc.message)
    else:
        registry.fail_task(
            task.task_id,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            retryable=exc.retryable,
        )
    return exc.to_error_info()


def registry_progress_callback(
    registry: TaskRegistry, task: TaskHandle
) -> Callable[[int, int, str], None]:
    """Build a progress callback that persists core progress updates."""

    def update(current: int, total: int, message: str) -> None:
        registry.update_progress(task.task_id, current, total, message)

    return update


def _task_payload(result: object) -> dict[str, Any]:
    """Convert a core result into a task-registry dictionary."""
    if isinstance(result, dict):
        return _json_value(result)
    if is_dataclass(result):
        value = _json_value(result)
        return value if isinstance(value, dict) else {"value": value}
    if isinstance(result, list):
        return {"items": _json_value(result), "count": len(result)}
    if isinstance(result, Path):
        return {"output_path": str(result)}
    return {"value": _json_value(result)}


def _json_value(value: object) -> Any:
    """Convert supported Python objects into JSON-compatible values."""
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _json_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
