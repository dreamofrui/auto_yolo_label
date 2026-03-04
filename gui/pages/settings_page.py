"""
AutoLabeler 设置页面
管理系统配置参数
"""

from PySide6.QtWidgets import QGridLayout
from qfluentwidgets import (
    PushButton,
    CardWidget,
    StrongBodyLabel,
    SubtitleLabel,
    FluentIcon,
    BodyLabel,
    SpinBox,
    DoubleSpinBox,
    LineEdit,
    ComboBox,
    CheckBox,
)

from gui.pages.base_page import BasePage


class SettingsPage(BasePage):
    """
    设置页面
    管理系统配置参数
    """

    def __init__(self, parent=None):
        super().__init__("设置", parent)

    def init_ui(self):
        """初始化UI"""
        # 标题和描述
        self.add_title("系统设置")
        self.add_description(
            "配置 AutoLabeler 的各项参数。"
            "设置将在下次操作时生效。"
        )
        self.add_spacing(20)

        # 抽样设置
        self._create_sample_settings()
        self.add_spacing(16)

        # 训练设置
        self._create_train_settings()
        self.add_spacing(16)

        # 推理设置
        self._create_inference_settings()
        self.add_spacing(16)

        # 操作按钮
        self._create_actions()

        self.add_stretch()

    def _create_sample_settings(self):
        """创建抽样设置区域"""
        card = CardWidget()
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 标题
        title = SubtitleLabel("抽样设置")
        layout.addWidget(title, 0, 0, 1, 3)

        row = 1

        # 抽样模式
        layout.addWidget(StrongBodyLabel("默认抽样模式:"), row, 0)
        self.sample_mode_combo = ComboBox()
        self.sample_mode_combo.addItems(["count", "ratio", "mixed"])
        self.sample_mode_combo.setCurrentIndex(0)
        layout.addWidget(self.sample_mode_combo, row, 1, 1, 2)

        row += 1

        # 固定数量
        layout.addWidget(StrongBodyLabel("默认抽样数量:"), row, 0)
        self.sample_count_spin = SpinBox()
        self.sample_count_spin.setRange(1, 500)
        self.sample_count_spin.setValue(40)
        layout.addWidget(self.sample_count_spin, row, 1, 1, 2)

        row += 1

        # 抽样比例
        layout.addWidget(StrongBodyLabel("默认抽样比例:"), row, 0)
        self.sample_ratio_spin = DoubleSpinBox()
        self.sample_ratio_spin.setRange(0.01, 1.0)
        self.sample_ratio_spin.setSingleStep(0.05)
        self.sample_ratio_spin.setValue(0.3)
        self.sample_ratio_spin.setDecimals(2)
        layout.addWidget(self.sample_ratio_spin, row, 1, 1, 2)

        row += 1

        # 全抽阈值
        layout.addWidget(StrongBodyLabel("全抽阈值:"), row, 0)
        self.sample_threshold_spin = SpinBox()
        self.sample_threshold_spin.setRange(1, 100)
        self.sample_threshold_spin.setValue(35)
        layout.addWidget(self.sample_threshold_spin, row, 1, 1, 2)

        self.content_layout.addWidget(card)

    def _create_train_settings(self):
        """创建训练设置区域"""
        card = CardWidget()
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 标题
        title = SubtitleLabel("训练设置")
        layout.addWidget(title, 0, 0, 1, 3)

        row = 1

        # 训练轮次
        layout.addWidget(StrongBodyLabel("默认训练轮次:"), row, 0)
        self.train_epochs_spin = SpinBox()
        self.train_epochs_spin.setRange(1, 500)
        self.train_epochs_spin.setValue(100)
        layout.addWidget(self.train_epochs_spin, row, 1, 1, 2)

        row += 1

        # 批次大小
        layout.addWidget(StrongBodyLabel("默认批次大小:"), row, 0)
        self.train_batch_spin = SpinBox()
        self.train_batch_spin.setRange(-1, 128)
        self.train_batch_spin.setValue(-1)
        self.train_batch_spin.setSpecialValueText("自动")
        layout.addWidget(self.train_batch_spin, row, 1, 1, 2)

        row += 1

        # 图片尺寸
        layout.addWidget(StrongBodyLabel("默认图片尺寸:"), row, 0)
        self.train_imgsz_spin = SpinBox()
        self.train_imgsz_spin.setRange(320, 1280)
        self.train_imgsz_spin.setSingleStep(32)
        self.train_imgsz_spin.setValue(640)
        layout.addWidget(self.train_imgsz_spin, row, 1, 1, 2)

        row += 1

        # 早停轮次
        layout.addWidget(StrongBodyLabel("早停轮次:"), row, 0)
        self.train_patience_spin = SpinBox()
        self.train_patience_spin.setRange(5, 100)
        self.train_patience_spin.setValue(50)
        layout.addWidget(self.train_patience_spin, row, 1, 1, 2)

        self.content_layout.addWidget(card)

    def _create_inference_settings(self):
        """创建推理设置区域"""
        card = CardWidget()
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 标题
        title = SubtitleLabel("推理设置")
        layout.addWidget(title, 0, 0, 1, 3)

        row = 1

        # 置信度阈值
        layout.addWidget(StrongBodyLabel("默认置信度:"), row, 0)
        self.infer_conf_spin = DoubleSpinBox()
        self.infer_conf_spin.setRange(0.01, 1.0)
        self.infer_conf_spin.setSingleStep(0.05)
        self.infer_conf_spin.setValue(0.25)
        self.infer_conf_spin.setDecimals(2)
        layout.addWidget(self.infer_conf_spin, row, 1, 1, 2)

        row += 1

        # IoU 阈值
        layout.addWidget(StrongBodyLabel("默认 IoU:"), row, 0)
        self.infer_iou_spin = DoubleSpinBox()
        self.infer_iou_spin.setRange(0.01, 1.0)
        self.infer_iou_spin.setSingleStep(0.05)
        self.infer_iou_spin.setValue(0.7)
        self.infer_iou_spin.setDecimals(2)
        layout.addWidget(self.infer_iou_spin, row, 1, 1, 2)

        row += 1

        # 批处理大小
        layout.addWidget(StrongBodyLabel("默认批处理大小:"), row, 0)
        self.infer_batch_spin = SpinBox()
        self.infer_batch_spin.setRange(1, 128)
        self.infer_batch_spin.setValue(32)
        layout.addWidget(self.infer_batch_spin, row, 1, 1, 2)

        self.content_layout.addWidget(card)

    def _create_actions(self):
        """创建操作按钮区域"""
        card = CardWidget()
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 保存按钮
        self.save_btn = PushButton("保存设置", self, FluentIcon.SAVE)
        self.save_btn.clicked.connect(self._save_settings)
        layout.addWidget(self.save_btn, 0, 0)

        # 重置按钮
        self.reset_btn = PushButton("重置默认", self, FluentIcon.SYNC)
        self.reset_btn.clicked.connect(self._reset_settings)
        layout.addWidget(self.reset_btn, 0, 1)

        self.content_layout.addWidget(card)

    def _save_settings(self):
        """保存设置"""
        self.window().show_info("保存成功", "设置已保存")

    def _reset_settings(self):
        """重置设置"""
        # 重置为默认值
        self.sample_mode_combo.setCurrentIndex(0)
        self.sample_count_spin.setValue(40)
        self.sample_ratio_spin.setValue(0.3)
        self.sample_threshold_spin.setValue(35)

        self.train_epochs_spin.setValue(100)
        self.train_batch_spin.setValue(-1)
        self.train_imgsz_spin.setValue(640)
        self.train_patience_spin.setValue(50)

        self.infer_conf_spin.setValue(0.25)
        self.infer_iou_spin.setValue(0.45)
        self.infer_batch_spin.setValue(32)

        self.window().show_info("重置完成", "设置已恢复为默认值")
