"""Label inspector API schemas."""

from __future__ import annotations

from pathlib import Path

from api.schemas.base import CamelModel
from api.schemas.common import TaskResponse


class ListRunsRequest(CamelModel):
    """HTTP request body for listing inference runs."""

    site_folder: Path


class GetRunTreeRequest(CamelModel):
    """HTTP request body for reading an inference run tree."""

    site_folder: Path
    run_id: str


class GetProductLabelsRequest(CamelModel):
    """HTTP request body for reading labels in one product folder."""

    site_folder: Path
    run_id: str
    code: str
    product: str


class InferenceRunResponse(CamelModel):
    """Serializable inference run metadata."""

    run_id: str
    path: str
    config_exists: bool
    config: dict[str, object] | None
    created_at: str


class ListRunsResultResponse(CamelModel):
    """Serializable list-runs result."""

    runs: list[InferenceRunResponse]


class RunTreeNodeResponse(CamelModel):
    """Serializable Code/Product run tree node."""

    code: str
    product: str
    label_count: int
    empty_count: int
    path: str


class RunTreeResultResponse(CamelModel):
    """Serializable run-tree result."""

    nodes: list[RunTreeNodeResponse]


class ProductLabelResponse(CamelModel):
    """Serializable product label row."""

    image_name: str
    image_path: str | None
    label_path: str
    object_count: int


class ProductLabelsResultResponse(CamelModel):
    """Serializable product-labels result."""

    labels: list[ProductLabelResponse]


class ListRunsResponse(CamelModel):
    """Successful list-runs response."""

    success: bool
    task: TaskResponse
    result: ListRunsResultResponse


class RunTreeResponse(CamelModel):
    """Successful run-tree response."""

    success: bool
    task: TaskResponse
    result: RunTreeResultResponse


class ProductLabelsResponse(CamelModel):
    """Successful product-labels response."""

    success: bool
    task: TaskResponse
    result: ProductLabelsResultResponse
