"""Sample API schemas."""

from __future__ import annotations

from pathlib import Path

from api.schemas.base import CamelModel
from api.schemas.common import TaskResponse


class SampleRequest(CamelModel):
    """HTTP request body for sampling a scanned site."""

    site_folder: Path
    output_dir: Path
    mode: str = "count"
    count: int = 40
    ratio: float = 0.3
    min_count: int = 20
    max_count: int = 50
    full_threshold: int = 35
    train_ratio: float = 0.9
    pre_labeled_priority: bool = True


class SamplePathsResponse(CamelModel):
    """Serializable sample output paths."""

    images_train: str
    images_val: str
    labels_train: str
    labels_val: str


class SampleStatisticsResponse(CamelModel):
    """Serializable sample statistics."""

    total_products: int
    sampled_count: int
    train_count: int
    val_count: int
    pre_labeled_count: int


class SampleResultResponse(CamelModel):
    """Serializable sample result."""

    mapping_path: str
    dataset_dir: str
    data_yaml: str
    paths: SamplePathsResponse
    statistics: SampleStatisticsResponse


class SampleResponse(CamelModel):
    """Successful sample response."""

    success: bool
    task: TaskResponse
    result: SampleResultResponse
