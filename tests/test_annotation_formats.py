"""Tests for shared annotation format helpers."""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree

import pytest

from core.annotation_formats import (
    AnnotationFormatError,
    VocAnnotation,
    VocObject,
    YoloBox,
    parse_voc_xml_text,
    parse_yolo_label_text,
    voc_objects_to_yolo_label_text,
    voc_objects_to_yolo_boxes,
    yolo_boxes_to_voc_xml,
)
from utils.exceptions import AutoLabelerError, ErrorCode


def test_parse_yolo_label_text_accepts_empty_annotations() -> None:
    """Empty YOLO label files represent images with no annotations."""
    assert parse_yolo_label_text("", classes=["cat"]) == []
    assert parse_yolo_label_text("\n  \n", classes=["cat"]) == []


def test_parse_yolo_label_text_returns_typed_boxes() -> None:
    """YOLO rows parse into typed normalized boxes."""
    boxes = parse_yolo_label_text(
        "0 0.500000 0.250000 0.200000 0.100000\n"
        "1 0.750000 0.500000 0.300000 0.400000",
        classes=["cat", "dog"],
    )

    assert boxes == [
        YoloBox(class_id=0, x_center=0.5, y_center=0.25, width=0.2, height=0.1),
        YoloBox(class_id=1, x_center=0.75, y_center=0.5, width=0.3, height=0.4),
    ]


def test_parse_yolo_label_text_rejects_class_id_outside_classes() -> None:
    """Class ids must resolve to the provided class list."""
    with pytest.raises(AutoLabelerError) as exc_info:
        parse_yolo_label_text(
            "2 0.500000 0.500000 0.100000 0.100000", classes=["cat", "dog"]
        )

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert exc_info.value.details == "line 1: 2"


@pytest.mark.parametrize(
    "row",
    [
        "0 -0.100000 0.500000 0.100000 0.100000",
        "0 1.100000 0.500000 0.100000 0.100000",
        "0 0.500000 0.500000 0.000000 0.100000",
        "0 0.500000 0.500000 -0.100000 0.100000",
        "0 nan 0.500000 0.100000 0.100000",
        "0 inf 0.500000 0.100000 0.100000",
    ],
)
def test_parse_yolo_label_text_rejects_invalid_geometry(row: str) -> None:
    """YOLO label rows must contain finite normalized geometry."""
    with pytest.raises(AnnotationFormatError):
        parse_yolo_label_text(row, classes=["cat"])


def test_yolo_boxes_to_voc_xml_rejects_boxes_outside_image() -> None:
    """YOLO to VOC conversion fails instead of clipping bad boxes."""
    with pytest.raises(AnnotationFormatError):
        yolo_boxes_to_voc_xml(
            filename="image.jpg",
            image_size=(100, 100),
            boxes=[
                YoloBox(
                    class_id=0,
                    x_center=0.05,
                    y_center=0.500000,
                    width=0.200000,
                    height=0.100000,
                )
            ],
            classes=["cat"],
        )


def test_yolo_boxes_to_voc_xml_uses_image_size_and_class_names() -> None:
    """Normalized YOLO boxes convert to VOC pixel bounds and class names."""
    xml_text = yolo_boxes_to_voc_xml(
        filename="image.jpg",
        image_size=(100, 200),
        boxes=[
            YoloBox(
                class_id=1,
                x_center=0.5,
                y_center=0.25,
                width=0.4,
                height=0.2,
            )
        ],
        classes=["cat", "dog"],
    )

    root = ElementTree.fromstring(xml_text)

    assert root.findtext("filename") == "image.jpg"
    assert root.findtext("size/width") == "100"
    assert root.findtext("size/height") == "200"
    assert root.findtext("object/name") == "dog"
    assert root.findtext("object/bndbox/xmin") == "30"
    assert root.findtext("object/bndbox/ymin") == "30"
    assert root.findtext("object/bndbox/xmax") == "70"
    assert root.findtext("object/bndbox/ymax") == "70"


def test_yolo_boxes_to_voc_xml_writes_labelimg_metadata_and_pretty_lines() -> None:
    """Restored VOC XML includes common LabelImg metadata and line breaks."""
    xml_text = yolo_boxes_to_voc_xml(
        filename="image.jpg",
        folder="Product1",
        path="D:/site/CodeA/Product1/image.jpg",
        image_size=(100, 200),
        boxes=[],
        classes=["cat"],
    )

    root = ElementTree.fromstring(xml_text)

    assert root.findtext("folder") == "Product1"
    assert root.findtext("filename") == "image.jpg"
    assert root.findtext("path") == "D:/site/CodeA/Product1/image.jpg"
    assert root.findtext("source/database") == "Unknown"
    assert "\n  <folder>" in xml_text
    assert "\n</annotation>" in xml_text


def test_parse_voc_xml_text_returns_image_size_and_objects() -> None:
    """VOC XML parses into image dimensions and object boxes."""
    annotation = parse_voc_xml_text(
        """
<annotation>
  <filename>image.jpg</filename>
  <size>
    <width>100</width>
    <height>200</height>
    <depth>3</depth>
  </size>
  <object>
    <name>cat</name>
    <bndbox>
      <xmin>10</xmin>
      <ymin>20</ymin>
      <xmax>30</xmax>
      <ymax>60</ymax>
    </bndbox>
  </object>
</annotation>
""".strip()
    )

    assert annotation == VocAnnotation(
        image_size=(100, 200),
        objects=[VocObject(name="cat", xmin=10, ymin=20, xmax=30, ymax=60)],
    )


def test_voc_objects_to_yolo_boxes_uses_class_order() -> None:
    """VOC object names convert to YOLO class ids from the provided order."""
    boxes = voc_objects_to_yolo_boxes(
        [VocObject(name="dog", xmin=10, ymin=20, xmax=30, ymax=60)],
        image_size=(100, 200),
        classes=["cat", "dog"],
    )

    assert boxes == [
        YoloBox(class_id=1, x_center=0.2, y_center=0.2, width=0.2, height=0.2)
    ]


@pytest.mark.parametrize(
    "obj",
    [
        VocObject(name="cat", xmin=-1, ymin=0, xmax=10, ymax=10),
        VocObject(name="cat", xmin=0, ymin=0, xmax=101, ymax=10),
        VocObject(name="cat", xmin=0, ymin=0, xmax=10, ymax=201),
    ],
)
def test_voc_objects_to_yolo_boxes_rejects_out_of_bounds_boxes(
    obj: VocObject,
) -> None:
    """VOC boxes must be inside the image before conversion."""
    with pytest.raises(AnnotationFormatError):
        voc_objects_to_yolo_boxes([obj], image_size=(100, 200), classes=["cat"])


def test_parse_voc_xml_text_rejects_decimal_coordinates() -> None:
    """VOC pixel coordinates must be integer text, not silently truncated."""
    with pytest.raises(AnnotationFormatError):
        parse_voc_xml_text(
            """
<annotation>
  <size><width>100</width><height>100</height></size>
  <object>
    <name>cat</name>
    <bndbox><xmin>10.9</xmin><ymin>20</ymin><xmax>30</xmax><ymax>40</ymax></bndbox>
  </object>
</annotation>
""".strip()
        )


def test_voc_objects_to_yolo_label_text_formats_rows() -> None:
    """VOC objects can be written as six-decimal YOLO rows."""
    text = voc_objects_to_yolo_label_text(
        [VocObject(name="dog", xmin=10, ymin=20, xmax=30, ymax=60)],
        image_size=(100, 200),
        classes=["cat", "dog"],
    )

    assert text == "1 0.200000 0.200000 0.200000 0.200000\n"
