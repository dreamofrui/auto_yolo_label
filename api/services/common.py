"""Shared service helpers for adapter layers."""

from __future__ import annotations

from api.schemas.common import TaskResponse
from utils.exceptions import AutoLabelerError, ErrorCode
from utils.task_registry import TaskHandle, TaskRegistry

_CANCELLATION_CODES = {ErrorCode.TASK_CANCELLED, ErrorCode.TRAIN_INTERRUPTED}


def task_response(task: TaskHandle) -> TaskResponse:
    """Convert a TaskHandle to an API response schema."""
    return TaskResponse(
        task_id=task.task_id,
        task_type=task.task_type,
        status=task.status,
        progress_current=task.progress_current,
        progress_total=task.progress_total,
        progress_message=task.progress_message,
    )


def finish_error_task(
    registry: TaskRegistry, task: TaskHandle, exc: AutoLabelerError
) -> TaskHandle:
    """Finish a task from a business exception while preserving cancellation."""
    if exc.code in _CANCELLATION_CODES:
        return registry.finish_cancelled_task(task.task_id, message=exc.message)
    return registry.fail_task(
        task.task_id,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        retryable=exc.retryable,
    )
