"""Train API schemas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from api.schemas.base import CamelModel
from api.schemas.common import TaskResponse


class TrainRequest(CamelModel):
    """HTTP request body for YOLO training."""

    data_yaml: Path
    base_model: Path
    output_dir: Path
    epochs: int = 100
    batch_size: int = -1
    image_size: int = 640
    device: str = "auto"
    patience: int = 50
    workers: int = 8
    optimizer: str = "AdamW"
    lr0: float = 0.01
    box: float = 7.5
    cls: float = 0.5
    dfl: float = 1.5
    scale: float = 0.5
    cache: str | bool = "ram"


class TrainMetricsResponse(CamelModel):
    """Serializable training metrics."""

    best_epoch: int
    best_map50: float
    best_map50_95: float
    final_map50: float
    final_map50_95: float


class TrainResultResponse(CamelModel):
    """Serializable training result."""

    best_model: str
    last_model: str | None
    output_dir: str
    effective_config: dict[str, Any]
    metrics: TrainMetricsResponse


class TrainResponse(CamelModel):
    """Successful train response."""

    success: bool
    task: TaskResponse
    result: TrainResultResponse
