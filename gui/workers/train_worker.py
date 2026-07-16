"""Desktop train worker adapter."""

from __future__ import annotations

from dataclasses import dataclass

from core.trainer import TrainConfig, TrainResult, Trainer
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
class TrainWorkerOutcome:
    """Desktop train worker outcome."""

    success: bool
    task: TaskHandle
    result: TrainResult | None
    error: ErrorInfo | None


class TrainWorker:
    """Thin desktop adapter for Trainer.train."""

    def __init__(self, registry: TaskRegistry | None = None) -> None:
        """Create a train worker with an optional shared registry."""
        self._registry = registry or default_task_registry()

    def run(self, config: TrainConfig) -> TrainWorkerOutcome:
        """Run train and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "train", "准备训练")
        try:
            result = Trainer(
                task_handle=task,
                progress_callback=registry_progress_callback(self._registry, task),
            ).train(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return TrainWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, result)
        return TrainWorkerOutcome(True, task, result, None)
