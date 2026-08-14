"""Scoped tests for the PySide workbench shell."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
)

from gui.task_runner import AsyncTaskRunner
from gui.tool_defaults import (
    DEFAULT_TOOL_DEFAULTS_PATH,
    ToolDefaults,
    save_tool_defaults,
)
from gui.workbench import MODULES, AutoLabelerWindow
from utils.exceptions import ErrorCode, ErrorInfo
from utils.task_registry import TaskRegistry

from conftest import (
    app,
    make_image,
    make_scanned_site,
    make_window,
    set_task_timestamp,
)

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

def test_default_tool_defaults_path_lives_in_project() -> None:
    """The settings file defaults to the project's local runtime directory."""
    project_root = Path(__file__).resolve().parents[2]

    assert DEFAULT_TOOL_DEFAULTS_PATH == (
        project_root / ".autolabeler" / "tool_defaults.json"
    )

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

def test_app_run_entrypoint_is_importable() -> None:
    """The GUI has an explicit QApplication entry point."""
    from gui.app import run

    assert callable(run)

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

