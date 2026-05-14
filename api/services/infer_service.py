"""Shared infer service for desktop and HTTP adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.services.common import finish_error_task
from core.inferencer import InferConfig, InferResult, Inferencer
from utils.exceptions import AutoLabelerError
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class InferServiceOutcome:
    """Result of an infer adapter call."""

    success: bool
    task: TaskHandle
    result: InferResult | None
    error: AutoLabelerError | None


def run_infer(config: InferConfig, registry: TaskRegistry) -> InferServiceOutcome:
    """Run Inferencer.infer with TaskRegistry lifecycle handling.

    Args:
        config: Core inference configuration.
        registry: Shared task registry.

    Returns:
        A service outcome for API and desktop callers.
    """
    task = registry.create_task("infer")
    registry.start_task(task.task_id, message="准备推理")
    try:
        result = Inferencer(task_handle=task).infer(config)
    except AutoLabelerError as exc:
        finish_error_task(registry, task, exc)
        return InferServiceOutcome(success=False, task=task, result=None, error=exc)
    registry.succeed_task(task.task_id, result=_infer_result_dict(result))
    return InferServiceOutcome(success=True, task=task, result=result, error=None)


def _infer_result_dict(result: InferResult) -> dict[str, Any]:
    """Convert InferResult to a JSON-compatible dict for task storage."""
    return {
        "mapping_path": str(result.mapping_path),
        "run_id": result.run_id,
        "inference_output_dir": str(result.inference_output_dir),
        "config_path": str(result.config_path),
        "statistics": {
            "pending": result.statistics.pending,
            "processed": result.statistics.processed,
            "success": result.statistics.success,
            "failed": result.statistics.failed,
            "predicted": result.statistics.predicted,
            "empty_prediction": result.statistics.empty_prediction,
        },
    }
