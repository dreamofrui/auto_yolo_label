"""Desktop label inspector worker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from api.services.label_inspector_service import get_product_labels, get_run_tree, list_runs
from core.label_inspector import (
    GetProductLabelsConfig,
    GetRunTreeConfig,
    InferenceRun,
    ListRunsConfig,
    ProductLabel,
    RunTreeNode,
)
from utils.exceptions import ErrorInfo
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
        self._registry = registry or TaskRegistry(Path.home() / ".autolabeler" / "tasks")

    def list_runs(self, config: ListRunsConfig) -> LabelInspectorWorkerOutcome:
        """List inference runs and return a desktop-friendly outcome."""
        outcome = list_runs(config, self._registry)
        return LabelInspectorWorkerOutcome(
            success=outcome.success,
            task=outcome.task,
            result=outcome.result,
            error=None if outcome.error is None else outcome.error.to_error_info(),
        )

    def get_run_tree(self, config: GetRunTreeConfig) -> LabelInspectorWorkerOutcome:
        """Read an inference run tree and return a desktop-friendly outcome."""
        outcome = get_run_tree(config, self._registry)
        return LabelInspectorWorkerOutcome(
            success=outcome.success,
            task=outcome.task,
            result=outcome.result,
            error=None if outcome.error is None else outcome.error.to_error_info(),
        )

    def get_product_labels(self, config: GetProductLabelsConfig) -> LabelInspectorWorkerOutcome:
        """Read product labels and return a desktop-friendly outcome."""
        outcome = get_product_labels(config, self._registry)
        return LabelInspectorWorkerOutcome(
            success=outcome.success,
            task=outcome.task,
            result=outcome.result,
            error=None if outcome.error is None else outcome.error.to_error_info(),
        )
