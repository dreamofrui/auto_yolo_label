"""Desktop label inspector worker adapter."""

from __future__ import annotations

from dataclasses import dataclass

from core.label_inspector import (
    GetProductLabelsConfig,
    GetRunTreeConfig,
    InferenceRun,
    ListRunsConfig,
    ProductLabel,
    RunTreeNode,
    LabelInspector,
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
class LabelInspectorWorkerOutcome:
    """Desktop label inspector worker outcome."""

    success: bool
    task: TaskHandle
    result: list[InferenceRun] | list[RunTreeNode] | list[ProductLabel] | None
    error: ErrorInfo | None


class LabelInspectorWorker:
    """Thin desktop adapter for LabelInspector operations."""

    def __init__(self, registry: TaskRegistry | None = None) -> None:
        """Create a label inspector worker with an optional registry."""
        self._registry = registry or default_task_registry()

    def list_runs(self, config: ListRunsConfig) -> LabelInspectorWorkerOutcome:
        """List inference runs and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "label_inspector", "读取推理 run")
        try:
            result = LabelInspector().list_runs(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return LabelInspectorWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, {"items": result, "count": len(result)})
        return LabelInspectorWorkerOutcome(True, task, result, None)

    def get_run_tree(self, config: GetRunTreeConfig) -> LabelInspectorWorkerOutcome:
        """Read an inference run tree and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "label_inspector", "读取 run 节点")
        try:
            result = LabelInspector().get_run_tree(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return LabelInspectorWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, {"items": result, "count": len(result)})
        return LabelInspectorWorkerOutcome(True, task, result, None)

    def get_product_labels(
        self, config: GetProductLabelsConfig
    ) -> LabelInspectorWorkerOutcome:
        """Read product labels and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "label_inspector", "读取产品标签")
        try:
            result = LabelInspector().get_product_labels(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return LabelInspectorWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, {"items": result, "count": len(result)})
        return LabelInspectorWorkerOutcome(True, task, result, None)
