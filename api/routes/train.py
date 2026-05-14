"""HTTP route for YOLO training."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas.train import (
    TrainMetricsResponse,
    TrainRequest,
    TrainResponse,
    TrainResultResponse,
)
from api.services.common import task_response
from api.services.train_service import run_train
from core.trainer import TrainConfig, TrainResult
from utils.task_registry import TaskRegistry

router = APIRouter(prefix="/api", tags=["train"])


@router.post("/train", response_model=TrainResponse)
def train_model(payload: TrainRequest, request: Request) -> TrainResponse:
    """Train a YOLO model via HTTP."""
    outcome = run_train(
        TrainConfig(
            data_yaml=payload.data_yaml,
            base_model=payload.base_model,
            output_dir=payload.output_dir,
            epochs=payload.epochs,
            batch_size=payload.batch_size,
            image_size=payload.image_size,
            device=payload.device,
            patience=payload.patience,
            workers=payload.workers,
            optimizer=payload.optimizer,
            lr0=payload.lr0,
            box=payload.box,
            cls=payload.cls,
            dfl=payload.dfl,
            scale=payload.scale,
            cache=payload.cache,
        ),
        _registry(request),
    )
    if outcome.error is not None:
        raise outcome.error
    if outcome.result is None:
        raise RuntimeError("train outcome missing result")
    return TrainResponse(
        success=True,
        task=task_response(outcome.task),
        result=_train_response(outcome.result),
    )


def _registry(request: Request) -> TaskRegistry:
    """Return shared registry from application state."""
    return request.app.state.task_registry


def _train_response(result: TrainResult) -> TrainResultResponse:
    """Convert TrainResult to response schema."""
    return TrainResultResponse(
        best_model=str(result.best_model),
        last_model=None if result.last_model is None else str(result.last_model),
        output_dir=str(result.output_dir),
        effective_config=result.effective_config,
        metrics=TrainMetricsResponse(
            best_epoch=result.metrics.best_epoch,
            best_map50=result.metrics.best_map50,
            best_map50_95=result.metrics.best_map50_95,
            final_map50=result.metrics.final_map50,
            final_map50_95=result.metrics.final_map50_95,
        ),
    )
