"""HTTP routes for LabelImg integration."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas.labelimg import (
    LabelImgLaunchRequest,
    LabelImgLaunchResponse,
    LabelImgLaunchResultResponse,
    LabelImgValidateRequest,
    LabelImgValidateResponse,
    LabelImgValidateResultResponse,
)
from api.services.common import task_response
from api.services.labelimg_service import launch_labelimg, validate_labelimg
from core.labelimg_launcher import LabelImgConfig, LabelImgLaunchResult, LabelImgLauncher, LabelImgValidateConfig, LabelImgValidateResult
from utils.task_registry import TaskRegistry

router = APIRouter(prefix="/api/labelimg", tags=["labelimg"])


@router.post("/validate", response_model=LabelImgValidateResponse)
def validate_environment(payload: LabelImgValidateRequest, request: Request) -> LabelImgValidateResponse:
    """Validate a LabelImg Python environment via HTTP."""
    outcome = validate_labelimg(
        LabelImgValidateConfig(python_path=payload.python_path),
        _registry(request),
        _launcher(request),
    )
    if outcome.error is not None:
        raise outcome.error
    if not isinstance(outcome.result, LabelImgValidateResult):
        raise RuntimeError("labelimg validation outcome missing result")
    return LabelImgValidateResponse(
        success=True,
        task=task_response(outcome.task),
        result=_validate_response(outcome.result),
    )


@router.post("/launch", response_model=LabelImgLaunchResponse)
def launch_labeling_tool(payload: LabelImgLaunchRequest, request: Request) -> LabelImgLaunchResponse:
    """Launch LabelImg via HTTP."""
    outcome = launch_labelimg(
        LabelImgConfig(
            python_path=payload.python_path,
            image_dir=payload.image_dir,
            label_dir=payload.label_dir,
            classes_file=payload.classes_file,
        ),
        _registry(request),
        _launcher(request),
    )
    if outcome.error is not None:
        raise outcome.error
    if not isinstance(outcome.result, LabelImgLaunchResult):
        raise RuntimeError("labelimg launch outcome missing result")
    return LabelImgLaunchResponse(
        success=True,
        task=task_response(outcome.task),
        result=_launch_response(outcome.result),
    )


def _registry(request: Request) -> TaskRegistry:
    """Return shared registry from application state."""
    return request.app.state.task_registry


def _launcher(request: Request) -> LabelImgLauncher | None:
    """Return optional injected LabelImg launcher from application state."""
    launcher = getattr(request.app.state, "labelimg_launcher", None)
    return launcher if isinstance(launcher, LabelImgLauncher) else launcher


def _validate_response(result: LabelImgValidateResult) -> LabelImgValidateResultResponse:
    """Convert validation result to response schema."""
    return LabelImgValidateResultResponse(
        is_valid=result.is_valid,
        labelimg_version=result.labelimg_version,
        python_version=result.python_version,
        error_message=result.error_message,
    )


def _launch_response(result: LabelImgLaunchResult) -> LabelImgLaunchResultResponse:
    """Convert launch result to response schema."""
    return LabelImgLaunchResultResponse(process_id=result.process_id, command=result.command)
