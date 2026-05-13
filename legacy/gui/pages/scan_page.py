"""
AutoLabeler 扫描页面
执行数据扫描，建立图片索引
"""

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QFileDialog
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
)

from gui.pages.base_page import BasePage
from gui.workers.scan_worker import ScanWorker


class ScanPage(BasePage):
    """
    扫描页面
    扫描站点文件夹，建立图片索引
    """

    def __init__(self, parent=None):
        # 在调用 super().__init__ 之前初始化属性
        # 因为 super().__init__ 会调用 init_ui()

        # UI 组件
        self.folder_input = None
        self.browse_btn = None
        self.scan_btn = None
        self.progress_bar = None
        self.log_output = None

        # 统计显示
        self.stats_labels = {}

        # Worker
        self.worker = None

        super().__init__("扫描", parent)

    def init_ui(self):
        """初始化UI"""
        # 标题和描述
        self.add_title("扫描站点文件夹")
        self.add_description(
            "扫描包含 Code/Product/Images 三级目录结构的站点文件夹，"
            "自动识别所有图片文件，建立全局索引。"
        )
        self.add_spacing(20)

        # 文件夹选择卡片
        self._create_folder_selection()
        self.add_spacing(16)

        # 扫描控制卡片
        self._create_scan_controls()
        self.add_spacing(16)

        # 统计信息卡片
        self._create_statistics()
        self.add_spacing(16)

        # 日志输出
        self._create_log_output()

        self.add_stretch()

    def _create_folder_selection(self):
        """创建文件夹选择区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # 标签
        label = StrongBodyLabel("站点文件夹:")
        card_layout.addWidget(label, 0, 0)

        # 输入框
        self.folder_input = LineEdit()
        self.folder_input.setPlaceholderText("选择站点文件夹路径...")
        self.folder_input.setReadOnly(True)
        card_layout.addWidget(self.folder_input, 0, 1)

        # 浏览按钮
        self.browse_btn = PushButton("浏览...", self, FluentIcon.FOLDER)
        self.browse_btn.clicked.connect(self._browse_folder)
        card_layout.addWidget(self.browse_btn, 0, 2)

        self.content_layout.addWidget(card)

    def _create_scan_controls(self):
        """创建扫描控制区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # 扫描按钮
        self.scan_btn = PushButton("开始扫描", self, FluentIcon.SEARCH)
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self._start_scan)
        card_layout.addWidget(self.scan_btn, 0, 0)

        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        card_layout.addWidget(self.progress_bar, 1, 0, 1, 3)

        # 状态标签
        self.status_label = BodyLabel("请选择站点文件夹")
        card_layout.addWidget(self.status_label, 2, 0, 1, 3)

        self.content_layout.addWidget(card)

    def _create_statistics(self):
        """创建统计信息区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        # 标题
        title = SubtitleLabel("扫描统计")
        card_layout.addWidget(title, 0, 0, 1, 4)

        # 统计项
        stats = [
            ("Code 数量", "total_codes", "0"),
            ("产品数量", "total_products", "0"),
            ("图片总数", "total_images", "0"),
        ]

        for i, (label_text, key, default) in enumerate(stats):
            row = 1 + i // 2
            col = (i % 2) * 2

            # 标签
            label = StrongBodyLabel(f"{label_text}:")
            card_layout.addWidget(label, row, col)

            # 数值
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

        # 标题
        title = StrongBodyLabel("扫描日志:")
        card_layout.addWidget(title, 0, 0)

        # 文本框
        self.log_output = TextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("扫描日志将在这里显示...")
        self.log_output.setMaximumHeight(200)
        card_layout.addWidget(self.log_output, 1, 0)

        self.content_layout.addWidget(card)

    def _browse_folder(self):
        """浏览并选择文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择站点文件夹",
            "",
            QFileDialog.ShowDirsOnly
        )

        if folder:
            self.folder_input.setText(folder)
            self.scan_btn.setEnabled(True)
            self.status_label.setText("已选择文件夹，点击开始扫描")

    def _start_scan(self):
        """开始扫描"""
        folder_path = self.folder_input.text()
        if not folder_path:
            self.window().show_warning("警告", "请先选择站点文件夹")
            return

        folder = Path(folder_path)
        if not folder.exists():
            self.window().show_error("错误", "选择的文件夹不存在")
            return

        # 禁用按钮
        self.scan_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)

        # 清空日志
        self.log_output.clear()

        # 创建并启动 Worker
        self.worker = ScanWorker(folder)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, current: int, total: int, message: str):
        """处理进度更新"""
        percentage = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)

    def _on_log(self, message: str):
        """处理日志消息"""
        self.log_output.append(message)

    def _on_finished(self, success: bool, result):
        """处理扫描完成"""
        # 恢复按钮
        self.scan_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)

        if success and result:
            # 更新统计
            stats = result.get("statistics", {})
            self.stats_labels["total_codes"].setText(str(stats.get("total_codes", 0)))
            self.stats_labels["total_products"].setText(str(stats.get("total_products", 0)))
            self.stats_labels["total_images"].setText(str(stats.get("total_images", 0)))

            self.window().show_info(
                "扫描完成",
                f"成功扫描 {stats.get('total_images', 0)} 张图片"
            )
        else:
            self.window().show_error("扫描失败", "扫描过程中出现错误")

    def _on_error(self, error_message: str):
        """处理错误"""
        self.log_output.append(f"错误: {error_message}")
        self.window().show_error("扫描错误", error_message)

    def on_leave(self):
        """离开页面时清理"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
