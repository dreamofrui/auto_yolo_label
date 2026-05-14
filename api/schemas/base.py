"""Shared pydantic schema helpers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    """Convert snake_case names to camelCase."""
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class CamelModel(BaseModel):
    """Base model using automatic camelCase aliases."""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, arbitrary_types_allowed=True
    )
