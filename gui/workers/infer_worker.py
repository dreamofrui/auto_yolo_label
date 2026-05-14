"""Desktop infer worker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from api.services.infer_service import run_infer
from core.inferencer import InferConfig, InferResult
from utils.exceptions import ErrorInfo
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class InferWorkerOutcome:
    """Desktop infer worker outcome."""

    success: bool
    task: TaskHandle
    result: InferResult | None
    error: ErrorInfo | None


class InferWorker:
    """Thin desktop adapter for Inferencer.infer."""

    def __init__(self, registry: TaskRegistry | None = None) -> None:
        """Create an infer worker with an optional shared registry."""
        self._registry = registry or TaskRegistry(Path.home() / ".autolabeler" / "tasks")

    def run(self, config: InferConfig) -> InferWorkerOutcome:
        """Run inference and return a desktop-friendly outcome."""
        outcome = run_infer(config, self._registry)
        return InferWorkerOutcome(
            success=outcome.success,
            task=outcome.task,
            result=outcome.result,
            error=None if outcome.error is None else outcome.error.to_error_info(),
        )
