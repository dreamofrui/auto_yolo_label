"""HTTP route for YOLO inference."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas.infer import (
    InferRequest,
    InferResponse,
    InferResultResponse,
    InferStatisticsResponse,
)
from api.services.common import task_response
from api.services.infer_service import run_infer
from core.inferencer import InferConfig, InferResult
from utils.task_registry import TaskRegistry

router = APIRouter(prefix="/api", tags=["infer"])


@router.post("/infer", response_model=InferResponse)
def infer_site(payload: InferRequest, request: Request) -> InferResponse:
    """Run YOLO inference via HTTP."""
    outcome = run_infer(
        InferConfig(
            model_path=payload.model_path,
            site_folder=payload.site_folder,
            output_base_dir=payload.output_base_dir,
            confidence=payload.confidence,
            iou=payload.iou,
            batch_size=payload.batch_size,
            device=payload.device,
            save_to_separate_dir=payload.save_to_separate_dir,
            image_source=payload.image_source,
            custom_images=payload.custom_images,
        ),
        _registry(request),
    )
    if outcome.error is not None:
        raise outcome.error
    if outcome.result is None:
        raise RuntimeError("infer outcome missing result")
    return InferResponse(
        success=True,
        task=task_response(outcome.task),
        result=_infer_response(outcome.result),
    )


def _registry(request: Request) -> TaskRegistry:
    """Return shared registry from application state."""
    return request.app.state.task_registry


def _infer_response(result: InferResult) -> InferResultResponse:
    """Convert InferResult to response schema."""
    return InferResultResponse(
        mapping_path=str(result.mapping_path),
        run_id=result.run_id,
        inference_output_dir=str(result.inference_output_dir),
        config_path=str(result.config_path),
        statistics=InferStatisticsResponse(
            pending=result.statistics.pending,
            processed=result.statistics.processed,
            success=result.statistics.success,
            failed=result.statistics.failed,
            predicted=result.statistics.predicted,
            empty_prediction=result.statistics.empty_prediction,
        ),
    )
