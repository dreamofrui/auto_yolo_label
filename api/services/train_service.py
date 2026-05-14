"""Shared train service for desktop and HTTP adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.services.common import finish_error_task
from core.trainer import TrainConfig, TrainResult, Trainer
from utils.exceptions import AutoLabelerError
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class TrainServiceOutcome:
    """Result of a train adapter call."""

    success: bool
    task: TaskHandle
    result: TrainResult | None
    error: AutoLabelerError | None


def run_train(config: TrainConfig, registry: TaskRegistry) -> TrainServiceOutcome:
    """Run Trainer.train with TaskRegistry lifecycle handling."""
    task = registry.create_task("train")
    registry.start_task(task.task_id, message="准备训练")
    try:
        result = Trainer(task_handle=task).train(config)
    except AutoLabelerError as exc:
        finish_error_task(registry, task, exc)
        return TrainServiceOutcome(success=False, task=task, result=None, error=exc)
    registry.succeed_task(task.task_id, result=_train_result_dict(result))
    return TrainServiceOutcome(success=True, task=task, result=result, error=None)


def _train_result_dict(result: TrainResult) -> dict[str, Any]:
    """Convert TrainResult to a JSON-compatible dict for task storage."""
    return {
        "best_model": str(result.best_model),
        "last_model": None if result.last_model is None else str(result.last_model),
        "output_dir": str(result.output_dir),
        "effective_config": result.effective_config,
        "metrics": {
            "best_epoch": result.metrics.best_epoch,
            "best_map50": result.metrics.best_map50,
            "best_map50_95": result.metrics.best_map50_95,
            "final_map50": result.metrics.final_map50,
            "final_map50_95": result.metrics.final_map50_95,
        },
    }
