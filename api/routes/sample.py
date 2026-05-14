"""HTTP route for dataset sampling."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas.sample import (
    SamplePathsResponse,
    SampleRequest,
    SampleResponse,
    SampleResultResponse,
    SampleStatisticsResponse,
)
from api.services.common import task_response
from api.services.sample_service import run_sample
from core.sampler import SampleConfig, SampleResult
from utils.task_registry import TaskRegistry

router = APIRouter(prefix="/api", tags=["sample"])


@router.post("/sample", response_model=SampleResponse)
def sample_site(payload: SampleRequest, request: Request) -> SampleResponse:
    """Sample a scanned site via HTTP."""
    outcome = run_sample(
        SampleConfig(
            site_folder=payload.site_folder,
            output_dir=payload.output_dir,
            mode=payload.mode,
            count=payload.count,
            ratio=payload.ratio,
            min_count=payload.min_count,
            max_count=payload.max_count,
            full_threshold=payload.full_threshold,
            train_ratio=payload.train_ratio,
            pre_labeled_priority=payload.pre_labeled_priority,
        ),
        _registry(request),
    )
    if outcome.error is not None:
        raise outcome.error
    if outcome.result is None:
        raise RuntimeError("sample outcome missing result")
    return SampleResponse(
        success=True,
        task=task_response(outcome.task),
        result=_sample_response(outcome.result),
    )


def _registry(request: Request) -> TaskRegistry:
    """Return shared registry from application state."""
    return request.app.state.task_registry


def _sample_response(result: SampleResult) -> SampleResultResponse:
    """Convert SampleResult to response schema."""
    return SampleResultResponse(
        mapping_path=str(result.mapping_path),
        dataset_dir=str(result.dataset_dir),
        data_yaml=str(result.data_yaml),
        paths=SamplePathsResponse(
            images_train=str(result.paths.images_train),
            images_val=str(result.paths.images_val),
            labels_train=str(result.paths.labels_train),
            labels_val=str(result.paths.labels_val),
        ),
        statistics=SampleStatisticsResponse(
            total_products=result.statistics.total_products,
            sampled_count=result.statistics.sampled_count,
            train_count=result.statistics.train_count,
            val_count=result.statistics.val_count,
            pre_labeled_count=result.statistics.pre_labeled_count,
        ),
    )
