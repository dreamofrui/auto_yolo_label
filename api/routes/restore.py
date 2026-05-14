"""HTTP route for restoring reviewed labels."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas.restore import (
    RestoreFileErrorResponse,
    RestoreRequest,
    RestoreResponse,
    RestoreResultResponse,
)
from api.services.common import task_response
from api.services.restore_service import run_restore
from core.restorer import RestoreConfig, RestoreResult
from utils.task_registry import TaskRegistry

router = APIRouter(prefix="/api", tags=["restore"])


@router.post("/restore", response_model=RestoreResponse)
def restore_labels(payload: RestoreRequest, request: Request) -> RestoreResponse:
    """Restore reviewed labels via HTTP."""
    outcome = run_restore(
        RestoreConfig(
            site_folder=payload.site_folder,
            source_type=payload.source_type,
            database_dir=payload.database_dir,
            inference_run_dir=payload.inference_run_dir,
            run_id=payload.run_id,
            overwrite=payload.overwrite,
        ),
        _registry(request),
    )
    if outcome.error is not None:
        raise outcome.error
    if outcome.result is None:
        raise RuntimeError("restore outcome missing result")
    return RestoreResponse(
        success=True,
        task=task_response(outcome.task),
        result=_restore_response(outcome.result),
    )


def _registry(request: Request) -> TaskRegistry:
    """Return shared registry from application state."""
    return request.app.state.task_registry


def _restore_response(result: RestoreResult) -> RestoreResultResponse:
    """Convert RestoreResult to response schema."""
    return RestoreResultResponse(
        total=result.total,
        success=result.success,
        skipped=result.skipped,
        failed=result.failed,
        errors=[
            RestoreFileErrorResponse(
                source_path=str(error.source_path),
                target_path=(
                    None if error.target_path is None else str(error.target_path)
                ),
                reason=error.reason,
            )
            for error in result.errors
        ],
    )
