"""Scoped tests for the PySide workbench shell."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PIL import Image
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
)

from core.restorer import RestorePreflightResult, RestoreResult
from core.converter import (
    XmlDatasetAnalysis,
    XmlDatasetConvertResult,
    XmlDatasetPaths,
)
from core.scanner import ScanConfig, Scanner
from core.scanner import ScanResult, ScanStatistics
from core.inferencer import InferResult, InferStatistics
from core.label_inspector import InferenceRun, ProductLabel, RunTreeNode
from core.labelimg_launcher import LabelImgLaunchResult, LabelImgValidateResult
from core.trainer import TrainResult
from gui.task_runner import ImmediateTaskRunner
from gui.task_runner import AsyncTaskRunner
from gui.tool_defaults import ToolDefaults, save_tool_defaults
from gui.workbench import MODULES, AutoLabelerWindow
from utils.exceptions import ErrorCode, ErrorInfo
from utils.task_registry import TaskRegistry

_IMMEDIATE_RUNNER = ImmediateTaskRunner()
def app() -> QApplication:
    """Return a QApplication for widget tests."""
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication(sys.argv[:1])
    return instance


def make_window(**kwargs) -> AutoLabelerWindow:
    """Create a test window with synchronous GUI worker execution."""
    kwargs.setdefault("task_runner", _IMMEDIATE_RUNNER)
    return AutoLabelerWindow(**kwargs)


@pytest.fixture(autouse=True)
def close_qt_windows():
    """Close top-level Qt widgets after each test to avoid native handle buildup."""
    yield
    instance = QApplication.instance()
    if instance is None:
        return
    for widget in instance.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    instance.processEvents()


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), color=(128, 128, 128)).save(path)


def set_task_timestamp(
    registry: TaskRegistry,
    task_id: str,
    created_at: str,
    finished_at: str | None = None,
) -> None:
    """Force deterministic task timestamps in GUI tests."""
    task = registry.get(task_id)
    task.created_at = created_at
    if finished_at is not None:
        task.finished_at = finished_at
    registry._persist(task)


def make_scanned_site(site: Path) -> None:
    """Create a site folder and mapping for GUI sampling tests."""
    make_image(site / "CodeA" / "Product1" / "a1.jpg")
    Scanner().scan(ScanConfig(site_folder=site))


def test_module_catalog_matches_ui_spec() -> None:
    """The shell exposes the eight owner-confirmed module entries in order."""
    assert [module.key for module in MODULES] == [
        "scan",
        "sample",
        "label",
        "train",
        "infer",
        "review",
        "restore",
        "convert",
    ]
    assert [module.title for module in MODULES] == [
        "扫描",
        "抽样",
        "标注",
        "训练",
        "推理",
        "复核",
        "还原",
        "转换",
    ]


def test_login_enters_workbench() -> None:
    """Demo login switches from the login view to the workbench shell."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()

    assert window.login_view.isVisible()
    assert not window.workbench_view.isVisible()

    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    assert not window.login_view.isVisible()
    assert window.workbench_view.isVisible()
    assert window.workbench_view.current_module_key() == "home"


def test_login_surface_has_populated_workflow_panel() -> None:
    """Login page presents the product workflow instead of a mostly empty panel."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()

    panel = window.login_view.login_workflow_panel
    assert panel.objectName() == "loginWorkflowPanel"
    steps = panel.findChildren(QLabel, "loginWorkflowStep")
    assert len(steps) == 6
    assert "扫描" in steps[0].text()
    assert "还原" in steps[-1].text()
    boundary_items = window.login_view.login_boundary_panel.findChildren(
        QLabel, "loginBoundaryItem"
    )
    assert len(boundary_items) == 4
    assert "mapping.json" in boundary_items[1].text()
    assert "预检" in boundary_items[2].text()


def test_login_surface_marks_distinct_visual_regions() -> None:
    """Login page separates product value, safety boundaries, and local access."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()

    assert window.login_view.login_story.property("surfaceRole") == "product"
    assert window.login_view.login_card.property("surfaceRole") == "access"
    assert window.login_view.login_workflow_panel.property("surfaceRole") == "workflow"
    assert window.login_view.login_boundary_panel.property("surfaceRole") == "boundary"
    assert window.login_view.demo_login_button.property("buttonRole") == "primaryAccess"


def test_workbench_registers_chinese_capable_ui_font() -> None:
    """The desktop shell uses a CJK-capable font so Chinese copy renders."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()

    expected_families = {
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "Noto Sans SC",
        "SimHei",
        "SimSun",
    }

    assert expected_families.intersection(set(QFontDatabase.families()))
    assert qt_app.font().family() in expected_families


def test_homepage_module_tiles_use_compact_product_copy() -> None:
    """Homepage module entries use workflow order and user-value copy."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    assert len(window.workbench_view.home_module_buttons) == 8
    assert [
        button.findChild(QLabel, "moduleTitleText").text()
        for button in window.workbench_view.home_module_buttons
    ] == [
        "01 扫描",
        "02 抽样",
        "03 标注",
        "04 训练",
        "05 推理",
        "06 复核",
        "07 还原",
        "08 转换",
    ]
    copy = [label.text() for label in window.workbench_view.home_module_descriptions]
    assert "不靠人记路径" in copy[0]
    assert "少标一批代表图" in copy[1]
    assert "人只修需要修的结果" in copy[4]


def test_homepage_module_cards_have_no_default_featured_tile() -> None:
    """Homepage module cards are neutral until hover or activation."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    assert [
        button.objectName() for button in window.workbench_view.home_module_buttons
    ] == ["moduleCardButton"] * len(MODULES)


def test_homepage_module_card_clicks_from_blank_area() -> None:
    """Clicking anywhere inside a module card opens that module."""
    qt_app = app()
    window = make_window()
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()

    train_card = window.workbench_view.home_module_buttons[3]
    click_point = QPoint(train_card.width() - 12, train_card.height() - 12)
    QTest.mouseClick(train_card, Qt.MouseButton.LeftButton, pos=click_point)

    assert window.workbench_view.current_module_key() == "train"


def test_homepage_fits_small_desktop_window() -> None:
    """Homepage stays within the app's small desktop baseline height."""
    qt_app = app()
    window = make_window()
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()

    assert window.workbench_view.home_page.sizeHint().height() <= 680
    assert not window.workbench_view.home_ai_preview.isVisible()
    assert "tasks" in window.workbench_view.nav_buttons


def test_homepage_module_titles_fit_small_desktop_width() -> None:
    """Homepage module titles have enough room in the small desktop baseline."""
    qt_app = app()
    window = make_window()
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()

    for button in window.workbench_view.home_module_buttons:
        assert button.width() >= button.sizeHint().width()


def test_homepage_module_cards_keep_readable_height() -> None:
    """Whole-card buttons remain readable after replacing title-only links."""
    qt_app = app()
    window = make_window()
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()

    for button in window.workbench_view.home_module_buttons:
        title = button.findChild(QLabel, "moduleTitleText")
        description = button.findChild(QLabel, "moduleDescription")
        assert button.height() >= 96
        assert title is not None and title.isVisible()
        assert description is not None and description.isVisible()


def test_homepage_uses_workbench_layout_not_empty_hero() -> None:
    """Homepage uses a restrained workbench layout with preview-only AI."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    assert window.workbench_view.home_support_panel.objectName() == "homeSupportPanel"
    assert window.workbench_view.home_module_panel.objectName() == "homeModulePanel"
    assert window.workbench_view.home_ai_preview.objectName() == "aiPreview"
    assert window.workbench_view.home_ai_preview.isVisible()
    assert window.workbench_view.home_developer_label.text() == "开发者：rui"
    assert window.workbench_view.home_ai_status.text() == "PREVIEW"
    assert not window.workbench_view.home_ai_send_button.isEnabled()
    strengths = [
        label.text() for label in window.workbench_view.home_strength_titles
    ]
    assert strengths == [
        "可追溯",
        "省人工",
        "防误操作",
        "可独立运行",
    ]


def test_side_nav_uses_structured_flow_entries() -> None:
    """Main workflow navigation exposes scannable number, title, and subtitle."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    flow_buttons = window.workbench_view.nav_flow_buttons

    assert len(flow_buttons) == len(MODULES)
    assert [button.objectName() for button in flow_buttons] == [
        "navFlowButton"
    ] * len(MODULES)
    assert [button.text() for button in flow_buttons] == [""] * len(MODULES)
    assert [
        button.findChild(QLabel, "navStepNumber").text()
        for button in flow_buttons
    ] == [f"{index:02d}" for index in range(1, len(MODULES) + 1)]
    assert [
        button.findChild(QLabel, "navStepTitle").text()
        for button in flow_buttons
    ] == [module.title for module in MODULES]
    assert [
        button.findChild(QLabel, "navStepSubtitle").text()
        for button in flow_buttons
    ] == [module.subtitle for module in MODULES]


def test_homepage_strengths_render_as_single_band() -> None:
    """System strengths use one stable row instead of staggered mini cards."""
    qt_app = app()
    window = make_window()
    window.resize(1366, 768)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()

    band = window.workbench_view.home_strength_band
    items = window.workbench_view.home_strength_items

    assert band.objectName() == "homeStrengthBand"
    assert len(items) == 4
    assert {item.objectName() for item in items} == {"strengthItem"}
    assert {item.geometry().y() for item in items} == {items[0].geometry().y()}
    assert max(item.height() for item in items) - min(
        item.height() for item in items
    ) <= 2


def test_window_uses_async_task_runner_by_default() -> None:
    """Production window uses an async runner unless tests inject one."""
    app()
    window = AutoLabelerWindow()

    assert isinstance(window.workbench_view._task_runner, AsyncTaskRunner)


