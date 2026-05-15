"""JSON CLI adapters for read-only inference label inspection."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

from cli.json_io import (
    error_payload,
    path_field,
    read_json_object,
    task_payload,
    write_json,
)
from core.label_inspector import (
    GetProductLabelsConfig,
    GetRunTreeConfig,
    InferenceRun,
    ListRunsConfig,
    ProductLabel,
    RunTreeNode,
)
from runtime.services.label_inspector_service import (
    LabelInspectorServiceOutcome,
    get_product_labels,
    get_run_tree,
    list_runs,
)
from utils.exceptions import AutoLabelerError, ValidationError
from utils.task_registry import TaskRegistry


def run_list_runs_command(request_path: Path) -> int:
    """Read a list-runs request and write one JSON response."""
    return _run_inspect_command(
        request_path,
        _list_runs_config,
        list_runs,
        _list_runs_outcome_payload,
    )


def run_tree_command(request_path: Path) -> int:
    """Read a run-tree request and write one JSON response."""
    return _run_inspect_command(
        request_path,
        _run_tree_config,
        get_run_tree,
        _run_tree_outcome_payload,
    )


def run_product_labels_command(request_path: Path) -> int:
    """Read a product-labels request and write one JSON response."""
    return _run_inspect_command(
        request_path,
        _product_labels_config,
        get_product_labels,
        _product_labels_outcome_payload,
    )


def _run_inspect_command(
    request_path: Path,
    config_factory: Callable[[dict[str, Any]], object],
    service: Callable[[object, TaskRegistry], LabelInspectorServiceOutcome],
    payload_factory: Callable[[LabelInspectorServiceOutcome], dict[str, Any]],
) -> int:
    """Execute one inspector service and write a JSON response."""
    try:
        request = read_json_object(request_path)
        config = config_factory(request)
        registry = TaskRegistry(path_field(request, "taskDir"))
        outcome = service(config, registry)
    except AutoLabelerError as exc:
        write_json(
            {
                "success": False,
                "task": None,
                "result": None,
                "error": error_payload(exc),
            }
        )
        return 1

    write_json(payload_factory(outcome))
    return 0 if outcome.success else 1


def _list_runs_config(data: dict[str, Any]) -> ListRunsConfig:
    """Convert list-runs JSON to a core dataclass."""
    return ListRunsConfig(site_folder=path_field(data, "siteFolder"))


def _run_tree_config(data: dict[str, Any]) -> GetRunTreeConfig:
    """Convert run-tree JSON to a core dataclass."""
    return GetRunTreeConfig(
        site_folder=path_field(data, "siteFolder"),
        run_id=_str_field(data, "runId"),
    )


def _product_labels_config(data: dict[str, Any]) -> GetProductLabelsConfig:
    """Convert product-labels JSON to a core dataclass."""
    return GetProductLabelsConfig(
        site_folder=path_field(data, "siteFolder"),
        run_id=_str_field(data, "runId"),
        code=_str_field(data, "code"),
        product=_str_field(data, "product"),
    )


def _list_runs_outcome_payload(
    outcome: LabelInspectorServiceOutcome,
) -> dict[str, Any]:
    """Convert a list-runs outcome to a JSON-compatible payload."""
    result = None
    if outcome.result is not None:
        runs = cast(list[InferenceRun], outcome.result)
        result = {"runs": [_run_payload(item) for item in runs]}
    return _outcome_payload(outcome, result)


def _run_tree_outcome_payload(
    outcome: LabelInspectorServiceOutcome,
) -> dict[str, Any]:
    """Convert a run-tree outcome to a JSON-compatible payload."""
    result = None
    if outcome.result is not None:
        nodes = cast(list[RunTreeNode], outcome.result)
        result = {"nodes": [_node_payload(item) for item in nodes]}
    return _outcome_payload(outcome, result)


def _product_labels_outcome_payload(
    outcome: LabelInspectorServiceOutcome,
) -> dict[str, Any]:
    """Convert a product-labels outcome to a JSON-compatible payload."""
    result = None
    if outcome.result is not None:
        labels = cast(list[ProductLabel], outcome.result)
        result = {"labels": [_label_payload(item) for item in labels]}
    return _outcome_payload(outcome, result)


def _outcome_payload(
    outcome: LabelInspectorServiceOutcome,
    result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Convert common inspector outcome fields to a JSON payload."""
    return {
        "success": outcome.success,
        "task": task_payload(outcome.task),
        "result": result,
        "error": None if outcome.error is None else error_payload(outcome.error),
    }


def _run_payload(run: InferenceRun) -> dict[str, Any]:
    """Convert one inference run to public CLI JSON."""
    return {
        "runId": run.run_id,
        "path": run.path.as_posix(),
        "configExists": run.config_exists,
        "config": run.config,
        "createdAt": run.created_at,
    }


def _node_payload(node: RunTreeNode) -> dict[str, Any]:
    """Convert one run tree node to public CLI JSON."""
    return {
        "code": node.code,
        "product": node.product,
        "labelCount": node.label_count,
        "emptyCount": node.empty_count,
        "path": node.path.as_posix(),
    }


def _label_payload(label: ProductLabel) -> dict[str, Any]:
    """Convert one product label to public CLI JSON."""
    return {
        "imageName": label.image_name,
        "imagePath": None if label.image_path is None else label.image_path.as_posix(),
        "labelPath": label.label_path.as_posix(),
        "objectCount": label.object_count,
    }


def _str_field(data: dict[str, Any], name: str) -> str:
    """Read a required string field."""
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise ValidationError("request field must be a non-empty string", details=name)
    return value
