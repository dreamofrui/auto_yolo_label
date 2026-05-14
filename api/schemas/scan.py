"""Scan API schemas."""

from __future__ import annotations

from pathlib import Path

from api.schemas.base import CamelModel


class ScanRequest(CamelModel):
    """HTTP request body for scanning a site."""

    site_folder: Path
    output_dir: Path | None = None
    validate_existing_xml: bool = True


class ScanStatisticsResponse(CamelModel):
    """Serializable scan statistics."""

    total_images: int
    total_codes: int
    total_products: int


class ScanResultResponse(CamelModel):
    """Serializable scan result."""

    mapping_path: str
    classes_path: str
    statistics: ScanStatisticsResponse
    classes: list[str]
    products: dict[str, dict[str, int]]


class TaskResponse(CamelModel):
    """Serializable TaskHandle subset."""

    task_id: str
    task_type: str
    status: str
    progress_current: int
    progress_total: int
    progress_message: str


class ScanResponse(CamelModel):
    """Successful scan response."""

    success: bool
    task: TaskResponse
    result: ScanResultResponse
