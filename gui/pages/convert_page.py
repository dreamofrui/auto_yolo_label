"""
AutoLabeler 转换页面
将 YOLO 格式标注转换为 VOC XML 格式
"""

from pathlib import Path
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
    CheckBox,
    setFont,
)

from gui.pages.base_page import BasePage
from gui.workers.convert_worker import ConvertWorker


class ConvertPage(BasePage):
    """
    转换页面
    将 YOLO 格式标注转换为 VOC XML 格式
    """

    def __init__(self, parent=None):
        # 在调用 super().__init__ 之前初始化属性
        self.folder_input = None
        self.browse_btn = None
        self.convert_btn = None
        self.progress_bar = None
        self.log_output = None

        # 配置参数
        self.recursive_check = None

        # 统计显示
        self.stats_labels = {}

        # Worker
        self.worker = None

        super().__init__("转换", parent)

    def init_ui(self):
        """初始化UI"""
        # 标题和描述
        self.add_title("格式转换")
        self.add_description(
            "将 YOLO 格式的 .txt 标注文件转换为 VOC 格式的 .xml 文件。"
            "转换后的 XML 文件将保存在与 .txt 相同的目录下。"
        )
        self.add_spacing(20)

        # 文件夹选择卡片
        self._create_folder_selection()
        self.add_spacing(16)

        # 转换配置卡片
        self._create_config_section()
        self.add_spacing(16)

        # 转换控制卡片
        self._create_controls()
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
        label = StrongBodyLabel("目标文件夹:")
        card_layout.addWidget(label, 0, 0)

        # 输入框
        self.folder_input = LineEdit()
        self.folder_input.setPlaceholderText("选择包含标注文件的文件夹...")
        self.folder_input.setReadOnly(True)
        card_layout.addWidget(self.folder_input, 0, 1)

        # 浏览按钮
        self.browse_btn = PushButton("浏览...", self, FluentIcon.FOLDER)
        self.browse_btn.clicked.connect(self._browse_folder)
        card_layout.addWidget(self.browse_btn, 0, 2)

        self.content_layout.addWidget(card)

    def _create_config_section(self):
        """创建配置区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # 递归处理
        self.recursive_check = CheckBox("递归处理子文件夹")
        self.recursive_check.setChecked(True)
        card_layout.addWidget(self.recursive_check, 0, 0)

        self.content_layout.addWidget(card)

    def _create_controls(self):
        """创建控制区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # 转换按钮
        self.convert_btn = PushButton("开始转换", self, FluentIcon.CODE)
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self._start_convert)
        card_layout.addWidget(self.convert_btn, 0, 0)

        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        card_layout.addWidget(self.progress_bar, 1, 0, 1, 3)

        # 状态标签
        self.status_label = BodyLabel("请选择包含标注文件的文件夹")
        card_layout.addWidget(self.status_label, 2, 0, 1, 3)

        self.content_layout.addWidget(card)

    def _create_statistics(self):
        """创建统计信息区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        # 标题
        title = SubtitleLabel("转换统计")
        card_layout.addWidget(title, 0, 0, 1, 4)

        # 统计项
        stats = [
            ("总文件数", "total", "0"),
            ("成功转换", "success", "0"),
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

        title = StrongBodyLabel("转换日志:")
        card_layout.addWidget(title, 0, 0)

        self.log_output = TextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("转换日志将在这里显示...")
        self.log_output.setMaximumHeight(150)
        card_layout.addWidget(self.log_output, 1, 0)

        self.content_layout.addWidget(card)

    def _browse_folder(self):
        """浏览并选择文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择包含标注文件的文件夹",
            "",
            QFileDialog.ShowDirsOnly
        )

        if folder:
            self.folder_input.setText(folder)
            self.convert_btn.setEnabled(True)
            self.status_label.setText("准备就绪，点击开始转换")

    def _start_convert(self):
        """开始转换"""
        folder_path = Path(self.folder_input.text())

        if not folder_path.exists():
            self.window().show_error("错误", "选择的文件夹不存在")
            return

        # 禁用按钮
        self.convert_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)

        # 清空日志
        self.log_output.clear()

        # 获取配置
        config = {
            "recursive": self.recursive_check.isChecked(),
        }

        # 创建并启动 Worker
        self.worker = ConvertWorker(folder_path, config)
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
        """处理转换完成"""
        # 恢复按钮
        self.convert_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)

        if success and result:
            # 更新统计
            self.stats_labels["total"].setText(str(result.get("total", 0)))
            self.stats_labels["success"].setText(str(result.get("success", 0)))
            self.stats_labels["skipped"].setText(str(result.get("skipped", 0)))
            self.stats_labels["failed"].setText(str(result.get("failed", 0)))

            self.window().show_info(
                "转换完成",
                f"成功转换 {result.get('success', 0)} 个文件"
            )
        else:
            self.window().show_error("转换失败", "转换过程中出现错误")

    def _on_error(self, error_message: str):
        """处理错误"""
        self.log_output.append(f"错误: {error_message}")
        self.window().show_error("转换错误", error_message)

    def on_leave(self):
        """离开页面时清理"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
