"""Desktop convert worker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from api.services.convert_service import run_txt_to_xml, run_xml_to_txt
from core.converter import ConvertResult, TxtToXmlConfig, XmlToTxtConfig
from utils.exceptions import ErrorInfo
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class TxtToXmlWorkerOutcome:
    """Desktop TXT to XML worker outcome."""

    success: bool
    task: TaskHandle
    result: ConvertResult | None
    error: ErrorInfo | None


@dataclass(frozen=True)
class XmlToTxtWorkerOutcome:
    """Desktop XML to TXT worker outcome."""

    success: bool
    task: TaskHandle
    output_path: Path | None
    error: ErrorInfo | None


class ConvertWorker:
    """Thin desktop adapter for Converter operations."""

    def __init__(self, registry: TaskRegistry | None = None) -> None:
        """Create a convert worker with an optional shared registry."""
        self._registry = registry or TaskRegistry(
            Path.home() / ".autolabeler" / "tasks"
        )

    def run_txt_to_xml(self, config: TxtToXmlConfig) -> TxtToXmlWorkerOutcome:
        """Run TXT to XML conversion and return a desktop-friendly outcome."""
        outcome = run_txt_to_xml(config, self._registry)
        return TxtToXmlWorkerOutcome(
            success=outcome.success,
            task=outcome.task,
            result=outcome.result,
            error=None if outcome.error is None else outcome.error.to_error_info(),
        )

    def run_xml_to_txt(self, config: XmlToTxtConfig) -> XmlToTxtWorkerOutcome:
        """Run XML to TXT conversion and return a desktop-friendly outcome."""
        outcome = run_xml_to_txt(config, self._registry)
        return XmlToTxtWorkerOutcome(
            success=outcome.success,
            task=outcome.task,
            output_path=outcome.output_path,
            error=None if outcome.error is None else outcome.error.to_error_info(),
        )
