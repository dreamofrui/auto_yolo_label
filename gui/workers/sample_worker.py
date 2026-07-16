"""Desktop sample worker adapter."""

from __future__ import annotations

from dataclasses import dataclass

from core.sampler import (
    IndependentSampleConfig,
    SampleConfig,
    SamplePreflightResult,
    SampleResult,
    Sampler,
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
class SampleWorkerOutcome:
    """Desktop sample worker outcome."""

    success: bool
    task: TaskHandle
    result: SampleResult | None
    error: ErrorInfo | None


@dataclass(frozen=True)
class SamplePreflightOutcome:
    """Desktop sample preflight outcome."""

    success: bool
    result: SamplePreflightResult | None
    error: ErrorInfo | None


class SampleWorker:
    """Thin desktop adapter for Sampler.sample."""

    def __init__(self, registry: TaskRegistry | None = None) -> None:
        """Create a sample worker with an optional shared registry."""
        self._registry = registry or default_task_registry()

    def run(self, config: SampleConfig) -> SampleWorkerOutcome:
        """Run sample and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "sample", "准备抽样")
        try:
            result = Sampler(task_handle=task).sample(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return SampleWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, result)
        return SampleWorkerOutcome(True, task, result, None)

    def preflight(self, config: SampleConfig) -> SamplePreflightOutcome:
        """Run Flow preflight and return desktop-friendly details."""
        try:
            result = Sampler().preflight(config)
        except Exception as exc:
            if hasattr(exc, "to_error_info"):
                return SamplePreflightOutcome(
                    success=False,
                    result=None,
                    error=exc.to_error_info(),
                )
            raise
        return SamplePreflightOutcome(success=True, result=result, error=None)

    def run_independent(
        self, config: IndependentSampleConfig
    ) -> SampleWorkerOutcome:
        """Run independent sample and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "sample", "准备独立抽样")
        try:
            result = Sampler(task_handle=task).sample_independent(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return SampleWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, result)
        return SampleWorkerOutcome(True, task, result, None)

    def preflight_independent(
        self, config: IndependentSampleConfig
    ) -> SamplePreflightOutcome:
        """Run Independent preflight and return desktop-friendly details."""
        try:
            result = Sampler().preflight_independent(config)
        except Exception as exc:
            if hasattr(exc, "to_error_info"):
                return SamplePreflightOutcome(
                    success=False,
                    result=None,
                    error=exc.to_error_info(),
                )
            raise
        return SamplePreflightOutcome(success=True, result=result, error=None)
