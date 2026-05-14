"""FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routes.convert import router as convert_router
from api.routes.infer import router as infer_router
from api.routes.label_inspector import router as label_inspector_router
from api.routes.labelimg import router as labelimg_router
from api.routes.restore import router as restore_router
from api.routes.sample import router as sample_router
from api.routes.scan import router as scan_router
from api.routes.train import router as train_router
from utils.exceptions import AutoLabelerError
from utils.task_registry import TaskRegistry


def create_app(task_registry: TaskRegistry | None = None) -> FastAPI:
    """Create the AutoLabeler HTTP application.

    Args:
        task_registry: Optional shared task registry for tests or embedding.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(title="AutoLabeler API")
    app.state.task_registry = task_registry or TaskRegistry(
        Path.home() / ".autolabeler" / "tasks"
    )
    app.include_router(scan_router)
    app.include_router(sample_router)
    app.include_router(train_router)
    app.include_router(infer_router)
    app.include_router(restore_router)
    app.include_router(convert_router)
    app.include_router(label_inspector_router)
    app.include_router(labelimg_router)

    @app.exception_handler(AutoLabelerError)
    async def handle_app_error(request: Request, exc: AutoLabelerError) -> JSONResponse:
        """Convert business exceptions to stable JSON responses."""
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": exc.code.value,
                    "message": exc.message,
                    "details": exc.details,
                    "retryable": exc.retryable,
                },
            },
        )

    return app


app = create_app()
