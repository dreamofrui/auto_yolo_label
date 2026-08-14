"""Scoped tests for the sample tool page."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QScrollArea
from utils.task_registry import TaskRegistry
from gui.workbench import AutoLabelerWindow

from conftest import (
    app,
    make_image,
    make_scanned_site,
    make_window,
    set_task_timestamp,
)

def test_sample_page_keeps_compact_inputs_and_logs() -> None:
    """Sample page keeps visible inputs while the log stays compact."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["sample"], Qt.MouseButton.LeftButton
    )

    sample_page = window.workbench_view.sample_page
    assert sample_page.flow_site_input.isVisible()
    assert sample_page.output_input.isVisible()
    assert sample_page.log_box.minimumHeight() <= 180


def test_sample_page_does_not_clip_path_pickers_at_small_width(tmp_path: Path) -> None:
    """Sample form shrinks into the small desktop viewport instead of clipping controls."""
    qt_app = app()
    site = tmp_path / "site"
    make_scanned_site(site)
    window = make_window()
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["sample"], Qt.MouseButton.LeftButton
    )

    sample_page = window.workbench_view.sample_page
    sample_page.flow_site_input.setText(str(site))
    sample_page.output_input.setText(str(tmp_path / "dataset"))
    sample_page.count_input.setText("1")
    sample_page.full_threshold_input.setText("1")
    QTest.mouseClick(sample_page.preflight_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()

    scroll_area = sample_page.findChild(QScrollArea, "toolScrollArea")
    assert scroll_area is not None
    assert scroll_area.widget().width() <= scroll_area.viewport().width()
    assert sample_page.flow_site_input.browse_button.isVisible()
    assert sample_page.output_input.browse_button.isVisible()


def test_sample_page_runs_flow_sample(tmp_path: Path) -> None:
    """Sample page builds SampleConfig and renders a success summary."""
    qt_app = app()
    site = tmp_path / "site"
    make_scanned_site(site)
    window = make_window(
        task_registry=TaskRegistry(task_dir=tmp_path / "tasks")
    )
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["sample"], Qt.MouseButton.LeftButton
    )

    sample_page = window.workbench_view.sample_page
    sample_page.flow_site_input.setText(str(site))
    sample_page.output_input.setText(str(tmp_path / "dataset"))
    sample_page.count_input.setText("1")
    sample_page.full_threshold_input.setText("1")
    QTest.mouseClick(sample_page.run_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()

    assert "抽样失败" not in sample_page.result_summary.text()
    assert (tmp_path / "dataset" / "data.yaml").exists()
    assert "抽样完成" in sample_page.result_summary.text()
    assert "选中 1" in sample_page.result_summary.text()


def test_sample_page_preflights_flow_sample(tmp_path: Path) -> None:
    """Sample page renders real Flow preflight estimates before execution."""
    qt_app = app()
    site = tmp_path / "site"
    make_scanned_site(site)
    window = make_window(
        task_registry=TaskRegistry(task_dir=tmp_path / "tasks")
    )
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["sample"], Qt.MouseButton.LeftButton
    )

    sample_page = window.workbench_view.sample_page
    sample_page.flow_site_input.setText(str(site))
    sample_page.output_input.setText(str(tmp_path / "dataset"))
    sample_page.count_input.setText("1")
    sample_page.full_threshold_input.setText("1")
    QTest.mouseClick(sample_page.preflight_button, Qt.MouseButton.LeftButton)

    assert "预检通过" in sample_page.result_summary.text()
    assert "选中 1" in sample_page.result_summary.text()
    assert "复制 1" in sample_page.result_summary.text()
    assert "预计输出" in sample_page.preflight_impact_summary.text()
    assert "阻断" in sample_page.preflight_risk_summary.text()
    assert "[preflight]" in sample_page.log_box.toPlainText()
    assert not (tmp_path / "dataset").exists()


