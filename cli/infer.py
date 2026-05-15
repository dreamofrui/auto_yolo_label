"""JSON CLI adapter for YOLO inference."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cli.json_io import (
    bool_field,
    error_payload,
    optional_path_field,
    path_field,
    read_json_object,
    task_payload,
    write_json,
)
from core.inferencer import InferConfig
from runtime.services.infer_service import InferServiceOutcome, run_infer
from utils.exceptions import AutoLabelerError, ValidationError
from utils.task_registry import TaskRegistry


def run_infer_command(request_path: Path) -> int:
    """Read an infer request, execute it, and write one JSON response."""
    try:
        request = read_json_object(request_path)
        config = infer_config_from_json(request)
        registry = TaskRegistry(path_field(request, "taskDir"))
        outcome = run_infer(config, registry)
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

    write_json(infer_outcome_payload(outcome))
    return 0 if outcome.success else 1


def infer_config_from_json(data: dict[str, Any]) -> InferConfig:
    """Convert one JSON infer request into a core dataclass."""
    return InferConfig(
        model_path=path_field(data, "modelPath"),
        site_folder=path_field(data, "siteFolder"),
        output_base_dir=optional_path_field(data, "outputBaseDir"),
        confidence=_float_field(data, "confidence", 0.25),
        iou=_float_field(data, "iou", 0.7),
        batch_size=_int_field(data, "batchSize", -1),
        device=_str_field(data, "device", "auto"),
        save_to_separate_dir=bool_field(data, "saveToSeparateDir", True),
        image_source=_str_field(data, "imageSource", "unsampled"),
        custom_images=_optional_path_list(data, "customImages"),
    )


def infer_outcome_payload(outcome: InferServiceOutcome) -> dict[str, Any]:
    """Convert an infer service outcome to public CLI JSON."""
    result = None
    if outcome.result is not None:
        result = {
            "mappingPath": outcome.result.mapping_path.as_posix(),
            "runId": outcome.result.run_id,
            "inferenceOutputDir": outcome.result.inference_output_dir.as_posix(),
            "configPath": outcome.result.config_path.as_posix(),
            "statistics": {
                "pending": outcome.result.statistics.pending,
                "processed": outcome.result.statistics.processed,
                "success": outcome.result.statistics.success,
                "failed": outcome.result.statistics.failed,
                "predicted": outcome.result.statistics.predicted,
                "emptyPrediction": outcome.result.statistics.empty_prediction,
            },
        }
    return {
        "success": outcome.success,
        "task": task_payload(outcome.task),
        "result": result,
        "error": None if outcome.error is None else error_payload(outcome.error),
    }


def _optional_path_list(data: dict[str, Any], name: str) -> list[Path] | None:
    """Read an optional list of paths."""
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError("request field must be a string array", details=name)
    return [Path(item) for item in value]


def _str_field(data: dict[str, Any], name: str, default: str) -> str:
    """Read an optional string field."""
    value = data.get(name)
    if value is None:
        return default
    if not isinstance(value, str) or not value:
        raise ValidationError("request field must be a non-empty string", details=name)
    return value


def _int_field(data: dict[str, Any], name: str, default: int) -> int:
    """Read an optional integer field."""
    value = data.get(name)
    if value is None:
        return default
    if not isinstance(value, int):
        raise ValidationError("request field must be an integer", details=name)
    return value


def _float_field(data: dict[str, Any], name: str, default: float) -> float:
    """Read an optional numeric field."""
    value = data.get(name)
    if value is None:
        return default
    if not isinstance(value, int | float):
        raise ValidationError("request field must be numeric", details=name)
    return float(value)