def test_task_center_lists_recent_registry_tasks(tmp_path: Path) -> None:
    """Task center groups recent tasks and exposes terminal-task deletion."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    now = datetime.now().replace(microsecond=0)
    today = now.replace(hour=11, minute=0, second=0)
    yesterday = today - timedelta(days=1)
    before_yesterday = today - timedelta(days=2)
    old_visible_cutoff = today - timedelta(days=3)
    stale = today - timedelta(days=11)
    scan_task = registry.create_task("scan")
    registry.start_task(scan_task.task_id, total=3, message="扫描")
    registry.succeed_task(
        scan_task.task_id,
        result={
            "mapping_path": "C:/project/.autolabeler/mapping.json",
            "classes_path": "C:/project/.autolabeler/classes.txt",
            "statistics": {
                "image_count": 66,
                "class_count": 8,
                "product_count": 4,
            },
        },
    )
    set_task_timestamp(
        registry,
        scan_task.task_id,
        today.strftime("%Y-%m-%d %H:%M:%S"),
        today.strftime("%Y-%m-%d %H:%M:%S"),
    )
    convert_task = registry.create_task("convert")
    registry.start_task(convert_task.task_id, total=299, message="转换")
    registry.succeed_task(
        convert_task.task_id,
        result={
            "dataset_dir": "C:/Users/0263488/Desktop/ARS/model1/pic_yolo_train",
            "paths": {
                "images_train": "C:/Users/0263488/Desktop/ARS/model1/pic_yolo_train/images/train",
                "data_yaml": "C:/Users/0263488/Desktop/ARS/model1/pic_yolo_train/data.yaml",
            },
            "total_pairs": 299,
            "train_count": 264,
            "val_count": 35,
            "class_count": 10,
        },
    )
    set_task_timestamp(
        registry,
        convert_task.task_id,
        yesterday.strftime("%Y-%m-%d %H:%M:%S"),
        yesterday.strftime("%Y-%m-%d %H:%M:%S"),
    )
    train_task = registry.create_task("train")
    registry.start_task(train_task.task_id, total=1, message="训练")
    registry.fail_task(
        train_task.task_id,
        ErrorCode.TRAIN_BASE_MODEL_NOT_FOUND,
        "模型不存在",
        details="best.pt",
    )
    set_task_timestamp(
        registry,
        train_task.task_id,
        before_yesterday.strftime("%Y-%m-%d %H:%M:%S"),
        before_yesterday.strftime("%Y-%m-%d %H:%M:%S"),
    )
    running_task = registry.create_task("infer")
    registry.start_task(running_task.task_id, total=12, message="推理中")
    set_task_timestamp(
        registry,
        running_task.task_id,
        today.strftime("%Y-%m-%d %H:%M:%S"),
    )
    older_recent_task = registry.create_task("labelimg")
    registry.start_task(older_recent_task.task_id, total=0, message="标注")
    registry.succeed_task(older_recent_task.task_id, result={"started": True})
    set_task_timestamp(
        registry,
        older_recent_task.task_id,
        old_visible_cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        old_visible_cutoff.strftime("%Y-%m-%d %H:%M:%S"),
    )
    stale_task = registry.create_task("restore")
    registry.start_task(stale_task.task_id, total=1, message="还原")
    registry.succeed_task(stale_task.task_id, result={"total": 1, "success": 1})
    set_task_timestamp(
        registry,
        stale_task.task_id,
        stale.strftime("%Y-%m-%d %H:%M:%S"),
        stale.strftime("%Y-%m-%d %H:%M:%S"),
    )
    window = make_window(task_registry=registry)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    assert "tasks" in window.workbench_view.nav_buttons
    QTest.mouseClick(
        window.workbench_view.nav_buttons["tasks"], Qt.MouseButton.LeftButton
    )

    assert window.workbench_view.current_module_key() == "tasks"
    assert window.workbench_view.task_center_summary_panel.objectName() == (
        "taskCenterSummaryPanel"
    )
    rows = window.workbench_view.task_center_list_panel.findChildren(QFrame, "taskRow")
    assert len(rows) == 5
    text = "\n".join(
        label.text()
        for row in rows
        for label in row.findChildren(QLabel)
    )
    all_list_text = "\n".join(
        label.text()
        for label in window.workbench_view.task_center_list_panel.findChildren(QLabel)
    )
    summary_text = "\n".join(
        label.text()
        for label in window.workbench_view.task_center_summary_panel.findChildren(
            QLabel
        )
    )
    group_headers = [
        label.text()
        for label in window.workbench_view.task_center_list_panel.findChildren(
            QLabel, "taskDateHeader"
        )
    ]
    assert "运行中" in summary_text
    assert "保留期完成" in summary_text
    assert "需要处理" in summary_text
    assert "保留策略" in summary_text
    assert "10天" in summary_text
    assert "最新产出" not in summary_text
    assert "3" in summary_text
    assert "1" in summary_text
    assert group_headers == [
        "今天",
        "昨天",
        "前天",
        old_visible_cutoff.strftime("%Y-%m-%d"),
    ]
    assert "扫描 · 已完成" in text
    assert "推理 · 运行中" in text
    assert "开始于" in text
    assert "完成于" in text
    assert "扫描 66 张图片，识别 8 个类别，覆盖 4 个产品组。" in text
    assert "转换 · 已完成" in text
    assert "已生成 YOLO 数据集，299 对图片/XML，训练集 264 张，验证集 35 张，类别 10 个。" in text
    assert "输出：C:/Users/.../pic_yolo_train" in text
    assert "{'mapping_path'" not in text
    assert "paths" not in text
    assert "images_train" not in text
    assert "data_yaml" not in text
    assert "训练 · 失败" in text
    assert "失败原因：模型不存在" in text
    assert "TRAIN_BASE_MODEL_NOT_FOUND" not in text
    assert "标注 · 已完成" in all_list_text
    assert "还原 · 已完成" not in all_list_text
    assert stale_task.task_id not in {task.task_id for task in registry.list_tasks()}
    back_buttons = window.workbench_view.task_center_list_panel.findChildren(
        QPushButton, "taskBackButton"
    )
    assert len(back_buttons) == 5
    delete_buttons = window.workbench_view.task_center_list_panel.findChildren(
        QPushButton, "taskDeleteButton"
    )
    assert len(delete_buttons) == 4
    assert (
        window.workbench_view.task_center_scroll.horizontalScrollBarPolicy()
        == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    action_panels = window.workbench_view.task_center_list_panel.findChildren(
        QFrame, "taskRowActions"
    )
    assert len(action_panels) == 5
    assert all(panel.maximumWidth() <= 128 for panel in action_panels)
    assert running_task.task_id not in {
        button.property("task_id") for button in delete_buttons
    }
    summary_buttons = window.workbench_view.task_center_summary_panel.findChildren(
        QPushButton, "taskSummaryButton"
    )
    assert {button.property("filter_key") for button in summary_buttons} == {
        "active",
        "attention",
    }
    active_button = next(
        button
        for button in summary_buttons
        if button.property("filter_key") == "active"
    )
    QTest.mouseClick(active_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()
    active_text = "\n".join(
        label.text()
        for label in window.workbench_view.task_center_list_panel.findChildren(QLabel)
    )
    assert window.workbench_view.task_center_filter_back_button.isVisible()
    assert "推理 · 运行中" in active_text
    assert "扫描 · 已完成" not in active_text

    summary_buttons = window.workbench_view.task_center_summary_panel.findChildren(
        QPushButton, "taskSummaryButton"
    )
    attention_button = next(
        button
        for button in summary_buttons
        if button.property("filter_key") == "attention"
    )
    QTest.mouseClick(attention_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()
    attention_text = "\n".join(
        label.text()
        for label in window.workbench_view.task_center_list_panel.findChildren(QLabel)
    )
    assert "训练 · 失败" in attention_text
    assert "推理 · 运行中" not in attention_text

    QTest.mouseClick(
        window.workbench_view.task_center_filter_back_button, Qt.MouseButton.LeftButton
    )
    qt_app.processEvents()
    assert not window.workbench_view.task_center_filter_back_button.isVisible()
    rows = window.workbench_view.task_center_list_panel.findChildren(QFrame, "taskRow")
    assert len(rows) == 5
    delete_buttons = window.workbench_view.task_center_list_panel.findChildren(
        QPushButton, "taskDeleteButton"
    )
    failed_delete_button = next(
        button
        for button in delete_buttons
        if button.property("task_id") == train_task.task_id
    )
    QTest.mouseClick(failed_delete_button, Qt.MouseButton.LeftButton)
    assert train_task.task_id not in {task.task_id for task in registry.list_tasks()}
    rows_after_delete = window.workbench_view.task_center_list_panel.findChildren(
        QFrame, "taskRow"
    )
    assert len(rows_after_delete) == 4
    back_buttons_after_delete = (
        window.workbench_view.task_center_list_panel.findChildren(
            QPushButton, "taskBackButton"
        )
    )
    scan_button = next(
        button
        for button in back_buttons_after_delete
        if button.property("module_key") == "scan"
    )
    assert scan_button.text() == "回到扫描"
    QTest.mouseClick(scan_button, Qt.MouseButton.LeftButton)
    assert window.workbench_view.current_module_key() == "scan"


def test_task_center_hides_unknown_internal_task_type(tmp_path: Path) -> None:
    """Unknown task types should not become operator-facing module names."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    task = registry.create_task("internal_probe")
    registry.start_task(task.task_id, total=1, message="检查")
    registry.succeed_task(task.task_id, result={"debug_path": "D:/tmp/debug.json"})
    window = make_window(task_registry=registry)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["tasks"], Qt.MouseButton.LeftButton
    )

    text = "\n".join(
        label.text()
        for label in window.workbench_view.task_center_list_panel.findChildren(QLabel)
    )
    back_buttons = window.workbench_view.task_center_list_panel.findChildren(
        QPushButton, "taskBackButton"
    )

    assert "任务 · 已完成" in text
    assert "internal_probe" not in text
    assert "debug_path" not in text
    assert back_buttons[0].text() == "回到首页"
    assert back_buttons[0].property("module_key") == "home"


