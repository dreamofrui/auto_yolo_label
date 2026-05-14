"""HTTP route for site scanning."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas.scan import (
    ScanRequest,
    ScanResponse,
    ScanResultResponse,
    ScanStatisticsResponse,
    TaskResponse,
)
from api.services.scan_service import run_scan
from core.scanner import ScanConfig, ScanResult
from utils.task_registry import TaskHandle, TaskRegistry

router = APIRouter(prefix="/api", tags=["scan"])


@router.post("/scan", response_model=ScanResponse)
def scan_site(payload: ScanRequest, request: Request) -> ScanResponse:
    """Scan a site folder via HTTP."""
    registry = _registry(request)
    outcome = run_scan(
        ScanConfig(
            site_folder=payload.site_folder,
            output_dir=payload.output_dir,
            validate_existing_xml=payload.validate_existing_xml,
        ),
        registry,
    )
    if outcome.error is not None:
        raise outcome.error
    if outcome.result is None:
        raise RuntimeError("scan outcome missing result")
    return ScanResponse(
        success=True,
        task=_task_response(outcome.task),
        result=_scan_response(outcome.result),
    )


def _registry(request: Request) -> TaskRegistry:
    """Return shared registry from application state."""
    return request.app.state.task_registry


def _task_response(task: TaskHandle) -> TaskResponse:
    """Convert TaskHandle to response schema."""
    return TaskResponse(
        task_id=task.task_id,
        task_type=task.task_type,
        status=task.status,
        progress_current=task.progress_current,
        progress_total=task.progress_total,
        progress_message=task.progress_message,
    )


def _scan_response(result: ScanResult) -> ScanResultResponse:
    """Convert ScanResult to response schema."""
    return ScanResultResponse(
        mapping_path=str(result.mapping_path),
        classes_path=str(result.classes_path),
        statistics=ScanStatisticsResponse(
            total_images=result.statistics.total_images,
            total_codes=result.statistics.total_codes,
            total_products=result.statistics.total_products,
        ),
        classes=result.classes,
        products=result.products,
    )
