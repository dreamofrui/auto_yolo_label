"""
AutoLabeler 还原页面
将标注文件还原回原始目录结构
支持从 database/labels/ 和 inference_results/ 还原
"""

from pathlib import Path
from PySide6.QtWidgets import QGridLayout, QFileDialog, QButtonGroup
from qfluentwidgets import (
    PushButton,
    CardWidget,
    LineEdit,
    StrongBodyLabel,
    SubtitleLabel,
    ProgressBar,
    FluentIcon,
    BodyLabel,
    TextEdit,
    setFont,
    RadioButton,
    ComboBox,
)

from gui.pages.base_page import BasePage
from gui.workers.restore_worker import RestoreWorker


class RestorePage(BasePage):
    """
    还原页面
    将标注文件还原回原始目录结构
    """

    def __init__(self, parent=None):
        # 在调用 super().__init__ 之前初始化属性
        self.database_input = None
        self.database_browse_btn = None
        self.site_input = None
        self.site_browse_btn = None
        self.restore_btn = None
        self.progress_bar = None
        self.log_output = None

        # 来源选择
        self.source_radio_database = None
        self.source_radio_inference = None
        self.source_button_group = None
        self.inference_combo = None
        self.inference_refresh_btn = None

        # 统计显示
        self.stats_labels = {}

        # Worker
        self.worker = None

        super().__init__("还原", parent)

    def init_ui(self):
        """初始化UI"""
        # 标题和描述
        self.add_title("还原标注文件")
        self.add_description(
            "将标注文件还原到原始图片所在的目录。"
            "支持从 Database 目录或推理结果目录还原。"
        )
        self.add_spacing(20)

        # 来源选择卡片
        self._create_source_selection()
        self.add_spacing(16)

        # 文件夹选择卡片
        self._create_folder_selection()
        self.add_spacing(16)

        # 还原控制卡片
        self._create_controls()
        self.add_spacing(16)

        # 统计信息卡片
        self._create_statistics()
        self.add_spacing(16)

        # 日志输出
        self._create_log_output()

        self.add_stretch()

    def _create_source_selection(self):
        """创建来源选择区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        row = 0

        # 标题
        title = StrongBodyLabel("标注来源:")
        card_layout.addWidget(title, row, 0, 1, 3)
        row += 1

        # 单选按钮
        self.source_radio_database = RadioButton("Database 目录")
        self.source_radio_inference = RadioButton("推理结果")
        self.source_radio_database.setChecked(True)

        self.source_button_group = QButtonGroup()
        self.source_button_group.addButton(self.source_radio_database, 0)
        self.source_button_group.addButton(self.source_radio_inference, 1)
        self.source_button_group.buttonClicked.connect(self._on_source_changed)

        card_layout.addWidget(self.source_radio_database, row, 0)
        card_layout.addWidget(self.source_radio_inference, row, 1)
        row += 1

        # 推理结果选择（初始隐藏）
        self.inference_combo = ComboBox()
        self.inference_combo.setMinimumWidth(300)
        self.inference_combo.currentIndexChanged.connect(self._check_ready)
        card_layout.addWidget(self.inference_combo, row, 0, 1, 2)

        self.inference_refresh_btn = PushButton("刷新", self, FluentIcon.SYNC)
        self.inference_refresh_btn.clicked.connect(self._refresh_inference_list)
        card_layout.addWidget(self.inference_refresh_btn, row, 2)

        # 初始隐藏推理选择
        self.inference_combo.hide()
        self.inference_refresh_btn.hide()

        self.content_layout.addWidget(card)

    def _create_folder_selection(self):
        """创建文件夹选择区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        row = 0

        # database 目录（用于从 database 还原）
        self.db_row = row
        db_label = StrongBodyLabel("Database 目录:")
        card_layout.addWidget(db_label, row, 0)

        self.database_input = LineEdit()
        self.database_input.setPlaceholderText("选择 database 目录...")
        self.database_input.setReadOnly(True)
        card_layout.addWidget(self.database_input, row, 1)

        self.database_browse_btn = PushButton("浏览...", self, FluentIcon.FOLDER)
        self.database_browse_btn.clicked.connect(self._browse_database)
        card_layout.addWidget(self.database_browse_btn, row, 2)

        row += 1

        # 站点文件夹（两种模式都需要）
        site_label = StrongBodyLabel("站点文件夹:")
        card_layout.addWidget(site_label, row, 0)

        self.site_input = LineEdit()
        self.site_input.setPlaceholderText("选择站点文件夹...")
        self.site_input.setReadOnly(True)
        card_layout.addWidget(self.site_input, row, 1)

        self.site_browse_btn = PushButton("浏览...", self, FluentIcon.FOLDER)
        self.site_browse_btn.clicked.connect(self._browse_site)
        card_layout.addWidget(self.site_browse_btn, row, 2)

        self.content_layout.addWidget(card)

    def _create_controls(self):
        """创建控制区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # 还原按钮
        self.restore_btn = PushButton("开始还原", self, FluentIcon.SYNC)
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self._start_restore)
        card_layout.addWidget(self.restore_btn, 0, 0)

        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        card_layout.addWidget(self.progress_bar, 1, 0, 1, 3)

        # 状态标签
        self.status_label = BodyLabel("请先选择 database 目录和站点文件夹")
        card_layout.addWidget(self.status_label, 2, 0, 1, 3)

        self.content_layout.addWidget(card)

    def _create_statistics(self):
        """创建统计信息区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        # 标题
        title = SubtitleLabel("还原统计")
        card_layout.addWidget(title, 0, 0, 1, 4)

        # 统计项
        stats = [
            ("总文件数", "total", "0"),
            ("成功还原", "success", "0"),
            ("跳过", "skipped", "0"),
            ("失败", "failed", "0"),
        ]

        for i, (label_text, key, default) in enumerate(stats):
            row = 1 + i // 2
            col = (i % 2) * 2

            label = StrongBodyLabel(f"{label_text}:")
            card_layout.addWidget(label, row, col)

            value_label = SubtitleLabel(default)
            setFont(value_label, 16)
            card_layout.addWidget(value_label, row, col + 1)

            self.stats_labels[key] = value_label

        self.content_layout.addWidget(card)

    def _create_log_output(self):
        """创建日志输出区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        title = StrongBodyLabel("还原日志:")
        card_layout.addWidget(title, 0, 0)

        self.log_output = TextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("还原日志将在这里显示...")
        self.log_output.setMaximumHeight(150)
        card_layout.addWidget(self.log_output, 1, 0)

        self.content_layout.addWidget(card)

    def _browse_database(self):
        """浏览并选择 database 目录"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择 database 目录",
            "",
            QFileDialog.ShowDirsOnly
        )

        if folder:
            self.database_input.setText(folder)
            self._check_ready()

    def _browse_site(self):
        """浏览并选择站点文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择站点文件夹",
            "",
            QFileDialog.ShowDirsOnly
        )

        if folder:
            self.site_input.setText(folder)
            self._check_ready()

    def _check_ready(self):
        """检查是否准备好开始"""
        site = self.site_input.text()
        is_inference = self.source_radio_inference.isChecked()

        if not site:
            self.restore_btn.setEnabled(False)
            self.status_label.setText("请先选择站点文件夹")
            return

        if is_inference:
            # 推理结果模式：需要站点文件夹和已选中的推理记录
            if self.inference_combo.count() > 0:
                selected_dir = self.inference_combo.currentData()
                if selected_dir:
                    self.restore_btn.setEnabled(True)
                    self.status_label.setText("准备就绪，点击开始还原")
                    return
            self.restore_btn.setEnabled(False)
            self.status_label.setText("请先选择推理记录")
        else:
            # Database 模式：需要 database 目录和站点文件夹
            database = self.database_input.text()
            if database:
                self.restore_btn.setEnabled(True)
                self.status_label.setText("准备就绪，点击开始还原")
            else:
                self.restore_btn.setEnabled(False)
                self.status_label.setText("请先选择 database 目录")

    def _on_progress(self, current: int, total: int, message: str):
        """处理进度更新"""
        percentage = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)

    def _on_log(self, message: str):
        """处理日志消息"""
        self.log_output.append(message)

    def _on_finished(self, success: bool, result):
        """处理还原完成"""
        # 恢复按钮
        self._restore_buttons()

        if success and result:
            # 更新统计
            self.stats_labels["total"].setText(str(result.get("total", 0)))
            self.stats_labels["success"].setText(str(result.get("success", 0)))
            self.stats_labels["skipped"].setText(str(result.get("skipped", 0)))
            self.stats_labels["failed"].setText(str(result.get("failed", 0)))

            self.window().show_info(
                "还原完成",
                f"成功还原 {result.get('success', 0)} 个标注文件"
            )
        else:
            self.window().show_error("还原失败", "还原过程中出现错误")

    def _on_error(self, error_message: str):
        """处理错误"""
        self.log_output.append(f"错误: {error_message}")
        self.window().show_error("还原错误", error_message)

    def _on_source_changed(self):
        """处理来源选择变化"""
        is_inference = self.source_radio_inference.isChecked()

        # 显示/隐藏相关控件
        if is_inference:
            self.database_input.hide()
            self.database_browse_btn.hide()
            self.inference_combo.show()
            self.inference_refresh_btn.show()
            # 自动刷新推理列表
            self._refresh_inference_list()
        else:
            self.database_input.show()
            self.database_browse_btn.show()
            self.inference_combo.hide()
            self.inference_refresh_btn.hide()

        self._check_ready()

    def _refresh_inference_list(self):
        """刷新推理结果列表"""
        self.inference_combo.clear()

        site_path = Path(self.site_input.text())
        if not site_path.exists():
            self.inference_combo.addItem(None, "请先选择站点文件夹")
            return

        # 查找推理结果目录
        inference_results_dir = site_path / ".autolabeler" / "inference_results"
        if not inference_results_dir.exists():
            self.inference_combo.addItem(None, "无推理结果")
            return

        # 获取所有推理运行目录
        from core.inferencer import Inferencer
        inferencer = Inferencer()
        history = inferencer.get_inference_history(inference_results_dir)

        if not history:
            self.inference_combo.addItem(None, "无推理结果")
            return

        # 添加到下拉框
        for item in history:
            config = item["config"]
            run_id = config.get("run_id", "unknown")
            timestamp = config.get("timestamp", "")
            model_path = config.get("model_path", "")
            image_count = config.get("image_count", 0)
            confidence = config.get("confidence", 0.25)
            iou = config.get("iou", 0.7)

            display_text = f"{timestamp} - {image_count} 张图片 - conf:{confidence:.2f} iou:{iou:.2f}"
            # addItem 参数顺序: (text, icon, userData)
            self.inference_combo.addItem(display_text, None, str(item["run_dir"]))

        # 刷新完成后检查是否准备好
        self._check_ready()

    def _start_restore(self):
        """开始还原"""
        site_path = Path(self.site_input.text())

        if not site_path.exists():
            self.window().show_error("错误", "站点文件夹不存在")
            return

        # 禁用按钮
        self.restore_btn.setEnabled(False)
        self.site_browse_btn.setEnabled(False)
        if not self.source_radio_inference.isChecked():
            self.database_browse_btn.setEnabled(False)

        # 清空日志
        self.log_output.clear()

        # 根据来源创建不同的 Worker
        if self.source_radio_inference.isChecked():
            # 从推理结果还原
            if self.inference_combo.count() == 0:
                self.window().show_error("错误", "无可用推理结果")
                self._restore_buttons()
                return

            # 获取选中的推理目录
            inference_dir = self.inference_combo.currentData()
            if inference_dir is None or not Path(inference_dir).exists():
                self.window().show_error("错误", "选择的推理结果不存在")
                self._restore_buttons()
                return

            # 创建并启动 Worker（从推理结果还原）
            self.worker = RestoreWorker(
                source_type="inference",
                source_path=Path(inference_dir),
                site_folder=site_path
            )
        else:
            # 从 database 还原
            database_path = Path(self.database_input.text())
            if not database_path.exists():
                self.window().show_error("错误", "database 目录不存在")
                self._restore_buttons()
                return

            # 创建并启动 Worker（从 database 还原）
            self.worker = RestoreWorker(
                source_type="database",
                source_path=database_path,
                site_folder=site_path
            )

        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _restore_buttons(self):
        """恢复按钮状态"""
        self.restore_btn.setEnabled(True)
        self.site_browse_btn.setEnabled(True)
        if not self.source_radio_inference.isChecked():
            self.database_browse_btn.setEnabled(True)

    def on_leave(self):
        """离开页面时清理"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
