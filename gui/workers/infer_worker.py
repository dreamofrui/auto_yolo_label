"""Desktop infer worker adapter."""

from __future__ import annotations

from dataclasses import dataclass

from core.inferencer import InferConfig, InferResult, Inferencer
from gui.workers._task_lifecycle import (
    default_task_registry,
    finish_worker_error,
    finish_worker_success,
    registry_progress_callback,
    start_worker_task,
)
from utils.exceptions import AutoLabelerError, ErrorInfo
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
        self._registry = registry or default_task_registry()

    def run(self, config: InferConfig) -> InferWorkerOutcome:
        """Run inference and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "infer", "准备推理")
        try:
            result = Inferencer(
                task_handle=task,
                progress_callback=registry_progress_callback(self._registry, task),
            ).infer(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return InferWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, result)
        return InferWorkerOutcome(True, task, result, None)