def test_task_center_refreshes_running_task_progress(tmp_path: Path) -> None:
    """Refreshing the task center shows the latest persisted running progress."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    task = registry.create_task("infer")
    registry.start_task(task.task_id, total=3, message="准备推理")
    window = make_window(task_registry=registry)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["tasks"], Qt.MouseButton.LeftButton
    )
    assert window.workbench_view._task_center_timer.isActive()

    registry.update_progress(task.task_id, current=2, total=3, message="已推理 2/3")
    window.workbench_view.refresh_task_center()

    text = "\n".join(
        label.text()
        for label in window.workbench_view.task_center_list_panel.findChildren(QLabel)
    )
    assert "推理 · 运行中" in text
    assert "进度 2/3" in text
    assert "已推理 2/3" in text


def test_manual_entry_opens_manual_page_from_nav_and_home() -> None:
    """Manual entry is a real page from both the sidebar and homepage."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    QTest.mouseClick(
        window.workbench_view.nav_buttons["manual"], Qt.MouseButton.LeftButton
    )

    assert window.workbench_view.current_module_key() == "manual"
    assert window.workbench_view._content_stack.currentWidget() is (
        window.workbench_view.manual_page
    )
    assert window.workbench_view.manual_page.objectName() == "manualPage"
    assert window.workbench_view.manual_steps_panel.objectName() == "manualStepsPanel"
    assert window.workbench_view.manual_steps_panel.sizeHint().height() < 260
    assert window.workbench_view.manual_content_scroll.objectName() == "manualContentScroll"
    assert window.workbench_view.manual_quick_nav_panel.objectName() == "manualQuickNavPanel"
    assert window.workbench_view.manual_steps_panel.parent() is (
        window.workbench_view.manual_overview_section
    )
    assert window.workbench_view.manual_scan_section.objectName() == "manualSection"
    assert window.workbench_view.manual_sample_section.objectName() == "manualSection"
    assert window.workbench_view.manual_label_section.objectName() == "manualSection"
    assert window.workbench_view.manual_train_section.objectName() == "manualSection"
    assert window.workbench_view.manual_infer_section.objectName() == "manualSection"
    assert window.workbench_view.manual_review_section.objectName() == "manualSection"
    assert window.workbench_view.manual_restore_section.objectName() == "manualSection"
    assert window.workbench_view.manual_convert_section.objectName() == "manualSection"
    assert window.workbench_view.manual_support_panel.maximumWidth() <= 220
    assert window.workbench_view.manual_content_scroll.height() > (
        window.workbench_view.manual_steps_panel.height()
    )

    step_buttons = [
        button.text()
        for button in window.workbench_view.manual_steps_panel.findChildren(
            QPushButton
        )
    ]
    assert step_buttons == [
        "01 扫描\n建立 Flow 映射",
        "02 抽样\n减少人工标注量",
        "03 标注\n打开 LabelImg",
        "04 训练\n训练 YOLO 模型",
        "05 推理\n生成预测标签",
        "06 复核\n检查预测结果",
        "07 还原\n写回 XML",
        "08 转换\nXML 与 YOLO 数据转换",
    ]
    review_step_button = next(
        button
        for button in window.workbench_view.manual_steps_panel.findChildren(
            QPushButton
        )
        if button.text().startswith("06 复核")
    )
    QTest.mouseClick(review_step_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()
    assert (
        window.workbench_view.manual_content_scroll.verticalScrollBar().value() > 0
    )

    manual_labels = "\n".join(
        label.text() for label in window.workbench_view.manual_page.findChildren(QLabel)
    )
    assert "00 完整流程" in manual_labels
    assert "01 扫描" in manual_labels
    assert "mapping.json" in manual_labels
    assert "02 抽样" in manual_labels
    assert "count" in manual_labels
    assert "每个分组固定抽取的数量" in manual_labels
    assert "03 标注" in manual_labels
    assert "标签输出目录" in manual_labels
    assert "VOC 标注" in manual_labels
    assert "图片同级" in manual_labels
    assert "04 训练" in manual_labels
    assert "All GPUs / GPU 0 / GPU 1 / GPU 0+1" in manual_labels
    assert "总 batch" in manual_labels
    assert "总 workers" in manual_labels
    assert "optimizer" in manual_labels
    assert "优化器" in manual_labels
    assert "05 推理" in manual_labels
    assert "IoU" in manual_labels
    assert "NMS 去重阈值" in manual_labels
    assert "06 复核" in manual_labels
    assert "run/labels" in manual_labels
    assert "07 还原" in manual_labels
    assert "预检失败时不会写任何 XML" in manual_labels
    assert "08 转换" in manual_labels
    assert "XML 转 YOLO" in manual_labels
    assert "其他功能" not in manual_labels
    right_labels = "\n".join(
        label.text()
        for label in window.workbench_view.manual_support_panel.findChildren(QLabel)
    )
    right_buttons = [
        button.text()
        for button in window.workbench_view.manual_support_panel.findChildren(
            QPushButton
        )
    ]
    assert right_buttons == [
        "00 完整流程",
        "01 扫描",
        "02 抽样",
        "03 标注",
        "04 训练",
        "05 推理",
        "06 复核",
        "07 还原",
        "08 转换",
    ]
    assert "推荐起步" not in right_labels
    assert "高风险提醒" not in right_labels

    QTest.mouseClick(window.workbench_view.nav_buttons["home"], Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.home_manual_button, Qt.MouseButton.LeftButton
    )

    assert window.workbench_view.current_module_key() == "manual"
    assert window.workbench_view._content_stack.currentWidget() is (
        window.workbench_view.manual_page
    )


def test_settings_entry_opens_settings_page() -> None:
    """Settings entry opens a dedicated first-version settings page."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    QTest.mouseClick(
        window.workbench_view.nav_buttons["settings"], Qt.MouseButton.LeftButton
    )

    assert window.workbench_view.current_module_key() == "settings"
    assert window.workbench_view._content_stack.currentWidget() is (
        window.workbench_view.settings_page
    )
    assert window.workbench_view.settings_page.objectName() == "settingsPage"
    assert window.workbench_view.settings_status_panel.objectName() == "settingsStatusPanel"
    assert (
        window.workbench_view.settings_content_scroll.objectName()
        == "settingsContentScroll"
    )
    assert (
        window.workbench_view.settings_quick_nav_panel.objectName()
        == "settingsQuickNavPanel"
    )
    assert window.workbench_view.settings_support_panel.maximumWidth() <= 220
    assert window.workbench_view.settings_content_scroll.height() > (
        window.workbench_view.settings_status_panel.height()
    )
    settings = window.workbench_view
    nav_buttons = settings.settings_quick_nav_panel.findChildren(QPushButton)
    assert [button.text() for button in nav_buttons] == [
        "01 抽样",
        "02 训练",
        "03 推理",
        "04 转换",
        "05 保存边界",
    ]
    assert settings.settings_status_panel.parentWidget() is (
        settings.settings_content_scroll.widget()
    )
    right_labels = [
        label.text()
        for label in settings.settings_support_panel.findChildren(QLabel)
    ]
    assert "不保存路径" not in right_labels
    assert "不保存覆盖确认" not in right_labels
    assert "路径不保存" not in right_labels
    assert "风险项不保存" not in right_labels
    assert not any("tool_defaults.json" in text for text in right_labels)

    QTest.mouseClick(nav_buttons[-1], Qt.MouseButton.LeftButton)
    qt_app.processEvents()
    assert settings.settings_content_scroll.verticalScrollBar().value() > 0


def test_settings_page_saves_tool_parameter_defaults(tmp_path: Path) -> None:
    """Settings edits non-path tool defaults and applies them to tool pages."""
    qt_app = app()
    defaults_path = tmp_path / "tool_defaults.json"
    window = make_window(defaults_path=defaults_path)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["settings"], Qt.MouseButton.LeftButton
    )

    settings = window.workbench_view
    assert settings.settings_defaults_path.text().endswith("tool_defaults.json")
    settings.settings_sample_strategy_input.setCurrentText("ratio")
    settings.settings_sample_count_input.setText("12")
    settings.settings_sample_ratio_input.setText("0.42")
    settings.settings_sample_train_ratio_input.setText("0.8")
    settings.settings_train_epochs_input.setText("33")
    settings.settings_train_batch_input.setText("4")
    settings.settings_train_device_input.setCurrentText("All GPUs")
    settings.settings_train_optimizer_input.setCurrentText("SGD")
    settings.settings_train_workers_input.setText("6")
    settings.settings_infer_confidence_input.setText("0.35")
    settings.settings_infer_iou_input.setText("0.6")
    settings.settings_infer_batch_input.setText("16")
    settings.settings_infer_label_y_offset_input.setText("5")
    settings.settings_infer_device_input.setCurrentText("cpu")
    settings.settings_convert_train_ratio_input.setText("0.7")
    QTest.mouseClick(settings.settings_save_button, Qt.MouseButton.LeftButton)

    assert defaults_path.exists()
    saved_defaults = json.loads(defaults_path.read_text(encoding="utf-8"))
    assert set(saved_defaults) == {"sample", "train", "infer", "convert"}
    assert set(saved_defaults["sample"]) == {
        "mode",
        "count",
        "ratio",
        "min_count",
        "max_count",
        "full_threshold",
        "train_ratio",
    }
    assert set(saved_defaults["train"]) == {
        "device",
        "epochs",
        "image_size",
        "batch_size",
        "patience",
        "workers",
        "optimizer",
        "lr0",
        "box",
        "cls",
        "dfl",
        "scale",
        "cache",
    }
    assert set(saved_defaults["infer"]) == {
        "confidence",
        "iou",
        "batch_size",
        "label_y_offset_px",
        "device",
    }
    assert set(saved_defaults["convert"]) == {"train_ratio"}
    assert "默认值已保存" in settings.settings_result_summary.text()
    assert settings.sample_page.ratio_strategy_button.isChecked()
    assert settings.sample_page.count_input.text() == "12"
    assert settings.sample_page.ratio_input.text() == "0.42"
    assert settings.sample_page.train_ratio_input.text() == "0.8"
    assert settings.sample_page.flow_site_input.text() == ""
    assert settings.sample_page.output_input.text() == ""
    assert settings.train_page.epochs_input.text() == "33"
    assert settings.train_page.batch_input.text() == "4"
    assert saved_defaults["train"]["device"] == "gpu"
    assert settings.train_page.device_input.currentText() == "All GPUs"
    assert settings.train_page.optimizer_input.currentText() == "SGD"
    assert settings.train_page.workers_input.text() == "6"
    assert settings.train_page.dataset_input.text() == ""
    assert settings.train_page.output_input.text() == ""
    assert settings.infer_page.confidence_input.text() == "0.35"
    assert settings.infer_page.iou_input.text() == "0.6"
    assert settings.infer_page.batch_input.text() == "16"
    assert settings.infer_page.label_y_offset_input.text() == "5"
    assert settings.infer_page.device_input.currentText() == "cpu"
    assert settings.infer_page.model_input.text() == ""
    assert settings.convert_page.train_ratio_input.text() == "0.7"
    assert not settings.train_page.overwrite_output_checkbox.isChecked()
    assert settings.train_page.run_name_input.text() == ""
    assert not settings.infer_page.overwrite_output_checkbox.isChecked()
    assert not settings.convert_page.overwrite_checkbox.isChecked()
    assert not settings.restore_page.overwrite_checkbox.isChecked()
    assert not settings.restore_page.confirm_write_checkbox.isChecked()
    assert not settings.sample_page.confirm_move_checkbox.isChecked()


def test_settings_page_blocks_invalid_default_values(tmp_path: Path) -> None:
    """Settings validates defaults before writing tool_defaults.json."""
    qt_app = app()
    defaults_path = tmp_path / "tool_defaults.json"
    save_tool_defaults(ToolDefaults(sample={"count": "9"}), defaults_path)
    original_text = defaults_path.read_text(encoding="utf-8")
    window = make_window(defaults_path=defaults_path)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["settings"], Qt.MouseButton.LeftButton
    )

    settings = window.workbench_view
    settings.settings_sample_ratio_input.setText("1.5")
    QTest.mouseClick(settings.settings_save_button, Qt.MouseButton.LeftButton)

    assert "默认值未保存" in settings.settings_result_summary.text()
    assert "抽样 ratio" in settings.settings_result_summary.text()
    assert defaults_path.read_text(encoding="utf-8") == original_text


def test_window_loads_persisted_tool_parameter_defaults(tmp_path: Path) -> None:
    """Persisted defaults are loaded when a new workbench is created."""
    qt_app = app()
    defaults_path = tmp_path / "tool_defaults.json"
    save_tool_defaults(
        ToolDefaults(
            sample={"mode": "count", "count": 9, "train_ratio": 0.75},
            train={
                "epochs": 44,
                "batch_size": 2,
                "device": "cpu",
                "run_name": "stale-run",
                "overwrite_output": True,
            },
            infer={
                "confidence": 0.45,
                "iou": 0.55,
                "batch_size": 8,
                "label_y_offset_px": 3,
                "overwrite_output": True,
            },
            convert={"train_ratio": 0.65, "overwrite_output": True},
            restore={"overwrite": True},
        ),
        defaults_path,
    )
    window = make_window(defaults_path=defaults_path)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    assert window.workbench_view.sample_page.count_strategy_button.isChecked()
    assert window.workbench_view.sample_page.count_input.text() == "9"
    assert window.workbench_view.sample_page.train_ratio_input.text() == "0.75"
    assert window.workbench_view.train_page.epochs_input.text() == "44"
    assert window.workbench_view.train_page.batch_input.text() == "2"
    assert window.workbench_view.train_page.device_input.currentText() == "cpu"
    assert window.workbench_view.infer_page.confidence_input.text() == "0.45"
    assert window.workbench_view.infer_page.iou_input.text() == "0.55"
    assert window.workbench_view.infer_page.batch_input.text() == "8"
    assert window.workbench_view.infer_page.label_y_offset_input.text() == "3"
    assert window.workbench_view.convert_page.train_ratio_input.text() == "0.65"
    assert window.workbench_view.train_page.run_name_input.text() == ""
    assert not window.workbench_view.train_page.overwrite_output_checkbox.isChecked()
    assert not window.workbench_view.infer_page.overwrite_output_checkbox.isChecked()
    assert not window.workbench_view.convert_page.overwrite_checkbox.isChecked()
    assert not window.workbench_view.restore_page.overwrite_checkbox.isChecked()


def test_sample_navigation_shows_shared_tool_page() -> None:
    """The Sample nav item opens the shared left/right workbench layout."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    QTest.mouseClick(
        window.workbench_view.nav_buttons["sample"], Qt.MouseButton.LeftButton
    )

    assert window.workbench_view.current_module_key() == "sample"
    sample_page = window.workbench_view.sample_page
    assert sample_page.ai_assistant_panel.objectName() == "rightSupportPanel"
    assert sample_page.log_box.objectName() == "logBox"
    assert sample_page.log_box.minimumHeight() <= 180
    assert sample_page.left_main_panel.objectName() == "leftMainPanel"
    assert sample_page.right_support_panel.objectName() == "rightSupportPanel"


