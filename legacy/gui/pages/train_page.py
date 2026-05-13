"""
AutoLabeler 训练页面
使用标注数据训练 YOLO 模型
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
    SpinBox,
    DoubleSpinBox,
    ComboBox,
    setFont,
)

from gui.pages.base_page import BasePage
from gui.workers.train_worker import TrainWorker


class TrainPage(BasePage):
    """
    训练页面
    使用标注数据训练 YOLO 模型
    """

    def __init__(self, parent=None):
        # 在调用 super().__init__ 之前初始化属性
        self.data_input = None
        self.data_browse_btn = None
        self.model_input = None
        self.model_browse_btn = None
        self.output_input = None
        self.output_browse_btn = None
        self.train_btn = None
        self.stop_btn = None
        self.progress_bar = None
        self.log_output = None

        # 配置参数
        self.epochs_spin = None
        self.batch_spin = None
        self.imgsz_spin = None
        self.device_combo = None
        self.patience_spin = None
        self.box_spin = None
        self.cls_spin = None
        self.scale_spin = None
        self.cache_combo = None

        # 训练指标显示
        self.metric_labels = {}

        # Worker
        self.worker = None

        super().__init__("训练", parent)

    def init_ui(self):
        """初始化UI"""
        # 标题和描述
        self.add_title("训练 YOLO 模型")
        self.add_description(
            "使用标注数据训练 YOLO 目标检测模型。"
            "训练过程会自动保存最佳模型权重。"
        )
        self.add_spacing(20)

        # 文件选择卡片
        self._create_file_selection()
        self.add_spacing(16)

        # 训练配置卡片
        self._create_config_section()
        self.add_spacing(16)

        # 训练控制卡片
        self._create_controls()
        self.add_spacing(16)

        # 训练指标卡片
        self._create_metrics()
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

        # data.yaml
        data_label = StrongBodyLabel("数据配置:")
        card_layout.addWidget(data_label, row, 0)

        self.data_input = LineEdit()
        self.data_input.setPlaceholderText("选择 data.yaml 文件...")
        self.data_input.setReadOnly(True)
        card_layout.addWidget(self.data_input, row, 1)

        self.data_browse_btn = PushButton("浏览...", self, FluentIcon.FOLDER)
        self.data_browse_btn.clicked.connect(self._browse_data)
        card_layout.addWidget(self.data_browse_btn, row, 2)

        row += 1

        # 基础模型
        model_label = StrongBodyLabel("基础模型:")
        card_layout.addWidget(model_label, row, 0)

        self.model_input = LineEdit()
        self.model_input.setPlaceholderText("选择预训练模型 (如 yolo11n.pt)...")
        self.model_input.setReadOnly(True)
        card_layout.addWidget(self.model_input, row, 1)

        self.model_browse_btn = PushButton("浏览...", self, FluentIcon.FOLDER)
        self.model_browse_btn.clicked.connect(self._browse_model)
        card_layout.addWidget(self.model_browse_btn, row, 2)

        row += 1

        # 输出目录
        output_label = StrongBodyLabel("输出目录:")
        card_layout.addWidget(output_label, row, 0)

        self.output_input = LineEdit()
        self.output_input.setPlaceholderText("选择模型输出目录...")
        self.output_input.setReadOnly(True)
        card_layout.addWidget(self.output_input, row, 1)

        self.output_browse_btn = PushButton("浏览...", self, FluentIcon.FOLDER)
        self.output_browse_btn.clicked.connect(self._browse_output)
        card_layout.addWidget(self.output_browse_btn, row, 2)

        self.content_layout.addWidget(card)

    def _create_config_section(self):
        """创建配置区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        row = 0

        # 训练轮次
        epochs_label = StrongBodyLabel("训练轮次:")
        card_layout.addWidget(epochs_label, row, 0)

        self.epochs_spin = SpinBox()
        self.epochs_spin.setRange(1, 500)
        self.epochs_spin.setValue(100)
        card_layout.addWidget(self.epochs_spin, row, 1, 1, 2)

        row += 1

        # 批次大小
        batch_label = StrongBodyLabel("批次大小:")
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

        # 图片尺寸
        imgsz_label = StrongBodyLabel("图片尺寸:")
        card_layout.addWidget(imgsz_label, row, 0)

        self.imgsz_spin = SpinBox()
        self.imgsz_spin.setRange(320, 1280)
        self.imgsz_spin.setSingleStep(32)
        self.imgsz_spin.setValue(640)
        card_layout.addWidget(self.imgsz_spin, row, 1, 1, 2)

        row += 1

        # 计算设备
        device_label = StrongBodyLabel("计算设备:")
        card_layout.addWidget(device_label, row, 0)

        self.device_combo = ComboBox()
        self.device_combo.addItems(["auto (自动检测)", "cpu", "0 (GPU 0)", "mps"])
        self.device_combo.setCurrentIndex(0)
        card_layout.addWidget(self.device_combo, row, 1, 1, 2)

        row += 1

        # 早停轮次
        patience_label = StrongBodyLabel("早停轮次:")
        card_layout.addWidget(patience_label, row, 0)

        self.patience_spin = SpinBox()
        self.patience_spin.setRange(5, 100)
        self.patience_spin.setValue(50)
        card_layout.addWidget(self.patience_spin, row, 1, 1, 2)

        row += 1

        # Box增益（小目标检测）
        box_label = StrongBodyLabel("Box增益:")
        card_layout.addWidget(box_label, row, 0)

        self.box_spin = DoubleSpinBox()
        self.box_spin.setRange(0.5, 20.0)
        self.box_spin.setSingleStep(0.5)
        self.box_spin.setValue(7.5)
        self.box_spin.setDecimals(1)
        box_help = BodyLabel("(小目标可降低此值，极小目标建议2-3)")
        box_help.setStyleSheet("color: #888; font-size: 11px;")
        card_layout.addWidget(self.box_spin, row, 1)
        card_layout.addWidget(box_help, row, 2)

        row += 1

        # Cls增益（小目标检测）
        cls_label = StrongBodyLabel("Cls增益:")
        card_layout.addWidget(cls_label, row, 0)

        self.cls_spin = DoubleSpinBox()
        self.cls_spin.setRange(0.1, 2.0)
        self.cls_spin.setSingleStep(0.1)
        self.cls_spin.setValue(0.5)
        self.cls_spin.setDecimals(1)
        cls_help = BodyLabel("(小目标建议0.3-0.5，降低类别损失权重)")
        cls_help.setStyleSheet("color: #888; font-size: 11px;")
        card_layout.addWidget(self.cls_spin, row, 1)
        card_layout.addWidget(cls_help, row, 2)

        row += 1

        # Scale缩放（小目标检测）
        scale_label = StrongBodyLabel("Scale缩放:")
        card_layout.addWidget(scale_label, row, 0)

        self.scale_spin = DoubleSpinBox()
        self.scale_spin.setRange(0.1, 1.5)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.setValue(0.5)
        self.scale_spin.setDecimals(1)
        scale_help = BodyLabel("(小目标建议0.3-0.5，减少缩放增强幅度)")
        scale_help.setStyleSheet("color: #888; font-size: 11px;")
        card_layout.addWidget(self.scale_spin, row, 1)
        card_layout.addWidget(scale_help, row, 2)

        row += 1

        # 数据缓存模式
        cache_label = StrongBodyLabel("数据缓存:")
        card_layout.addWidget(cache_label, row, 0)

        self.cache_combo = ComboBox()
        self.cache_combo.addItems(["ram (内存缓存)", "disk (硬盘缓存)", "none (不缓存)"])
        self.cache_combo.setCurrentIndex(0)  # 默认 ram
        cache_help = BodyLabel("(ram最快但占内存，disk适中)")
        cache_help.setStyleSheet("color: #888; font-size: 11px;")
        card_layout.addWidget(self.cache_combo, row, 1)
        card_layout.addWidget(cache_help, row, 2)

        self.content_layout.addWidget(card)

    def _create_controls(self):
        """创建控制区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # 训练按钮
        self.train_btn = PushButton("开始训练", self, FluentIcon.IOT)
        self.train_btn.setEnabled(False)
        self.train_btn.clicked.connect(self._start_train)
        card_layout.addWidget(self.train_btn, 0, 0)

        # 停止按钮
        self.stop_btn = PushButton("停止训练", self, FluentIcon.PAUSE)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_train)
        card_layout.addWidget(self.stop_btn, 0, 1)

        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        card_layout.addWidget(self.progress_bar, 1, 0, 1, 3)

        # 状态标签
        self.status_label = BodyLabel("请先选择数据配置、模型和输出目录")
        card_layout.addWidget(self.status_label, 2, 0, 1, 3)

        self.content_layout.addWidget(card)

    def _create_metrics(self):
        """创建训练指标区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        # 标题
        title = SubtitleLabel("训练指标")
        card_layout.addWidget(title, 0, 0, 1, 4)

        # 指标项
        metrics = [
            ("当前轮次", "epoch", "0 / 0"),
            ("mAP50", "map50", "0.000"),
            ("mAP50-95", "map50_95", "0.000"),
        ]

        for i, (label_text, key, default) in enumerate(metrics):
            row = 1 + i // 2
            col = (i % 2) * 2

            label = StrongBodyLabel(f"{label_text}:")
            card_layout.addWidget(label, row, col)

            value_label = SubtitleLabel(default)
            setFont(value_label, 16)
            card_layout.addWidget(value_label, row, col + 1)

            self.metric_labels[key] = value_label

        self.content_layout.addWidget(card)

    def _create_log_output(self):
        """创建日志输出区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        title = StrongBodyLabel("训练日志:")
        card_layout.addWidget(title, 0, 0)

        self.log_output = TextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("训练日志将在这里显示...")
        self.log_output.setMaximumHeight(150)
        card_layout.addWidget(self.log_output, 1, 0)

        self.content_layout.addWidget(card)

    def _browse_data(self):
        """浏览并选择 data.yaml 文件"""
        file, _ = QFileDialog.getOpenFileName(
            self,
            "选择 data.yaml 文件",
            "",
            "YAML Files (*.yaml);;All Files (*)"
        )

        if file:
            self.data_input.setText(file)
            self._check_ready()

    def _browse_model(self):
        """浏览并选择模型文件"""
        file, _ = QFileDialog.getOpenFileName(
            self,
            "选择预训练模型",
            "",
            "Model Files (*.pt);;All Files (*)"
        )

        if file:
            self.model_input.setText(file)
            self._check_ready()

    def _browse_output(self):
        """浏览并选择输出目录"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            "",
            QFileDialog.ShowDirsOnly
        )

        if folder:
            self.output_input.setText(folder)
            self._check_ready()

    def _get_cache_value(self):
        """获取缓存模式的值"""
        cache_text = self.cache_combo.currentText()
        if "ram" in cache_text:
            return "ram"
        elif "disk" in cache_text:
            return True  # disk
        else:
            return False  # none

    def _check_ready(self):
        """检查是否准备好开始"""
        data = self.data_input.text()
        model = self.model_input.text()
        output = self.output_input.text()

        if data and model and output:
            self.train_btn.setEnabled(True)
            self.status_label.setText("准备就绪，点击开始训练")
        else:
            self.train_btn.setEnabled(False)

    def _start_train(self):
        """开始训练"""
        data_path = Path(self.data_input.text())
        model_path = Path(self.model_input.text())
        output_path = Path(self.output_input.text())

        if not data_path.exists():
            self.window().show_error("错误", "数据配置文件不存在")
            return

        if not model_path.exists():
            self.window().show_error("错误", "模型文件不存在")
            return

        # 禁用按钮
        self.train_btn.setEnabled(False)
        self.data_browse_btn.setEnabled(False)
        self.model_browse_btn.setEnabled(False)
        self.output_browse_btn.setEnabled(False)
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
            "epochs": self.epochs_spin.value(),
            "batch_size": self.batch_spin.value(),
            "image_size": self.imgsz_spin.value(),
            "device": device,
            "patience": self.patience_spin.value(),
            "box": self.box_spin.value(),
            "cls": self.cls_spin.value(),
            "scale": self.scale_spin.value(),
            "cache": self._get_cache_value(),
        }

        # 创建并启动 Worker
        self.worker = TrainWorker(data_path, model_path, output_path, config)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.metrics.connect(self._on_metrics)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _stop_train(self):
        """停止训练"""
        if self.worker:
            self.worker.cancel()
            self.stop_btn.setEnabled(False)
            self.status_label.setText("正在停止训练...")

    def _on_progress(self, current: int, total: int, message: str):
        """处理进度更新"""
        percentage = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(percentage)

        # 特殊处理完成消息
        if message == "Training completed":
            self.status_label.setText("训练完成")
        else:
            self.status_label.setText(message)

    def _on_log(self, message: str):
        """处理日志消息"""
        self.log_output.append(message)

    def _on_metrics(self, metrics: dict):
        """处理训练指标更新"""
        if "epoch" in metrics:
            current = metrics.get("epoch", 0)
            total = metrics.get("total_epochs", 0)
            self.metric_labels["epoch"].setText(f"{current} / {total}")

        if "metrics" in metrics:
            m = metrics["metrics"]
            if "mAP50" in m:
                self.metric_labels["map50"].setText(f"{m['mAP50']:.3f}")
            if "mAP50-95" in m:
                self.metric_labels["map50_95"].setText(f"{m['mAP50-95']:.3f}")

    def _on_finished(self, success: bool, result):
        """处理训练完成"""
        # 恢复按钮
        self.train_btn.setEnabled(True)
        self.data_browse_btn.setEnabled(True)
        self.model_browse_btn.setEnabled(True)
        self.output_browse_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if success and result:
            best_model = result.get("best_model", "")
            self.window().show_info(
                "训练完成",
                f"最佳模型已保存到: {best_model}"
            )
        else:
            self.window().show_error("训练失败", "训练过程中出现错误")

    def _on_error(self, error_message: str):
        """处理错误"""
        self.log_output.append(f"错误: {error_message}")
        self.window().show_error("训练错误", error_message)

    def on_leave(self):
        """离开页面时清理"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
