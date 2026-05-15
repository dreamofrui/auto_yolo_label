"""JSON CLI adapter for restoring label files."""

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
from core.restorer import RestoreConfig, RestoreFileIssue
from runtime.services.restore_service import RestoreServiceOutcome, run_restore
from utils.exceptions import AutoLabelerError, ValidationError
from utils.task_registry import TaskRegistry


def run_restore_command(request_path: Path) -> int:
    """Read a restore request, execute it, and write one JSON response."""
    try:
        request = read_json_object(request_path)
        config = restore_config_from_json(request)
        registry = TaskRegistry(path_field(request, "taskDir"))
        outcome = run_restore(config, registry)
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

    write_json(restore_outcome_payload(outcome))
    return 0 if outcome.success else 1


def restore_config_from_json(data: dict[str, Any]) -> RestoreConfig:
    """Convert one JSON restore request into a core dataclass."""
    return RestoreConfig(
        site_folder=path_field(data, "siteFolder"),
        source_type=_str_field(data, "sourceType"),
        database_dir=_optional_path_field(data, "databaseDir"),
        inference_run_dir=_optional_path_field(data, "inferenceRunDir"),
        run_id=_optional_str_field(data, "runId"),
        overwrite=bool_field(data, "overwrite", False),
    )


def restore_outcome_payload(outcome: RestoreServiceOutcome) -> dict[str, Any]:
    """Convert a restore service outcome to public CLI JSON."""
    result = None
    if outcome.result is not None:
        result = {
            "total": outcome.result.total,
            "success": outcome.result.success,
            "skipped": outcome.result.skipped,
            "failed": outcome.result.failed,
            "errors": [_file_issue_payload(item) for item in outcome.result.errors],
        }
    return {
        "success": outcome.success,
        "task": task_payload(outcome.task),
        "result": result,
        "error": None if outcome.error is None else error_payload(outcome.error),
    }


def _file_issue_payload(issue: RestoreFileIssue) -> dict[str, Any]:
    """Convert one per-file restore issue to public CLI JSON."""
    return {
        "sourcePath": issue.source_path.as_posix(),
        "targetPath": (
            None if issue.target_path is None else issue.target_path.as_posix()
        ),
        "reason": issue.reason,
    }


def _optional_path_field(data: dict[str, Any], name: str) -> Path | None:
    """Read an optional path field."""
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValidationError("request field must be a non-empty string", details=name)
    return Path(value)


def _optional_str_field(data: dict[str, Any], name: str) -> str | None:
    """Read an optional string field."""
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValidationError("request field must be a non-empty string", details=name)
    return value


def _str_field(data: dict[str, Any], name: str) -> str:
    """Read a required string field."""
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise ValidationError("request field must be a non-empty string", details=name)
    return value
