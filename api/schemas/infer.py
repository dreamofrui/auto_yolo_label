"""Infer API schemas."""

from __future__ import annotations

from pathlib import Path

from api.schemas.base import CamelModel
from api.schemas.common import TaskResponse


class InferRequest(CamelModel):
    """HTTP request body for YOLO inference."""

    model_path: Path
    site_folder: Path
    output_base_dir: Path | None = None
    confidence: float = 0.25
    iou: float = 0.7
    batch_size: int = -1
    device: str = "auto"
    save_to_separate_dir: bool = True
    image_source: str = "unsampled"
    custom_images: list[Path] | None = None


class InferStatisticsResponse(CamelModel):
    """Serializable inference statistics."""

    pending: int
    processed: int
    success: int
    failed: int
    predicted: int
    empty_prediction: int


class InferResultResponse(CamelModel):
    """Serializable inference result."""

    mapping_path: str
    run_id: str
    inference_output_dir: str
    config_path: str
    statistics: InferStatisticsResponse


class InferResponse(CamelModel):
    """Successful infer response."""

    success: bool
    task: TaskResponse
    result: InferResultResponse
