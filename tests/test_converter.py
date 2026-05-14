"""Tests for the converter core module."""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from core.converter import (
    ConvertClassesNotFoundError,
    ConvertClassIdOutOfRangeError,
    ConvertFileError,
    ConvertFolderNotFoundError,
    ConvertResult,
    ConvertXmlParseError,
    Converter,
    TxtToXmlConfig,
    XmlToTxtConfig,
)
from utils.exceptions import ErrorCode, TaskCancelledError
from utils.mapping_manager import MappingManager
from utils.task_registry import TaskHandle


def make_image(path: Path, size: tuple[int, int] = (64, 48)) -> None:
    """Create a tiny RGB image for conversion tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(255, 0, 0)).save(path)


def write_txt(path: Path, lines: list[str]) -> None:
    """Write a YOLO annotation file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_xml(
    path: Path,
    *,
    width: int = 100,
    height: int = 200,
    objects: list[dict[str, Any]] | None = None,
) -> None:
    """Write a minimal Pascal VOC XML document."""
    objects = objects or []
    object_xml = "".join(
        """
        <object>
          <name>{name}</name>
          <pose>Unspecified</pose>
          <truncated>0</truncated>
          <difficult>0</difficult>
          <bndbox>
            <xmin>{xmin}</xmin>
            <ymin>{ymin}</ymin>
            <xmax>{xmax}</xmax>
            <ymax>{ymax}</ymax>
          </bndbox>
        </object>
        """.format(**item)
        for item in objects
    )
    xml = f"""
<annotation>
  <folder>site</folder>
  <filename>{path.with_suffix('.jpg').name}</filename>
  <path>{path.with_suffix('.jpg')}</path>
  <source><database>Unknown</database></source>
  <size>
    <width>{width}</width>
    <height>{height}</height>
    <depth>3</depth>
  </size>
  <segmented>0</segmented>
  {object_xml}
</annotation>
"""
    path.write_text("\n".join(line.rstrip() for line in xml.strip().splitlines()), encoding="utf-8")


def make_task_handle(task_type: str = "convert") -> TaskHandle:
    """Create an in-memory task handle for tests."""
    return TaskHandle(
        task_id="task_convert_test",
        task_type=task_type,
        status="running",
        progress_current=0,
        progress_total=0,
        progress_message="",
        logs=[],
        result=None,
        error=None,
        created_at="2026-05-14 00:00:00",
        started_at="2026-05-14 00:00:00",
        finished_at=None,
        is_cancel_requested=False,
    )


def test_converter_constructs_successfully() -> None:
    """Converter can be created with default dependencies."""
    converter = Converter()

    assert isinstance(converter, Converter)


def test_txt_to_xml_converts_single_file_with_explicit_classes(tmp_path: Path) -> None:
    """A single YOLO file converts to VOC XML with no declaration."""
    folder = tmp_path / "site"
    write_txt(folder / "labels" / "IMG_001.txt", ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "labels" / "IMG_001.jpg", size=(100, 100))

    result = Converter().txt_to_xml(
        TxtToXmlConfig(folder=folder, classes=["cat"]),
    )

    xml_path = folder / "labels" / "IMG_001.xml"
    xml_text = xml_path.read_text(encoding="utf-8")
    root = ElementTree.parse(xml_path).getroot()

    assert isinstance(result, ConvertResult)
    assert result.total == 1
    assert result.success == 1
    assert result.skipped == 0
    assert result.failed == 0
    assert result.errors == []
    assert xml_path.exists()
    assert not xml_text.startswith("<?xml")
    assert root.findtext("./object/name") == "cat"


