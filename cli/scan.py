"""JSON CLI adapter for site scanning."""

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
    tuple_field,
    write_json,
)
from core.scanner import ScanConfig
from runtime.services.scan_service import ScanServiceOutcome, run_scan
from utils.exceptions import AutoLabelerError
from utils.task_registry import TaskRegistry


def run_scan_command(request_path: Path) -> int:
    """Read a scan request, execute it, and write one JSON response."""
    try:
        request = read_json_object(request_path)
        config = scan_config_from_json(request)
        registry = TaskRegistry(path_field(request, "taskDir"))
        outcome = run_scan(config, registry)
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

    write_json(scan_outcome_payload(outcome))
    return 0 if outcome.success else 1


def scan_config_from_json(data: dict[str, Any]) -> ScanConfig:
    """Convert one JSON scan request into a core dataclass."""
    return ScanConfig(
        site_folder=path_field(data, "siteFolder"),
        output_dir=optional_path_field(data, "outputDir"),
        supported_formats=tuple_field(
            data, "supportedFormats", (".jpg", ".jpeg", ".png", ".bmp")
        ),
        validate_existing_xml=bool_field(data, "validateExistingXml", True),
    )


def scan_outcome_payload(outcome: ScanServiceOutcome) -> dict[str, Any]:
    """Convert a scan service outcome to a JSON-compatible payload."""
    return {
        "success": outcome.success,
        "task": task_payload(outcome.task),
        "result": None if outcome.result is None else _scan_result(outcome),
        "error": None if outcome.error is None else error_payload(outcome.error),
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
