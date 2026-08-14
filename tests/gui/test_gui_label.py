"""Scoped tests for the label tool page."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from gui.workbench import AutoLabelerWindow

from conftest import FakeLabelImgWorker
from conftest import (
    app,
    make_image,
    make_scanned_site,
    make_window,
    set_task_timestamp,
)

def test_label_page_builds_labelimg_config(tmp_path: Path) -> None:
    """Label page launches free labeling with explicit paths."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    window = make_window(labelimg_worker=labelimg_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["label"], Qt.MouseButton.LeftButton
    )

    label_page = window.workbench_view.label_page
    image_dir = tmp_path / "images"
    classes_file = tmp_path / "classes.txt"
    label_dir = tmp_path / "labels"
    label_page.image_dir_input.setText(str(image_dir))
    label_page.classes_file_input.setText(str(classes_file))
    label_page.label_dir_input.setText(str(label_dir))
    QTest.mouseClick(label_page.launch_button, Qt.MouseButton.LeftButton)

    assert labelimg_worker.launch_config is not None
    assert str(labelimg_worker.launch_config.python_path).replace("\\", "/") == (
        "D:/miniforge3/envs/labelimg/python.exe"
    )
    assert labelimg_worker.launch_config.image_dir == image_dir
    assert labelimg_worker.launch_config.classes_file == classes_file
    assert labelimg_worker.launch_config.label_dir == label_dir
    assert "已启动 LabelImg" in label_page.result_summary.text()
    launch_log = label_page.log_box.toPlainText()
    assert "pid: 4321" in launch_log
    assert "import sys" not in launch_log
    assert "-c" not in launch_log


def test_label_page_builds_voc_folder_labelimg_config(tmp_path: Path) -> None:
    """VOC labeling opens an image folder and saves XML beside images."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    window = make_window(labelimg_worker=labelimg_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["label"], Qt.MouseButton.LeftButton
    )

    label_page = window.workbench_view.label_page
    image_dir = tmp_path / "images"
    label_page.image_dir_input.setText(str(image_dir))
    QTest.mouseClick(label_page.voc_mode_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(label_page.launch_button, Qt.MouseButton.LeftButton)

    assert labelimg_worker.launch_config is not None
    assert labelimg_worker.launch_config.image_dir == image_dir
    assert labelimg_worker.launch_config.annotation_format == "voc"
    assert labelimg_worker.launch_config.classes_file is None
    assert labelimg_worker.launch_config.label_dir is None
    assert not label_page.classes_file_input.isVisible()
    assert not label_page.label_dir_input.isVisible()
    assert "XML 写在图片同级" in label_page.mode_note.text()


def test_label_page_preflight_rejects_missing_yolo_paths_before_worker(
    tmp_path: Path,
) -> None:
    """Label page preflight validates current YOLO inputs before worker execution."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    window = make_window(labelimg_worker=labelimg_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["label"], Qt.MouseButton.LeftButton
    )

    label_page = window.workbench_view.label_page
    label_page.image_dir_input.setText(str(tmp_path / "images"))
    QTest.mouseClick(label_page.validate_button, Qt.MouseButton.LeftButton)

    assert labelimg_worker.validate_config is None
    assert labelimg_worker.preflight_config is None
    assert "请选择 classes.txt" in label_page.result_summary.text()


def test_label_page_preflights_voc_folder_config(tmp_path: Path) -> None:
    """VOC preflight uses image folder only and does not require YOLO paths."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    window = make_window(labelimg_worker=labelimg_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["label"], Qt.MouseButton.LeftButton
    )

    label_page = window.workbench_view.label_page
    image_dir = tmp_path / "images"
    label_page.image_dir_input.setText(str(image_dir))
    QTest.mouseClick(label_page.voc_mode_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(label_page.validate_button, Qt.MouseButton.LeftButton)

    assert labelimg_worker.validate_config is None
    assert labelimg_worker.preflight_config is not None
    assert labelimg_worker.preflight_config.image_dir == image_dir
    assert labelimg_worker.preflight_config.annotation_format == "voc"
    assert labelimg_worker.preflight_config.classes_file is None
    assert labelimg_worker.preflight_config.label_dir is None
    assert "预检通过" in label_page.result_summary.text()


def test_label_page_rejects_empty_paths_before_launch() -> None:
    """Label page blocks blank paths before launch config construction."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    window = make_window(labelimg_worker=labelimg_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["label"], Qt.MouseButton.LeftButton
    )

    label_page = window.workbench_view.label_page
    QTest.mouseClick(label_page.launch_button, Qt.MouseButton.LeftButton)

    assert labelimg_worker.launch_config is None
    assert "请选择图片目录" in label_page.result_summary.text()