def test_sample_page_independent_mode_defaults_to_xml_output(tmp_path: Path) -> None:
    """Independent mode defaults to XML labeling output."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["sample"], Qt.MouseButton.LeftButton
    )

    sample_page = window.workbench_view.sample_page
    QTest.mouseClick(
        sample_page.independent_mode_button, Qt.MouseButton.LeftButton
    )

    assert sample_page.current_mode() == "independent"
    assert sample_page.xml_output_button.isChecked()
    assert not sample_page.classes_input.isVisible()
    assert "XML" in sample_page.mode_note.text()


def test_sample_page_rejects_empty_paths_before_building_config() -> None:
    """Sample page does not allow blank paths to become the current directory."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["sample"], Qt.MouseButton.LeftButton
    )

    sample_page = window.workbench_view.sample_page
    QTest.mouseClick(sample_page.run_button, Qt.MouseButton.LeftButton)

    assert "请选择站点路径" in sample_page.result_summary.text()


class RecordingIndependentSampleWorker:
    """Fake worker that records IndependentSampleConfig calls."""

    def __init__(self) -> None:
        self.independent_config = None

    def run(self, config):  # pragma: no cover - should not be called here
        raise AssertionError("flow run should not be called")

    def run_independent(self, config):
        self.independent_config = config

        class Outcome:
            success = False
            result = None
            task = None
            error = None

        return Outcome()


def test_sample_independent_requires_confirmation_before_move(tmp_path: Path) -> None:
    """Independent YOLO mode cannot run move-based sampling before confirmation."""
    qt_app = app()
    worker = RecordingIndependentSampleWorker()
    window = make_window(sample_worker=worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["sample"], Qt.MouseButton.LeftButton
    )

    sample_page = window.workbench_view.sample_page
    QTest.mouseClick(
        sample_page.independent_mode_button, Qt.MouseButton.LeftButton
    )
    QTest.mouseClick(sample_page.yolo_output_button, Qt.MouseButton.LeftButton)
    sample_page.independent_source_input.setText(str(tmp_path / "source"))
    sample_page.output_input.setText(str(tmp_path / "dataset"))
    QTest.mouseClick(sample_page.run_button, Qt.MouseButton.LeftButton)

    assert worker.independent_config is None
    assert "确认会移动" in sample_page.result_summary.text()

    QTest.mouseClick(sample_page.confirm_move_checkbox, Qt.MouseButton.LeftButton)
    QTest.mouseClick(sample_page.run_button, Qt.MouseButton.LeftButton)

    assert worker.independent_config is not None
    assert worker.independent_config.output_format == "yolo"


def test_sample_independent_xml_output_is_default_after_move_confirmation(
    tmp_path: Path,
) -> None:
    """Independent mode sends XML output by default after move confirmation."""
    qt_app = app()
    worker = RecordingIndependentSampleWorker()
    window = make_window(sample_worker=worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["sample"], Qt.MouseButton.LeftButton
    )

    sample_page = window.workbench_view.sample_page
    QTest.mouseClick(
        sample_page.independent_mode_button, Qt.MouseButton.LeftButton
    )
    sample_page.independent_source_input.setText(str(tmp_path / "source"))
    sample_page.output_input.setText(str(tmp_path / "labeling_sample"))
    QTest.mouseClick(sample_page.confirm_move_checkbox, Qt.MouseButton.LeftButton)
    QTest.mouseClick(sample_page.run_button, Qt.MouseButton.LeftButton)

    assert worker.independent_config is not None
    assert worker.independent_config.output_format == "xml"


def test_sample_independent_classes_file_is_passed_to_config(tmp_path: Path) -> None:
    """Independent mode can pass classes from a user-selected classes.txt."""
    qt_app = app()
    worker = RecordingIndependentSampleWorker()
    classes_file = tmp_path / "classes.txt"
    classes_file.write_text("CodeA\nCodeB\n", encoding="utf-8")
    window = make_window(sample_worker=worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["sample"], Qt.MouseButton.LeftButton
    )

    sample_page = window.workbench_view.sample_page
    QTest.mouseClick(
        sample_page.independent_mode_button, Qt.MouseButton.LeftButton
    )
    QTest.mouseClick(sample_page.yolo_output_button, Qt.MouseButton.LeftButton)
    sample_page.independent_source_input.setText(str(tmp_path / "source"))
    sample_page.output_input.setText(str(tmp_path / "dataset"))
    sample_page.classes_input.setText(str(classes_file))
    QTest.mouseClick(sample_page.confirm_move_checkbox, Qt.MouseButton.LeftButton)
    QTest.mouseClick(sample_page.run_button, Qt.MouseButton.LeftButton)

    assert worker.independent_config is not None
    assert worker.independent_config.classes == ["CodeA", "CodeB"]