def test_txt_to_xml_recursive_false_only_top_level(tmp_path: Path) -> None:
    """Recursive scanning disabled ignores nested TXT files."""
    folder = tmp_path / "site"
    write_txt(folder / "top.txt", ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "top.jpg", size=(80, 80))
    write_txt(folder / "nested" / "inner.txt", ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "nested" / "inner.jpg", size=(80, 80))

    result = Converter().txt_to_xml(
        TxtToXmlConfig(folder=folder, recursive=False, classes=["cat"]),
    )

    assert result.total == 1
    assert result.success == 1
    assert (folder / "top.xml").exists()
    assert not (folder / "nested" / "inner.xml").exists()


def test_txt_to_xml_recursive_true_includes_nested_files(tmp_path: Path) -> None:
    """Recursive scanning includes nested TXT files."""
    folder = tmp_path / "site"
    write_txt(folder / "top.txt", ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "top.jpg", size=(80, 80))
    write_txt(folder / "nested" / "inner.txt", ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "nested" / "inner.jpg", size=(80, 80))

    result = Converter().txt_to_xml(
        TxtToXmlConfig(folder=folder, recursive=True, classes=["cat"]),
    )

    assert result.total == 2
    assert result.success == 2
    assert (folder / "top.xml").exists()
    assert (folder / "nested" / "inner.xml").exists()


def test_txt_to_xml_skips_control_files(tmp_path: Path) -> None:
    """Control files are filtered out before batch accounting."""
    folder = tmp_path / "site"
    write_txt(folder / "classes.txt", ["0 cat"])
    write_txt(folder / "README.txt", ["notes"])
    (folder / "data.yaml").parent.mkdir(parents=True, exist_ok=True)
    (folder / "data.yaml").write_text("train: images/train", encoding="utf-8")
    write_txt(folder / "real.txt", ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "real.png", size=(90, 90))

    result = Converter().txt_to_xml(
        TxtToXmlConfig(folder=folder, classes=["cat"]),
    )

    assert result.total == 1
    assert result.success == 1
    assert result.skipped == 0
    assert result.failed == 0


def test_txt_to_xml_skips_when_image_missing(tmp_path: Path) -> None:
    """A TXT file without a same-stem image is skipped."""
    folder = tmp_path / "site"
    write_txt(folder / "missing.txt", ["0 0.500000 0.500000 0.500000 0.500000"])

    result = Converter().txt_to_xml(
        TxtToXmlConfig(folder=folder, classes=["cat"]),
    )

    assert result.total == 1
    assert result.success == 0
    assert result.skipped == 1
    assert result.failed == 0
    assert result.errors == []


def test_txt_to_xml_finds_uppercase_image_suffix(tmp_path: Path) -> None:
    """Uppercase image suffixes are matched case-insensitively."""
    folder = tmp_path / "site"
    write_txt(folder / "item.txt", ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "item.JPG", size=(100, 60))

    result = Converter().txt_to_xml(
        TxtToXmlConfig(folder=folder, classes=["cat"]),
    )

    assert result.success == 1
    assert (folder / "item.xml").exists()


