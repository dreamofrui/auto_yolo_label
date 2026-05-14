"""FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routes.scan import router as scan_router
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
    app.state.task_registry = task_registry or TaskRegistry(Path.home() / ".autolabeler" / "tasks")
    app.include_router(scan_router)

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
