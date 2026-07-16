"""Shared YOLO TXT and Pascal VOC XML annotation helpers."""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from utils.exceptions import AutoLabelerError, ErrorCode


@dataclass(frozen=True)
class YoloBox:
    """One normalized YOLO annotation box."""

    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float


@dataclass(frozen=True)
class VocObject:
    """One Pascal VOC object box."""

    name: str
    xmin: int
    ymin: int
    xmax: int
    ymax: int


@dataclass(frozen=True)
class VocAnnotation:
    """Parsed Pascal VOC annotation content used by core modules."""

    image_size: tuple[int, int]
    objects: list[VocObject]


class AnnotationFormatError(AutoLabelerError):
    """Raised when annotation text cannot be parsed or converted."""

    code = ErrorCode.VALIDATION_ERROR


def parse_yolo_label_text(text: str, classes: Sequence[str]) -> list[YoloBox]:
    """Parse YOLO label text into normalized boxes.

    Empty files and blank-only files are valid negative annotations.
    """
    boxes: list[YoloBox] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) != 5:
            raise AnnotationFormatError(
                "Invalid YOLO label row", details=f"line {line_number}"
            )
        try:
            class_id = int(parts[0])
            x_center, y_center, width, height = (
                float(parts[1]),
                float(parts[2]),
                float(parts[3]),
                float(parts[4]),
            )
        except ValueError as exc:
            raise AnnotationFormatError(
                "Invalid YOLO label row", details=f"line {line_number}"
            ) from exc
        _ensure_class_id(class_id, classes, f"line {line_number}: {class_id}")
        _ensure_yolo_geometry(
            x_center,
            y_center,
            width,
            height,
            details=f"line {line_number}",
        )
        boxes.append(
            YoloBox(
                class_id=class_id,
                x_center=x_center,
                y_center=y_center,
                width=width,
                height=height,
            )
        )
    return boxes


def yolo_boxes_to_voc_xml(
    filename: str,
    image_size: tuple[int, int],
    boxes: Sequence[YoloBox],
    classes: Sequence[str],
    *,
    folder: str | None = None,
    path: str | None = None,
) -> str:
    """Convert normalized YOLO boxes to Pascal VOC XML text."""
    image_width, image_height = _positive_image_size(image_size)
    root = ElementTree.Element("annotation")
    if folder is not None:
        ElementTree.SubElement(root, "folder").text = folder
    ElementTree.SubElement(root, "filename").text = filename
    if path is not None:
        ElementTree.SubElement(root, "path").text = path
    source_node = ElementTree.SubElement(root, "source")
    ElementTree.SubElement(source_node, "database").text = "Unknown"
    size_node = ElementTree.SubElement(root, "size")
    ElementTree.SubElement(size_node, "width").text = str(image_width)
    ElementTree.SubElement(size_node, "height").text = str(image_height)
    ElementTree.SubElement(size_node, "depth").text = "3"
    ElementTree.SubElement(root, "segmented").text = "0"

    for box in boxes:
        _ensure_class_id(box.class_id, classes, str(box.class_id))
        _ensure_yolo_box(box)
        _append_voc_object(root, box, image_size, classes)

    ElementTree.indent(root, space="  ")
    return (
        ElementTree.tostring(root, encoding="unicode", short_empty_elements=False)
        + "\n"
    )


def parse_voc_xml_text(text: str) -> VocAnnotation:
    """Parse Pascal VOC XML text into image dimensions and objects."""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise AnnotationFormatError("Invalid VOC XML", details=str(exc)) from exc

    image_size = (
        _positive_int(root.findtext("size/width"), "size/width"),
        _positive_int(root.findtext("size/height"), "size/height"),
    )
    objects = [_parse_voc_object(obj) for obj in root.findall("object")]
    return VocAnnotation(image_size=image_size, objects=objects)


def voc_objects_to_yolo_boxes(
    objects: Sequence[VocObject],
    image_size: tuple[int, int],
    classes: Sequence[str],
) -> list[YoloBox]:
    """Convert Pascal VOC objects to normalized YOLO boxes."""
    image_width, image_height = _positive_image_size(image_size)
    boxes: list[YoloBox] = []
    for obj in objects:
        if obj.name not in classes:
            raise AnnotationFormatError("Unknown VOC class", details=obj.name)
        _ensure_voc_object_bounds(obj, image_width, image_height)
        boxes.append(
            YoloBox(
                class_id=classes.index(obj.name),
                x_center=((obj.xmin + obj.xmax) / 2) / image_width,
                y_center=((obj.ymin + obj.ymax) / 2) / image_height,
                width=(obj.xmax - obj.xmin) / image_width,
                height=(obj.ymax - obj.ymin) / image_height,
            )
        )
    return boxes


