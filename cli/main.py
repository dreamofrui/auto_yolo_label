"""Minimal JSON command-line entry point for AutoLabeler."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from core.scanner import ScanConfig
from runtime.services.scan_service import ScanServiceOutcome, run_scan
from utils.exceptions import AutoLabelerError, ErrorInfo, ValidationError
from utils.task_registry import TaskHandle, TaskRegistry


def run(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = argparse.ArgumentParser(prog="auto-yolo-label")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("request_json")
    args = parser.parse_args(argv)

    if args.command == "scan":
        return _run_scan_command(Path(args.request_json))
    raise AssertionError(f"Unhandled command: {args.command}")


def main() -> None:
    """Run the CLI as a Python module."""
    raise SystemExit(run())


def _run_scan_command(request_path: Path) -> int:
    """Read a scan request, execute it, and write one JSON response."""
    try:
        request = _read_json_object(request_path)
        config = _scan_config_from_json(request)
        registry = TaskRegistry(_path_field(request, "taskDir"))
        outcome = run_scan(config, registry)
    except AutoLabelerError as exc:
        _write_json({"success": False, "task": None, "result": None, "error": _error(exc)})
        return 1

    _write_json(_scan_outcome(outcome))
    return 0 if outcome.success else 1


def _read_json_object(path: Path) -> dict[str, Any]:
    """Read a JSON object from disk."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValidationError("请求 JSON 无法读取", details=str(exc)) from exc
    if not isinstance(data, dict):
        raise ValidationError("请求 JSON 必须是对象", details=str(path))
    return data


def _scan_config_from_json(data: dict[str, Any]) -> ScanConfig:
    """Convert one JSON scan request into a core dataclass."""
    return ScanConfig(
        site_folder=_path_field(data, "siteFolder"),
        output_dir=_optional_path_field(data, "outputDir"),
        supported_formats=_tuple_field(
            data, "supportedFormats", (".jpg", ".jpeg", ".png", ".bmp")
        ),
        validate_existing_xml=_bool_field(data, "validateExistingXml", True),
    )


def _path_field(data: dict[str, Any], name: str) -> Path:
    """Read a required path field."""
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise ValidationError("请求字段必须是非空字符串", details=name)
    return Path(value)


def _optional_path_field(data: dict[str, Any], name: str) -> Path | None:
    """Read an optional path field."""
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValidationError("请求字段必须是非空字符串", details=name)
    return Path(value)


def _tuple_field(
    data: dict[str, Any], name: str, default: tuple[str, ...]
) -> tuple[str, ...]:
    """Read an optional string-list field."""
    value = data.get(name)
    if value is None:
        return default
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError("请求字段必须是字符串数组", details=name)
    return tuple(value)


def _bool_field(data: dict[str, Any], name: str, default: bool) -> bool:
    """Read an optional boolean field."""
    value = data.get(name)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValidationError("请求字段必须是布尔值", details=name)
    return value


def _scan_outcome(outcome: ScanServiceOutcome) -> dict[str, Any]:
    """Convert a scan service outcome to a JSON-compatible payload."""
    return {
        "success": outcome.success,
        "task": _task(outcome.task),
        "result": None if outcome.result is None else _scan_result(outcome),
        "error": None if outcome.error is None else _error(outcome.error),
    }


def _scan_result(outcome: ScanServiceOutcome) -> dict[str, Any]:
    """Convert a successful scan outcome to the public CLI JSON shape."""
    if outcome.result is None:
        return {}
    result = outcome.result
    return {
        "mappingPath": result.mapping_path.as_posix(),
        "classesPath": result.classes_path.as_posix(),
        "statistics": {
            "totalImages": result.statistics.total_images,
            "totalCodes": result.statistics.total_codes,
            "totalProducts": result.statistics.total_products,
        },
        "classes": result.classes,
        "products": result.products,
    }


def _task(task: TaskHandle) -> dict[str, Any]:
    """Convert public task fields to JSON."""
    return {
        "taskId": task.task_id,
        "taskType": task.task_type,
        "status": task.status,
        "progressCurrent": task.progress_current,
        "progressTotal": task.progress_total,
        "progressMessage": task.progress_message,
        "createdAt": task.created_at,
        "startedAt": task.started_at,
        "finishedAt": task.finished_at,
    }


def _error(error: AutoLabelerError) -> dict[str, Any]:
    """Convert a business error to JSON."""
    return _error_info(error.to_error_info())


def _error_info(error: ErrorInfo) -> dict[str, Any]:
    """Convert serializable error info to JSON."""
    return {
        "code": error.code,
        "message": error.message,
        "details": error.details,
        "retryable": error.retryable,
    }


def _write_json(payload: dict[str, Any]) -> None:
    """Write one JSON object to stdout."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