def test_txt_to_xml_class_id_out_of_range_records_error_and_continues(tmp_path: Path) -> None:
    """One bad TXT file does not stop later files from converting."""
    folder = tmp_path / "site"
    write_txt(folder / "bad.txt", ["1 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "bad.jpg", size=(100, 100))
    write_txt(folder / "good.txt", ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "good.jpg", size=(100, 100))

    result = Converter().txt_to_xml(
        TxtToXmlConfig(folder=folder, classes=["cat"]),
    )

    assert result.total == 2
    assert result.success == 1
    assert result.skipped == 0
    assert result.failed == 1
    assert len(result.errors) == 1
    assert result.errors[0].code == ErrorCode.CONVERT_CLASS_ID_OUT_OF_RANGE
    assert isinstance(result.errors[0], ConvertFileError)
    assert (folder / "good.xml").exists()
    assert not (folder / "bad.xml").exists()


def test_txt_to_xml_default_does_not_delete_source(tmp_path: Path) -> None:
    """TXT sources remain in place unless deletion is explicitly requested."""
    folder = tmp_path / "site"
    txt_path = folder / "item.txt"
    write_txt(txt_path, ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "item.jpg", size=(100, 100))

    Converter().txt_to_xml(TxtToXmlConfig(folder=folder, classes=["cat"]))

    assert txt_path.exists()


def test_txt_to_xml_delete_source_with_backup_preserves_relative_path(tmp_path: Path) -> None:
    """Deletion with backup copies the TXT before removing the source."""
    folder = tmp_path / "site"
    backup_dir = tmp_path / "backup"
    txt_path = folder / "nested" / "item.txt"
    write_txt(txt_path, ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "nested" / "item.png", size=(100, 100))

    result = Converter().txt_to_xml(
        TxtToXmlConfig(
            folder=folder,
            classes=["cat"],
            delete_source=True,
            backup_dir=backup_dir,
        ),
    )

    backup_path = backup_dir / "nested" / "item.txt"
    assert result.success == 1
    assert not txt_path.exists()
    assert backup_path.exists()
    assert backup_path.read_text(encoding="utf-8").strip() == "0 0.500000 0.500000 0.500000 0.500000"


def test_txt_to_xml_backup_failure_records_failed_without_delete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backup failures keep the source TXT and mark the file failed."""
    folder = tmp_path / "site"
    backup_dir = tmp_path / "backup"
    txt_path = folder / "item.txt"
    write_txt(txt_path, ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "item.jpg", size=(100, 100))

    def fail_copy2(*args: object, **kwargs: object) -> None:
        raise OSError("backup failed")

    monkeypatch.setattr("shutil.copy2", fail_copy2)

    result = Converter().txt_to_xml(
        TxtToXmlConfig(
            folder=folder,
            classes=["cat"],
            delete_source=True,
            backup_dir=backup_dir,
        ),
    )

    assert result.success == 0
    assert result.failed == 1
    assert txt_path.exists()
    assert not (folder / "item.xml").exists()
    assert result.errors[0].code == ErrorCode.INTERNAL_ERROR


def test_txt_to_xml_resolves_classes_from_mapping_manager(tmp_path: Path) -> None:
    """Classes can be loaded from mapping.json through MappingManager."""
    folder = tmp_path / "site"
    mapping_path = folder / ".autolabeler" / "mapping.json"
    manager = MappingManager(mapping_path).create_new(folder)
    manager.add_class(0, "cat")
    manager.add_class(1, "dog")
    manager.save()
    write_txt(folder / "item.txt", ["1 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "item.jpg", size=(100, 100))

    result = Converter(mapping_manager=MappingManager(mapping_path)).txt_to_xml(
        TxtToXmlConfig(folder=folder),
    )

    xml_path = folder / "item.xml"
    assert result.success == 1
    assert ElementTree.parse(xml_path).getroot().findtext("./object/name") == "dog"


def test_txt_to_xml_missing_classes_raises_convert_classes_not_found(tmp_path: Path) -> None:
    """Missing explicit and mapped classes raise a converter-specific error."""
    folder = tmp_path / "site"
    folder.mkdir()

    with pytest.raises(ConvertClassesNotFoundError):
        Converter().txt_to_xml(TxtToXmlConfig(folder=folder))


def test_txt_to_xml_missing_folder_raises_convert_folder_not_found(tmp_path: Path) -> None:
    """Missing folders raise the dedicated folder error."""
    with pytest.raises(ConvertFolderNotFoundError):
        Converter().txt_to_xml(TxtToXmlConfig(folder=tmp_path / "missing", classes=["cat"]))


def test_xml_to_txt_converts_voc_box_to_yolo(tmp_path: Path) -> None:
    """VOC boxes convert to six-decimal YOLO annotations."""
    xml_path = tmp_path / "sample.xml"
    output_path = tmp_path / "out" / "sample.txt"
    write_xml(
        xml_path,
        width=100,
        height=200,
        objects=[
            {
                "name": "cat",
                "xmin": 10,
                "ymin": 20,
                "xmax": 30,
                "ymax": 60,
            }
        ],
    )

    result = Converter().xml_to_txt(
        XmlToTxtConfig(xml_path=xml_path, classes=["cat"], output_path=output_path),
    )

    assert result == output_path
    assert output_path.read_text(encoding="utf-8").strip() == "0 0.200000 0.200000 0.200000 0.200000"


def test_xml_to_txt_unknown_class_raises_convert_xml_parse(tmp_path: Path) -> None:
    """Unknown VOC object names raise an XML parse error."""
    xml_path = tmp_path / "sample.xml"
    write_xml(
        xml_path,
        objects=[
            {
                "name": "dog",
                "xmin": 10,
                "ymin": 20,
                "xmax": 30,
                "ymax": 60,
            }
        ],
    )

    with pytest.raises(ConvertXmlParseError):
        Converter().xml_to_txt(
            XmlToTxtConfig(xml_path=xml_path, classes=["cat"], output_path=tmp_path / "out.txt"),
        )


def test_xml_to_txt_missing_size_raises_convert_xml_parse(tmp_path: Path) -> None:
    """Missing size information raises an XML parse error."""
    xml_path = tmp_path / "sample.xml"
    xml_path.write_text(
        """
<annotation>
  <object>
    <name>cat</name>
    <bndbox>
      <xmin>1</xmin>
      <ymin>2</ymin>
      <xmax>3</xmax>
      <ymax>4</ymax>
    </bndbox>
  </object>
</annotation>
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConvertXmlParseError):
        Converter().xml_to_txt(
            XmlToTxtConfig(xml_path=xml_path, classes=["cat"], output_path=tmp_path / "out.txt"),
        )


def test_xml_to_txt_invalid_xml_raises_convert_xml_parse(tmp_path: Path) -> None:
    """Malformed XML raises an XML parse error."""
    xml_path = tmp_path / "sample.xml"
    xml_path.write_text("<annotation><object></annotation>", encoding="utf-8")

    with pytest.raises(ConvertXmlParseError):
        Converter().xml_to_txt(
            XmlToTxtConfig(xml_path=xml_path, classes=["cat"], output_path=tmp_path / "out.txt"),
        )


def test_task_handle_progress_updates_for_batch(tmp_path: Path) -> None:
    """Batch conversion updates progress on the injected task handle."""
    folder = tmp_path / "site"
    write_txt(folder / "one.txt", ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "one.jpg", size=(100, 100))
    write_txt(folder / "two.txt", ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "two.jpg", size=(100, 100))
    task_handle = make_task_handle()

    result = Converter(task_handle=task_handle).txt_to_xml(
        TxtToXmlConfig(folder=folder, classes=["cat"]),
    )

    assert result.total == 2
    assert task_handle.progress_total == 2
    assert task_handle.progress_current == 2
    assert task_handle.progress_message


def test_txt_to_xml_cancellation_raises_task_cancelled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancellation requested during the loop raises TaskCancelledError."""
    folder = tmp_path / "site"
    write_txt(folder / "one.txt", ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "one.jpg", size=(100, 100))
    write_txt(folder / "two.txt", ["0 0.500000 0.500000 0.500000 0.500000"])
    make_image(folder / "two.jpg", size=(100, 100))
    task_handle = make_task_handle()
    original_open = Image.open
    call_count = {"value": 0}

    def wrapped_open(*args: object, **kwargs: object):
        call_count["value"] += 1
        if call_count["value"] == 1:
            task_handle.is_cancel_requested = True
        return original_open(*args, **kwargs)

    monkeypatch.setattr("PIL.Image.open", wrapped_open)

    with pytest.raises(TaskCancelledError):
        Converter(task_handle=task_handle).txt_to_xml(
            TxtToXmlConfig(folder=folder, classes=["cat"]),
        )