def voc_objects_to_yolo_label_text(
    objects: Sequence[VocObject],
    image_size: tuple[int, int],
    classes: Sequence[str],
) -> str:
    """Convert Pascal VOC objects to newline-terminated YOLO label text."""
    boxes = voc_objects_to_yolo_boxes(objects, image_size, classes)
    return "".join(
        f"{box.class_id} "
        f"{box.x_center:.6f} "
        f"{box.y_center:.6f} "
        f"{box.width:.6f} "
        f"{box.height:.6f}\n"
        for box in boxes
    )


def _append_voc_object(
    root: ElementTree.Element,
    box: YoloBox,
    image_size: tuple[int, int],
    classes: Sequence[str],
) -> None:
    image_width, image_height = image_size
    xmin = round((box.x_center - box.width / 2) * image_width)
    ymin = round((box.y_center - box.height / 2) * image_height)
    xmax = round((box.x_center + box.width / 2) * image_width)
    ymax = round((box.y_center + box.height / 2) * image_height)
    if (
        xmin < 0
        or ymin < 0
        or xmax > image_width
        or ymax > image_height
        or xmax <= xmin
        or ymax <= ymin
    ):
        raise AnnotationFormatError("Invalid YOLO box", details=str(box.class_id))

    obj = ElementTree.SubElement(root, "object")
    ElementTree.SubElement(obj, "name").text = classes[box.class_id]
    ElementTree.SubElement(obj, "pose").text = "Unspecified"
    ElementTree.SubElement(obj, "truncated").text = "0"
    ElementTree.SubElement(obj, "difficult").text = "0"
    bndbox = ElementTree.SubElement(obj, "bndbox")
    ElementTree.SubElement(bndbox, "xmin").text = str(xmin)
    ElementTree.SubElement(bndbox, "ymin").text = str(ymin)
    ElementTree.SubElement(bndbox, "xmax").text = str(xmax)
    ElementTree.SubElement(bndbox, "ymax").text = str(ymax)


def _parse_voc_object(obj: ElementTree.Element) -> VocObject:
    name = (obj.findtext("name") or "").strip()
    if not name:
        raise AnnotationFormatError("Missing VOC object name")
    return VocObject(
        name=name,
        xmin=_int_text(obj.findtext("bndbox/xmin"), "bndbox/xmin"),
        ymin=_int_text(obj.findtext("bndbox/ymin"), "bndbox/ymin"),
        xmax=_int_text(obj.findtext("bndbox/xmax"), "bndbox/xmax"),
        ymax=_int_text(obj.findtext("bndbox/ymax"), "bndbox/ymax"),
    )


def _ensure_class_id(
    class_id: int, classes: Sequence[str], details: str | None = None
) -> None:
    if class_id < 0 or class_id >= len(classes):
        raise AnnotationFormatError("YOLO class id out of range", details=details)


def _ensure_yolo_box(box: YoloBox) -> None:
    _ensure_yolo_geometry(
        box.x_center,
        box.y_center,
        box.width,
        box.height,
        details=str(box.class_id),
    )


def _ensure_yolo_geometry(
    x_center: float,
    y_center: float,
    width: float,
    height: float,
    details: str | None = None,
) -> None:
    values = (x_center, y_center, width, height)
    if not all(isfinite(value) for value in values):
        raise AnnotationFormatError("Invalid YOLO geometry", details=details)
    if not (0.0 <= x_center <= 1.0 and 0.0 <= y_center <= 1.0):
        raise AnnotationFormatError("Invalid YOLO geometry", details=details)
    if not (0.0 < width <= 1.0 and 0.0 < height <= 1.0):
        raise AnnotationFormatError("Invalid YOLO geometry", details=details)


def _ensure_voc_object_bounds(
    obj: VocObject, image_width: int, image_height: int
) -> None:
    if obj.xmax <= obj.xmin or obj.ymax <= obj.ymin:
        raise AnnotationFormatError("Invalid VOC object box", details=obj.name)
    if (
        obj.xmin < 0
        or obj.ymin < 0
        or obj.xmax > image_width
        or obj.ymax > image_height
    ):
        raise AnnotationFormatError("VOC object box out of bounds", details=obj.name)


def _positive_image_size(image_size: tuple[int, int]) -> tuple[int, int]:
    width, height = image_size
    if width <= 0 or height <= 0:
        raise AnnotationFormatError("Invalid image size")
    return width, height


def _positive_int(text: str | None, field_name: str) -> int:
    value = _int_text(text, field_name)
    if value <= 0:
        raise AnnotationFormatError("Invalid VOC size field", details=field_name)
    return value


def _int_text(text: str | None, field_name: str) -> int:
    if text is None or not text.strip():
        raise AnnotationFormatError("Missing VOC field", details=field_name)
    try:
        return int(text)
    except ValueError as exc:
        raise AnnotationFormatError("Invalid VOC field", details=field_name) from exc
