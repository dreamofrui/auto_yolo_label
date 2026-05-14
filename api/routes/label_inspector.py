"""HTTP routes for inference label inspection."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas.label_inspector import (
    GetProductLabelsRequest,
    GetRunTreeRequest,
    InferenceRunResponse,
    ListRunsRequest,
    ListRunsResponse,
    ListRunsResultResponse,
    ProductLabelResponse,
    ProductLabelsResponse,
    ProductLabelsResultResponse,
    RunTreeNodeResponse,
    RunTreeResponse,
    RunTreeResultResponse,
)
from api.services.common import task_response
from api.services.label_inspector_service import get_product_labels, get_run_tree, list_runs
from core.label_inspector import (
    GetProductLabelsConfig,
    GetRunTreeConfig,
    InferenceRun,
    ListRunsConfig,
    ProductLabel,
    RunTreeNode,
)
from utils.task_registry import TaskRegistry

router = APIRouter(prefix="/api/label-inspector", tags=["label-inspector"])


@router.post("/runs", response_model=ListRunsResponse)
def list_inference_runs(payload: ListRunsRequest, request: Request) -> ListRunsResponse:
    """List inference runs via HTTP."""
    outcome = list_runs(ListRunsConfig(site_folder=payload.site_folder), _registry(request))
    if outcome.error is not None:
        raise outcome.error
    if outcome.result is None:
        raise RuntimeError("label inspector outcome missing result")
    runs = [item for item in outcome.result if isinstance(item, InferenceRun)]
    return ListRunsResponse(
        success=True,
        task=task_response(outcome.task),
        result=ListRunsResultResponse(runs=[_run_response(item) for item in runs]),
    )


@router.post("/run-tree", response_model=RunTreeResponse)
def read_run_tree(payload: GetRunTreeRequest, request: Request) -> RunTreeResponse:
    """Read one inference run tree via HTTP."""
    outcome = get_run_tree(
        GetRunTreeConfig(site_folder=payload.site_folder, run_id=payload.run_id),
        _registry(request),
    )
    if outcome.error is not None:
        raise outcome.error
    if outcome.result is None:
        raise RuntimeError("label inspector outcome missing result")
    nodes = [item for item in outcome.result if isinstance(item, RunTreeNode)]
    return RunTreeResponse(
        success=True,
        task=task_response(outcome.task),
        result=RunTreeResultResponse(nodes=[_node_response(item) for item in nodes]),
    )


@router.post("/product-labels", response_model=ProductLabelsResponse)
def read_product_labels(payload: GetProductLabelsRequest, request: Request) -> ProductLabelsResponse:
    """Read labels for one Code/Product directory via HTTP."""
    outcome = get_product_labels(
        GetProductLabelsConfig(
            site_folder=payload.site_folder,
            run_id=payload.run_id,
            code=payload.code,
            product=payload.product,
        ),
        _registry(request),
    )
    if outcome.error is not None:
        raise outcome.error
    if outcome.result is None:
        raise RuntimeError("label inspector outcome missing result")
    labels = [item for item in outcome.result if isinstance(item, ProductLabel)]
    return ProductLabelsResponse(
        success=True,
        task=task_response(outcome.task),
        result=ProductLabelsResultResponse(labels=[_label_response(item) for item in labels]),
    )


def _registry(request: Request) -> TaskRegistry:
    """Return shared registry from application state."""
    return request.app.state.task_registry


def _run_response(result: InferenceRun) -> InferenceRunResponse:
    """Convert an inference run to response schema."""
    return InferenceRunResponse(
        run_id=result.run_id,
        path=str(result.path),
        config_exists=result.config_exists,
        config=result.config,
        created_at=result.created_at,
    )


def _node_response(result: RunTreeNode) -> RunTreeNodeResponse:
    """Convert a run tree node to response schema."""
    return RunTreeNodeResponse(
        code=result.code,
        product=result.product,
        label_count=result.label_count,
        empty_count=result.empty_count,
        path=str(result.path),
    )


def _label_response(result: ProductLabel) -> ProductLabelResponse:
    """Convert a product label to response schema."""
    return ProductLabelResponse(
        image_name=result.image_name,
        image_path=None if result.image_path is None else str(result.image_path),
        label_path=str(result.label_path),
        object_count=result.object_count,
    )
