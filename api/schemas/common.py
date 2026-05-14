"""Common API response schemas."""

from __future__ import annotations

from api.schemas.base import CamelModel


class TaskResponse(CamelModel):
    """Serializable TaskHandle subset."""

    task_id: str
    task_type: str
    status: str
    progress_current: int
    progress_total: int
    progress_message: str
