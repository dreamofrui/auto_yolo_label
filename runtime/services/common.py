"""Shared service helpers for desktop and future CLI adapters."""

from __future__ import annotations

from utils.exceptions import AutoLabelerError, ErrorCode
from utils.task_registry import TaskHandle, TaskRegistry

_CANCELLATION_CODES = {ErrorCode.TASK_CANCELLED, ErrorCode.TRAIN_INTERRUPTED}


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
