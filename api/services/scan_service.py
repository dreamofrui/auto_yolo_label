"""Shared scan service for desktop and HTTP adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.scanner import ScanConfig, ScanResult, Scanner
from utils.exceptions import AutoLabelerError
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class ScanServiceOutcome:
    """Result of a scan adapter call."""

    success: bool
    task: TaskHandle
    result: ScanResult | None
    error: AutoLabelerError | None


def run_scan(config: ScanConfig, registry: TaskRegistry) -> ScanServiceOutcome:
    """Run Scanner.scan with TaskRegistry lifecycle handling.

    Args:
        config: Core scan configuration.
        registry: Shared task registry.

    Returns:
        A service outcome for API and desktop callers.
    """
    task = registry.create_task("scan")
    registry.start_task(task.task_id, message="准备扫描")
    try:
        result = Scanner(task_handle=task).scan(config)
    except AutoLabelerError as exc:
        registry.fail_task(
            task.task_id,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            retryable=exc.retryable,
        )
        return ScanServiceOutcome(success=False, task=task, result=None, error=exc)
    registry.succeed_task(task.task_id, result=_scan_result_dict(result))
    return ScanServiceOutcome(success=True, task=task, result=result, error=None)


def _scan_result_dict(result: ScanResult) -> dict[str, Any]:
    """Convert ScanResult to a JSON-compatible dict for task storage."""
    return {
        "mapping_path": str(result.mapping_path),
        "classes_path": str(result.classes_path),
        "statistics": {
            "total_images": result.statistics.total_images,
            "total_codes": result.statistics.total_codes,
            "total_products": result.statistics.total_products,
        },
        "classes": result.classes,
        "products": result.products,
    }
