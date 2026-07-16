"""Desktop restore worker adapter."""

from __future__ import annotations

from dataclasses import dataclass

from core.restorer import (
    IndependentRestoreConfig,
    RestoreConfig,
    RestorePreflightResult,
    RestoreResult,
    Restorer,
)
from gui.workers._task_lifecycle import (
    default_task_registry,
    finish_worker_error,
    finish_worker_success,
    start_worker_task,
)
from utils.exceptions import AutoLabelerError, ErrorInfo
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class RestoreWorkerOutcome:
    """Desktop restore worker outcome."""

    success: bool
    task: TaskHandle
    result: RestoreResult | None
    error: ErrorInfo | None


@dataclass(frozen=True)
class RestorePreflightOutcome:
    """Desktop restore preflight outcome."""

    success: bool
    result: RestorePreflightResult | None
    error: ErrorInfo | None


class RestoreWorker:
    """Thin desktop adapter for Restorer.restore."""

    def __init__(self, registry: TaskRegistry | None = None) -> None:
        """Create a restore worker with an optional shared registry."""
        self._registry = registry or default_task_registry()

    def run(self, config: RestoreConfig) -> RestoreWorkerOutcome:
        """Run restore and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "restore", "准备还原")
        try:
            result = Restorer(task_handle=task).restore(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return RestoreWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, result)
        return RestoreWorkerOutcome(True, task, result, None)

    def preflight(self, config: RestoreConfig) -> RestorePreflightOutcome:
        """Run Flow restore preflight and return desktop-friendly details."""
        try:
            result = Restorer().preflight(config)
        except Exception as exc:
            if hasattr(exc, "to_error_info"):
                return RestorePreflightOutcome(
                    success=False,
                    result=None,
                    error=exc.to_error_info(),
                )
            raise
        return RestorePreflightOutcome(success=True, result=result, error=None)

    def run_independent(
        self, config: IndependentRestoreConfig
    ) -> RestoreWorkerOutcome:
        """Run independent restore and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "restore", "准备独立还原")
        try:
            result = Restorer(task_handle=task).restore_independent(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return RestoreWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, result)
        return RestoreWorkerOutcome(True, task, result, None)

    def preflight_independent(
        self, config: IndependentRestoreConfig
    ) -> RestorePreflightOutcome:
        """Run Independent restore preflight and return desktop-friendly details."""
        try:
            result = Restorer().preflight_independent(config)
        except Exception as exc:
            if hasattr(exc, "to_error_info"):
                return RestorePreflightOutcome(
                    success=False,
                    result=None,
                    error=exc.to_error_info(),
                )
            raise
        return RestorePreflightOutcome(success=True, result=result, error=None)
