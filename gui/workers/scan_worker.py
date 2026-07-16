"""Desktop scan worker adapter."""

from __future__ import annotations

from dataclasses import dataclass

from core.scanner import ScanConfig, ScanResult, Scanner
from gui.workers._task_lifecycle import (
    default_task_registry,
    finish_worker_error,
    finish_worker_success,
    start_worker_task,
)
from utils.exceptions import AutoLabelerError, ErrorInfo
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class ScanWorkerOutcome:
    """Desktop worker outcome."""

    success: bool
    task: TaskHandle
    result: ScanResult | None
    error: ErrorInfo | None


class ScanWorker:
    """Thin desktop adapter for Scanner.scan."""

    def __init__(self, registry: TaskRegistry | None = None) -> None:
        """Create a scan worker with an optional shared registry.

        Args:
            registry: Optional task registry supplied by the desktop app.
        """
        self._registry = registry or default_task_registry()

    def run(self, config: ScanConfig) -> ScanWorkerOutcome:
        """Run scan and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "scan", "准备扫描")
        try:
            result = Scanner(task_handle=task).scan(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return ScanWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, result)
        return ScanWorkerOutcome(True, task, result, None)
