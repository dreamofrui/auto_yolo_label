"""HTTP route for site scanning."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas.scan import (
    ScanRequest,
    ScanResponse,
    ScanResultResponse,
    ScanStatisticsResponse,
)
from api.services.common import task_response
from api.services.scan_service import run_scan
from core.scanner import ScanConfig, ScanResult
from utils.task_registry import TaskRegistry

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
        task=task_response(outcome.task),
        result=_scan_response(outcome.result),
    )


def _registry(request: Request) -> TaskRegistry:
    """Return shared registry from application state."""
    return request.app.state.task_registry


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
