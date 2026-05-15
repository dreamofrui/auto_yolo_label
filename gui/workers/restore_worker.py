"""Desktop restore worker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.restorer import RestoreConfig, RestoreResult
from runtime.services.restore_service import run_restore
from utils.exceptions import ErrorInfo
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class RestoreWorkerOutcome:
    """Desktop restore worker outcome."""

    success: bool
    task: TaskHandle
    result: RestoreResult | None
    error: ErrorInfo | None


class RestoreWorker:
    """Thin desktop adapter for Restorer.restore."""

    def __init__(self, registry: TaskRegistry | None = None) -> None:
        """Create a restore worker with an optional shared registry."""
        self._registry = registry or TaskRegistry(
            Path.home() / ".autolabeler" / "tasks"
        )

    def run(self, config: RestoreConfig) -> RestoreWorkerOutcome:
        """Run restore and return a desktop-friendly outcome."""
        outcome = run_restore(config, self._registry)
        return RestoreWorkerOutcome(
            success=outcome.success,
            task=outcome.task,
            result=outcome.result,
            error=None if outcome.error is None else outcome.error.to_error_info(),
        )