def test_tool_pages_use_right_support_panel_with_preview_only_ai() -> None:
    """Tool pages use left-side logs and a persistent support panel."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    pages_with_logs = {
        "scan": window.workbench_view.scan_page,
        "sample": window.workbench_view.sample_page,
        "label": window.workbench_view.label_page,
        "train": window.workbench_view.train_page,
        "infer": window.workbench_view.infer_page,
        "restore": window.workbench_view.restore_page,
        "convert": window.workbench_view.convert_page,
    }
    for key, page in pages_with_logs.items():
        QTest.mouseClick(
            window.workbench_view.nav_buttons[key],
            Qt.MouseButton.LeftButton,
        )
        qt_app.processEvents()

        assert not hasattr(page, "task_tab_button")
        assert not hasattr(page, "ai_tab_button")
        assert page.log_box.objectName() == "logBox"
        assert page.ai_assistant_panel.objectName() == "rightSupportPanel"
        assert page.right_support_panel is page.ai_assistant_panel
        assert page.right_support_panel.layout().spacing() <= 10
        assert page.left_main_panel.layout().spacing() <= 10
        assert page.log_box.parent() is page.left_main_panel
        assert "任务状态" in page.right_support_panel.findChildren(QLabel)[0].text()
        preview_inputs = [
            child
            for child in page.right_support_panel.findChildren(QTextEdit)
            if child.objectName() == "aiRailInput"
        ]
        assert preview_inputs
        assert not preview_inputs[0].isEnabled()

    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"],
        Qt.MouseButton.LeftButton,
    )
    qt_app.processEvents()

    review_page = window.workbench_view.review_page
    assert not hasattr(review_page, "log_box")
    assert review_page.ai_assistant_panel.objectName() == "rightSupportPanel"
    assert review_page.right_support_panel is review_page.ai_assistant_panel


def test_tool_feedback_labels_do_not_expand_pages_with_long_paths() -> None:
    """Long result/status paths must not push action buttons out of view."""
    qt_app = app()
    window = make_window()
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    long_path = "D:/" + "/".join([("segment" * 8)] * 8) + "/output.xml"
    pages = [
        window.workbench_view.sample_page,
        window.workbench_view.train_page,
        window.workbench_view.infer_page,
        window.workbench_view.restore_page,
        window.workbench_view.convert_page,
        window.workbench_view.scan_page,
        window.workbench_view.label_page,
        window.workbench_view.review_page,
    ]
    labels_by_page = {
        window.workbench_view.sample_page: [
            window.workbench_view.sample_page.result_summary,
            window.workbench_view.sample_page.preflight_impact_summary,
            window.workbench_view.sample_page.preflight_risk_summary,
        ],
        window.workbench_view.train_page: [
            window.workbench_view.train_page.result_summary,
            window.workbench_view.train_page.runtime_detail_label,
        ],
        window.workbench_view.infer_page: [
            window.workbench_view.infer_page.result_summary,
            window.workbench_view.infer_page.run_path_preview,
        ],
        window.workbench_view.restore_page: [
            window.workbench_view.restore_page.result_summary,
            window.workbench_view.restore_page.preflight_match_summary,
            window.workbench_view.restore_page.preflight_write_summary,
        ],
        window.workbench_view.convert_page: [
            window.workbench_view.convert_page.result_summary,
            window.workbench_view.convert_page.analysis_class_summary,
            window.workbench_view.convert_page.analysis_risk_summary,
        ],
        window.workbench_view.scan_page: [
            window.workbench_view.scan_page.result_summary,
        ],
        window.workbench_view.label_page: [
            window.workbench_view.label_page.result_summary,
        ],
        window.workbench_view.review_page: [
            window.workbench_view.review_page.result_summary,
            window.workbench_view.review_page.review_status_summary,
        ],
    }

    for page in pages:
        for label in labels_by_page[page]:
            label.setText(f"输出：{long_path}")
        qt_app.processEvents()
        scroll = page.findChild(QScrollArea, "toolScrollArea")
        assert scroll is not None
        assert page.left_main_panel.minimumSizeHint().width() <= (
            scroll.viewport().width() + 8
        )


def test_tool_pages_mark_explanations_results_and_risks_by_role() -> None:
    """Dense tool pages expose stable visual roles for help, status, and risk areas."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)

    sample_page = window.workbench_view.sample_page
    restore_page = window.workbench_view.restore_page
    convert_page = window.workbench_view.convert_page

    assert sample_page.mode_note.property("feedbackRole") == "explanation"
    assert sample_page.mapping_status.property("feedbackRole") == "status"
    assert sample_page.result_summary.property("feedbackRole") == "result"
    assert sample_page.preflight_impact_summary.property("feedbackRole") == "output"
    assert sample_page.preflight_risk_summary.property("feedbackRole") == "risk"
    assert sample_page.confirm_move_checkbox.property("buttonRole") == "riskConfirm"

    assert restore_page.mode_note.property("feedbackRole") == "explanation"
    assert restore_page.result_summary.property("feedbackRole") == "result"
    assert restore_page.preflight_match_summary.property("feedbackRole") == "output"
    assert restore_page.preflight_write_summary.property("feedbackRole") == "risk"
    assert restore_page.confirm_write_checkbox.property("feedbackRole") == "riskConfirm"

    assert convert_page.result_summary.property("feedbackRole") == "result"
    assert convert_page.analysis_class_summary.property("feedbackRole") == "output"
    assert convert_page.analysis_risk_summary.property("feedbackRole") == "risk"
    assert convert_page.confirm_classes_checkbox.property("feedbackRole") == "riskConfirm"


