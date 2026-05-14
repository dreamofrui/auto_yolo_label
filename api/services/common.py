"""Shared service helpers for adapter layers."""

from __future__ import annotations

from api.schemas.common import TaskResponse
from utils.task_registry import TaskHandle


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
