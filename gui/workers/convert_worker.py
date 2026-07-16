"""Desktop convert worker adapter."""

from __future__ import annotations

from dataclasses import dataclass

from core.converter import (
    Converter,
    ConvertResult,
    TxtToXmlConfig,
    XmlDatasetAnalysis,
    XmlDatasetAnalyzeConfig,
    XmlDatasetConvertConfig,
    XmlDatasetConvertResult,
    XmlToTxtConfig,
)
from gui.workers._task_lifecycle import (
    default_task_registry,
    finish_worker_error,
    finish_worker_success,
    start_worker_task,
)
from utils.exceptions import AutoLabelerError, ErrorInfo
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


@dataclass(frozen=True)
class XmlDatasetAnalyzeWorkerOutcome:
    """Desktop XML dataset analysis worker outcome."""

    success: bool
    task: TaskHandle
    analysis: XmlDatasetAnalysis | None
    error: ErrorInfo | None


@dataclass(frozen=True)
class XmlDatasetConvertWorkerOutcome:
    """Desktop XML dataset conversion worker outcome."""

    success: bool
    task: TaskHandle
    result: XmlDatasetConvertResult | None
    error: ErrorInfo | None


class ConvertWorker:
    """Thin desktop adapter for Converter operations."""

    def __init__(self, registry: TaskRegistry | None = None) -> None:
        """Create a convert worker with an optional shared registry."""
        self._registry = registry or default_task_registry()

    def run_txt_to_xml(self, config: TxtToXmlConfig) -> TxtToXmlWorkerOutcome:
        """Run TXT to XML conversion and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "convert", "准备 TXT 转 XML")
        try:
            result = Converter(task_handle=task).txt_to_xml(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return TxtToXmlWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, result)
        return TxtToXmlWorkerOutcome(True, task, result, None)

    def run_xml_to_txt(self, config: XmlToTxtConfig) -> XmlToTxtWorkerOutcome:
        """Run XML to TXT conversion and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "convert", "准备 XML 转 TXT")
        try:
            output_path = Converter(task_handle=task).xml_to_txt(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return XmlToTxtWorkerOutcome(False, task, None, error)
        finish_worker_success(
            self._registry, task, output_path, {"output_path": str(output_path)}
        )
        return XmlToTxtWorkerOutcome(True, task, output_path, None)

    def analyze_xml_dataset(
        self, config: XmlDatasetAnalyzeConfig
    ) -> XmlDatasetAnalyzeWorkerOutcome:
        """Analyze XML dataset conversion and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "convert", "分析 XML 数据集")
        try:
            analysis = Converter(task_handle=task).analyze_xml_dataset(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return XmlDatasetAnalyzeWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, analysis)
        return XmlDatasetAnalyzeWorkerOutcome(True, task, analysis, None)

    def convert_xml_dataset(
        self, config: XmlDatasetConvertConfig
    ) -> XmlDatasetConvertWorkerOutcome:
        """Run XML dataset conversion and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "convert", "准备 XML 数据集转换")
        try:
            result = Converter(task_handle=task).convert_xml_dataset(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return XmlDatasetConvertWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, result)
        return XmlDatasetConvertWorkerOutcome(True, task, result, None)
