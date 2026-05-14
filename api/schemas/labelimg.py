"""LabelImg API schemas."""

from __future__ import annotations

from pathlib import Path

from api.schemas.base import CamelModel
from api.schemas.common import TaskResponse


class LabelImgValidateRequest(CamelModel):
    """HTTP request body for LabelImg environment validation."""

    python_path: Path


class LabelImgLaunchRequest(CamelModel):
    """HTTP request body for launching LabelImg."""

    python_path: Path
    image_dir: Path
    label_dir: Path | None = None
    classes_file: Path | None = None


class LabelImgValidateResultResponse(CamelModel):
    """Serializable LabelImg validation result."""

    is_valid: bool
    labelimg_version: str | None
    python_version: str
    error_message: str | None


class LabelImgLaunchResultResponse(CamelModel):
    """Serializable LabelImg launch result."""

    process_id: int
    command: str


class LabelImgValidateResponse(CamelModel):
    """Successful LabelImg validation response."""

    success: bool
    task: TaskResponse
    result: LabelImgValidateResultResponse


class LabelImgLaunchResponse(CamelModel):
    """Successful LabelImg launch response."""

    success: bool
    task: TaskResponse
    result: LabelImgLaunchResultResponse
