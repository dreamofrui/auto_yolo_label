"""Tests for the convert HTTP routes."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from api.main import create_app
from utils.task_registry import TaskRegistry


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(255, 255, 255)).save(path)


def make_client(tmp_path: Path) -> TestClient:
    """Create a test client from the main API app."""
    return TestClient(create_app(task_registry=TaskRegistry(task_dir=tmp_path / "tasks")))


def write_voc_xml(path: Path) -> None:
    """Write a minimal VOC XML fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
<annotation>
  <size>
    <width>100</width>
    <height>100</height>
    <depth>3</depth>
  </size>
  <object>
    <name>Product1</name>
    <bndbox>
      <xmin>25</xmin>
      <ymin>25</ymin>
      <xmax>75</xmax>
      <ymax>75</ymax>
    </bndbox>
  </object>
</annotation>
""".strip(),
        encoding="utf-8",
    )


def test_yolo_to_voc_route_converts_txt_annotations(tmp_path: Path) -> None:
    """YOLO to VOC route returns a succeeded task and writes XML."""
    labels = tmp_path / "labels"
    make_image(labels / "a.jpg")
    (labels / "a.txt").write_text("0 0.5 0.5 0.5 0.5", encoding="utf-8")
    client = make_client(tmp_path)

    response = client.post(
        "/api/convert/yolo-to-voc",
        json={
            "folder": str(labels),
            "recursive": False,
            "classes": ["Product1"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["task"]["status"] == "succeeded"
    assert payload["result"]["success"] == 1
    assert (labels / "a.xml").exists()


def test_voc_to_yolo_route_converts_xml_annotation(tmp_path: Path) -> None:
    """VOC to YOLO route returns outputPath and writes TXT."""
    xml_path = tmp_path / "input" / "a.xml"
    output_path = tmp_path / "output" / "a.txt"
    write_voc_xml(xml_path)
    client = make_client(tmp_path)

    response = client.post(
        "/api/convert/voc-to-yolo",
        json={
            "xmlPath": str(xml_path),
            "classes": ["Product1"],
            "outputPath": str(output_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["task"]["status"] == "succeeded"
    assert payload["result"]["outputPath"] == str(output_path)
    assert output_path.exists()


def test_yolo_to_voc_route_maps_business_error_to_json(tmp_path: Path) -> None:
    """Missing folders become stable JSON errors."""
    client = make_client(tmp_path)

    response = client.post(
        "/api/convert/yolo-to-voc",
        json={
            "folder": str(tmp_path / "missing"),
            "recursive": False,
            "classes": ["Product1"],
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "CONVERT_FOLDER_NOT_FOUND"

