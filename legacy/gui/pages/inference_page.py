"""
AutoLabeler 推理页面
使用训练好的模型自动标注图片
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
    DoubleSpinBox,
    SpinBox,
    ComboBox,
    setFont,
)

from gui.pages.base_page import BasePage
from gui.workers.inference_worker import InferenceWorker


class InferencePage(BasePage):
    """
    推理页面
    使用训练好的模型自动标注图片
    """

    def __init__(self, parent=None):
        # 在调用 super().__init__ 之前初始化属性
        self.model_input = None
        self.model_browse_btn = None
        self.site_input = None
        self.site_browse_btn = None
        self.infer_btn = None
        self.stop_btn = None
        self.progress_bar = None
        self.log_output = None

        # 配置参数
        self.conf_spin = None
        self.iou_spin = None
        self.batch_spin = None
        self.device_combo = None

        # 统计显示
        self.stats_labels = {}

        # Worker
        self.worker = None

        super().__init__("推理", parent)

    def init_ui(self):
        """初始化UI"""
        # 标题和描述
        self.add_title("自动推理标注")
        self.add_description(
            "使用训练好的模型对未抽样的图片进行自动标注。"
            "标注结果将保存为 YOLO 格式的 .txt 文件。"
        )
        self.add_spacing(20)

        # 文件选择卡片
        self._create_file_selection()
        self.add_spacing(16)

        # 推理配置卡片
        self._create_config_section()
        self.add_spacing(16)

        # 推理控制卡片
        self._create_controls()
        self.add_spacing(16)

        # 统计信息卡片
        self._create_statistics()
        self.add_spacing(16)

        # 日志输出
        self._create_log_output()

        self.add_stretch()

    def _create_file_selection(self):
        """创建文件选择区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        row = 0

        # 模型文件
        model_label = StrongBodyLabel("模型文件:")
        card_layout.addWidget(model_label, row, 0)

        self.model_input = LineEdit()
        self.model_input.setPlaceholderText("选择训练好的模型 (best.pt)...")
        self.model_input.setReadOnly(True)
        card_layout.addWidget(self.model_input, row, 1)

        self.model_browse_btn = PushButton("浏览...", self, FluentIcon.FOLDER)
        self.model_browse_btn.clicked.connect(self._browse_model)
        card_layout.addWidget(self.model_browse_btn, row, 2)

        row += 1

        # 站点文件夹
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

    def _create_config_section(self):
        """创建配置区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        row = 0

        # 置信度阈值
        conf_label = StrongBodyLabel("置信度阈值:")
        card_layout.addWidget(conf_label, row, 0)

        self.conf_spin = DoubleSpinBox()
        self.conf_spin.setRange(0.01, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.25)
        self.conf_spin.setDecimals(2)
        card_layout.addWidget(self.conf_spin, row, 1, 1, 2)

        row += 1

        # IoU 阈值
        iou_label = StrongBodyLabel("IoU 阈值:")
        card_layout.addWidget(iou_label, row, 0)

        self.iou_spin = DoubleSpinBox()
        self.iou_spin.setRange(0.01, 1.0)
        self.iou_spin.setSingleStep(0.05)
        self.iou_spin.setValue(0.7)
        self.iou_spin.setDecimals(2)
        card_layout.addWidget(self.iou_spin, row, 1, 1, 2)

        row += 1

        # 批处理大小
        batch_label = StrongBodyLabel("批处理大小:")
        card_layout.addWidget(batch_label, row, 0)

        self.batch_spin = SpinBox()
        self.batch_spin.setRange(-1, 128)
        self.batch_spin.setValue(-1)
        self.batch_spin.setSpecialValueText("自动")
        batch_help = BodyLabel("(-1 表示自动检测)")
        batch_help.setStyleSheet("color: #888; font-size: 11px;")
        card_layout.addWidget(self.batch_spin, row, 1)
        card_layout.addWidget(batch_help, row, 2)

        row += 1

        # 计算设备
        device_label = StrongBodyLabel("计算设备:")
        card_layout.addWidget(device_label, row, 0)

        self.device_combo = ComboBox()
        self.device_combo.addItems(["auto (自动检测)", "cpu", "0 (GPU 0)", "mps"])
        self.device_combo.setCurrentIndex(0)
        card_layout.addWidget(self.device_combo, row, 1, 1, 2)

        self.content_layout.addWidget(card)

    def _create_controls(self):
        """创建控制区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # 推理按钮
        self.infer_btn = PushButton("开始推理", self, FluentIcon.ROBOT)
        self.infer_btn.setEnabled(False)
        self.infer_btn.clicked.connect(self._start_inference)
        card_layout.addWidget(self.infer_btn, 0, 0)

        # 停止按钮
        self.stop_btn = PushButton("停止推理", self, FluentIcon.PAUSE)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_inference)
        card_layout.addWidget(self.stop_btn, 0, 1)

        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        card_layout.addWidget(self.progress_bar, 1, 0, 1, 3)

        # 状态标签
        self.status_label = BodyLabel("请先选择模型文件和站点文件夹")
        card_layout.addWidget(self.status_label, 2, 0, 1, 3)

        self.content_layout.addWidget(card)

    def _create_statistics(self):
        """创建统计信息区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        # 标题
        title = SubtitleLabel("推理统计")
        card_layout.addWidget(title, 0, 0, 1, 4)

        # 统计项
        stats = [
            ("待推理图片", "pending", "0"),
            ("已处理", "processed", "0"),
            ("成功", "success", "0"),
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

        title = StrongBodyLabel("推理日志:")
        card_layout.addWidget(title, 0, 0)

        self.log_output = TextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("推理日志将在这里显示...")
        self.log_output.setMaximumHeight(150)
        card_layout.addWidget(self.log_output, 1, 0)

        self.content_layout.addWidget(card)

    def _browse_model(self):
        """浏览并选择模型文件"""
        file, _ = QFileDialog.getOpenFileName(
            self,
            "选择模型文件",
            "",
            "Model Files (*.pt);;All Files (*)"
        )

        if file:
            self.model_input.setText(file)
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
        model = self.model_input.text()
        site = self.site_input.text()

        if model and site:
            self.infer_btn.setEnabled(True)
            self.status_label.setText("准备就绪，点击开始推理")
        else:
            self.infer_btn.setEnabled(False)

    def _start_inference(self):
        """开始推理"""
        model_path = Path(self.model_input.text())
        site_path = Path(self.site_input.text())

        if not model_path.exists():
            self.window().show_error("错误", "模型文件不存在")
            return

        if not site_path.exists():
            self.window().show_error("错误", "站点文件夹不存在")
            return

        # 禁用按钮
        self.infer_btn.setEnabled(False)
        self.model_browse_btn.setEnabled(False)
        self.site_browse_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 清空日志
        self.log_output.clear()

        # 获取配置
        device_text = self.device_combo.currentText()
        if "auto" in device_text:
            device = "auto"
        elif "cpu" in device_text:
            device = "cpu"
        elif "0" in device_text:
            device = "0"
        else:
            device = "mps"

        config = {
            "confidence": self.conf_spin.value(),
            "iou": self.iou_spin.value(),
            "batch_size": self.batch_spin.value(),
            "device": device,
        }

        # 创建并启动 Worker
        self.worker = InferenceWorker(model_path, site_path, config)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _stop_inference(self):
        """停止推理"""
        if self.worker:
            self.worker.cancel()
            self.stop_btn.setEnabled(False)
            self.status_label.setText("正在停止推理...")

    def _on_progress(self, current: int, total: int, message: str):
        """处理进度更新"""
        percentage = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)

    def _on_log(self, message: str):
        """处理日志消息"""
        self.log_output.append(message)

    def _on_finished(self, success: bool, result):
        """处理推理完成"""
        # 恢复按钮
        self.infer_btn.setEnabled(True)
        self.model_browse_btn.setEnabled(True)
        self.site_browse_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if success and result:
            # 更新统计
            stats = result.get("statistics", {})
            self.stats_labels["pending"].setText(str(stats.get("pending", 0)))
            self.stats_labels["processed"].setText(str(stats.get("processed", 0)))
            self.stats_labels["success"].setText(str(stats.get("success", 0)))
            self.stats_labels["failed"].setText(str(stats.get("failed", 0)))

            self.window().show_info(
                "推理完成",
                f"成功处理 {stats.get('success', 0)} 张图片"
            )
        else:
            self.window().show_error("推理失败", "推理过程中出现错误")

    def _on_error(self, error_message: str):
        """处理错误"""
        self.log_output.append(f"错误: {error_message}")
        self.window().show_error("推理错误", error_message)

    def on_leave(self):
        """离开页面时清理"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
