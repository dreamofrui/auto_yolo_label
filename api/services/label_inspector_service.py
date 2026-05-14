"""Shared label inspector services for desktop and HTTP adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from api.services.common import finish_error_task
from core.label_inspector import (
    GetProductLabelsConfig,
    GetRunTreeConfig,
    InferenceRun,
    LabelInspector,
    ListRunsConfig,
    ProductLabel,
    RunTreeNode,
)
from utils.exceptions import AutoLabelerError
from utils.task_registry import TaskHandle, TaskRegistry

InspectorResult: TypeAlias = list[InferenceRun] | list[RunTreeNode] | list[ProductLabel]


@dataclass(frozen=True)
class LabelInspectorServiceOutcome:
    """Result of a label inspector adapter call."""

    success: bool
    task: TaskHandle
    result: InspectorResult | None
    error: AutoLabelerError | None


def list_runs(
    config: ListRunsConfig, registry: TaskRegistry
) -> LabelInspectorServiceOutcome:
    """List inference runs with TaskRegistry lifecycle handling."""
    task = registry.create_task("label_inspector")
    registry.start_task(task.task_id, message="Listing inference runs")
    try:
        result = LabelInspector().list_runs(config)
    except AutoLabelerError as exc:
        return _fail(registry, task, exc)
    registry.succeed_task(
        task.task_id, result={"runs": [_run_dict(item) for item in result]}
    )
    return LabelInspectorServiceOutcome(
        success=True, task=task, result=result, error=None
    )


def get_run_tree(
    config: GetRunTreeConfig, registry: TaskRegistry
) -> LabelInspectorServiceOutcome:
    """Read an inference run tree with TaskRegistry lifecycle handling."""
    task = registry.create_task("label_inspector")
    registry.start_task(task.task_id, message="Reading inference run tree")
    try:
        result = LabelInspector().get_run_tree(config)
    except AutoLabelerError as exc:
        return _fail(registry, task, exc)
    registry.succeed_task(
        task.task_id, result={"nodes": [_node_dict(item) for item in result]}
    )
    return LabelInspectorServiceOutcome(
        success=True, task=task, result=result, error=None
    )


def get_product_labels(
    config: GetProductLabelsConfig,
    registry: TaskRegistry,
) -> LabelInspectorServiceOutcome:
    """Read product labels with TaskRegistry lifecycle handling."""
    task = registry.create_task("label_inspector")
    registry.start_task(task.task_id, message="Reading product labels")
    try:
        result = LabelInspector().get_product_labels(config)
    except AutoLabelerError as exc:
        return _fail(registry, task, exc)
    registry.succeed_task(
        task.task_id, result={"labels": [_label_dict(item) for item in result]}
    )
    return LabelInspectorServiceOutcome(
        success=True, task=task, result=result, error=None
    )


def _fail(
    registry: TaskRegistry,
    task: TaskHandle,
    exc: AutoLabelerError,
) -> LabelInspectorServiceOutcome:
    """Mark a label inspector task as failed."""
    finish_error_task(registry, task, exc)
    return LabelInspectorServiceOutcome(
        success=False, task=task, result=None, error=exc
    )


def _run_dict(result: InferenceRun) -> dict[str, object]:
    """Convert InferenceRun to a JSON-compatible dict."""
    return {
        "run_id": result.run_id,
        "path": str(result.path),
        "config_exists": result.config_exists,
        "config": result.config,
        "created_at": result.created_at,
    }


def _node_dict(result: RunTreeNode) -> dict[str, object]:
    """Convert RunTreeNode to a JSON-compatible dict."""
    return {
        "code": result.code,
        "product": result.product,
        "label_count": result.label_count,
        "empty_count": result.empty_count,
        "path": str(result.path),
    }


def _label_dict(result: ProductLabel) -> dict[str, object]:
    """Convert ProductLabel to a JSON-compatible dict."""
    return {
        "image_name": result.image_name,
        "image_path": None if result.image_path is None else str(result.image_path),
        "label_path": str(result.label_path),
        "object_count": result.object_count,
    }
