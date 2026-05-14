"""Shared sample service for desktop and HTTP adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.services.common import finish_error_task
from core.sampler import SampleConfig, SampleResult, Sampler
from utils.exceptions import AutoLabelerError
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class SampleServiceOutcome:
    """Result of a sample adapter call."""

    success: bool
    task: TaskHandle
    result: SampleResult | None
    error: AutoLabelerError | None


def run_sample(config: SampleConfig, registry: TaskRegistry) -> SampleServiceOutcome:
    """Run Sampler.sample with TaskRegistry lifecycle handling."""
    task = registry.create_task("sample")
    registry.start_task(task.task_id, message="准备抽样")
    try:
        result = Sampler(task_handle=task).sample(config)
    except AutoLabelerError as exc:
        finish_error_task(registry, task, exc)
        return SampleServiceOutcome(success=False, task=task, result=None, error=exc)
    registry.succeed_task(task.task_id, result=_sample_result_dict(result))
    return SampleServiceOutcome(success=True, task=task, result=result, error=None)


def _sample_result_dict(result: SampleResult) -> dict[str, Any]:
    """Convert SampleResult to a JSON-compatible dict for task storage."""
    return {
        "mapping_path": str(result.mapping_path),
        "dataset_dir": str(result.dataset_dir),
        "data_yaml": str(result.data_yaml),
        "paths": {
            "images_train": str(result.paths.images_train),
            "images_val": str(result.paths.images_val),
            "labels_train": str(result.paths.labels_train),
            "labels_val": str(result.paths.labels_val),
        },
        "statistics": {
            "total_products": result.statistics.total_products,
            "sampled_count": result.statistics.sampled_count,
            "train_count": result.statistics.train_count,
            "val_count": result.statistics.val_count,
            "pre_labeled_count": result.statistics.pre_labeled_count,
        },
    }
