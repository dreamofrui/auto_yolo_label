"""Tests for the desktop convert worker adapter."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from core.converter import TxtToXmlConfig, XmlToTxtConfig
from gui.workers.convert_worker import ConvertWorker
from utils.task_registry import TaskRegistry


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(128, 128, 128)).save(path)


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


def test_convert_worker_runs_txt_to_xml_and_updates_task(tmp_path: Path) -> None:
    """Desktop convert worker runs TXT to XML through the shared service."""
    labels = tmp_path / "labels"
    make_image(labels / "a.jpg")
    (labels / "a.txt").write_text("0 0.5 0.5 0.5 0.5", encoding="utf-8")
    registry = TaskRegistry(task_dir=tmp_path / "tasks")

    outcome = ConvertWorker(registry=registry).run_txt_to_xml(
        TxtToXmlConfig(folder=labels, recursive=False, classes=["Product1"])
    )

    assert outcome.success is True
    assert outcome.result is not None
    assert outcome.result.success == 1
    assert outcome.error is None
    assert (labels / "a.xml").exists()
    assert registry.get(outcome.task.task_id).status == "succeeded"


def test_convert_worker_runs_xml_to_txt_and_updates_task(tmp_path: Path) -> None:
    """Desktop convert worker runs XML to TXT through the shared service."""
    xml_path = tmp_path / "input" / "a.xml"
    output_path = tmp_path / "output" / "a.txt"
    write_voc_xml(xml_path)
    registry = TaskRegistry(task_dir=tmp_path / "tasks")

    outcome = ConvertWorker(registry=registry).run_xml_to_txt(
        XmlToTxtConfig(xml_path=xml_path, classes=["Product1"], output_path=output_path)
    )

    assert outcome.success is True
    assert outcome.output_path == output_path
    assert outcome.error is None
    assert output_path.exists()
    assert registry.get(outcome.task.task_id).status == "succeeded"


def test_convert_worker_converts_errors_to_failed_task(tmp_path: Path) -> None:
    """Desktop convert worker records converter failures on the shared registry."""
    registry = TaskRegistry(task_dir=tmp_path / "tasks")

    outcome = ConvertWorker(registry=registry).run_txt_to_xml(
        TxtToXmlConfig(folder=tmp_path / "missing", recursive=False, classes=["Product1"])
    )

    assert outcome.success is False
    assert outcome.error is not None
    assert outcome.error.code == "CONVERT_FOLDER_NOT_FOUND"
    assert registry.get(outcome.task.task_id).status == "failed"

