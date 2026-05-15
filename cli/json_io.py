"""JSON helpers shared by CLI command adapters."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from utils.exceptions import AutoLabelerError, ErrorInfo, ValidationError
from utils.task_registry import TaskHandle


def read_json_object(path: Path) -> dict[str, Any]:
    """Read a JSON object from disk."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValidationError("请求 JSON 无法读取", details=str(exc)) from exc
    if not isinstance(data, dict):
        raise ValidationError("请求 JSON 必须是对象", details=str(path))
    return data


def write_json(payload: dict[str, Any]) -> None:
    """Write one JSON object to stdout."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def path_field(data: dict[str, Any], name: str) -> Path:
    """Read a required path field."""
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise ValidationError("请求字段必须是非空字符串", details=name)
    return Path(value)


def optional_path_field(data: dict[str, Any], name: str) -> Path | None:
    """Read an optional path field."""
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValidationError("请求字段必须是非空字符串", details=name)
    return Path(value)


def tuple_field(
    data: dict[str, Any], name: str, default: tuple[str, ...]
) -> tuple[str, ...]:
    """Read an optional string-list field."""
    value = data.get(name)
    if value is None:
        return default
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError("请求字段必须是字符串数组", details=name)
    return tuple(value)


def bool_field(data: dict[str, Any], name: str, default: bool) -> bool:
    """Read an optional boolean field."""
    value = data.get(name)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValidationError("请求字段必须是布尔值", details=name)
    return value


def task_payload(task: TaskHandle) -> dict[str, Any]:
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


def error_payload(error: AutoLabelerError) -> dict[str, Any]:
    """Convert a business error to JSON."""
    return error_info_payload(error.to_error_info())


def error_info_payload(error: ErrorInfo) -> dict[str, Any]:
    """Convert serializable error info to JSON."""
    return {
        "code": error.code,
        "message": error.message,
        "details": error.details,
        "retryable": error.retryable,
    }
