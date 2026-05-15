"""Shared restore service for desktop and future CLI adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.restorer import RestoreConfig, RestoreResult, Restorer
from runtime.services.common import finish_error_task
from utils.exceptions import AutoLabelerError
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class RestoreServiceOutcome:
    """Result of a restore adapter call."""

    success: bool
    task: TaskHandle
    result: RestoreResult | None
    error: AutoLabelerError | None


def run_restore(config: RestoreConfig, registry: TaskRegistry) -> RestoreServiceOutcome:
    """Run Restorer.restore with TaskRegistry lifecycle handling."""
    task = registry.create_task("restore")
    registry.start_task(task.task_id, message="准备还原")
    try:
        result = Restorer(task_handle=task).restore(config)
    except AutoLabelerError as exc:
        finish_error_task(registry, task, exc)
        return RestoreServiceOutcome(success=False, task=task, result=None, error=exc)
    registry.succeed_task(task.task_id, result=_restore_result_dict(result))
    return RestoreServiceOutcome(success=True, task=task, result=result, error=None)


def _restore_result_dict(result: RestoreResult) -> dict[str, Any]:
    """Convert RestoreResult to a JSON-compatible dict for task storage."""
    return {
        "total": result.total,
        "success": result.success,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": [
            {
                "source_path": str(error.source_path),
                "target_path": (
                    None if error.target_path is None else str(error.target_path)
                ),
                "reason": error.reason,
            }
            for error in result.errors
        ],
    }
