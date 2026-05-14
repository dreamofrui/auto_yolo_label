"""Convert API schemas."""

from __future__ import annotations

from pathlib import Path

from api.schemas.base import CamelModel
from api.schemas.common import TaskResponse


class TxtToXmlRequest(CamelModel):
    """HTTP request body for YOLO TXT to VOC XML conversion."""

    folder: Path
    recursive: bool = True
    classes: list[str] | None = None
    delete_source: bool = False
    backup_dir: Path | None = None


class XmlToTxtRequest(CamelModel):
    """HTTP request body for VOC XML to YOLO TXT conversion."""

    xml_path: Path
    classes: list[str]
    output_path: Path


class ConvertFileErrorResponse(CamelModel):
    """Serializable per-file conversion failure."""

    path: str
    code: str
    message: str
    details: str | None = None


class TxtToXmlResultResponse(CamelModel):
    """Serializable TXT to XML conversion result."""

    total: int
    success: int
    skipped: int
    failed: int
    errors: list[ConvertFileErrorResponse]


class TxtToXmlResponse(CamelModel):
    """Successful TXT to XML response."""

    success: bool
    task: TaskResponse
    result: TxtToXmlResultResponse


class XmlToTxtResultResponse(CamelModel):
    """Serializable XML to TXT conversion result."""

    output_path: str


class XmlToTxtResponse(CamelModel):
    """Successful XML to TXT response."""

    success: bool
    task: TaskResponse
    result: XmlToTxtResultResponse

