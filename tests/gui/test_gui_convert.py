"""Scoped tests for the convert tool page."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QCheckBox, QScrollArea
from core.converter import XmlDatasetAnalysis, XmlDatasetConvertResult, XmlDatasetPaths
from utils.task_registry import TaskRegistry
from gui.workbench import AutoLabelerWindow

from conftest import (
    app,
    make_image,
    make_scanned_site,
    make_window,
    set_task_timestamp,
)

def test_convert_page_keeps_logging_without_overcrowding() -> None:
    """Convert page keeps a real log area but should not feel overgrown."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["convert"], Qt.MouseButton.LeftButton
    )

    convert_page = window.workbench_view.convert_page
    assert convert_page.log_box.objectName() == "logBox"
    assert convert_page.log_box.maximumHeight() <= 120
    assert isinstance(convert_page.overwrite_checkbox, QCheckBox)
    assert isinstance(convert_page.confirm_classes_checkbox, QCheckBox)
    assert convert_page.confirm_classes_checkbox.objectName() == "riskCheckbox"
    assert convert_page.train_ratio_label.text() == "训练比例"
    assert convert_page.classes_file_label.text() == "类别文件"
    assert not convert_page.analysis_panel.isVisible()


class FakeConvertWorker:
    """Small fake worker that records Convert configs from the GUI."""

    def __init__(self) -> None:
        self.analyze_config = None
        self.convert_config = None
        self.analysis = XmlDatasetAnalysis(
            collected_classes=["cat", "dog"],
            valid_pair_count=4,
            skipped_image_count=1,
            skipped_xml_count=2,
        )

    def analyze_xml_dataset(self, config):
        self.analyze_config = config

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, analysis):
                self.analysis = analysis

        return Outcome(self.analysis)

    def convert_xml_dataset(self, config):
        self.convert_config = config
        paths = XmlDatasetPaths(
            images_train=config.output_dir / "images" / "train",
            images_val=config.output_dir / "images" / "val",
            labels_train=config.output_dir / "labels" / "train",
            labels_val=config.output_dir / "labels" / "val",
            classes_txt=config.output_dir / "classes.txt",
            data_yaml=config.output_dir / "data.yaml",
        )
        result = XmlDatasetConvertResult(
            dataset_dir=config.output_dir,
            paths=paths,
            total_pairs=4,
            train_count=3,
            val_count=1,
            class_count=len(config.confirmed_classes),
            skipped_image_count=1,
            skipped_xml_count=2,
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)


def test_convert_page_analyzes_before_conversion(tmp_path: Path) -> None:
    """Convert page analyzes XML datasets before building convert config."""
    qt_app = app()
    convert_worker = FakeConvertWorker()
    window = make_window(convert_worker=convert_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["convert"], Qt.MouseButton.LeftButton
    )

    convert_page = window.workbench_view.convert_page
    source = tmp_path / "source"
    output = tmp_path / "dataset"
    convert_page.source_input.setText(str(source))
    convert_page.output_input.setText(str(output))
    convert_page.train_ratio_input.setText("0.8")
    QTest.mouseClick(convert_page.analyze_button, Qt.MouseButton.LeftButton)

    assert convert_worker.analyze_config is not None
    assert convert_worker.analyze_config.source_dir == source
    assert convert_worker.analyze_config.output_dir == output
    assert convert_worker.analyze_config.train_ratio == 0.8
    assert "分析完成" in convert_page.result_summary.text()
    assert convert_page.analysis_panel.isVisible()
    assert "类别确认" in convert_page.analysis_class_summary.text()
    assert "输出风险" in convert_page.analysis_risk_summary.text()
    assert "cat" in convert_page.classes_box.toPlainText()


def test_convert_page_requires_analysis_and_class_confirmation(
    tmp_path: Path,
) -> None:
    """Convert page blocks conversion until analysis and class confirmation."""
    qt_app = app()
    convert_worker = FakeConvertWorker()
    window = make_window(convert_worker=convert_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["convert"], Qt.MouseButton.LeftButton
    )

    convert_page = window.workbench_view.convert_page
    convert_page.source_input.setText(str(tmp_path / "source"))
    convert_page.output_input.setText(str(tmp_path / "dataset"))

    assert not convert_page.confirm_classes_checkbox.isEnabled()
    assert not convert_page.convert_button.isEnabled()
    assert convert_worker.convert_config is None

    QTest.mouseClick(convert_page.analyze_button, Qt.MouseButton.LeftButton)
    assert convert_page.confirm_classes_checkbox.isEnabled()
    assert not convert_page.convert_button.isEnabled()
    QTest.mouseClick(convert_page.convert_button, Qt.MouseButton.LeftButton)

    assert convert_worker.convert_config is None
    assert "分析完成" in convert_page.result_summary.text()

    QTest.mouseClick(
        convert_page.confirm_classes_checkbox,
        Qt.MouseButton.LeftButton,
        pos=QPoint(8, convert_page.confirm_classes_checkbox.height() // 2),
    )
    assert convert_page.convert_button.isEnabled()
    QTest.mouseClick(convert_page.convert_button, Qt.MouseButton.LeftButton)

    assert convert_worker.convert_config is not None
    assert convert_worker.convert_config.confirmed_classes == ["cat", "dog"]
    assert "转换完成" in convert_page.result_summary.text()


def test_convert_page_keeps_actions_visible_after_analysis(tmp_path: Path) -> None:
    """Convert actions stay reachable in the small desktop baseline."""
    qt_app = app()
    convert_worker = FakeConvertWorker()
    window = make_window(convert_worker=convert_worker)
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["convert"], Qt.MouseButton.LeftButton
    )

    convert_page = window.workbench_view.convert_page
    convert_page.source_input.setText(str(tmp_path / "source"))
    convert_page.output_input.setText(str(tmp_path / "dataset"))
    QTest.mouseClick(convert_page.analyze_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()

    scroll = convert_page.findChild(QScrollArea, "toolScrollArea")
    assert scroll is not None

    def center_is_in_viewport(widget) -> bool:
        point = widget.mapTo(
            scroll.viewport(),
            QPoint(widget.width() // 2, widget.height() // 2),
        )
        return scroll.viewport().rect().contains(point)

    assert center_is_in_viewport(convert_page.analyze_button)
    assert center_is_in_viewport(convert_page.convert_button)


def test_convert_page_renders_persisted_running_progress(tmp_path: Path) -> None:
    """Convert page can render persisted XML dataset conversion progress."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    task = registry.create_task("convert")
    registry.start_task(task.task_id, total=3744, message="准备转换")
    registry.update_progress(
        task.task_id, current=1200, total=3744, message="Converted 1200/3744"
    )
    window = make_window(task_registry=registry, convert_worker=FakeConvertWorker())
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["convert"], Qt.MouseButton.LeftButton
    )

    convert_page = window.workbench_view.convert_page
    convert_page.refresh_running_progress()

    assert "1200/3744" in convert_page.progress_label.text()
    assert convert_page.progress_bar.value() == 1200
    assert convert_page.progress_bar.maximum() == 3744


def test_convert_page_rejects_empty_paths_before_analysis() -> None:
    """Convert page blocks blank paths before constructing Path('')."""
    qt_app = app()
    convert_worker = FakeConvertWorker()
    window = make_window(convert_worker=convert_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["convert"], Qt.MouseButton.LeftButton
    )

    convert_page = window.workbench_view.convert_page
    QTest.mouseClick(convert_page.analyze_button, Qt.MouseButton.LeftButton)

    assert convert_worker.analyze_config is None
    assert "请选择源目录" in convert_page.result_summary.text()


