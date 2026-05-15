"""JSON CLI adapters for LabelImg integration."""

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
from core.labelimg_launcher import LabelImgValidateConfig, LabelImgValidateResult
from runtime.services.labelimg_service import LabelImgServiceOutcome, validate_labelimg
from utils.exceptions import AutoLabelerError
from utils.task_registry import TaskRegistry


def run_validate_command(request_path: Path) -> int:
    """Read a LabelImg validate request and write one JSON response."""
    try:
        request = read_json_object(request_path)
        config = validate_config_from_json(request)
        registry = TaskRegistry(path_field(request, "taskDir"))
        outcome = validate_labelimg(config, registry)
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

    write_json(validate_outcome_payload(outcome))
    return 0 if outcome.success else 1


def validate_config_from_json(data: dict[str, Any]) -> LabelImgValidateConfig:
    """Convert one JSON LabelImg validate request into a core dataclass."""
    return LabelImgValidateConfig(python_path=path_field(data, "pythonPath"))


def validate_outcome_payload(outcome: LabelImgServiceOutcome) -> dict[str, Any]:
    """Convert a LabelImg validate outcome to public CLI JSON."""
    result = None
    if isinstance(outcome.result, LabelImgValidateResult):
        result = {
            "isValid": outcome.result.is_valid,
            "labelimgVersion": outcome.result.labelimg_version,
            "pythonVersion": outcome.result.python_version,
            "errorMessage": outcome.result.error_message,
        }
    return {
        "success": outcome.success,
        "task": task_payload(outcome.task),
        "result": result,
        "error": None if outcome.error is None else error_payload(outcome.error),
    }