def test_workbench_stylesheet_targets_visual_roles() -> None:
    """The shared stylesheet owns role-based contrast for dense GUI pages."""
    app()
    window = make_window()
    stylesheet = window.styleSheet()

    assert 'surfaceRole="product"' in stylesheet
    assert 'surfaceRole="access"' in stylesheet
    assert 'feedbackRole="explanation"' in stylesheet
    assert 'feedbackRole="result"' in stylesheet
    assert 'feedbackRole="risk"' in stylesheet
    assert 'buttonRole="riskConfirm"' in stylesheet


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


def test_train_page_shows_common_options_and_hides_advanced_by_default() -> None:
    """Train page keeps common options visible and hides rarer YOLO parameters."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    assert hasattr(train_page, "common_options_panel")
    assert train_page.common_options_panel.isVisible()
    assert hasattr(train_page, "advanced_toggle_button")
    assert hasattr(train_page, "advanced_options_panel")
    assert not train_page.advanced_options_panel.isVisible()
    assert train_page.device_input.currentText() == "auto"
    assert train_page.runtime_status_label.text() == "等待训练"
    assert "设备" in train_page.runtime_detail_label.text()
    assert hasattr(train_page, "stop_button")
    assert not train_page.stop_button.isEnabled()


def test_infer_page_shows_common_settings_and_hides_rare_advanced_options() -> None:
    """Infer page keeps common prediction settings visible by default."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    assert infer_page.flow_source_unsampled.text() == "未抽样图片（默认）"
    assert infer_page.flow_source_all.text() == "全部扫描图片（含已抽样）"
    assert hasattr(infer_page, "common_options_panel")
    assert infer_page.common_options_panel.isVisible()
    assert infer_page.confidence_input.isVisible()
    assert infer_page.iou_input.isVisible()
    assert infer_page.batch_input.isVisible()
    assert "NMS" in infer_page.iou_input.toolTip()
    assert infer_page.device_input.currentText() == "auto"
    assert hasattr(infer_page, "advanced_toggle_button")
    assert hasattr(infer_page, "advanced_options_panel")
    assert not infer_page.advanced_options_panel.isVisible()
    assert isinstance(infer_page.overwrite_output_checkbox, QCheckBox)
    assert hasattr(infer_page, "stop_button")
    assert not infer_page.stop_button.isEnabled()
    assert "run_YYYYMMDD_HHMMSS" in infer_page.run_path_preview.text()
    assert "不改变 sampled" in infer_page.flow_source_note.text()
    infer_page.site_input.setText("D:/site")
    assert "不改变 sampled" in infer_page.flow_source_note.text()
    assert "inference_results" in infer_page.run_path_preview.text()


def test_restore_page_labels_writeback_controls_clearly() -> None:
    """Restore page exposes real write-back controls instead of vague text."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["restore"], Qt.MouseButton.LeftButton
    )

    restore_page = window.workbench_view.restore_page
    assert isinstance(restore_page.overwrite_checkbox, QCheckBox)
    assert isinstance(restore_page.confirm_write_checkbox, QCheckBox)
    assert "已有 XML 冲突" in restore_page.overwrite_checkbox.text()
    assert "允许覆盖" in restore_page.overwrite_checkbox.text()
    assert "写回 XML 到原图同级目录" in restore_page.confirm_write_checkbox.text()
    assert restore_page.confirm_write_checkbox.objectName() == "riskCheckbox"
    assert restore_page.log_box.objectName() == "logBox"


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


def test_app_run_entrypoint_is_importable() -> None:
    """The GUI has an explicit QApplication entry point."""
    from gui.app import run

    assert callable(run)


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


class FakeTrainWorker:
    """Small fake worker that records TrainConfig from the GUI."""

    def __init__(self) -> None:
        self.config = None

    def run(self, config):
        self.config = config
        result = TrainResult(
            best_model=config.output_dir / "train" / "weights" / "best.pt",
            last_model=config.output_dir / "train" / "weights" / "last.pt",
            output_dir=config.output_dir / "train",
            warnings=["labels/val is empty"],
            preflight={"train_images": 3, "val_images": 0, "classes": ["CodeA"]},
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)


class InterruptedTrainWorker:
    """Small fake worker that returns a user-stopped training outcome."""

    def __init__(self) -> None:
        self.config = None

    def run(self, config):
        self.config = config

        class Outcome:
            success = False
            result = None
            task = None
            error = ErrorInfo(
                code=ErrorCode.TRAIN_INTERRUPTED.value,
                message="训练已取消",
                details=None,
                retryable=False,
            )

        return Outcome()


def test_train_page_builds_config_and_renders_result(tmp_path: Path) -> None:
    """Train page builds TrainConfig from main fields and displays output paths."""
    qt_app = app()
    train_worker = FakeTrainWorker()
    window = make_window(train_worker=train_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    dataset = tmp_path / "dataset"
    model = tmp_path / "yolov8n.pt"
    output = tmp_path / "runs"
    train_page.dataset_input.setText(str(dataset))
    train_page.model_input.setText(str(model))
    train_page.output_input.setText(str(output))
    train_page.epochs_input.setText("2")
    train_page.batch_input.setText("1")
    train_page.image_size_input.setText("640")
    train_page.device_input.setCurrentText("cpu")
    QTest.mouseClick(train_page.run_button, Qt.MouseButton.LeftButton)

    assert train_worker.config is not None
    assert train_worker.config.data_yaml == dataset / "data.yaml"
    assert train_worker.config.base_model == model
    assert train_worker.config.output_dir == output
    assert train_worker.config.epochs == 2
    assert train_worker.config.batch_size == 1
    assert train_worker.config.device == "cpu"
    assert "训练完成" in train_page.result_summary.text()
    assert "best.pt" in train_page.log_box.toPlainText()


def test_train_page_accepts_explicit_multi_gpu_device(tmp_path: Path) -> None:
    """Train page exposes explicit CUDA ids and passes selected ids to training."""
    qt_app = app()
    train_worker = FakeTrainWorker()
    window = make_window(train_worker=train_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    device_items = [
        train_page.device_input.itemText(index)
        for index in range(train_page.device_input.count())
    ]
    assert {"All GPUs", "GPU 0", "GPU 1", "GPU 0+1"}.issubset(set(device_items))

    train_page.dataset_input.setText(str(tmp_path / "dataset"))
    train_page.model_input.setText(str(tmp_path / "yolov8n.pt"))
    train_page.output_input.setText(str(tmp_path / "runs"))
    train_page.batch_input.setText("16")
    train_page.workers_input.setText("4")
    train_page.device_input.setCurrentText("GPU 0+1")
    QTest.mouseClick(train_page.run_button, Qt.MouseButton.LeftButton)

    assert train_worker.config is not None
    assert train_worker.config.device == "0,1"
    assert train_worker.config.batch_size == 16
    assert train_worker.config.workers == 4


def test_train_page_builds_advanced_yolo_config(tmp_path: Path) -> None:
    """Train page maps backend-supported rarer YOLO parameters from advanced fields."""
    qt_app = app()
    train_worker = FakeTrainWorker()
    window = make_window(train_worker=train_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    train_page.dataset_input.setText(str(tmp_path / "dataset"))
    train_page.model_input.setText(str(tmp_path / "yolov8n.pt"))
    train_page.output_input.setText(str(tmp_path / "runs"))
    QTest.mouseClick(train_page.advanced_toggle_button, Qt.MouseButton.LeftButton)
    train_page.patience_input.setText("12")
    train_page.workers_input.setText("3")
    train_page.optimizer_input.setCurrentText("SGD")
    train_page.lr0_input.setText("0.02")
    train_page.box_input.setText("8.0")
    train_page.cls_input.setText("0.7")
    train_page.dfl_input.setText("1.9")
    train_page.scale_input.setText("0.3")
    train_page.cache_input.setCurrentText("false")
    train_page.run_name_input.setText("custom_train")
    train_page.overwrite_output_checkbox.setChecked(True)
    QTest.mouseClick(train_page.run_button, Qt.MouseButton.LeftButton)

    assert train_worker.config is not None
    assert train_worker.config.patience == 12
    assert train_worker.config.workers == 3
    assert train_worker.config.optimizer == "SGD"
    assert train_worker.config.lr0 == 0.02
    assert train_worker.config.box == 8.0
    assert train_worker.config.cls == 0.7
    assert train_worker.config.dfl == 1.9
    assert train_worker.config.scale == 0.3
    assert train_worker.config.cache is False
    assert train_worker.config.run_name == "custom_train"
    assert train_worker.config.overwrite_output is True


def test_train_page_renders_persisted_running_progress(tmp_path: Path) -> None:
    """Train page can render persisted epoch progress for a running train task."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    task = registry.create_task("train")
    registry.start_task(task.task_id, total=10, message="准备训练")
    registry.update_progress(task.task_id, current=3, total=10, message="Epoch 3/10")
    window = make_window(task_registry=registry, train_worker=FakeTrainWorker())
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    train_page.refresh_running_progress()

    assert "3/10" in train_page.progress_label.text()
    assert train_page.progress_bar.value() == 3
    assert train_page.progress_bar.maximum() == 10


