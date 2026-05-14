"""Restore API schemas."""

from __future__ import annotations

from pathlib import Path

from api.schemas.base import CamelModel
from api.schemas.common import TaskResponse


class RestoreRequest(CamelModel):
    """HTTP request body for restoring reviewed labels."""

    site_folder: Path
    source_type: str
    database_dir: Path | None = None
    inference_run_dir: Path | None = None
    run_id: str | None = None
    overwrite: bool = False


class RestoreFileErrorResponse(CamelModel):
    """Serializable per-file restore failure."""

    source_path: str
    target_path: str | None
    reason: str


class RestoreResultResponse(CamelModel):
    """Serializable restore result counters."""

    total: int
    success: int
    skipped: int
    failed: int
    errors: list[RestoreFileErrorResponse]


class RestoreResponse(CamelModel):
    """Successful restore response."""

    success: bool
    task: TaskResponse
    result: RestoreResultResponse
