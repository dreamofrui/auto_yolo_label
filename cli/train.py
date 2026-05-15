"""JSON CLI adapter for YOLO training."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cli.json_io import (
    error_payload,
    path_field,
    read_json_object,
    task_payload,
    write_json,
)
from core.trainer import TrainConfig
from runtime.services.train_service import TrainServiceOutcome, run_train
from utils.exceptions import AutoLabelerError, ValidationError
from utils.task_registry import TaskRegistry


def run_train_command(request_path: Path) -> int:
    """Read a train request, execute it, and write one JSON response."""
    try:
        request = read_json_object(request_path)
        config = train_config_from_json(request)
        registry = TaskRegistry(path_field(request, "taskDir"))
        outcome = run_train(config, registry)
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

    write_json(train_outcome_payload(outcome))
    return 0 if outcome.success else 1


def train_config_from_json(data: dict[str, Any]) -> TrainConfig:
    """Convert one JSON train request into a core dataclass."""
    return TrainConfig(
        data_yaml=path_field(data, "dataYaml"),
        base_model=path_field(data, "baseModel"),
        output_dir=path_field(data, "outputDir"),
        epochs=_int_field(data, "epochs", 100),
        batch_size=_int_field(data, "batchSize", -1),
        image_size=_int_field(data, "imageSize", 640),
        device=_str_field(data, "device", "auto"),
        patience=_int_field(data, "patience", 50),
        workers=_int_field(data, "workers", 8),
        optimizer=_str_field(data, "optimizer", "AdamW"),
        lr0=_float_field(data, "lr0", 0.01),
        box=_float_field(data, "box", 7.5),
        cls=_float_field(data, "cls", 0.5),
        dfl=_float_field(data, "dfl", 1.5),
        scale=_float_field(data, "scale", 0.5),
        cache=_cache_field(data, "cache", "ram"),
    )


def train_outcome_payload(outcome: TrainServiceOutcome) -> dict[str, Any]:
    """Convert a train service outcome to public CLI JSON."""
    result = None
    if outcome.result is not None:
        result = {
            "bestModel": outcome.result.best_model.as_posix(),
            "lastModel": (
                None
                if outcome.result.last_model is None
                else outcome.result.last_model.as_posix()
            ),
            "outputDir": outcome.result.output_dir.as_posix(),
            "effectiveConfig": outcome.result.effective_config,
            "metrics": {
                "bestEpoch": outcome.result.metrics.best_epoch,
                "bestMap50": outcome.result.metrics.best_map50,
                "bestMap50_95": outcome.result.metrics.best_map50_95,
                "finalMap50": outcome.result.metrics.final_map50,
                "finalMap50_95": outcome.result.metrics.final_map50_95,
            },
        }
    return {
        "success": outcome.success,
        "task": task_payload(outcome.task),
        "result": result,
        "error": None if outcome.error is None else error_payload(outcome.error),
    }


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


def _cache_field(data: dict[str, Any], name: str, default: str | bool) -> str | bool:
    """Read the YOLO cache option."""
    value = data.get(name)
    if value is None:
        return default
    if not isinstance(value, str | bool):
        raise ValidationError("request field must be string or boolean", details=name)
    return value
