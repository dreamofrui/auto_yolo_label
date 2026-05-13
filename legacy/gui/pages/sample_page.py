"""
AutoLabeler 抽样页面
从产品文件夹中抽取样本图片用于标注
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
    ComboBox,
    SpinBox,
    DoubleSpinBox,
    setFont,
)

from gui.pages.base_page import BasePage
from gui.workers.sample_worker import SampleWorker


class SamplePage(BasePage):
    """
    抽样页面
    从产品文件夹中抽取样本图片用于标注
    """

    def __init__(self, parent=None):
        # 在调用 super().__init__ 之前初始化属性
        self.site_input = None
        self.browse_btn = None
        self.output_input = None
        self.output_browse_btn = None
        self.sample_btn = None
        self.progress_bar = None
        self.log_output = None

        # 配置参数
        self.mode_combo = None
        self.count_spin = None
        self.ratio_spin = None
        self.threshold_spin = None
        self.train_ratio_spin = None

        # 统计显示
        self.stats_labels = {}

        # Worker
        self.worker = None

        super().__init__("抽样", parent)

    def init_ui(self):
        """初始化UI"""
        # 标题和描述
        self.add_title("抽取样本图片")
        self.add_description(
            "从每个产品文件夹中抽取部分图片用于人工标注。"
            "支持按固定数量、比例或混合模式抽取。"
        )
        self.add_spacing(20)

        # 文件夹选择卡片
        self._create_folder_selection()
        self.add_spacing(16)

        # 抽样配置卡片
        self._create_config_section()
        self.add_spacing(16)

        # 扫描控制卡片
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

        row = 0

        # 站点文件夹
        site_label = StrongBodyLabel("站点文件夹:")
        card_layout.addWidget(site_label, row, 0)

        self.site_input = LineEdit()
        self.site_input.setPlaceholderText("选择站点文件夹...")
        self.site_input.setReadOnly(True)
        card_layout.addWidget(self.site_input, row, 1)

        self.browse_btn = PushButton("浏览...", self, FluentIcon.FOLDER)
        self.browse_btn.clicked.connect(self._browse_site)
        card_layout.addWidget(self.browse_btn, row, 2)

        row += 1

        # 输出文件夹
        output_label = StrongBodyLabel("输出文件夹:")
        card_layout.addWidget(output_label, row, 0)

        self.output_input = LineEdit()
        self.output_input.setPlaceholderText("选择输出文件夹（database）...")
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

        # 抽样模式
        mode_label = StrongBodyLabel("抽样模式:")
        card_layout.addWidget(mode_label, row, 0)

        self.mode_combo = ComboBox()
        self.mode_combo.addItems(["count (固定数量)", "ratio (比例)", "mixed (混合)"])
        self.mode_combo.setCurrentIndex(0)
        card_layout.addWidget(self.mode_combo, row, 1, 1, 2)

        row += 1

        # 固定数量
        count_label = StrongBodyLabel("抽样数量:")
        card_layout.addWidget(count_label, row, 0)

        self.count_spin = SpinBox()
        self.count_spin.setRange(1, 1000)
        self.count_spin.setValue(40)
        card_layout.addWidget(self.count_spin, row, 1, 1, 2)

        row += 1

        # 抽样比例
        ratio_label = StrongBodyLabel("抽样比例:")
        card_layout.addWidget(ratio_label, row, 0)

        self.ratio_spin = DoubleSpinBox()
        self.ratio_spin.setRange(0.01, 1.0)
        self.ratio_spin.setSingleStep(0.05)
        self.ratio_spin.setValue(0.3)
        self.ratio_spin.setDecimals(2)
        card_layout.addWidget(self.ratio_spin, row, 1, 1, 2)

        row += 1

        # 全抽阈值
        threshold_label = StrongBodyLabel("全抽阈值:")
        card_layout.addWidget(threshold_label, row, 0)

        self.threshold_spin = SpinBox()
        self.threshold_spin.setRange(1, 100)
        self.threshold_spin.setValue(35)
        threshold_help = BodyLabel("(图片数<=此值时全部抽取)")
        threshold_help.setStyleSheet("color: #888; font-size: 11px;")
        card_layout.addWidget(self.threshold_spin, row, 1)
        card_layout.addWidget(threshold_help, row, 2)

        row += 1

        # 训练集比例
        train_label = StrongBodyLabel("训练集比例:")
        card_layout.addWidget(train_label, row, 0)

        self.train_ratio_spin = DoubleSpinBox()
        self.train_ratio_spin.setRange(0.5, 0.99)
        self.train_ratio_spin.setSingleStep(0.05)
        self.train_ratio_spin.setValue(0.9)
        self.train_ratio_spin.setDecimals(2)
        card_layout.addWidget(self.train_ratio_spin, row, 1, 1, 2)

        self.content_layout.addWidget(card)

    def _create_controls(self):
        """创建控制区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # 抽样按钮
        self.sample_btn = PushButton("开始抽样", self, FluentIcon.FILTER)
        self.sample_btn.setEnabled(False)
        self.sample_btn.clicked.connect(self._start_sample)
        card_layout.addWidget(self.sample_btn, 0, 0)

        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        card_layout.addWidget(self.progress_bar, 1, 0, 1, 3)

        # 状态标签
        self.status_label = BodyLabel("请先选择站点文件夹和输出文件夹")
        card_layout.addWidget(self.status_label, 2, 0, 1, 3)

        self.content_layout.addWidget(card)

    def _create_statistics(self):
        """创建统计信息区域"""
        card = CardWidget()
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        # 标题
        title = SubtitleLabel("抽样统计")
        card_layout.addWidget(title, 0, 0, 1, 4)

        # 统计项
        stats = [
            ("总产品数", "total_products", "0"),
            ("抽取样本数", "sampled_count", "0"),
            ("训练集", "train_count", "0"),
            ("验证集", "val_count", "0"),
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

        title = StrongBodyLabel("抽样日志:")
        card_layout.addWidget(title, 0, 0)

        self.log_output = TextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("抽样日志将在这里显示...")
        self.log_output.setMaximumHeight(150)
        card_layout.addWidget(self.log_output, 1, 0)

        self.content_layout.addWidget(card)

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

    def _browse_output(self):
        """浏览并选择输出文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择输出文件夹",
            "",
            QFileDialog.ShowDirsOnly
        )

        if folder:
            self.output_input.setText(folder)
            self._check_ready()

    def _check_ready(self):
        """检查是否准备好开始"""
        site = self.site_input.text()
        output = self.output_input.text()

        if site and output:
            self.sample_btn.setEnabled(True)
            self.status_label.setText("准备就绪，点击开始抽样")
        else:
            self.sample_btn.setEnabled(False)

    def _start_sample(self):
        """开始抽样"""
        site_path = Path(self.site_input.text())
        output_path = Path(self.output_input.text())

        if not site_path.exists():
            self.window().show_error("错误", "站点文件夹不存在")
            return

        # 禁用按钮
        self.sample_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.output_browse_btn.setEnabled(False)

        # 清空日志
        self.log_output.clear()

        # 获取配置
        mode_text = self.mode_combo.currentText()
        if "count" in mode_text:
            mode = "count"
        elif "ratio" in mode_text:
            mode = "ratio"
        else:
            mode = "mixed"

        config = {
            "mode": mode,
            "count": self.count_spin.value(),
            "ratio": self.ratio_spin.value(),
            "full_threshold": self.threshold_spin.value(),
            "train_ratio": self.train_ratio_spin.value(),
        }

        # 创建并启动 Worker
        self.worker = SampleWorker(site_path, output_path, config)
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
        """处理抽样完成"""
        # 恢复按钮
        self.sample_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.output_browse_btn.setEnabled(True)

        if success and result:
            # 更新统计
            stats = result.get("statistics", {})
            self.stats_labels["total_products"].setText(str(stats.get("total_products", 0)))
            self.stats_labels["sampled_count"].setText(str(stats.get("sampled_count", 0)))
            self.stats_labels["train_count"].setText(str(stats.get("train_count", 0)))
            self.stats_labels["val_count"].setText(str(stats.get("val_count", 0)))

            self.window().show_info(
                "抽样完成",
                f"成功抽取 {stats.get('sampled_count', 0)} 张图片"
            )
        else:
            self.window().show_error("抽样失败", "抽样过程中出现错误")

    def _on_error(self, error_message: str):
        """处理错误"""
        self.log_output.append(f"错误: {error_message}")
        self.window().show_error("抽样错误", error_message)

    def on_leave(self):
        """离开页面时清理"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
