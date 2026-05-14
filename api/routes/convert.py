"""HTTP routes for annotation format conversion."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas.convert import (
    ConvertFileErrorResponse,
    TxtToXmlRequest,
    TxtToXmlResponse,
    TxtToXmlResultResponse,
    XmlToTxtRequest,
    XmlToTxtResponse,
    XmlToTxtResultResponse,
)
from api.services.common import task_response
from api.services.convert_service import run_txt_to_xml, run_xml_to_txt
from core.converter import ConvertResult, TxtToXmlConfig, XmlToTxtConfig
from utils.task_registry import TaskRegistry

router = APIRouter(prefix="/api/convert", tags=["convert"])


@router.post("/yolo-to-voc", response_model=TxtToXmlResponse)
def yolo_to_voc(payload: TxtToXmlRequest, request: Request) -> TxtToXmlResponse:
    """Convert YOLO TXT files to VOC XML via HTTP."""
    outcome = run_txt_to_xml(
        TxtToXmlConfig(
            folder=payload.folder,
            recursive=payload.recursive,
            classes=payload.classes,
            delete_source=payload.delete_source,
            backup_dir=payload.backup_dir,
        ),
        _registry(request),
    )
    if outcome.error is not None:
        raise outcome.error
    if outcome.result is None:
        raise RuntimeError("convert outcome missing result")
    return TxtToXmlResponse(
        success=True,
        task=task_response(outcome.task),
        result=_txt_to_xml_response(outcome.result),
    )


@router.post("/voc-to-yolo", response_model=XmlToTxtResponse)
def voc_to_yolo(payload: XmlToTxtRequest, request: Request) -> XmlToTxtResponse:
    """Convert one VOC XML file to YOLO TXT via HTTP."""
    outcome = run_xml_to_txt(
        XmlToTxtConfig(
            xml_path=payload.xml_path,
            classes=payload.classes,
            output_path=payload.output_path,
        ),
        _registry(request),
    )
    if outcome.error is not None:
        raise outcome.error
    if outcome.output_path is None:
        raise RuntimeError("convert outcome missing output path")
    return XmlToTxtResponse(
        success=True,
        task=task_response(outcome.task),
        result=XmlToTxtResultResponse(output_path=str(outcome.output_path)),
    )


def _registry(request: Request) -> TaskRegistry:
    """Return shared registry from application state."""
    return request.app.state.task_registry


def _txt_to_xml_response(result: ConvertResult) -> TxtToXmlResultResponse:
    """Convert ConvertResult to response schema."""
    return TxtToXmlResultResponse(
        total=result.total,
        success=result.success,
        skipped=result.skipped,
        failed=result.failed,
        errors=[
            ConvertFileErrorResponse(
                path=str(error.path),
                code=error.code.value,
                message=error.message,
                details=error.details,
            )
            for error in result.errors
        ],
    )