def test_train_page_stop_button_requests_running_task_cancel(tmp_path: Path) -> None:
    """Train stop button requests cancellation on the active train task."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    task = registry.create_task("train")
    registry.start_task(task.task_id, total=10, message="Epoch 3/10")
    window = make_window(task_registry=registry, train_worker=FakeTrainWorker())
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    train_page.refresh_running_progress()
    assert train_page.stop_button.isEnabled()
    QTest.mouseClick(train_page.stop_button, Qt.MouseButton.LeftButton)

    cancelled = registry.get(task.task_id)
    assert cancelled.status == "running"
    assert cancelled.is_cancel_requested is True
    assert not train_page.stop_button.isEnabled()
    assert "停止" in train_page.result_summary.text()


def test_train_page_renders_interrupted_outcome_as_stopped(tmp_path: Path) -> None:
    """Train page treats worker interruption as a stopped run, not a failure."""
    qt_app = app()
    train_worker = InterruptedTrainWorker()
    window = make_window(train_worker=train_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    train_page.dataset_input.setText(str(tmp_path / "dataset"))
    train_page.model_input.setText(str(tmp_path / "yolov8n.pt"))
    train_page.output_input.setText(str(tmp_path / "runs"))
    QTest.mouseClick(train_page.run_button, Qt.MouseButton.LeftButton)

    assert "停止" in train_page.result_summary.text()
    assert "failed" not in train_page.log_box.toPlainText()


def test_train_page_rejects_empty_paths_before_building_config() -> None:
    """Train page blocks blank paths instead of resolving them as cwd."""
    qt_app = app()
    train_worker = FakeTrainWorker()
    window = make_window(train_worker=train_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    QTest.mouseClick(train_page.run_button, Qt.MouseButton.LeftButton)

    assert train_worker.config is None
    assert "请选择数据集目录" in train_page.result_summary.text()


class FakeInferWorker:
    """Small fake worker that records InferConfig from the GUI."""

    def __init__(self) -> None:
        self.config = None

    def run(self, config):
        self.config = config
        result = InferResult(
            mapping_path=config.site_folder / ".autolabeler" / "mapping.json"
            if config.image_source != "folder"
            else None,
            run_id="run_20260520_112000",
            inference_output_dir=(config.output_base_dir or config.site_folder / ".autolabeler" / "inference_results")
            / "run_20260520_112000",
            config_path=(config.output_base_dir or config.site_folder / ".autolabeler" / "inference_results")
            / "run_20260520_112000"
            / "inference_config.json",
            classes_path=(config.output_base_dir or config.site_folder / ".autolabeler" / "inference_results")
            / "run_20260520_112000"
            / "classes.txt",
            statistics=InferStatistics(
                pending=3,
                processed=3,
                success=3,
                failed=0,
                predicted=2,
                empty_prediction=1,
            ),
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)


class CancelledInferWorker:
    """Small fake infer worker that returns a user-cancelled outcome."""

    def __init__(self) -> None:
        self.config = None

    def run(self, config):
        self.config = config

        class Outcome:
            success = False
            result = None
            task = None
            error = ErrorInfo(
                code=ErrorCode.TASK_CANCELLED.value,
                message="推理任务已取消",
                details=None,
                retryable=False,
            )

        return Outcome()


def test_infer_page_builds_flow_config_and_renders_result(tmp_path: Path) -> None:
    """Infer page builds Flow InferConfig with fixed site output root."""
    qt_app = app()
    infer_worker = FakeInferWorker()
    window = make_window(infer_worker=infer_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    site = tmp_path / "site"
    model = tmp_path / "best.pt"
    infer_page.site_input.setText(str(site))
    infer_page.model_input.setText(str(model))
    infer_page.confidence_input.setText("0.25")
    infer_page.iou_input.setText("0.7")
    infer_page.batch_input.setText("1")
    infer_page.label_y_offset_input.setText("4")
    infer_page.device_input.setCurrentText("cpu")
    infer_page.overwrite_output_checkbox.setChecked(True)
    QTest.mouseClick(infer_page.run_button, Qt.MouseButton.LeftButton)

    assert infer_worker.config is not None
    assert infer_worker.config.model_path == model
    assert infer_worker.config.site_folder == site
    assert infer_worker.config.image_source == "unsampled"
    assert infer_worker.config.output_base_dir is None
    assert infer_worker.config.overwrite_output is True
    assert infer_worker.config.label_y_offset_px == 4
    assert "推理完成" in infer_page.result_summary.text()
    assert "run_20260520_112000" in infer_page.log_box.toPlainText()


def test_infer_page_stop_button_requests_running_task_cancel(tmp_path: Path) -> None:
    """Infer stop button requests cancellation on the active infer task."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    task = registry.create_task("infer")
    registry.start_task(task.task_id, total=3, message="正在推理")
    window = make_window(task_registry=registry, infer_worker=FakeInferWorker())
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    infer_page.refresh_running_progress()
    assert infer_page.stop_button.isEnabled()
    QTest.mouseClick(infer_page.stop_button, Qt.MouseButton.LeftButton)

    cancelled = registry.get(task.task_id)
    assert cancelled.status == "running"
    assert cancelled.is_cancel_requested is True
    assert not infer_page.stop_button.isEnabled()
    assert "停止" in infer_page.result_summary.text()


def test_infer_page_renders_cancelled_outcome_as_stopped(tmp_path: Path) -> None:
    """Infer page treats worker cancellation as a stopped run, not a failure."""
    qt_app = app()
    infer_worker = CancelledInferWorker()
    window = make_window(infer_worker=infer_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    infer_page.site_input.setText(str(tmp_path / "site"))
    infer_page.model_input.setText(str(tmp_path / "best.pt"))
    QTest.mouseClick(infer_page.run_button, Qt.MouseButton.LeftButton)

    assert "停止" in infer_page.result_summary.text()
    assert "failed" not in infer_page.log_box.toPlainText()


def test_infer_page_renders_persisted_running_progress(tmp_path: Path) -> None:
    """Infer page can render persisted progress for a running inference task."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    task = registry.create_task("infer")
    registry.start_task(task.task_id, total=1000, message="准备推理")
    registry.update_progress(task.task_id, current=275, total=1000, message="已推理 275/1000")
    window = make_window(task_registry=registry, infer_worker=FakeInferWorker())
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    infer_page.refresh_running_progress()

    assert "275/1000" in infer_page.progress_label.text()
    assert infer_page.progress_bar.value() == 275
    assert infer_page.progress_bar.maximum() == 1000


def test_infer_page_keeps_waiting_before_task_is_registered(tmp_path: Path) -> None:
    """Infer page polling does not stop before the worker creates its task."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    window = make_window(task_registry=registry, infer_worker=FakeInferWorker())
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    infer_page._infer_running = True
    infer_page._progress_timer.start()
    infer_page.refresh_running_progress()

    assert infer_page._progress_timer.isActive()
    assert "等待任务登记" in infer_page.progress_label.text()


def test_infer_page_builds_independent_folder_config(tmp_path: Path) -> None:
    """Infer page independent mode uses image_folder and output root without mapping."""
    qt_app = app()
    infer_worker = FakeInferWorker()
    window = make_window(infer_worker=infer_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    QTest.mouseClick(infer_page.independent_mode_button, Qt.MouseButton.LeftButton)
    image_root = tmp_path / "images"
    output_root = tmp_path / "runs"
    model = tmp_path / "best.pt"
    infer_page.image_folder_input.setText(str(image_root))
    infer_page.output_root_input.setText(str(output_root))
    infer_page.model_input.setText(str(model))
    QTest.mouseClick(infer_page.run_button, Qt.MouseButton.LeftButton)

    assert infer_worker.config is not None
    assert infer_worker.config.image_source == "folder"
    assert infer_worker.config.image_folder == image_root
    assert infer_worker.config.output_base_dir == output_root
    assert infer_worker.config.site_folder == image_root


def test_infer_page_rejects_empty_paths_before_building_config() -> None:
    """Infer page blocks blank model/source paths instead of resolving cwd."""
    qt_app = app()
    infer_worker = FakeInferWorker()
    window = make_window(infer_worker=infer_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    QTest.mouseClick(infer_page.run_button, Qt.MouseButton.LeftButton)

    assert infer_worker.config is None
    assert "请选择模型文件" in infer_page.result_summary.text()


class FakeRestoreWorker:
    """Small fake worker that records Restore configs from the GUI."""

    def __init__(self) -> None:
        self.flow_config = None
        self.independent_config = None
        self.preflight_config = None
        self.preflight_independent_config = None

    def preflight(self, config):
        self.preflight_config = config
        result = RestorePreflightResult(
            mode=f"flow-{config.source_type}",
            can_execute=True,
            total_labels=3,
            matched_images=3,
            xml_to_write=3,
            classes_path=config.site_folder / ".autolabeler" / "classes.txt",
            target_folders=[config.site_folder / "CodeA" / "Product1"],
        )

        class Outcome:
            success = True
            error = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)

    def preflight_independent(self, config):
        self.preflight_independent_config = config
        result = RestorePreflightResult(
            mode="independent",
            can_execute=True,
            total_labels=2,
            matched_images=2,
            xml_to_write=2,
            classes_path=config.classes_file or config.label_root / "classes.txt",
            target_folders=[config.image_root / "Product1"],
        )

        class Outcome:
            success = True
            error = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)

    def run(self, config):
        self.flow_config = config
        result = RestoreResult(total=3, success=3, skipped=0, failed=0)

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)

    def run_independent(self, config):
        self.independent_config = config
        result = RestoreResult(total=2, success=2, skipped=0, failed=0)

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)


