"""Shared convert service for desktop and future CLI adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.converter import ConvertResult, Converter, TxtToXmlConfig, XmlToTxtConfig
from runtime.services.common import finish_error_task
from utils.exceptions import AutoLabelerError
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class TxtToXmlServiceOutcome:
    """Result of a TXT to XML adapter call."""

    success: bool
    task: TaskHandle
    result: ConvertResult | None
    error: AutoLabelerError | None


@dataclass(frozen=True)
class XmlToTxtServiceOutcome:
    """Result of an XML to TXT adapter call."""

    success: bool
    task: TaskHandle
    output_path: Path | None
    error: AutoLabelerError | None


def run_txt_to_xml(
    config: TxtToXmlConfig, registry: TaskRegistry
) -> TxtToXmlServiceOutcome:
    """Run Converter.txt_to_xml with TaskRegistry lifecycle handling."""
    task = registry.create_task("convert")
    registry.start_task(task.task_id, message="准备转换")
    try:
        result = Converter(task_handle=task).txt_to_xml(config)
    except AutoLabelerError as exc:
        finish_error_task(registry, task, exc)
        return TxtToXmlServiceOutcome(success=False, task=task, result=None, error=exc)
    registry.succeed_task(task.task_id, result=_txt_to_xml_result_dict(result))
    return TxtToXmlServiceOutcome(success=True, task=task, result=result, error=None)


def run_xml_to_txt(
    config: XmlToTxtConfig, registry: TaskRegistry
) -> XmlToTxtServiceOutcome:
    """Run Converter.xml_to_txt with TaskRegistry lifecycle handling."""
    task = registry.create_task("convert")
    registry.start_task(task.task_id, total=1, message="准备转换")
    try:
        output_path = Converter(task_handle=task).xml_to_txt(config)
    except AutoLabelerError as exc:
        finish_error_task(registry, task, exc)
        return XmlToTxtServiceOutcome(
            success=False, task=task, output_path=None, error=exc
        )
    registry.succeed_task(task.task_id, result={"output_path": str(output_path)})
    return XmlToTxtServiceOutcome(
        success=True, task=task, output_path=output_path, error=None
    )


def _txt_to_xml_result_dict(result: ConvertResult) -> dict[str, Any]:
    """Convert ConvertResult to a JSON-compatible dict for task storage."""
    return {
        "total": result.total,
        "success": result.success,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": [
            {
                "path": str(error.path),
                "code": error.code.value,
                "message": error.message,
                "details": error.details,
            }
            for error in result.errors
        ],
    }
