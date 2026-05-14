"""Desktop scan worker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from api.services.scan_service import run_scan
from core.scanner import ScanConfig, ScanResult
from utils.exceptions import ErrorInfo
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
        self._registry = registry or TaskRegistry(Path.home() / ".autolabeler" / "tasks")

    def run(self, config: ScanConfig) -> ScanWorkerOutcome:
        """Run scan and return a desktop-friendly outcome."""
        outcome = run_scan(config, self._registry)
        return ScanWorkerOutcome(
            success=outcome.success,
            task=outcome.task,
            result=outcome.result,
            error=None if outcome.error is None else outcome.error.to_error_info(),
        )