def test_restore_page_requires_preflight_and_confirmation(tmp_path: Path) -> None:
    """Restore page blocks writes until preflight and confirmation are complete."""
    qt_app = app()
    restore_worker = FakeRestoreWorker()
    window = make_window(restore_worker=restore_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["restore"], Qt.MouseButton.LeftButton
    )

    restore_page = window.workbench_view.restore_page
    restore_page.site_input.setText(str(tmp_path / "site"))
    restore_page.run_input.setText("run_20260520_120000")

    assert not restore_page.confirm_write_checkbox.isEnabled()
    assert not restore_page.run_button.isEnabled()
    assert restore_worker.flow_config is None

    QTest.mouseClick(restore_page.preflight_button, Qt.MouseButton.LeftButton)
    assert restore_worker.preflight_config is not None
    assert "预检通过" in restore_page.result_summary.text()
    assert "匹配质量" in restore_page.preflight_match_summary.text()
    assert "写入影响" in restore_page.preflight_write_summary.text()
    assert "不覆盖已有 XML" in restore_page.preflight_write_summary.text()
    assert "等待写回确认" in restore_page.preflight_write_summary.text()
    assert restore_page.confirm_write_checkbox.isEnabled()
    assert not restore_page.run_button.isEnabled()

    QTest.mouseClick(restore_page.run_button, Qt.MouseButton.LeftButton)
    assert restore_worker.flow_config is None
    assert "预检通过" in restore_page.result_summary.text()

    QTest.mouseClick(
        restore_page.confirm_write_checkbox,
        Qt.MouseButton.LeftButton,
        pos=QPoint(8, restore_page.confirm_write_checkbox.height() // 2),
    )
    assert restore_page.run_button.isEnabled()
    QTest.mouseClick(restore_page.run_button, Qt.MouseButton.LeftButton)

    assert restore_worker.flow_config is not None
    assert restore_worker.flow_config.source_type == "inference"
    assert restore_worker.flow_config.run_id == "run_20260520_120000"
    assert "还原完成" in restore_page.result_summary.text()


def test_restore_page_keeps_write_actions_visible_after_preflight(
    tmp_path: Path,
) -> None:
    """Restore actions stay reachable in the small desktop baseline."""
    qt_app = app()
    restore_worker = FakeRestoreWorker()
    window = make_window(restore_worker=restore_worker)
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["restore"], Qt.MouseButton.LeftButton
    )

    restore_page = window.workbench_view.restore_page
    restore_page.site_input.setText(str(tmp_path / "site"))
    restore_page.run_input.setText("run_20260520_120000")
    QTest.mouseClick(restore_page.preflight_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()

    scroll = restore_page.findChild(QScrollArea, "toolScrollArea")
    assert scroll is not None

    def center_is_in_viewport(widget) -> bool:
        point = widget.mapTo(
            scroll.viewport(),
            QPoint(widget.width() // 2, widget.height() // 2),
        )
        return scroll.viewport().rect().contains(point)

    assert center_is_in_viewport(restore_page.preflight_button)
    assert center_is_in_viewport(restore_page.run_button)


def test_restore_page_builds_dataset_and_independent_configs(tmp_path: Path) -> None:
    """Restore page supports Flow dataset labels and Independent restore configs."""
    qt_app = app()
    restore_worker = FakeRestoreWorker()
    window = make_window(restore_worker=restore_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["restore"], Qt.MouseButton.LeftButton
    )

    restore_page = window.workbench_view.restore_page
    restore_page.site_input.setText(str(tmp_path / "site"))
    restore_page.dataset_dir_input.setText(str(tmp_path / "dataset"))
    QTest.mouseClick(restore_page.dataset_mode_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(restore_page.preflight_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        restore_page.confirm_write_checkbox,
        Qt.MouseButton.LeftButton,
        pos=QPoint(8, restore_page.confirm_write_checkbox.height() // 2),
    )
    QTest.mouseClick(restore_page.run_button, Qt.MouseButton.LeftButton)

    assert restore_worker.flow_config is not None
    assert restore_worker.flow_config.source_type == "database"
    assert restore_worker.flow_config.database_dir == tmp_path / "dataset"

    restore_worker.flow_config = None
    classes_file = tmp_path / "metadata" / "classes.txt"
    restore_page.image_root_input.setText(str(tmp_path / "images"))
    restore_page.label_root_input.setText(str(tmp_path / "labels"))
    QTest.mouseClick(
        restore_page.independent_mode_button, Qt.MouseButton.LeftButton
    )
    assert restore_page.classes_file_input.isVisible()
    restore_page.classes_file_input.setText(str(classes_file))
    QTest.mouseClick(restore_page.preflight_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        restore_page.confirm_write_checkbox,
        Qt.MouseButton.LeftButton,
        pos=QPoint(8, restore_page.confirm_write_checkbox.height() // 2),
    )
    QTest.mouseClick(restore_page.run_button, Qt.MouseButton.LeftButton)

    assert restore_worker.flow_config is None
    assert restore_worker.independent_config is not None
    assert restore_worker.independent_config.image_root == tmp_path / "images"
    assert restore_worker.independent_config.label_root == tmp_path / "labels"
    assert restore_worker.independent_config.classes_file == classes_file


def test_restore_page_rejects_empty_paths_before_building_config() -> None:
    """Restore page blocks blank paths before constructing Path('')."""
    qt_app = app()
    restore_worker = FakeRestoreWorker()
    window = make_window(restore_worker=restore_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["restore"], Qt.MouseButton.LeftButton
    )

    restore_page = window.workbench_view.restore_page
    QTest.mouseClick(restore_page.preflight_button, Qt.MouseButton.LeftButton)

    assert restore_worker.preflight_config is None
    assert "请选择站点路径" in restore_page.result_summary.text()


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


class FakeScanWorker:
    """Small fake worker that records ScanConfig from the GUI."""

    def __init__(self) -> None:
        self.config = None

    def run(self, config):
        self.config = config
        result = ScanResult(
            mapping_path=config.site_folder / ".autolabeler" / "mapping.json",
            classes_path=config.site_folder / ".autolabeler" / "classes.txt",
            statistics=ScanStatistics(
                total_images=8,
                total_codes=2,
                total_products=3,
            ),
            classes=["CodeA", "CodeB"],
            products={"CodeA": {"Product1": 5}, "CodeB": {"Product2": 3}},
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)


def test_scan_page_builds_config_and_renders_result(tmp_path: Path) -> None:
    """Scan page builds ScanConfig and displays mapping/classes outputs."""
    qt_app = app()
    scan_worker = FakeScanWorker()
    window = make_window(scan_worker=scan_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["scan"], Qt.MouseButton.LeftButton
    )

    scan_page = window.workbench_view.scan_page
    site = tmp_path / "site"
    scan_page.site_input.setText(str(site))
    QTest.mouseClick(scan_page.run_button, Qt.MouseButton.LeftButton)

    assert scan_worker.config is not None
    assert scan_worker.config.site_folder == site
    assert scan_worker.config.output_dir is None
    assert "扫描完成" in scan_page.result_summary.text()
    assert "mapping.json" in scan_page.result_summary.text()
    assert "classes.txt" in scan_page.result_summary.text()
    assert "mapping.json" in scan_page.log_box.toPlainText()
    assert scan_page.structure_example_panel.objectName() == "scanStructureExample"
    example_text = " ".join(
        label.text()
        for label in scan_page.structure_example_panel.findChildren(QLabel)
    )
    assert "site/" in example_text
    assert "CodeA/" in example_text
    assert "Product1/" in example_text


def test_scan_page_rejects_empty_site_before_building_config() -> None:
    """Scan page blocks blank site path before constructing Path('')."""
    qt_app = app()
    scan_worker = FakeScanWorker()
    window = make_window(scan_worker=scan_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["scan"], Qt.MouseButton.LeftButton
    )

    scan_page = window.workbench_view.scan_page
    QTest.mouseClick(scan_page.run_button, Qt.MouseButton.LeftButton)

    assert scan_worker.config is None
    assert "请选择站点路径" in scan_page.result_summary.text()


class FakeLabelImgWorker:
    """Small fake worker that records LabelImg configs from the GUI."""

    def __init__(self) -> None:
        self.validate_config = None
        self.preflight_config = None
        self.launch_config = None

    def validate(self, config):
        self.validate_config = config
        result = LabelImgValidateResult(
            is_valid=True,
            labelimg_version="labelImg 1.8.6",
            python_version="Python 3.11.14",
            error_message=None,
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)

    def preflight(self, config):
        self.preflight_config = config
        result = LabelImgValidateResult(
            is_valid=True,
            labelimg_version="labelImg 1.8.6",
            python_version="Python 3.11.14",
            error_message=None,
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)

    def launch(self, config):
        self.launch_config = config
        result = LabelImgLaunchResult(
            process_id=4321,
            command="python.exe -c \"import sys; print('internal wrapper')\" voc images",
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)


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


class FakeInspectorWorker:
    """Small fake inspector worker that returns one run and product node."""

    def __init__(self, site: Path, *, product: str = "Product1") -> None:
        self.site = site
        self.product = product
        self.list_config = None
        self.tree_config = None
        self.labels_config = None

    def list_runs(self, config):
        self.list_config = config
        run = InferenceRun(
            run_id="run_20260520_120000",
            path=config.site_folder
            / ".autolabeler"
            / "inference_results"
            / "run_20260520_120000",
            config_exists=True,
            config={},
            created_at="2026-05-20 12:00:00",
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome([run])

    def get_run_tree(self, config):
        self.tree_config = config
        node = RunTreeNode(
            code="CodeA",
            product=self.product,
            label_count=2,
            empty_count=1,
            path=config.site_folder
            / ".autolabeler"
            / "inference_results"
            / config.run_id
            / "labels"
            / "CodeA"
            / self.product,
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome([node])

    def get_product_labels(self, config):
        self.labels_config = config
        product_dir = config.site_folder / "CodeA" / self.product
        labels_dir = (
            config.site_folder
            / ".autolabeler"
            / "inference_results"
            / config.run_id
            / "labels"
            / "CodeA"
            / self.product
        )
        result = [
            ProductLabel(
                image_name="a.jpg",
                image_path=product_dir / "a.jpg",
                label_path=labels_dir / "a.txt",
                object_count=1,
                missing_label=False,
            ),
            ProductLabel(
                image_name="b.jpg",
                image_path=product_dir / "b.jpg",
                label_path=labels_dir / "b.txt",
                object_count=0,
                missing_label=True,
            ),
        ]

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)


def test_review_page_loads_product_and_launches_labelimg(tmp_path: Path) -> None:
    """Review page prepares Flow prediction review and launches LabelImg."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    inspector_worker = FakeInspectorWorker(tmp_path / "site")
    window = make_window(
        labelimg_worker=labelimg_worker,
        inspector_worker=inspector_worker,
    )
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    site = tmp_path / "site"
    review_page.site_input.setText(str(site))
    QTest.mouseClick(review_page.load_runs_button, Qt.MouseButton.LeftButton)
    assert review_page.run_combo.count() == 1
    assert review_page.review_empty_state_panel.objectName() == "reviewEmptyState"
    assert "先选择站点" in review_page.review_empty_text.text()
    assert "run_20260520_120000" in review_page.run_combo.itemText(0)
    assert not hasattr(review_page, "run_input")
    assert not hasattr(review_page, "code_input")
    assert not hasattr(review_page, "product_input")

    QTest.mouseClick(review_page.load_tree_button, Qt.MouseButton.LeftButton)
    assert review_page.run_tree.topLevelItemCount() == 1
    code_item = review_page.run_tree.topLevelItem(0)
    assert code_item.text(0) == "CodeA"
    assert code_item.childCount() == 1
    product_item = code_item.child(0)
    assert product_item.text(0) == "Product1"
    review_page.run_tree.setCurrentItem(product_item)

    QTest.mouseClick(review_page.prepare_button, Qt.MouseButton.LeftButton)
    assert "缺少标签 1" in review_page.result_summary.text()
    assert "图片目录" in review_page.review_status_summary.text()
    assert "标签目录" in review_page.review_status_summary.text()
    assert "classes.txt" in review_page.review_status_summary.text()

    QTest.mouseClick(review_page.launch_button, Qt.MouseButton.LeftButton)
    assert labelimg_worker.launch_config is not None
    assert labelimg_worker.launch_config.image_dir == site / "CodeA" / "Product1"
    assert (
        labelimg_worker.launch_config.label_dir
        == site
        / ".autolabeler"
        / "inference_results"
        / "run_20260520_120000"
        / "labels"
        / "CodeA"
        / "Product1"
    )
    assert labelimg_worker.launch_config.classes_file == site / ".autolabeler" / "classes.txt"


def test_review_page_uses_compact_run_combo_and_full_product_tree(
    tmp_path: Path,
) -> None:
    """Review page keeps run selection compact and gives product names room."""
    qt_app = app()
    long_product = "H4A270FDF10_EXTENDED_PRODUCT_NAME_SHOULD_REMAIN_VISIBLE"
    inspector_worker = FakeInspectorWorker(tmp_path / "site", product=long_product)
    window = make_window(inspector_worker=inspector_worker)
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    review_page.site_input.setText(str(tmp_path / "site"))
    QTest.mouseClick(review_page.load_runs_button, Qt.MouseButton.LeftButton)

    assert hasattr(review_page, "run_combo")
    assert not hasattr(review_page, "run_list")
    assert review_page.run_combo.count() == 1
    assert review_page.run_combo.currentData() == "run_20260520_120000"

    QTest.mouseClick(review_page.load_tree_button, Qt.MouseButton.LeftButton)
    code_item = review_page.run_tree.topLevelItem(0)
    product_item = code_item.child(0)
    assert product_item.text(0) == long_product
    assert f"CodeA/{long_product}" in product_item.toolTip(0)
    assert "标签：2，空标签：1" in product_item.toolTip(0)
    assert (
        review_page.run_tree.header().sectionResizeMode(0)
        == QHeaderView.ResizeMode.Stretch
    )


def test_review_page_keeps_prepare_actions_before_growing_status_panel(
    tmp_path: Path,
) -> None:
    """Review action buttons stay above the prepared path summary in small windows."""
    qt_app = app()
    inspector_worker = FakeInspectorWorker(tmp_path / "site")
    window = make_window(inspector_worker=inspector_worker)
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    review_page.site_input.setText(str(tmp_path / "site"))
    QTest.mouseClick(review_page.prepare_button, Qt.MouseButton.LeftButton)

    form = review_page.review_form.layout()
    actions_index = form.indexOf(review_page.review_actions_widget)
    status_index = form.indexOf(review_page.review_status_panel)
    actions_row = form.getItemPosition(actions_index)[0]
    status_row = form.getItemPosition(status_index)[0]

    assert actions_row < status_row
    assert review_page.prepare_button.isVisible()
    assert review_page.review_launch_button.isVisible()


def test_review_page_launch_auto_prepares_selected_node(tmp_path: Path) -> None:
    """Opening review prepares the selected node automatically if needed."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    inspector_worker = FakeInspectorWorker(tmp_path / "site")
    window = make_window(
        labelimg_worker=labelimg_worker,
        inspector_worker=inspector_worker,
    )
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    site = tmp_path / "site"
    review_page.site_input.setText(str(site))
    QTest.mouseClick(review_page.load_runs_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(review_page.load_tree_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(review_page.launch_button, Qt.MouseButton.LeftButton)

    assert inspector_worker.labels_config is not None
    assert labelimg_worker.launch_config is not None
    assert labelimg_worker.launch_config.image_dir == site / "CodeA" / "Product1"
    assert "已启动 LabelImg" in review_page.result_summary.text()


def test_review_page_prepared_paths_do_not_expand_left_panel(
    tmp_path: Path,
) -> None:
    """Prepared long Windows-style paths stay bounded inside the status panel."""
    qt_app = app()
    long_site = (
        tmp_path
        / "very_long_review_site_root"
        / ("segment_" * 12)
        / ("product_" * 8)
    )
    inspector_worker = FakeInspectorWorker(long_site)
    window = make_window(inspector_worker=inspector_worker)
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    review_page.site_input.setText(str(long_site))
    QTest.mouseClick(review_page.prepare_button, Qt.MouseButton.LeftButton)

    assert review_page.review_status_summary.minimumSizeHint().width() <= (
        review_page.review_status_panel.width()
    )
    assert review_page.review_status_summary.toolTip()
    assert "..." in review_page.review_status_summary.text()


def test_review_page_rejects_empty_site_before_listing_runs() -> None:
    """Review page blocks blank site path before list-runs config construction."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    inspector_worker = FakeInspectorWorker(Path("unused"))
    window = make_window(
        labelimg_worker=labelimg_worker,
        inspector_worker=inspector_worker,
    )
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    QTest.mouseClick(review_page.load_runs_button, Qt.MouseButton.LeftButton)

    assert inspector_worker.list_config is None
    assert "请选择站点路径" in review_page.result_summary.text()


def test_review_page_invalidates_prepared_launch_when_inputs_change(
    tmp_path: Path,
) -> None:
    """Review page does not launch stale prepared paths after review inputs change."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    inspector_worker = FakeInspectorWorker(tmp_path / "site")
    window = make_window(
        labelimg_worker=labelimg_worker,
        inspector_worker=inspector_worker,
    )
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    review_page.site_input.setText(str(tmp_path / "site"))
    QTest.mouseClick(review_page.prepare_button, Qt.MouseButton.LeftButton)
    assert "复核准备完成" in review_page.result_summary.text()

    review_page.site_input.setText(str(tmp_path / "site_changed"))
    QTest.mouseClick(review_page.launch_button, Qt.MouseButton.LeftButton)

    assert inspector_worker.labels_config is not None
    assert inspector_worker.labels_config.site_folder == tmp_path / "site_changed"
    assert labelimg_worker.launch_config is not None
    assert (
        labelimg_worker.launch_config.image_dir
        == tmp_path / "site_changed" / "CodeA" / "Product1"
    )

