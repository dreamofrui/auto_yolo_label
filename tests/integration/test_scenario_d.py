"""Scenario D: standalone YOLO TXT to VOC XML conversion."""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from pathlib import Path

from PIL import Image

from core.converter import Converter, TxtToXmlConfig


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 40), color=(0, 128, 255)).save(path)


def test_scenario_d_pure_format_conversion(tmp_path: Path) -> None:
    """A folder with YOLO TXT labels can be converted without other modules."""
    folder = tmp_path / "labels"
    make_image(folder / "item.jpg")
    (folder / "item.txt").write_text(
        "0 0.500000 0.500000 0.500000 0.500000\n", encoding="utf-8"
    )

    result = Converter().txt_to_xml(TxtToXmlConfig(folder=folder, classes=["CodeA"]))

    xml_path = folder / "item.xml"
    assert result.total == 1
    assert result.success == 1
    assert xml_path.exists()
    root = ElementTree.parse(xml_path).getroot()
    assert root.findtext("filename") == "item.jpg"
    assert root.findtext("object/name") == "CodeA"
