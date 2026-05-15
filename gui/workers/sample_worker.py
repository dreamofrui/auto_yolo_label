"""Desktop sample worker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.sampler import SampleConfig, SampleResult
from runtime.services.sample_service import run_sample
from utils.exceptions import ErrorInfo
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class SampleWorkerOutcome:
    """Desktop sample worker outcome."""

    success: bool
    task: TaskHandle
    result: SampleResult | None
    error: ErrorInfo | None


class SampleWorker:
    """Thin desktop adapter for Sampler.sample."""

    def __init__(self, registry: TaskRegistry | None = None) -> None:
        """Create a sample worker with an optional shared registry."""
        self._registry = registry or TaskRegistry(
            Path.home() / ".autolabeler" / "tasks"
        )

    def run(self, config: SampleConfig) -> SampleWorkerOutcome:
        """Run sample and return a desktop-friendly outcome."""
        outcome = run_sample(config, self._registry)
        return SampleWorkerOutcome(
            success=outcome.success,
            task=outcome.task,
            result=outcome.result,
            error=None if outcome.error is None else outcome.error.to_error_info(),
        )
