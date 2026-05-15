"""JSON CLI adapter for dataset sampling."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cli.json_io import (
    bool_field,
    error_payload,
    path_field,
    read_json_object,
    task_payload,
    write_json,
)
from core.sampler import SampleConfig
from runtime.services.sample_service import SampleServiceOutcome, run_sample
from utils.exceptions import AutoLabelerError, ValidationError
from utils.task_registry import TaskRegistry


def run_sample_command(request_path: Path) -> int:
    """Read a sample request, execute it, and write one JSON response."""
    try:
        request = read_json_object(request_path)
        config = sample_config_from_json(request)
        registry = TaskRegistry(path_field(request, "taskDir"))
        outcome = run_sample(config, registry)
    except AutoLabelerError as exc:
        write_json(
            {"success": False, "task": None, "result": None, "error": error_payload(exc)}
        )
        return 1

    write_json(sample_outcome_payload(outcome))
    return 0 if outcome.success else 1


def sample_config_from_json(data: dict[str, Any]) -> SampleConfig:
    """Convert one JSON sample request into a core dataclass."""
    return SampleConfig(
        site_folder=path_field(data, "siteFolder"),
        output_dir=path_field(data, "outputDir"),
        mode=_str_field(data, "mode", "count"),
        count=_int_field(data, "count", 40),
        ratio=_float_field(data, "ratio", 0.3),
        min_count=_int_field(data, "minCount", 20),
        max_count=_int_field(data, "maxCount", 50),
        full_threshold=_int_field(data, "fullThreshold", 35),
        train_ratio=_float_field(data, "trainRatio", 0.9),
        pre_labeled_priority=bool_field(data, "preLabeledPriority", True),
    )


def sample_outcome_payload(outcome: SampleServiceOutcome) -> dict[str, Any]:
    """Convert a sample service outcome to a JSON-compatible payload."""
    return {
        "success": outcome.success,
        "task": task_payload(outcome.task),
        "result": None if outcome.result is None else _sample_result(outcome),
        "error": None if outcome.error is None else error_payload(outcome.error),
    }


def _sample_result(outcome: SampleServiceOutcome) -> dict[str, Any]:
    """Convert a successful sample outcome to the public CLI JSON shape."""
    if outcome.result is None:
        return {}
    result = outcome.result
    return {
        "mappingPath": result.mapping_path.as_posix(),
        "datasetDir": result.dataset_dir.as_posix(),
        "dataYaml": result.data_yaml.as_posix(),
        "paths": {
            "imagesTrain": result.paths.images_train.as_posix(),
            "imagesVal": result.paths.images_val.as_posix(),
            "labelsTrain": result.paths.labels_train.as_posix(),
            "labelsVal": result.paths.labels_val.as_posix(),
        },
        "statistics": {
            "totalProducts": result.statistics.total_products,
            "sampledCount": result.statistics.sampled_count,
            "trainCount": result.statistics.train_count,
            "valCount": result.statistics.val_count,
            "preLabeledCount": result.statistics.pre_labeled_count,
        },
    }


def _str_field(data: dict[str, Any], name: str, default: str) -> str:
    """Read an optional string field."""
    value = data.get(name)
    if value is None:
        return default
    if not isinstance(value, str) or not value:
        raise ValidationError("请求字段必须是非空字符串", details=name)
    return value


def _int_field(data: dict[str, Any], name: str, default: int) -> int:
    """Read an optional integer field."""
    value = data.get(name)
    if value is None:
        return default
    if not isinstance(value, int):
        raise ValidationError("请求字段必须是整数", details=name)
    return value


def _float_field(data: dict[str, Any], name: str, default: float) -> float:
    """Read an optional numeric field."""
    value = data.get(name)
    if value is None:
        return default
    if not isinstance(value, int | float):
        raise ValidationError("请求字段必须是数字", details=name)
    return float(value)
