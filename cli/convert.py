"""JSON CLI adapters for annotation conversion."""

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
from core.converter import ConvertFileIssue, TxtToXmlConfig, XmlToTxtConfig
from runtime.services.convert_service import (
    TxtToXmlServiceOutcome,
    XmlToTxtServiceOutcome,
    run_txt_to_xml,
    run_xml_to_txt,
)
from utils.exceptions import AutoLabelerError, ValidationError
from utils.task_registry import TaskRegistry


def run_txt_to_xml_command(request_path: Path) -> int:
    """Read a TXT-to-XML request and write one JSON response."""
    try:
        request = read_json_object(request_path)
        config = txt_to_xml_config_from_json(request)
        registry = TaskRegistry(path_field(request, "taskDir"))
        outcome = run_txt_to_xml(config, registry)
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

    write_json(txt_to_xml_outcome_payload(outcome))
    return 0 if outcome.success else 1


def run_xml_to_txt_command(request_path: Path) -> int:
    """Read an XML-to-TXT request and write one JSON response."""
    try:
        request = read_json_object(request_path)
        config = xml_to_txt_config_from_json(request)
        registry = TaskRegistry(path_field(request, "taskDir"))
        outcome = run_xml_to_txt(config, registry)
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

    write_json(xml_to_txt_outcome_payload(outcome))
    return 0 if outcome.success else 1


def txt_to_xml_config_from_json(data: dict[str, Any]) -> TxtToXmlConfig:
    """Convert one JSON TXT-to-XML request into a core dataclass."""
    return TxtToXmlConfig(
        folder=path_field(data, "folder"),
        recursive=bool_field(data, "recursive", True),
        classes=_optional_string_list(data, "classes"),
        delete_source=bool_field(data, "deleteSource", False),
        backup_dir=_optional_path_field(data, "backupDir"),
    )


def xml_to_txt_config_from_json(data: dict[str, Any]) -> XmlToTxtConfig:
    """Convert one JSON XML-to-TXT request into a core dataclass."""
    return XmlToTxtConfig(
        xml_path=path_field(data, "xmlPath"),
        classes=_string_list(data, "classes"),
        output_path=path_field(data, "outputPath"),
    )


def txt_to_xml_outcome_payload(outcome: TxtToXmlServiceOutcome) -> dict[str, Any]:
    """Convert a TXT-to-XML service outcome to public CLI JSON."""
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


def xml_to_txt_outcome_payload(outcome: XmlToTxtServiceOutcome) -> dict[str, Any]:
    """Convert an XML-to-TXT service outcome to public CLI JSON."""
    result = None
    if outcome.output_path is not None:
        result = {"outputPath": outcome.output_path.as_posix()}
    return {
        "success": outcome.success,
        "task": task_payload(outcome.task),
        "result": result,
        "error": None if outcome.error is None else error_payload(outcome.error),
    }


def _file_issue_payload(issue: ConvertFileIssue) -> dict[str, Any]:
    """Convert one per-file conversion issue to public CLI JSON."""
    return {
        "path": issue.path.as_posix(),
        "code": issue.code.value,
        "message": issue.message,
        "details": issue.details,
    }


def _optional_path_field(data: dict[str, Any], name: str) -> Path | None:
    """Read an optional path field."""
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValidationError("request field must be a non-empty string", details=name)
    return Path(value)


def _optional_string_list(data: dict[str, Any], name: str) -> list[str] | None:
    """Read an optional list of strings."""
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError("request field must be a string array", details=name)
    return list(value)


def _string_list(data: dict[str, Any], name: str) -> list[str]:
    """Read a required list of strings."""
    value = data.get(name)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError("request field must be a string array", details=name)
    return list(value)
