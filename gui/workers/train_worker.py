"""Desktop train worker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.trainer import TrainConfig, TrainResult
from runtime.services.train_service import run_train
from utils.exceptions import ErrorInfo
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
        self._registry = registry or TaskRegistry(
            Path.home() / ".autolabeler" / "tasks"
        )

    def run(self, config: TrainConfig) -> TrainWorkerOutcome:
        """Run train and return a desktop-friendly outcome."""
        outcome = run_train(config, self._registry)
        return TrainWorkerOutcome(
            success=outcome.success,
            task=outcome.task,
            result=outcome.result,
            error=None if outcome.error is None else outcome.error.to_error_info(),
        )
