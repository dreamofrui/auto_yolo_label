"""PySide6 desktop workbench shell."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.sample_page import SamplePage
from gui.train_page import TrainPage
from gui.infer_page import InferPage
from gui.restore_page import RestorePage
from gui.convert_page import ConvertPage
from gui.scan_page import ScanPage
from gui.labelimg_page import LabelImgPage
from gui.task_runner import AsyncTaskRunner, TaskRunner
from gui.tool_defaults import (
    DEFAULT_TOOL_DEFAULTS_PATH,
    ToolDefaults,
    default_text,
    load_tool_defaults,
    save_tool_defaults,
)
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class ModuleEntry:
    """Navigation entry for a first-version module."""

    key: str
    title: str
    subtitle: str
    description: str
    primary_action: str
    mode_hint: str


@dataclass(frozen=True)
class ManualSectionSpec:
    """Operator manual section content."""

    key: str
    title: str
    copy: str
    rows: tuple[tuple[str, str, str, str], ...]
    note_title: str | None = None
    note_body: str | None = None


MODULES: tuple[ModuleEntry, ...] = (
    ModuleEntry(
        key="scan",
        title="扫描",
        subtitle="建立 Flow 映射",
        description="扫描严格的 site / Code / Product / image 结构，生成 mapping.json 和 classes.txt。",
        primary_action="开始扫描",
        mode_hint="Flow only",
    ),
    ModuleEntry(
        key="sample",
        title="抽样",
        subtitle="减少人工标注量",
        description="Flow 模式按 Code/Product 复制样本，独立模式按最小图片文件夹移动选中图片。",
        primary_action="准备抽样",
        mode_hint="Flow / Independent",
    ),
    ModuleEntry(
        key="label",
        title="标注",
        subtitle="打开 LabelImg",
        description="按 YOLO 或 VOC 模式启动外部 LabelImg；VOC 标注把 XML 写到图片同级。",
        primary_action="打开 LabelImg",
        mode_hint="YOLO / VOC",
    ),
    ModuleEntry(
        key="train",
        title="训练",
        subtitle="训练 YOLO 模型",
        description="校验标准 YOLO 数据集，保留常用参数，训练结果由用户自行选择用于推理。",
        primary_action="检查数据集",
        mode_hint="YOLO dataset",
    ),
    ModuleEntry(
        key="infer",
        title="推理",
        subtitle="生成预测标签",
        description="Flow 模式默认推理未抽样图片，独立模式递归处理用户选择的图片目录。",
        primary_action="准备推理",
        mode_hint="Flow / Independent",
    ),
    ModuleEntry(
        key="review",
        title="复核",
        subtitle="检查预测结果",
        description="Flow 模式通过 mapping 定位原图，使用 run/labels 作为可编辑预测标签目录。",
        primary_action="打开复核",
        mode_hint="Prediction review",
    ),
    ModuleEntry(
        key="restore",
        title="还原",
        subtitle="写回 XML",
        description="把 YOLO 标签转换为 VOC XML，写到匹配原图同级目录，执行前必须预检。",
        primary_action="开始预检",
        mode_hint="Preflight required",
    ),
    ModuleEntry(
        key="convert",
        title="转换",
        subtitle="XML 与 YOLO 数据转换",
        description="主流程是图片加 XML 目录生成标准 YOLO 数据集，辅助转换折叠处理。",
        primary_action="分析目录",
        mode_hint="XML -> YOLO",
    ),
)

_HOME_AI_PREVIEW_MIN_WIDTH = 1120
_ACTIVE_TASK_STATUSES = {"queued", "running"}
_ATTENTION_TASK_STATUSES = {"failed", "cancelled", "interrupted"}
_TERMINAL_TASK_STATUSES = {"succeeded", "failed", "cancelled", "interrupted"}
_TASK_CENTER_RETENTION_DAYS = 10
_UI_FONT_FAMILIES = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "Noto Sans SC",
    "SimHei",
    "SimSun",
    "Segoe UI",
)
_UI_FONT_FILES = (
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/simsun.ttc"),
)

_TASK_STATUS_LABELS = {
    "queued": "等待中",
    "running": "运行中",
    "succeeded": "已完成",
    "failed": "失败",
    "cancelled": "已停止",
    "interrupted": "已中断",
}

_TRAIN_DEVICE_OPTIONS = (
    ("auto", "auto"),
    ("cpu", "cpu"),
    ("All GPUs", "gpu"),
    ("GPU 0", "0"),
    ("GPU 1", "1"),
    ("GPU 0+1", "0,1"),
)

_MANUAL_SAMPLE_ROWS = (
    ("模式", "Flow / 独立", "Flow 依赖 mapping 并复制样本；独立模式用显式路径并移动选中图片。", "需要追溯原图时用 Flow；只处理散图时用独立模式。"),
    ("count", "40", "每个分组固定抽取的数量。", "各产品组数量接近时使用，人工标注量更可控。"),
    ("ratio", "0.3", "每个分组按比例抽取，0.3 表示约 30%。", "组大小差距大时使用，提高或降低整体标注量。"),
    ("mixed", "推荐", "小组可全取，大组受比例、最小数量和最大数量共同限制。", "生产数据优先使用，兼顾覆盖和人工成本。"),
    ("min_count", "20", "mixed 下每个大分组尽量至少抽到的数量。", "小类漏检风险高时提高。"),
    ("max_count", "50", "mixed 下每个大分组最多抽取的数量。", "大组过多占用标注时间时降低。"),
    ("全量阈值", "35", "小于或等于该数量的分组可全量进入样本。", "小组需要完整覆盖时提高。"),
    ("训练比例", "0.9", "抽中样本再按分组切为 train/val，单张图片进 train。", "验证集太少时降低到 0.8。"),
)

_MANUAL_SCAN_ROWS = (
    ("输入", "站点根目录", "必须是 site / Code / Product / image 三级业务结构。", "结构不符合时先整理目录再扫描。"),
    ("输出", "mapping.json", "记录原图、Code、Product、抽样、推理和还原关系。", "后续 Flow 流程都依赖它追溯原图。"),
    ("输出", "classes.txt", "从 Code/Product 结构生成类别清单。", "标注、训练、复核和还原时保持同一份类别顺序。"),
    ("安全规则", "只读取", "扫描不移动、不复制、不删除源图片。", "扫描失败时根据错误路径修正目录。"),
)

_MANUAL_TRAIN_ROWS = (
    ("device", "auto / All GPUs / GPU 0 / GPU 1 / GPU 0+1", "auto 自动选择；All GPUs 使用可见 CUDA；GPU 0 或 GPU 1 固定单卡；GPU 0+1 使用双卡。", "多卡训练时 batch 要填总 batch，避免使用 -1 自动 batch。"),
    ("epochs", "100-200", "完整训练轮数。2 只适合冒烟测试。", "欠拟合时提高，快速验证时降低。"),
    ("image size", "640", "模型输入尺寸。尺寸越大越慢、越耗显存。", "小目标漏检时试 960 或 1280。"),
    ("batch", "-1 / 16 / 32", "单卡或 CPU 可用 -1 自动；多卡时这是所有卡合计的总 batch。", "双卡 batch 32 约等于每卡 16；显存不足时改小。"),
    ("workers", "8", "每个训练进程的数据加载线程数；多卡总 workers 约为 workers 乘以卡数。", "四卡 workers 8 会变成约 32 个加载线程，CPU 或磁盘紧张时降低。"),
    ("optimizer", "AdamW", "优化器，AdamW 稳定；SGD 更传统；auto 交给后端。", "结果波动大时固定 AdamW 或 SGD 对比。"),
    ("lr0", "0.001-0.01", "初始学习率，大则快但可能不稳定，小则稳但慢。", "AdamW 可先试 0.001；SGD 常用 0.01。"),
    ("box / cls / dfl", "7.5 / 0.5 / 1.5", "定位框、类别分类和边框细节的损失权重。", "框偏移调 box，类别混淆调 cls，dfl 通常不改。"),
    ("scale", "0.5", "缩放增强幅度。", "小目标受缩放影响时降到 0.3。"),
    ("cache", "ram / disk", "缓存训练数据，ram 快但占内存，disk 占磁盘。", "内存紧张用 disk 或 false。"),
    ("run name", "按实验命名", "固定输出文件夹名，方便比较实验。", "需要复现实验时填写。"),
    ("overwrite", "默认关闭", "允许覆盖固定 run 输出。", "确认旧结果不保留时才开启。"),
)

_MANUAL_LABEL_ROWS = (
    ("模式", "YOLO / VOC", "YOLO 标注保存 txt；VOC 标注保存 Pascal VOC XML。", "需要直接生成 XML 时切到 VOC 标注。"),
    ("图片目录", "必填", "LabelImg 打开的原图目录。", "标训练样本时选择抽样数据集的图片目录。"),
    ("classes.txt", "YOLO 必填", "类别名称列表，顺序决定 YOLO 标签中的类别编号。", "必须和训练/推理/还原使用的类别顺序一致。"),
    ("标签输出目录", "YOLO 必填", "LabelImg 保存 YOLO txt 的目录。", "训练标注写到数据集 labels 目录；复核不要用这里，使用复核功能。"),
    ("VOC 输出", "图片同级", "VOC 模式只选图片目录，LabelImg 会把同名 XML 写在图片所在文件夹。", "适合像 LabelImg 原生方式一样打开一个图片文件夹标注 XML。"),
    ("常见问题", "看不到旧框", "LabelImg 读取已有 YOLO 标签时需要标签目录旁有 classes.txt。", "确认 classes.txt 已同步到标签目录。"),
)

_MANUAL_INFER_ROWS = (
    ("模式", "Flow / 独立", "Flow 默认推理未抽样图片；独立模式递归推理图片文件夹。", "没有 mapping 时用独立模式。"),
    ("confidence", "0.25", "置信度阈值，越低检出越多但误检也更多。", "漏检多时降到 0.05-0.15，误检多时提高。"),
    ("IoU", "0.7", "NMS 去重阈值，控制重叠预测框如何合并或抑制。", "重复框多时降低；目标密集靠近时不要过低。"),
    ("batch", "-1 / 32", "每批推理图片数，影响速度和显存。", "显存不足或卡住时调小。"),
    ("device", "auto / gpu", "auto 自动选择；gpu 使用显卡；cpu 使用 CPU。", "批量推理优先 gpu。"),
    ("输出根目录", "自动 run", "每次生成 run_YYYYMMDD_HHMMSS，包含 inference_config.json、classes.txt、labels。", "独立模式只选择输出根目录，不直接写散文件。"),
    ("overwrite", "默认关闭", "允许覆盖已有 run 输出。", "通常不启用，只在明确复用固定目录时开启。"),
)

_MANUAL_REVIEW_ROWS = (
    ("站点目录", "Flow site", "包含 mapping.json 和推理 run 的原始站点目录。", "只复核 Flow 推理结果时使用。"),
    ("推理 run", "run_时间戳", "选择需要检查的预测结果目录。", "同一模型多次推理时按 run 时间选择。"),
    ("Code/Product", "树节点", "选择一个业务节点后定位原图和 run/labels。", "优先逐个节点复核，避免混淆产品。"),
    ("缺失标签", "允许但提醒", "没有预测 txt 的图片仍可进入 LabelImg 新增标注。", "缺失原图会阻塞打开。"),
)

_MANUAL_RESTORE_ROWS = (
    ("来源模式", "Flow run / Flow dataset / 独立", "从预测 run、训练数据集或独立标签目录还原 XML。", "Flow 优先用 mapping；散图用独立模式。"),
    ("classes.txt", "必须可解析", "把 YOLO 类别编号转换成 XML 里的类别名称。", "独立还原需要手动选择 classes.txt。"),
    ("预检", "必须先做", "检查标签、原图匹配、重复文件名、已有 XML 和无效标签。", "预检失败时不会写任何 XML。"),
    ("覆盖", "默认关闭", "已有 XML 默认阻塞，开启覆盖前要确认旧结果不保留。", "正式数据建议先备份或换输出副本验证。"),
)

_MANUAL_CONVERT_ROWS = (
    ("主功能", "XML 转 YOLO", "图片目录加同名 VOC XML 转为标准 YOLO 数据集。", "已有 XML 标注需要训练 YOLO 时使用。"),
    ("训练比例", "0.9", "按最小图片文件夹分组后切 train/val。", "验证集太少时降到 0.8。"),
    ("类别来源", "XML / classes.txt", "可从 XML 收集类别，也可用已有 classes.txt 固定顺序。", "跨批次训练建议用固定 classes.txt。"),
    ("安全规则", "复制不移动", "转换会复制图片并生成 YOLO txt，不移动源数据。", "输出目录非空时需确认，失败不写部分数据集。"),
)

_MANUAL_WORKFLOW_ITEMS = (
    ("扫描", "建立 Flow 映射"),
    ("抽样", "减少人工标注量"),
    ("标注", "打开 LabelImg"),
    ("训练", "训练 YOLO 模型"),
    ("推理", "生成预测标签"),
    ("复核", "检查预测结果"),
    ("还原", "写回 XML"),
    ("转换", "XML 与 YOLO 数据转换"),
)

_MANUAL_FUNCTION_SPECS = (
    ManualSectionSpec(
        "scan",
        "扫描",
        "建立 Flow 模式的基础数据，只读取目录并生成 mapping.json 和 classes.txt。",
        _MANUAL_SCAN_ROWS,
        "目录要求",
        "Flow 扫描要求 site / Code / Product / image。结构不符合时先修正目录，不要在后续步骤手动拼路径。",
    ),
    ManualSectionSpec(
        "sample",
        "抽样",
        "决定抽多少图、如何分 train/val，以及是否移动源文件。",
        _MANUAL_SAMPLE_ROWS,
        "推荐起步",
        "正式建训练集优先用 mixed，ratio 0.3，min 20，max 50，全量阈值 35，训练比例 0.9。",
    ),
    ManualSectionSpec(
        "label",
        "标注",
        "打开外部 LabelImg，对抽样图片补齐 YOLO 标签，或直接按 VOC 模式写同级 XML。",
        _MANUAL_LABEL_ROWS,
        "类别顺序",
        "YOLO 模式下 classes.txt 的行号就是类别编号。VOC 模式写 XML 类别名，后续转 YOLO 时仍要确认类别顺序。",
    ),
    ManualSectionSpec(
        "train",
        "训练",
        "决定训练速度、显存占用、收敛方式和输出 run 的管理方式。",
        _MANUAL_TRAIN_ROWS,
        "服务器测试组合",
        "单卡先用 gpu、epochs 100、image size 640、batch -1、optimizer AdamW、lr0 0.001；双卡用 0,1，并把 batch 改成 16 或 32。",
    ),
    ManualSectionSpec(
        "infer",
        "推理",
        "决定检出数量、重叠框去重、推理速度和输出 run 的位置。",
        _MANUAL_INFER_ROWS,
        "输出结构",
        "每次推理生成 run_YYYYMMDD_HHMMSS，里面包含 inference_config.json、classes.txt 和 labels/；空预测也会写空 txt。",
    ),
    ManualSectionSpec(
        "review",
        "复核",
        "打开预测 run，对 run/labels 下的预测标签进行人工检查和修改。",
        _MANUAL_REVIEW_ROWS,
        "编辑位置",
        "复核编辑的是推理 run 里的 labels，不会直接改原图目录。确认后再用还原功能写回 XML。",
    ),
    ManualSectionSpec(
        "restore",
        "还原",
        "把已确认的 YOLO 标签转换为 VOC XML，写回匹配原图旁边。",
        _MANUAL_RESTORE_ROWS,
        "高风险动作",
        "还原会写文件。必须先看预检结果，再确认写回和覆盖选项。",
    ),
    ManualSectionSpec(
        "convert",
        "转换",
        "在 XML 和 YOLO 数据集之间做格式转换，主要用于把已有 XML 标注转成训练数据。",
        _MANUAL_CONVERT_ROWS,
        "与还原区别",
        "转换不使用 mapping，也不追溯 Flow 原图关系；需要把复核结果写回原始业务目录时使用还原。",
    ),
)


class LoginView(QWidget):
    """Enterprise-looking first-version login surface."""

    login_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("loginView")

        root = QHBoxLayout(self)
        root.setContentsMargins(48, 42, 48, 42)
        root.setSpacing(24)

        self.login_story = QFrame()
        story = self.login_story
        story.setObjectName("loginStory")
        story.setProperty("surfaceRole", "product")
        story_layout = QVBoxLayout(story)
        story_layout.setContentsMargins(34, 32, 34, 32)
        story_layout.setSpacing(18)

        brand = QLabel("AutoLabeler")
        brand.setObjectName("loginBrand")
        headline = QLabel("半自动图像标注工作台")
        headline.setObjectName("loginHeadline")
        headline.setWordWrap(True)
        copy = QLabel(
            "把扫描、抽样、标注、训练、推理、复核和 XML 写回放在一个桌面工作台里，"
            "减少重复人工标注，同时保留可追溯流程。"
        )
        copy.setObjectName("mutedText")
        copy.setWordWrap(True)

        self.login_workflow_panel = QFrame()
        self.login_workflow_panel.setObjectName("loginWorkflowPanel")
        self.login_workflow_panel.setProperty("surfaceRole", "workflow")
        workflow_layout = QGridLayout(self.login_workflow_panel)
        workflow_layout.setContentsMargins(12, 12, 12, 12)
        workflow_layout.setHorizontalSpacing(10)
        workflow_layout.setVerticalSpacing(10)
        for index, text in enumerate(
            (
                "01 扫描建映射",
                "02 抽样少标注",
                "03 LabelImg 标注",
                "04 训练模型",
                "05 推理复核",
                "06 还原 XML",
            )
        ):
            step = QLabel(text)
            step.setObjectName("loginWorkflowStep")
            workflow_layout.addWidget(step, index // 3, index % 3)

        self.login_boundary_panel = QFrame()
        self.login_boundary_panel.setObjectName("loginBoundaryPanel")
        self.login_boundary_panel.setProperty("surfaceRole", "boundary")
        boundary_layout = QGridLayout(self.login_boundary_panel)
        boundary_layout.setContentsMargins(12, 12, 12, 12)
        boundary_layout.setHorizontalSpacing(10)
        boundary_layout.setVerticalSpacing(10)
        for index, text in enumerate(
            (
                "输入：站点目录、YOLO 数据集、推理 run",
                "输出：mapping.json、classes.txt、标签和 XML",
                "安全：移动、覆盖、写回前先预检和确认",
                "AI 预览：只准备参数，不直接执行任务",
            )
        ):
            item = QLabel(text)
            item.setObjectName("loginBoundaryItem")
            item.setWordWrap(True)
            boundary_layout.addWidget(item, index // 2, index % 2)

        strip = QGridLayout()
        strip.setHorizontalSpacing(10)
        strip.setVerticalSpacing(10)
        for index, text in enumerate(("可追溯", "少标注", "可复核", "可写回")):
            tile = QLabel(text)
            tile.setObjectName("loginStripTile")
            tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
            strip.addWidget(tile, 0, index)

        story_layout.addWidget(brand)
        story_layout.addWidget(headline)
        story_layout.addWidget(copy)
        story_layout.addWidget(self.login_workflow_panel, 0)
        story_layout.addWidget(self.login_boundary_panel, 0)
        story_layout.addStretch(1)
        story_layout.addLayout(strip)

        self.login_card = QFrame()
        card = self.login_card
        card.setObjectName("loginCard")
        card.setProperty("surfaceRole", "access")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(14)

        title = QLabel("进入工作台")
        title.setObjectName("panelTitle")
        note = QLabel("第一版保留企业 SSO 入口，实际使用本地演示登录。")
        note.setObjectName("mutedText")
        note.setWordWrap(True)
        sso_button = QPushButton("企业 SSO（预留）")
        sso_button.setEnabled(False)
        sso_button.setObjectName("secondaryButton")
        sso_button.setProperty("buttonRole", "reservedAccess")
        self.demo_login_button = QPushButton("本地演示登录")
        self.demo_login_button.setObjectName("primaryButton")
        self.demo_login_button.setProperty("buttonRole", "primaryAccess")
        self.demo_login_button.clicked.connect(self.login_requested.emit)

        username = QLineEdit()
        username.setPlaceholderText("账号")
        username.setObjectName("formInput")
        password = QLineEdit()
        password.setPlaceholderText("密码（第一版不校验）")
        password.setEchoMode(QLineEdit.EchoMode.Password)
        password.setObjectName("formInput")
        footnote = QLabel("这里不实现真实权限或云端身份管理，避免界面承诺不存在的安全能力。")
        footnote.setObjectName("footnote")
        footnote.setWordWrap(True)

        card_layout.addWidget(title)
        card_layout.addWidget(note)
        card_layout.addWidget(sso_button)
        card_layout.addWidget(username)
        card_layout.addWidget(password)
        card_layout.addWidget(self.demo_login_button)
        card_layout.addStretch(1)
        card_layout.addWidget(footnote)

        root.addWidget(story, 1)
        root.addWidget(card, 0)


class WorkbenchView(QWidget):
    """Main desktop workbench with navigation and shared page layout."""

    def __init__(
        self,
        task_registry: TaskRegistry | None = None,
        sample_worker: object | None = None,
        train_worker: object | None = None,
        infer_worker: object | None = None,
        restore_worker: object | None = None,
        convert_worker: object | None = None,
        scan_worker: object | None = None,
        labelimg_worker: object | None = None,
        inspector_worker: object | None = None,
        task_runner: TaskRunner | None = None,
        defaults_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("workbenchView")
        self._task_registry = task_registry or TaskRegistry(
            Path.home() / ".autolabeler" / "tasks"
        )
        self._defaults_path = defaults_path or DEFAULT_TOOL_DEFAULTS_PATH
        self._tool_defaults = load_tool_defaults(self._defaults_path)
        self._sample_worker = sample_worker
        self._train_worker = train_worker
        self._infer_worker = infer_worker
        self._restore_worker = restore_worker
        self._convert_worker = convert_worker
        self._scan_worker = scan_worker
        self._labelimg_worker = labelimg_worker
        self._inspector_worker = inspector_worker
        self._task_runner = task_runner or AsyncTaskRunner(self)
        self.nav_buttons: dict[str, QPushButton] = {}
        self.nav_flow_buttons: list[QPushButton] = []
        self.home_module_buttons: list[QPushButton] = []
        self._current_key = "home"
        self._task_center_filter: str | None = None
        self._task_center_timer = QTimer(self)
        self._task_center_timer.setInterval(1000)
        self._task_center_timer.timeout.connect(self.refresh_task_center)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._content_stack = QStackedWidget()
        self._home_page = self._build_home_page()
        self.home_page = self._home_page
        self._manual_page = self._build_manual_page()
        self.manual_page = self._manual_page
        self._settings_page = self._build_settings_page()
        self.settings_page = self._settings_page
        self._task_center_page = self._build_task_center_page()
        self.sample_page = SamplePage(
            worker=self._sample_worker,
            registry=self._task_registry,
            task_runner=self._task_runner,
            defaults=self._tool_defaults,
        )
        self.train_page = TrainPage(
            worker=self._train_worker,
            registry=self._task_registry,
            task_runner=self._task_runner,
            defaults=self._tool_defaults,
        )
        self.infer_page = InferPage(
            worker=self._infer_worker,
            registry=self._task_registry,
            task_runner=self._task_runner,
            defaults=self._tool_defaults,
        )
        self.restore_page = RestorePage(
            worker=self._restore_worker,
            registry=self._task_registry,
            task_runner=self._task_runner,
            defaults=self._tool_defaults,
        )
        self.convert_page = ConvertPage(
            worker=self._convert_worker,
            registry=self._task_registry,
            task_runner=self._task_runner,
            defaults=self._tool_defaults,
        )
        self.scan_page = ScanPage(
            worker=self._scan_worker,
            registry=self._task_registry,
            task_runner=self._task_runner,
        )
        self.label_page = LabelImgPage(
            default_mode="label",
            labelimg_worker=self._labelimg_worker,
            inspector_worker=self._inspector_worker,
            registry=self._task_registry,
            task_runner=self._task_runner,
        )
        self.review_page = LabelImgPage(
            default_mode="review",
            labelimg_worker=self._labelimg_worker,
            inspector_worker=self._inspector_worker,
            registry=self._task_registry,
            task_runner=self._task_runner,
        )
        self._content_stack.addWidget(self._home_page)
        self._content_stack.addWidget(self._manual_page)
        self._content_stack.addWidget(self._settings_page)
        self._content_stack.addWidget(self._task_center_page)
        self._content_stack.addWidget(self.sample_page)
        self._content_stack.addWidget(self.train_page)
        self._content_stack.addWidget(self.infer_page)
        self._content_stack.addWidget(self.restore_page)
        self._content_stack.addWidget(self.convert_page)
        self._content_stack.addWidget(self.scan_page)
        self._content_stack.addWidget(self.label_page)
        self._content_stack.addWidget(self.review_page)

        root.addWidget(self._build_nav(), 0)
        root.addWidget(self._content_stack, 1)

    def current_module_key(self) -> str:
        """Return the selected module key, or home."""
        return self._current_key

    def show_home(self) -> None:
        """Show the homepage."""
        self._current_key = "home"
        self._task_center_timer.stop()
        self._sync_responsive_home()
        self._content_stack.setCurrentWidget(self._home_page)
        self._sync_nav()

    def show_task_center(self) -> None:
        """Show the lightweight task center."""
        self._current_key = "tasks"
        self._task_center_filter = None
        self.refresh_task_center()
        self._content_stack.setCurrentWidget(self._task_center_page)
        self._sync_nav()
        self._sync_task_center_timer()

    def show_manual(self) -> None:
        """Show the compact usage manual."""
        self._current_key = "manual"
        self._task_center_timer.stop()
        self._content_stack.setCurrentWidget(self._manual_page)
        self._sync_nav()

    def show_settings(self) -> None:
        """Show the lightweight settings page."""
        self._current_key = "settings"
        self._task_center_timer.stop()
        self._content_stack.setCurrentWidget(self._settings_page)
        self._sync_nav()

    def show_module(self, key: str) -> None:
        """Show a module page by key."""
        module = _module_by_key(key)
        self._current_key = module.key
        self._task_center_timer.stop()
        if module.key == "sample":
            self._content_stack.setCurrentWidget(self.sample_page)
            self._sync_nav()
            return
        if module.key == "train":
            self._content_stack.setCurrentWidget(self.train_page)
            self._sync_nav()
            return
        if module.key == "infer":
            self._content_stack.setCurrentWidget(self.infer_page)
            self._sync_nav()
            return
        if module.key == "restore":
            self._content_stack.setCurrentWidget(self.restore_page)
            self._sync_nav()
            return
        if module.key == "convert":
            self._content_stack.setCurrentWidget(self.convert_page)
            self._sync_nav()
            return
        if module.key == "scan":
            self._content_stack.setCurrentWidget(self.scan_page)
            self._sync_nav()
            return
        if module.key == "label":
            self._content_stack.setCurrentWidget(self.label_page)
            self._sync_nav()
            return
        if module.key == "review":
            self._content_stack.setCurrentWidget(self.review_page)
            self._sync_nav()
            return
        raise KeyError(f"Unknown module key: {module.key}")

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Keep optional homepage content from squeezing the workflow grid."""
        super().resizeEvent(event)
        self._sync_responsive_home()

    def _sync_responsive_home(self) -> None:
        """Hide the preview-only AI rail when the desktop window is narrow."""
        if not hasattr(self, "home_ai_preview"):
            return
        show_preview = self.width() >= _HOME_AI_PREVIEW_MIN_WIDTH
        self.home_ai_preview.setVisible(show_preview)

    def _build_nav(self) -> QWidget:
        nav = QFrame()
        nav.setObjectName("sideNav")
        layout = QVBoxLayout(nav)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setSpacing(7)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        mark = QLabel("AL")
        mark.setObjectName("navMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand = QLabel("AutoLabeler\n半自动图像标注工作台")
        brand.setObjectName("navBrand")
        brand_row.addWidget(mark, 0)
        brand_row.addWidget(brand, 1)
        layout.addLayout(brand_row)
        layout.addSpacing(14)

        home_button = _nav_utility_button("首页", "首", "工作台概览")
        home_button.clicked.connect(self.show_home)
        self.nav_buttons["home"] = home_button
        layout.addWidget(home_button)

        task_button = _nav_utility_button("任务中心", "任", "运行状态和历史")
        task_button.clicked.connect(self.show_task_center)
        self.nav_buttons["tasks"] = task_button
        layout.addWidget(task_button)

        section = QLabel("主流程")
        section.setObjectName("navSection")
        layout.addWidget(section)

        for index, module in enumerate(MODULES, start=1):
            button = _nav_flow_button(index, module)
            button.clicked.connect(lambda checked=False, key=module.key: self.show_module(key))
            self.nav_buttons[module.key] = button
            self.nav_flow_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch(1)
        manual = _nav_utility_button("使用手册", "册", "参数流程参考")
        manual.clicked.connect(self.show_manual)
        self.nav_buttons["manual"] = manual
        settings = _nav_utility_button("设置", "设", "工具默认参数")
        settings.clicked.connect(self.show_settings)
        self.nav_buttons["settings"] = settings
        layout.addWidget(manual)
        layout.addWidget(settings)
        self._sync_nav()
        return nav

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("homePage")
        layout = QGridLayout(page)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)
        layout.setRowStretch(0, 24)
        layout.setRowStretch(1, 45)
        layout.setRowStretch(2, 25)

        hero = QFrame()
        hero.setObjectName("homeHero")
        hero.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.home_hero = hero
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(26, 22, 26, 20)
        hero_layout.setSpacing(10)

        eyebrow = QLabel("AutoLabeler Workbench")
        eyebrow.setObjectName("homeEyebrow")
        title = QLabel("从少量标注到批量预测复核")
        title.setObjectName("homeTitle")
        title.setWordWrap(True)
        copy = QLabel(
            "扫描、抽样、标注、训练、推理、复核和写回都在一个桌面工作台里，"
            "入口清楚，也能独立使用。"
        )
        copy.setObjectName("mutedText")
        copy.setWordWrap(True)
        hero_layout.addWidget(eyebrow, 0)
        hero_layout.addWidget(title, 0)
        hero_layout.addWidget(copy, 1)

        hero_actions = QHBoxLayout()
        hero_actions.setSpacing(8)
        flow_button = QPushButton("开始 Flow 流程")
        flow_button.setObjectName("primaryButton")
        flow_button.clicked.connect(lambda checked=False: self.show_module("scan"))
        manual_button = QPushButton("使用手册")
        manual_button.setObjectName("secondaryButton")
        manual_button.clicked.connect(self.show_manual)
        self.home_manual_button = manual_button
        hero_actions.addWidget(flow_button, 0)
        hero_actions.addWidget(manual_button, 0)
        hero_actions.addStretch(1)
        hero_layout.addLayout(hero_actions, 0)
        layout.addWidget(hero, 0, 0)

        module_panel = QFrame()
        module_panel.setObjectName("homeModulePanel")
        module_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.home_module_panel = module_panel
        module_grid = QGridLayout(module_panel)
        module_grid.setContentsMargins(0, 0, 0, 0)
        module_grid.setHorizontalSpacing(9)
        module_grid.setVerticalSpacing(9)
        for column in range(4):
            module_grid.setColumnStretch(column, 1)
        for row in range(2):
            module_grid.setRowStretch(row, 1)
        self.home_module_descriptions: list[QLabel] = []
        for index, module in enumerate(MODULES):
            card = QPushButton()
            card.setObjectName("moduleCardButton")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setMinimumHeight(108)
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
            card.clicked.connect(
                lambda checked=False, key=module.key: self.show_module(key)
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 12, 10, 12)
            card_layout.setSpacing(7)
            card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_label = QLabel(f"{index + 1:02d} {module.title}")
            title_label.setObjectName("moduleTitleText")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            description = QLabel(_home_tile_copy(module.key))
            description.setObjectName("moduleDescription")
            description.setWordWrap(True)
            description.setAlignment(Qt.AlignmentFlag.AlignCenter)
            description.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.home_module_buttons.append(card)
            self.home_module_descriptions.append(description)
            card_layout.addStretch(1)
            card_layout.addWidget(title_label, 0)
            card_layout.addWidget(description, 0)
            card_layout.addStretch(1)
            module_grid.addWidget(card, index // 4, index % 4)
        layout.addWidget(module_panel, 1, 0)

        ai_preview = QFrame()
        ai_preview.setObjectName("aiPreview")
        ai_preview.setMinimumWidth(260)
        ai_preview.setMaximumWidth(318)
        self.home_ai_preview = ai_preview
        ai_layout = QVBoxLayout(ai_preview)
        ai_layout.setContentsMargins(15, 14, 15, 14)
        ai_layout.setSpacing(10)
        ai_head = QHBoxLayout()
        ai_title = QLabel("AI 操作助手")
        ai_title.setObjectName("aiTitle")
        ai_status = QLabel("PREVIEW")
        ai_status.setObjectName("aiStatus")
        self.home_ai_status = ai_status
        ai_head.addWidget(ai_title)
        ai_head.addStretch(1)
        ai_head.addWidget(ai_status)
        ai_layout.addLayout(ai_head)
        ai_kicker = QLabel("用一句话把任务交给工作台")
        ai_kicker.setObjectName("smallTitle")
        ai_layout.addWidget(ai_kicker)
        ai_copy = QLabel("先跳到正确模块并预填路径和参数，真正执行前仍由用户确认。")
        ai_copy.setObjectName("mutedText")
        ai_copy.setWordWrap(True)
        ai_layout.addWidget(ai_copy)
        chips = QHBoxLayout()
        chips.setSpacing(6)
        for text in ("抽样", "推理", "复核", "还原"):
            chip = QLabel(text)
            chip.setObjectName("aiChip")
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chips.addWidget(chip)
        chips.addStretch(1)
        ai_layout.addLayout(chips)
        thread = QFrame()
        thread.setObjectName("aiThread")
        thread_layout = QVBoxLayout(thread)
        thread_layout.setContentsMargins(0, 2, 0, 2)
        thread_layout.setSpacing(8)
        for object_name, text in (
            ("aiBubbleUser", "抽样 A9950，比例 20%"),
            ("aiBubbleBot", "可预填来源、比例和输出目录。执行前仍需确认。"),
            ("aiBubbleUser", "推理 images，模型 best.pt"),
            ("aiBubbleBot", "只准备参数；覆盖、写回或移动前仍先预检。"),
        ):
            bubble = QLabel(text)
            bubble.setObjectName(object_name)
            bubble.setWordWrap(True)
            thread_layout.addWidget(bubble)
        thread_layout.addStretch(1)
        ai_layout.addWidget(thread, 1)
        input_frame = QFrame()
        input_frame.setObjectName("aiInput")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(9, 8, 8, 8)
        input_layout.setSpacing(8)
        input_hint = QLabel("预览功能暂不可输入")
        input_hint.setObjectName("aiInputHint")
        input_hint.setWordWrap(True)
        send_button = QPushButton("预览中")
        send_button.setObjectName("aiSendButton")
        send_button.setEnabled(False)
        self.home_ai_send_button = send_button
        input_layout.addWidget(input_hint, 1)
        input_layout.addWidget(send_button, 0)
        ai_layout.addWidget(input_frame, 0)
        layout.addWidget(ai_preview, 0, 1, 2, 1)

        support = QFrame()
        support.setObjectName("homeSupportPanel")
        self.home_support_panel = support
        support_layout = QVBoxLayout(support)
        support_layout.setContentsMargins(16, 10, 16, 8)
        support_layout.setSpacing(8)
        support_header = QHBoxLayout()
        support_title = QLabel("系统优势")
        support_title.setObjectName("homeSectionTitle")
        support_core = QLabel("CORE")
        support_core.setObjectName("supportCore")
        support_header.addWidget(support_title)
        support_header.addStretch(1)
        support_header.addWidget(support_core)
        support_layout.addLayout(support_header)
        self.home_strength_band = QFrame()
        self.home_strength_band.setObjectName("homeStrengthBand")
        strength_band_layout = QHBoxLayout(self.home_strength_band)
        strength_band_layout.setContentsMargins(10, 8, 10, 8)
        strength_band_layout.setSpacing(0)
        self.home_strength_titles: list[QLabel] = []
        self.home_strength_items: list[QFrame] = []
        strengths = (
            (
                "01",
                "可追溯",
                "mapping 串起来源、预测、复核和写回。",
            ),
            (
                "02",
                "省人工",
                "先标代表样本，再批量预测剩余图片。",
            ),
            (
                "03",
                "防误操作",
                "移动、覆盖、写回前先预检和确认。",
            ),
            (
                "04",
                "可独立运行",
                "每个工具都说明自己的输入和输出。",
            ),
        )
        for index, (badge_text, title_text, body_text) in enumerate(strengths):
            item = QFrame()
            item.setObjectName("strengthItem")
            item_layout = QVBoxLayout(item)
            item_layout.setContentsMargins(12, 8, 12, 8)
            item_layout.setSpacing(5)
            item_header = QHBoxLayout()
            item_header.setContentsMargins(0, 0, 0, 0)
            item_header.setSpacing(8)
            badge = QLabel(badge_text)
            badge.setObjectName("strengthBadge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_label = QLabel(title_text)
            title_label.setObjectName("strengthTitle")
            body_label = QLabel(body_text)
            body_label.setObjectName("strengthBody")
            body_label.setWordWrap(True)
            self.home_strength_titles.append(title_label)
            self.home_strength_items.append(item)
            item_header.addWidget(badge, 0)
            item_header.addWidget(title_label, 1)
            item_layout.addLayout(item_header, 0)
            item_layout.addWidget(body_label, 1)
            strength_band_layout.addWidget(item, 1)
            if index < len(strengths) - 1:
                divider = QFrame()
                divider.setObjectName("strengthDivider")
                divider.setFrameShape(QFrame.Shape.VLine)
                strength_band_layout.addWidget(divider, 0)
        support_layout.addWidget(self.home_strength_band, 1)
        self.home_developer_label = QLabel("开发者：rui")
        self.home_developer_label.setObjectName("developerLabel")
        self.home_developer_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        support_layout.addWidget(self.home_developer_label, 0)
        layout.addWidget(support, 2, 0, 1, 2)

        return page

    def _build_manual_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("manualPage")
        root = QHBoxLayout(page)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(16)

        self.manual_main_panel = QFrame()
        self.manual_main_panel.setObjectName("leftMainPanel")
        left = QVBoxLayout(self.manual_main_panel)
        left.setContentsMargins(24, 22, 24, 22)
        left.setSpacing(14)

        eyebrow = QLabel("Help")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("使用手册")
        title.setObjectName("toolTitle")
        subtitle = QLabel("按章节查流程、参数和输出位置")
        subtitle.setObjectName("smallTitle")

        self.manual_content_scroll = QScrollArea()
        self.manual_content_scroll.setObjectName("manualContentScroll")
        self.manual_content_scroll.setWidgetResizable(True)
        self.manual_content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.manual_content_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        manual_content = QWidget()
        manual_content.setObjectName("manualContent")
        content_layout = QVBoxLayout(manual_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        self.manual_overview_section = self._build_manual_section(
            "00 完整流程",
            "按业务顺序进入各功能。需要追溯原图时走 Flow；只处理散图时使用独立模式或转换工具。",
        )

        self.manual_function_sections: dict[str, QFrame] = {}
        for index, spec in enumerate(_MANUAL_FUNCTION_SPECS, start=1):
            section = self._build_manual_detail_section(index, spec)
            self.manual_function_sections[spec.key] = section
            setattr(self, f"manual_{spec.key}_section", section)

        self.manual_steps_panel = QFrame()
        self.manual_steps_panel.setObjectName("manualStepsPanel")
        steps_layout = QGridLayout(self.manual_steps_panel)
        steps_layout.setContentsMargins(12, 12, 12, 12)
        steps_layout.setHorizontalSpacing(10)
        steps_layout.setVerticalSpacing(10)
        for index, (spec, workflow_item) in enumerate(
            zip(_MANUAL_FUNCTION_SPECS, _MANUAL_WORKFLOW_ITEMS, strict=True)
        ):
            title_text, body_text = workflow_item
            button = QPushButton(f"{index + 1:02d} {title_text}\n{body_text}")
            button.setObjectName("manualStepButton")
            button.clicked.connect(
                lambda checked=False, key=spec.key: self.manual_content_scroll.ensureWidgetVisible(
                    self.manual_function_sections[key]
                )
            )
            steps_layout.addWidget(button, index // 4, index % 4)

        self.manual_overview_section.layout().addWidget(self.manual_steps_panel)
        self.manual_overview_section.layout().addWidget(
            self._manual_note(
                "流程产出",
                "扫描产出 mapping.json/classes.txt；抽样产出 YOLO 数据集；标注补齐 labels；训练产出 best.pt/last.pt；推理产出 run/labels；复核修改预测标签；还原写回 VOC XML；转换用于 XML 与 YOLO 数据集互转。",
            )
        )

        manual_sections = [self.manual_overview_section]
        manual_sections.extend(
            self.manual_function_sections[spec.key]
            for spec in _MANUAL_FUNCTION_SPECS
        )
        for section in manual_sections:
            content_layout.addWidget(section)
        content_layout.addStretch(1)
        self.manual_content_scroll.setWidget(manual_content)

        back = QPushButton("返回首页")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.show_home)

        left.addWidget(eyebrow)
        left.addWidget(title)
        left.addWidget(subtitle)
        left.addWidget(self.manual_content_scroll, 1)
        left.addWidget(back, 0)

        self.manual_support_panel = QFrame()
        self.manual_support_panel.setObjectName("rightSupportPanel")
        self.manual_support_panel.setMinimumWidth(176)
        self.manual_support_panel.setMaximumWidth(210)
        right = QVBoxLayout(self.manual_support_panel)
        right.setContentsMargins(14, 16, 14, 16)
        right.setSpacing(8)

        panel_title = QLabel("本页目录")
        panel_title.setObjectName("panelTitle")
        panel_copy = QLabel("选择章节后在左侧正文查看。")
        panel_copy.setObjectName("mutedText")
        panel_copy.setWordWrap(True)
        self.manual_quick_nav_panel = QFrame()
        self.manual_quick_nav_panel.setObjectName("manualQuickNavPanel")
        nav_layout = QVBoxLayout(self.manual_quick_nav_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(4)
        nav_items = [("00 完整流程", self.manual_overview_section)]
        nav_items.extend(
            (
                f"{index:02d} {spec.title}",
                self.manual_function_sections[spec.key],
            )
            for index, spec in enumerate(_MANUAL_FUNCTION_SPECS, start=1)
        )
        for text, target in nav_items:
            button = QPushButton(text)
            button.setObjectName("manualNavButton")
            button.clicked.connect(
                lambda checked=False, widget=target: self.manual_content_scroll.ensureWidgetVisible(
                    widget
                )
            )
            nav_layout.addWidget(button)

        right.addWidget(panel_title)
        right.addWidget(panel_copy)
        right.addWidget(self.manual_quick_nav_panel)
        right.addStretch(1)

        root.addWidget(self.manual_main_panel, 1)
        root.addWidget(self.manual_support_panel, 0)
        return page

    def _build_manual_detail_section(
        self, section_number: int, spec: ManualSectionSpec
    ) -> QFrame:
        section = self._build_manual_section(
            f"{section_number:02d} {spec.title}",
            spec.copy,
        )
        section.layout().addWidget(self._manual_param_table(spec.rows))
        if spec.note_title and spec.note_body:
            section.layout().addWidget(
                self._manual_note(spec.note_title, spec.note_body)
            )
        return section

    def _build_manual_section(self, title: str, copy: str) -> QFrame:
        section = QFrame()
        section.setObjectName("manualSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("manualSectionTitle")
        copy_label = QLabel(copy)
        copy_label.setObjectName("mutedText")
        copy_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(copy_label)
        return section

    def _manual_param_table(self, rows: tuple[tuple[str, str, str, str], ...]) -> QFrame:
        table = QFrame()
        table.setObjectName("manualParamTable")
        layout = QGridLayout(table)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        for column, text in enumerate(("参数", "建议", "含义", "何时调整")):
            header = QLabel(text)
            header.setObjectName("manualTableHeader")
            layout.addWidget(header, 0, column)
        for row_index, row in enumerate(rows, start=1):
            for column, text in enumerate(row):
                label = QLabel(text)
                label.setObjectName("manualTableCell")
                label.setWordWrap(True)
                label.setMinimumWidth(0)
                label.setSizePolicy(
                    QSizePolicy.Policy.Ignored,
                    QSizePolicy.Policy.Preferred,
                )
                layout.addWidget(label, row_index, column)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 3)
        layout.setColumnStretch(3, 3)
        return table

    def _manual_note(self, title: str, body: str) -> QFrame:
        note = QFrame()
        note.setObjectName("manualNote")
        layout = QVBoxLayout(note)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("smallTitle")
        body_label = QLabel(body)
        body_label.setObjectName("mutedText")
        body_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(body_label)
        return note

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("settingsPage")
        root = QHBoxLayout(page)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(16)

        self.settings_main_panel = QFrame()
        self.settings_main_panel.setObjectName("leftMainPanel")
        left = QVBoxLayout(self.settings_main_panel)
        left.setContentsMargins(24, 22, 24, 22)
        left.setSpacing(14)

        eyebrow = QLabel("System")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("设置")
        title.setObjectName("toolTitle")
        subtitle = QLabel("工具参数默认值")
        subtitle.setObjectName("smallTitle")
        copy = QLabel(
            "这里只保存低风险参数默认值。路径、固定 run 名、覆盖开关和写回确认仍在每次任务中手动选择。"
        )
        copy.setObjectName("mutedText")
        copy.setWordWrap(True)

        settings_form = QWidget()
        settings_form.setObjectName("settingsDefaultsForm")
        form_layout = QVBoxLayout(settings_form)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(12)

        self.settings_sample_strategy_input = _settings_combo(
            ("mixed", "count", "ratio"),
            default_text(self._tool_defaults, "sample", "mode", "mixed"),
        )
        self.settings_sample_count_input = _settings_line(
            default_text(self._tool_defaults, "sample", "count", "40")
        )
        self.settings_sample_ratio_input = _settings_line(
            default_text(self._tool_defaults, "sample", "ratio", "0.3")
        )
        self.settings_sample_min_count_input = _settings_line(
            default_text(self._tool_defaults, "sample", "min_count", "20")
        )
        self.settings_sample_max_count_input = _settings_line(
            default_text(self._tool_defaults, "sample", "max_count", "50")
        )
        self.settings_sample_full_threshold_input = _settings_line(
            default_text(self._tool_defaults, "sample", "full_threshold", "35")
        )
        self.settings_sample_train_ratio_input = _settings_line(
            default_text(self._tool_defaults, "sample", "train_ratio", "0.9")
        )
        self.settings_sample_section = _settings_section(
            "01 抽样",
            (
                ("默认策略", self.settings_sample_strategy_input, "mixed 适合正式数据，count/ratio 用于固定实验。"),
                ("count", self.settings_sample_count_input, "count 策略每组抽取数量。"),
                ("ratio", self.settings_sample_ratio_input, "ratio/mixed 策略每组抽取比例。"),
                ("min count", self.settings_sample_min_count_input, "mixed 策略大组最低抽样数量。"),
                ("max count", self.settings_sample_max_count_input, "mixed 策略大组最高抽样数量。"),
                ("全量阈值", self.settings_sample_full_threshold_input, "mixed 策略小组全量进入样本的阈值。"),
                ("训练比例", self.settings_sample_train_ratio_input, "抽中样本切分 train/val 的比例。"),
            ),
        )
        form_layout.addWidget(self.settings_sample_section)

        self.settings_train_device_input = _settings_combo(
            _train_device_option_labels(),
            _train_device_label_for_value(
                default_text(self._tool_defaults, "train", "device", "auto")
            ),
        )
        self.settings_train_epochs_input = _settings_line(
            default_text(self._tool_defaults, "train", "epochs", "2")
        )
        self.settings_train_image_size_input = _settings_line(
            default_text(self._tool_defaults, "train", "image_size", "640")
        )
        self.settings_train_batch_input = _settings_line(
            default_text(self._tool_defaults, "train", "batch_size", "-1")
        )
        self.settings_train_patience_input = _settings_line(
            default_text(self._tool_defaults, "train", "patience", "50")
        )
        self.settings_train_workers_input = _settings_line(
            default_text(self._tool_defaults, "train", "workers", "8")
        )
        self.settings_train_optimizer_input = _settings_combo(
            ("AdamW", "SGD", "Adam", "auto"),
            default_text(self._tool_defaults, "train", "optimizer", "AdamW"),
        )
        self.settings_train_lr0_input = _settings_line(
            default_text(self._tool_defaults, "train", "lr0", "0.01")
        )
        self.settings_train_box_input = _settings_line(
            default_text(self._tool_defaults, "train", "box", "7.5")
        )
        self.settings_train_cls_input = _settings_line(
            default_text(self._tool_defaults, "train", "cls", "0.5")
        )
        self.settings_train_dfl_input = _settings_line(
            default_text(self._tool_defaults, "train", "dfl", "1.5")
        )
        self.settings_train_scale_input = _settings_line(
            default_text(self._tool_defaults, "train", "scale", "0.5")
        )
        self.settings_train_cache_input = _settings_combo(
            ("ram", "disk", "false", "true"),
            default_text(self._tool_defaults, "train", "cache", "ram"),
        )
        self.settings_train_section = _settings_section(
            "02 训练",
            (
                ("device", self.settings_train_device_input, "auto 自动选择；All GPUs 使用可见 CUDA；GPU 0/1 固定单卡，GPU 0+1 使用双卡。"),
                ("epochs", self.settings_train_epochs_input, "训练轮数，正式训练通常高于冒烟测试。"),
                ("image size", self.settings_train_image_size_input, "输入尺寸，越大越慢且更占显存。"),
                ("batch", self.settings_train_batch_input, "-1 表示自动；多卡时填写所有卡合计的总 batch。"),
                ("patience", self.settings_train_patience_input, "早停等待轮数。"),
                ("workers", self.settings_train_workers_input, "每个训练进程的数据加载数，多卡总数会随卡数增加。"),
                ("optimizer", self.settings_train_optimizer_input, "优化器，AdamW 稳定，SGD 适合对比实验。"),
                ("lr0", self.settings_train_lr0_input, "初始学习率。"),
                ("box", self.settings_train_box_input, "框定位损失权重。"),
                ("cls", self.settings_train_cls_input, "类别损失权重。"),
                ("dfl", self.settings_train_dfl_input, "边框分布损失权重。"),
                ("scale", self.settings_train_scale_input, "缩放增强幅度。"),
                ("cache", self.settings_train_cache_input, "ram 快但占内存，disk 占磁盘。"),
            ),
        )
        form_layout.addWidget(self.settings_train_section)

        self.settings_infer_confidence_input = _settings_line(
            default_text(self._tool_defaults, "infer", "confidence", "0.25")
        )
        self.settings_infer_iou_input = _settings_line(
            default_text(self._tool_defaults, "infer", "iou", "0.7")
        )
        self.settings_infer_batch_input = _settings_line(
            default_text(self._tool_defaults, "infer", "batch_size", "-1")
        )
        self.settings_infer_label_y_offset_input = _settings_line(
            default_text(self._tool_defaults, "infer", "label_y_offset_px", "0")
        )
        self.settings_infer_device_input = _settings_combo(
            ("auto", "cpu", "gpu"),
            default_text(self._tool_defaults, "infer", "device", "auto"),
        )
        self.settings_infer_section = _settings_section(
            "03 推理",
            (
                ("confidence", self.settings_infer_confidence_input, "置信度阈值，越低检出越多。"),
                ("IoU", self.settings_infer_iou_input, "NMS 去重阈值，控制重叠框保留。"),
                ("batch", self.settings_infer_batch_input, "每批推理图片数。"),
                ("label Y offset", self.settings_infer_label_y_offset_input, "保存标签时整体下移的像素数，0 表示不修正。"),
                ("device", self.settings_infer_device_input, "auto/cpu/gpu。"),
            ),
        )
        form_layout.addWidget(self.settings_infer_section)

        self.settings_convert_train_ratio_input = _settings_line(
            default_text(self._tool_defaults, "convert", "train_ratio", "0.9")
        )
        self.settings_convert_section = _settings_section(
            "04 转换",
            (
                ("转换训练比例", self.settings_convert_train_ratio_input, "XML 转 YOLO 数据集时切分 train/val。"),
            ),
        )
        form_layout.addWidget(self.settings_convert_section)

        self.settings_status_panel = QFrame()
        self.settings_status_panel.setObjectName("settingsStatusPanel")
        status_layout = QVBoxLayout(self.settings_status_panel)
        status_layout.setContentsMargins(12, 10, 12, 10)
        status_layout.setSpacing(7)
        status_title = QLabel("05 保存边界")
        status_title.setObjectName("smallTitle")
        status_layout.addWidget(status_title)
        for index, (title_text, body_text) in enumerate(
            (
                ("保存位置", str(self._defaults_path)),
                ("路径不保存", "输入、输出、classes.txt 每次手动选择。"),
                ("风险项不保存", "覆盖、固定 run 名和写回确认只在工具页本次生效。"),
                ("即时生效", "保存后应用到当前工具页的低风险参数。"),
            )
        ):
            item = QFrame()
            item.setObjectName("settingsStatusItem")
            item_layout = QVBoxLayout(item)
            item_layout.setContentsMargins(8, 6, 8, 6)
            item_layout.setSpacing(2)
            item_title = QLabel(title_text)
            item_title.setObjectName("smallTitle")
            item_body = QLabel(body_text)
            item_body.setObjectName("mutedText")
            item_body.setWordWrap(True)
            if index == 0:
                self.settings_defaults_path = item_body
                self.settings_defaults_path.setToolTip(str(self._defaults_path))
            item_layout.addWidget(item_title)
            item_layout.addWidget(item_body)
            status_layout.addWidget(item)
        form_layout.addWidget(self.settings_status_panel)
        form_layout.addStretch(1)

        self.settings_content_scroll = QScrollArea()
        self.settings_content_scroll.setObjectName("settingsContentScroll")
        self.settings_content_scroll.setWidgetResizable(True)
        self.settings_content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_content_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.settings_content_scroll.setWidget(settings_form)

        action_row = QHBoxLayout()
        self.settings_result_summary = QLabel("修改参数后点击保存。")
        self.settings_result_summary.setObjectName("formPlaceholder")
        self.settings_result_summary.setProperty("feedbackRole", "result")
        self.settings_result_summary.setWordWrap(True)
        self.settings_save_button = QPushButton("保存默认值")
        self.settings_save_button.setObjectName("primaryButton")
        self.settings_save_button.clicked.connect(self.save_tool_default_settings)
        back = QPushButton("返回首页")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.show_home)
        action_row.addWidget(self.settings_result_summary, 1)
        action_row.addWidget(back, 0)
        action_row.addWidget(self.settings_save_button, 0)

        left.addWidget(eyebrow)
        left.addWidget(title)
        left.addWidget(subtitle)
        left.addWidget(copy)
        left.addWidget(self.settings_content_scroll, 1)
        left.addLayout(action_row)

        self.settings_support_panel = QFrame()
        self.settings_support_panel.setObjectName("rightSupportPanel")
        self.settings_support_panel.setMinimumWidth(176)
        self.settings_support_panel.setMaximumWidth(210)
        right = QVBoxLayout(self.settings_support_panel)
        right.setContentsMargins(14, 16, 14, 16)
        right.setSpacing(8)

        panel_title = QLabel("本页目录")
        panel_title.setObjectName("panelTitle")
        panel_copy = QLabel("选择章节后在左侧修改安全默认值。")
        panel_copy.setObjectName("mutedText")
        panel_copy.setWordWrap(True)
        self.settings_quick_nav_panel = QFrame()
        self.settings_quick_nav_panel.setObjectName("settingsQuickNavPanel")
        nav_layout = QVBoxLayout(self.settings_quick_nav_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(4)
        for text, target in (
            ("01 抽样", self.settings_sample_section),
            ("02 训练", self.settings_train_section),
            ("03 推理", self.settings_infer_section),
            ("04 转换", self.settings_convert_section),
            ("05 保存边界", self.settings_status_panel),
        ):
            button = QPushButton(text)
            button.setObjectName("manualNavButton")
            button.clicked.connect(
                lambda checked=False, widget=target: self.settings_content_scroll.ensureWidgetVisible(
                    widget
                )
            )
            nav_layout.addWidget(button)

        right.addWidget(panel_title)
        right.addWidget(panel_copy)
        right.addWidget(self.settings_quick_nav_panel)
        right.addStretch(1)

        root.addWidget(self.settings_main_panel, 1)
        root.addWidget(self.settings_support_panel, 0)
        return page

    def save_tool_default_settings(self) -> None:
        """Persist settings-page defaults and apply them to open tool pages."""
        validation_error = self._validate_tool_defaults_from_settings()
        if validation_error:
            self.settings_result_summary.setText(f"默认值未保存：{validation_error}")
            return
        self._tool_defaults = self._collect_tool_defaults_from_settings()
        try:
            saved_path = save_tool_defaults(self._tool_defaults, self._defaults_path)
        except OSError as exc:
            self.settings_result_summary.setText(f"默认值未保存：无法写入配置文件（{exc}）")
            return
        self.settings_defaults_path.setText(str(saved_path))
        self.settings_defaults_path.setToolTip(str(saved_path))
        self._apply_tool_defaults_to_pages()
        self.settings_result_summary.setText(f"默认值已保存：{saved_path}")

    def _validate_tool_defaults_from_settings(self) -> str | None:
        """Return a user-facing validation error, or None when settings are valid."""
        validators = (
            ("抽样 count", self.settings_sample_count_input, "int", 1, None, False),
            ("抽样 ratio", self.settings_sample_ratio_input, "float", 0, 1, False),
            ("抽样 min count", self.settings_sample_min_count_input, "int", 0, None, False),
            ("抽样 max count", self.settings_sample_max_count_input, "int", 1, None, False),
            ("抽样 全量阈值", self.settings_sample_full_threshold_input, "int", 0, None, False),
            ("抽样 训练比例", self.settings_sample_train_ratio_input, "float", 0, 1, False),
            ("训练 epochs", self.settings_train_epochs_input, "int", 1, None, False),
            ("训练 image size", self.settings_train_image_size_input, "int", 1, None, False),
            ("训练 batch", self.settings_train_batch_input, "int", 1, None, True),
            ("训练 patience", self.settings_train_patience_input, "int", 0, None, False),
            ("训练 workers", self.settings_train_workers_input, "int", 0, None, False),
            ("训练 lr0", self.settings_train_lr0_input, "float", 0, None, False),
            ("训练 box", self.settings_train_box_input, "float", 0, None, False),
            ("训练 cls", self.settings_train_cls_input, "float", 0, None, False),
            ("训练 dfl", self.settings_train_dfl_input, "float", 0, None, False),
            ("训练 scale", self.settings_train_scale_input, "float", 0, None, False),
            ("推理 confidence", self.settings_infer_confidence_input, "float", 0, 1, False),
            ("推理 IoU", self.settings_infer_iou_input, "float", 0, 1, False),
            ("推理 batch", self.settings_infer_batch_input, "int", 1, None, True),
            ("推理 label Y offset", self.settings_infer_label_y_offset_input, "float", -1000, 1000, False),
            ("转换训练比例", self.settings_convert_train_ratio_input, "float", 0, 1, False),
        )
        for label, field, value_type, minimum, maximum, allow_auto in validators:
            text = field.text().strip()
            if not text:
                return f"{label} 不能为空。"
            try:
                value = int(text) if value_type == "int" else float(text)
            except ValueError:
                return f"{label} 必须是数字。"
            if allow_auto and value == -1:
                continue
            if minimum is not None and value < minimum:
                return f"{label} 不能小于 {minimum}。"
            if maximum is not None and value > maximum:
                return f"{label} 不能大于 {maximum}。"
        return None

    def _collect_tool_defaults_from_settings(self) -> ToolDefaults:
        """Build persisted defaults from settings controls."""
        return ToolDefaults(
            sample={
                "mode": self.settings_sample_strategy_input.currentText(),
                "count": self.settings_sample_count_input.text().strip(),
                "ratio": self.settings_sample_ratio_input.text().strip(),
                "min_count": self.settings_sample_min_count_input.text().strip(),
                "max_count": self.settings_sample_max_count_input.text().strip(),
                "full_threshold": self.settings_sample_full_threshold_input.text().strip(),
                "train_ratio": self.settings_sample_train_ratio_input.text().strip(),
            },
            train={
                "device": _train_device_value_from_label(
                    self.settings_train_device_input.currentText()
                ),
                "epochs": self.settings_train_epochs_input.text().strip(),
                "image_size": self.settings_train_image_size_input.text().strip(),
                "batch_size": self.settings_train_batch_input.text().strip(),
                "patience": self.settings_train_patience_input.text().strip(),
                "workers": self.settings_train_workers_input.text().strip(),
                "optimizer": self.settings_train_optimizer_input.currentText(),
                "lr0": self.settings_train_lr0_input.text().strip(),
                "box": self.settings_train_box_input.text().strip(),
                "cls": self.settings_train_cls_input.text().strip(),
                "dfl": self.settings_train_dfl_input.text().strip(),
                "scale": self.settings_train_scale_input.text().strip(),
                "cache": self.settings_train_cache_input.currentText(),
            },
            infer={
                "confidence": self.settings_infer_confidence_input.text().strip(),
                "iou": self.settings_infer_iou_input.text().strip(),
                "batch_size": self.settings_infer_batch_input.text().strip(),
                "label_y_offset_px": self.settings_infer_label_y_offset_input.text().strip(),
                "device": self.settings_infer_device_input.currentText(),
            },
            convert={
                "train_ratio": self.settings_convert_train_ratio_input.text().strip(),
            },
        )

    def _apply_tool_defaults_to_pages(self) -> None:
        """Apply saved defaults to pages that expose defaultable parameters."""
        self.sample_page.apply_defaults(self._tool_defaults)
        self.train_page.apply_defaults(self._tool_defaults)
        self.infer_page.apply_defaults(self._tool_defaults)
        self.convert_page.apply_defaults(self._tool_defaults)
        self.restore_page.apply_defaults(self._tool_defaults)

    def _build_task_center_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("taskCenterPage")
        root = QHBoxLayout(page)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(16)

        panel = QFrame()
        panel.setObjectName("leftMainPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        eyebrow = QLabel("Global tasks")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("任务中心")
        title.setObjectName("toolTitle")
        subtitle = QLabel("查看运行中和最近任务")
        subtitle.setObjectName("smallTitle")
        copy = QLabel("显示自动化标注流程状态、最近产出和需要处理的问题。")
        copy.setObjectName("mutedText")
        copy.setWordWrap(True)
        self.task_center_summary_panel = QFrame()
        self.task_center_summary_panel.setObjectName("taskCenterSummaryPanel")
        self.task_center_summary_layout = QGridLayout(self.task_center_summary_panel)
        self.task_center_summary_layout.setContentsMargins(12, 12, 12, 12)
        self.task_center_summary_layout.setHorizontalSpacing(10)
        self.task_center_summary_layout.setVerticalSpacing(10)
        task_actions = QHBoxLayout()
        task_actions.setContentsMargins(0, 0, 0, 0)
        task_actions.setSpacing(10)
        self.refresh_tasks_button = QPushButton("刷新")
        self.refresh_tasks_button.setObjectName("secondaryButton")
        self.refresh_tasks_button.setMaximumWidth(88)
        self.refresh_tasks_button.clicked.connect(self.refresh_task_center)
        self.task_center_filter_back_button = QPushButton("返回任务中心主页")
        self.task_center_filter_back_button.setObjectName("secondaryButton")
        self.task_center_filter_back_button.clicked.connect(
            self._clear_task_center_filter
        )
        task_actions.addWidget(self.refresh_tasks_button, 0)
        task_actions.addWidget(self.task_center_filter_back_button, 0)
        task_actions.addStretch(1)
        self.task_center_list_panel = QFrame()
        self.task_center_list_panel.setObjectName("taskCenterList")
        self.task_center_list_layout = QVBoxLayout(self.task_center_list_panel)
        self.task_center_list_layout.setContentsMargins(0, 0, 0, 0)
        self.task_center_list_layout.setSpacing(8)
        self.task_center_scroll = QScrollArea()
        self.task_center_scroll.setObjectName("toolScrollArea")
        self.task_center_scroll.setWidgetResizable(True)
        self.task_center_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.task_center_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.task_center_scroll.setWidget(self.task_center_list_panel)

        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(copy)
        layout.addWidget(self.task_center_summary_panel, 0)
        layout.addLayout(task_actions)
        layout.addWidget(self.task_center_scroll, 1)
        root.addWidget(panel, 1)
        return page

    def refresh_task_center(self) -> None:
        """Refresh task center text from the shared task registry."""
        _clear_layout(self.task_center_list_layout)
        _clear_layout(self.task_center_summary_layout)
        if self._task_registry is None:
            self._populate_task_center_summary([])
            self.task_center_list_layout.addWidget(
                _task_empty_state("当前未配置共享任务记录。")
            )
            self._task_center_timer.stop()
            return
        self._task_registry.cleanup_finished_older_than(_TASK_CENTER_RETENTION_DAYS)
        tasks = self._task_registry.list_tasks()
        visible_tasks = _visible_task_center_tasks(tasks)
        self._populate_task_center_summary(visible_tasks)
        if not visible_tasks:
            self.task_center_filter_back_button.setVisible(False)
            self.task_center_list_layout.addWidget(_task_empty_state("保留期内暂无任务。"))
            self._task_center_timer.stop()
            return
        filtered_tasks = self._filtered_task_center_tasks(visible_tasks)
        self.task_center_filter_back_button.setVisible(
            self._task_center_filter is not None
        )
        if not filtered_tasks:
            self.task_center_list_layout.addWidget(
                _task_empty_state(self._task_center_empty_text())
            )
            self._sync_task_center_timer()
            return
        for group_title, group_tasks in _group_task_center_tasks(filtered_tasks):
            header = QLabel(group_title)
            header.setObjectName("taskDateHeader")
            self.task_center_list_layout.addWidget(header)
            for task in group_tasks:
                self.task_center_list_layout.addWidget(self._build_task_center_row(task))
        self.task_center_list_layout.addStretch(1)
        self._sync_task_center_timer()

    def _build_task_center_row(self, task: TaskHandle) -> QFrame:
        """Build one task-center row."""
        progress = f"{task.progress_current}/{task.progress_total}"
        row = QFrame()
        row.setObjectName("taskRow")
        row_layout = QGridLayout(row)
        row_layout.setContentsMargins(12, 10, 12, 10)
        row_layout.setHorizontalSpacing(10)
        row_layout.setVerticalSpacing(4)
        module_key = _module_key_for_task_type(task.task_type)
        module_title = _task_module_title(task)
        title_label = QLabel(
            f"{module_title} · {_TASK_STATUS_LABELS.get(task.status, task.status)}"
        )
        title_label.setObjectName("taskRowTitle")
        title_label.setMinimumWidth(0)
        title_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        meta = QLabel(
            f"{_task_time_label(task)} · 进度 {progress} · {task.progress_message or '等待'}"
        )
        meta.setObjectName("mutedText")
        meta.setWordWrap(True)
        meta.setMinimumWidth(0)
        meta.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        if task.error:
            detail_text = f"失败原因：{task.error.message}"
        else:
            detail_text = _format_task_summary(task)
        detail_label = QLabel(detail_text)
        detail_label.setObjectName("mutedText")
        detail_label.setWordWrap(True)
        detail_label.setMinimumWidth(0)
        detail_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        back_button = QPushButton(f"回到{module_title}")
        if module_key == "home":
            back_button.setText("回到首页")
        back_button.setObjectName("taskBackButton")
        back_button.setProperty("module_key", module_key)
        back_button.clicked.connect(
            lambda checked=False, key=module_key: self.show_module(key)
        )
        action_panel = QFrame()
        action_panel.setObjectName("taskRowActions")
        action_panel.setMinimumWidth(112)
        action_panel.setMaximumWidth(128)
        action_layout = QVBoxLayout(action_panel)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(6)
        action_layout.addWidget(back_button)
        if task.status in _TERMINAL_TASK_STATUSES:
            delete_button = QPushButton("删除记录")
            delete_button.setObjectName("taskDeleteButton")
            delete_button.setProperty("task_id", task.task_id)
            delete_button.clicked.connect(
                lambda checked=False, task_id=task.task_id: self._delete_task_record(
                    task_id
                )
            )
            action_layout.addWidget(delete_button)
        action_layout.addStretch(1)
        row_layout.addWidget(title_label, 0, 0)
        row_layout.addWidget(meta, 1, 0)
        row_layout.addWidget(detail_label, 2, 0)
        row_layout.addWidget(action_panel, 0, 1, 3, 1, Qt.AlignmentFlag.AlignTop)
        row_layout.setColumnStretch(0, 1)
        row_layout.setColumnStretch(1, 0)
        return row

    def _delete_task_record(self, task_id: str) -> None:
        """Delete one terminal task record and refresh the task center."""
        if self._task_registry is None:
            return
        if self._task_registry.delete_task(task_id):
            self.refresh_task_center()

    def _populate_task_center_summary(self, tasks: list[TaskHandle]) -> None:
        """Populate business-level task center summary metrics."""
        active_count = sum(task.status in _ACTIVE_TASK_STATUSES for task in tasks)
        recent_completed_count = sum(task.status == "succeeded" for task in tasks)
        attention_count = sum(task.status in _ATTENTION_TASK_STATUSES for task in tasks)
        items = (
            ("运行中", f"{active_count}", "当前正在推进的任务", "active"),
            ("保留期完成", f"{recent_completed_count}", "保留期内完成的自动化步骤", None),
            ("需要处理", f"{attention_count}", "失败、停止或中断任务", "attention"),
            ("保留策略", f"{_TASK_CENTER_RETENTION_DAYS}天", "更早的已结束记录自动清理", None),
        )
        for index, (label_text, value_text, helper_text, filter_key) in enumerate(items):
            item = QFrame()
            item.setObjectName("taskSummaryItem")
            item.setProperty(
                "selected",
                filter_key is not None and self._task_center_filter == filter_key,
            )
            item_layout = QGridLayout(item)
            item_layout.setContentsMargins(10, 8, 10, 8)
            item_layout.setSpacing(0)

            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(3)
            label = QLabel(label_text)
            label.setObjectName("taskSummaryLabel")
            value = QLabel(value_text)
            value.setObjectName("taskSummaryValue")
            value.setWordWrap(True)
            helper = QLabel(helper_text)
            helper.setObjectName("mutedText")
            helper.setWordWrap(True)
            content_layout.addWidget(label)
            content_layout.addWidget(value)
            content_layout.addWidget(helper)
            item_layout.addWidget(content, 0, 0)

            if filter_key is not None:
                button = QPushButton("")
                button.setObjectName("taskSummaryButton")
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setProperty("filter_key", filter_key)
                button.setAccessibleName(f"查看{label_text}任务")
                button.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
                button.clicked.connect(
                    lambda checked=False, key=filter_key: self._show_task_center_filter(
                        key
                    )
                )
                item_layout.addWidget(button, 0, 0)

            self.task_center_summary_layout.addWidget(item, 0, index)
            self.task_center_summary_layout.setColumnStretch(index, 1)

    def _show_task_center_filter(self, filter_key: str) -> None:
        """Show only the task-center rows matching one summary category."""
        self._task_center_filter = filter_key
        self.refresh_task_center()

    def _clear_task_center_filter(self) -> None:
        """Return from a filtered task-center view to the full task list."""
        self._task_center_filter = None
        self.refresh_task_center()

    def _filtered_task_center_tasks(
        self, tasks: list[TaskHandle]
    ) -> list[TaskHandle]:
        """Apply the active task-center filter to visible task records."""
        if self._task_center_filter == "active":
            return [task for task in tasks if task.status in _ACTIVE_TASK_STATUSES]
        if self._task_center_filter == "attention":
            return [task for task in tasks if task.status in _ATTENTION_TASK_STATUSES]
        return tasks

    def _task_center_empty_text(self) -> str:
        """Return the empty-state text for the active task-center filter."""
        if self._task_center_filter == "active":
            return "当前没有运行中的任务。"
        if self._task_center_filter == "attention":
            return "当前没有需要处理的任务。"
        return "保留期内暂无任务。"

    def _sync_task_center_timer(self) -> None:
        """Refresh task center automatically only while active tasks are visible."""
        if self._current_key != "tasks" or self._task_registry is None:
            self._task_center_timer.stop()
            return
        has_active_task = any(
            task.status in _ACTIVE_TASK_STATUSES
            for task in self._task_registry.list_tasks()
        )
        if has_active_task:
            self._task_center_timer.start()
            return
        self._task_center_timer.stop()

    def _sync_nav(self) -> None:
        for key, button in self.nav_buttons.items():
            selected = key == self._current_key
            button.setProperty("selected", selected)
            button.style().unpolish(button)
            button.style().polish(button)


class AutoLabelerWindow(QMainWindow):
    """Top-level AutoLabeler desktop window."""

    def __init__(
        self,
        task_registry: TaskRegistry | None = None,
        sample_worker: object | None = None,
        train_worker: object | None = None,
        infer_worker: object | None = None,
        restore_worker: object | None = None,
        convert_worker: object | None = None,
        scan_worker: object | None = None,
        labelimg_worker: object | None = None,
        inspector_worker: object | None = None,
        task_runner: TaskRunner | None = None,
        defaults_path: Path | None = None,
    ) -> None:
        super().__init__()
        _ensure_ui_font()
        self.setWindowTitle("AutoLabeler")
        self.resize(1280, 820)
        self.setMinimumSize(1024, 680)
        self.setObjectName("autoLabelerWindow")

        self._stack = QStackedWidget()
        self.login_view = LoginView()
        self.workbench_view = WorkbenchView(
            task_registry=task_registry,
            sample_worker=sample_worker,
            train_worker=train_worker,
            infer_worker=infer_worker,
            restore_worker=restore_worker,
            convert_worker=convert_worker,
            scan_worker=scan_worker,
            labelimg_worker=labelimg_worker,
            inspector_worker=inspector_worker,
            task_runner=task_runner,
            defaults_path=defaults_path,
        )
        self._stack.addWidget(self.login_view)
        self._stack.addWidget(self.workbench_view)
        self.setCentralWidget(self._stack)
        self.login_view.login_requested.connect(self.enter_workbench)
        self.setStyleSheet(_stylesheet())

    def enter_workbench(self) -> None:
        """Enter the main workbench after local/demo login."""
        self.workbench_view.show_home()
        self._stack.setCurrentWidget(self.workbench_view)


def _ensure_ui_font() -> None:
    """Register a Chinese-capable UI font before the stylesheet is applied."""
    app = QApplication.instance()
    if app is None:
        return
    for font_path in _UI_FONT_FILES:
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))
    available = set(QFontDatabase.families())
    for family in _UI_FONT_FAMILIES:
        if family in available:
            app.setFont(QFont(family, 9))
            return


def _nav_flow_button(index: int, module: ModuleEntry) -> QPushButton:
    """Build a structured side-nav entry for one workflow module."""
    button = QPushButton()
    button.setObjectName("navFlowButton")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setMinimumHeight(52)
    button.setText("")

    layout = QHBoxLayout(button)
    layout.setContentsMargins(10, 7, 10, 7)
    layout.setSpacing(9)

    number = QLabel(f"{index:02d}")
    number.setObjectName("navStepNumber")
    number.setAlignment(Qt.AlignmentFlag.AlignCenter)
    number.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    text_layout = QVBoxLayout()
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(1)
    title = QLabel(module.title)
    title.setObjectName("navStepTitle")
    subtitle = QLabel(module.subtitle)
    subtitle.setObjectName("navStepSubtitle")
    for label in (title, subtitle):
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    text_layout.addWidget(title)
    text_layout.addWidget(subtitle)

    layout.addWidget(number, 0)
    layout.addLayout(text_layout, 1)
    return button


def _nav_utility_button(title: str, badge_char: str, subtitle: str) -> QPushButton:
    """Build a structured side-nav entry for utility navigation."""
    button = QPushButton()
    button.setObjectName("navUtilityButton")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setMinimumHeight(50)
    button.setText("")

    layout = QHBoxLayout(button)
    layout.setContentsMargins(10, 7, 10, 7)
    layout.setSpacing(9)

    badge = QLabel(badge_char)
    badge.setObjectName("navUtilityBadge")
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    text_layout = QVBoxLayout()
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(1)
    title_label = QLabel(title)
    title_label.setObjectName("navStepTitle")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("navStepSubtitle")
    for label in (title_label, subtitle_label):
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    text_layout.addWidget(title_label)
    text_layout.addWidget(subtitle_label)

    layout.addWidget(badge, 0)
    layout.addLayout(text_layout, 1)
    return button


def _module_by_key(key: str) -> ModuleEntry:
    for module in MODULES:
        if module.key == key:
            return module
    raise KeyError(f"Unknown module key: {key}")


def _settings_line(value: str = "") -> QLineEdit:
    """Build a compact settings text input."""
    field = QLineEdit()
    field.setObjectName("formInput")
    field.setText(value)
    return field


def _settings_combo(options: tuple[str, ...], current: str) -> QComboBox:
    """Build a compact settings option input."""
    field = QComboBox()
    field.setObjectName("formInput")
    field.addItems(options)
    if current and current not in options:
        field.addItem(current)
    field.setCurrentText(current if current else options[0])
    return field


def _train_device_option_labels() -> tuple[str, ...]:
    """Return display labels for training device choices."""
    return tuple(label for label, _value in _TRAIN_DEVICE_OPTIONS)


def _train_device_label_for_value(value: str) -> str:
    """Map a persisted training device value to its display label."""
    normalized = value.strip()
    for label, option_value in _TRAIN_DEVICE_OPTIONS:
        if normalized == option_value or normalized == label:
            return label
    return normalized or "auto"


def _train_device_value_from_label(label: str) -> str:
    """Map a displayed training device label to the core device value."""
    normalized = label.strip()
    for option_label, value in _TRAIN_DEVICE_OPTIONS:
        if normalized == option_label or normalized == value:
            return value
    return normalized or "auto"


def _settings_section(
    title: str, rows: tuple[tuple[str, QWidget, str], ...]
) -> QFrame:
    """Build one settings section with dense parameter rows."""
    section = QFrame()
    section.setObjectName("settingsSectionPanel")
    layout = QGridLayout(section)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setHorizontalSpacing(10)
    layout.setVerticalSpacing(7)
    title_label = QLabel(title)
    title_label.setObjectName("smallTitle")
    layout.addWidget(title_label, 0, 0, 1, 3)
    for index, (label_text, widget, helper_text) in enumerate(rows, start=1):
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        helper = QLabel(helper_text)
        helper.setObjectName("mutedText")
        helper.setWordWrap(True)
        helper.setMinimumWidth(0)
        helper.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(label, index, 0)
        layout.addWidget(widget, index, 1)
        layout.addWidget(helper, index, 2)
    layout.setColumnStretch(0, 0)
    layout.setColumnStretch(1, 1)
    layout.setColumnStretch(2, 2)
    return section


def _home_tile_copy(key: str) -> str:
    """Return compact homepage copy for one module tile."""
    copy_by_key = {
        "scan": "不靠人记路径，建立 Flow 映射。",
        "sample": "少标一批代表图，备好训练集。",
        "label": "打开 LabelImg，直接标注。",
        "train": "训练 YOLO 模型，减少重复框图。",
        "infer": "批量生成预测标签，人只修需要修的结果。",
        "review": "按批次复核，不混图片和结果。",
        "restore": "写回 VOC XML，方便归档。",
        "convert": "XML 资产整理成训练数据集。",
    }
    return copy_by_key[key]


def _format_task_summary(task: TaskHandle) -> str:
    """Return a business-readable task summary without raw registry fields."""
    result = task.result or {}
    stats = _dict_value(result, "statistics")
    if task.status in _ACTIVE_TASK_STATUSES:
        return _active_task_summary(task)
    if task.status in {"cancelled", "interrupted"}:
        return task.progress_message or "任务已停止，未继续写入新的业务结果。"
    if task.status != "succeeded":
        return task.progress_message or "暂无结果摘要。"

    match _module_key_for_task_type(task.task_type):
        case "scan":
            images = _int_value(stats, "total_images", "image_count")
            classes = _int_value(stats, "total_codes", "class_count")
            products = _int_value(stats, "total_products", "product_count")
            return f"扫描 {images} 张图片，识别 {classes} 个类别，覆盖 {products} 个产品组。"
        case "sample":
            sampled = _int_value(stats, "sampled_count")
            train = _int_value(stats, "train_count")
            val = _int_value(stats, "val_count")
            lines = [f"已生成 YOLO 训练数据集，抽样 {sampled} 张，训练集 {train} 张，验证集 {val} 张。"]
            _append_output_line(lines, result, "dataset_dir")
            return "\n".join(lines)
        case "train":
            lines = ["训练完成，best.pt 已生成，用户可选择该模型进入推理。"]
            _append_output_line(lines, result, "best_model")
            return "\n".join(lines)
        case "infer":
            processed = _int_value(stats, "processed", "success")
            predicted = _int_value(stats, "predicted")
            empty = _int_value(stats, "empty_prediction")
            failed = _int_value(stats, "failed")
            lines = [
                f"推理完成，处理 {processed} 张图片，{predicted} 张有预测，{empty} 张空预测，失败 {failed} 张。"
            ]
            _append_output_line(lines, result, "inference_output_dir")
            return "\n".join(lines)
        case "restore":
            total = _int_value(result, "total")
            success = _int_value(result, "success")
            skipped = _int_value(result, "skipped")
            failed = _int_value(result, "failed")
            return f"XML 写回完成，总计 {total}，成功 {success}，跳过 {skipped}，失败 {failed}。"
        case "convert":
            if "total_pairs" in result:
                pairs = _int_value(result, "total_pairs")
                train = _int_value(result, "train_count")
                val = _int_value(result, "val_count")
                classes = _int_value(result, "class_count")
                lines = [
                    f"已生成 YOLO 数据集，{pairs} 对图片/XML，训练集 {train} 张，验证集 {val} 张，类别 {classes} 个。"
                ]
                _append_output_line(lines, result, "dataset_dir")
                return "\n".join(lines)
            total = _int_value(result, "total")
            success = _int_value(result, "success")
            failed = _int_value(result, "failed")
            return f"格式转换完成，总计 {total}，成功 {success}，失败 {failed}。"
        case "label":
            if "is_valid" in result:
                return "LabelImg 环境验证通过。" if result.get("is_valid") else "LabelImg 环境验证未通过。"
            return "LabelImg 已启动，请在标注窗口完成框选和保存。"
        case "review":
            return "复核数据已读取，可回到复核页继续选择 run 和 Code/Product。"
    return task.progress_message or "任务已完成。"


def _active_task_summary(task: TaskHandle) -> str:
    """Return a concise running-state summary."""
    module_key = _module_key_for_task_type(task.task_type)
    match module_key:
        case "train":
            return "正在训练 YOLO 模型，完成后会显示 best.pt 和 last.pt。"
        case "infer":
            return "正在生成预测标签，完成后进入复核页检查结果。"
        case "sample":
            return "正在生成 YOLO 训练数据集。"
        case "restore":
            return "正在写回 XML，请等待任务完成后再检查原图目录。"
        case "convert":
            return "正在转换数据集，源文件不会被移动。"
    return task.progress_message or "任务正在执行。"


def _visible_task_center_tasks(tasks: list[TaskHandle]) -> list[TaskHandle]:
    """Return task-center records after retention cleanup."""
    return sorted(tasks, key=_task_sort_key)


def _group_task_center_tasks(
    tasks: list[TaskHandle],
) -> list[tuple[str, list[TaskHandle]]]:
    """Group visible task-center records by display date."""
    today = date.today()
    grouped: list[tuple[str, list[TaskHandle]]] = []
    for task in reversed(tasks):
        label = _task_date_group_label(_task_display_date(task), today)
        if not grouped or grouped[-1][0] != label:
            grouped.append((label, []))
        grouped[-1][1].append(task)
    return grouped


def _task_date_group_label(task_date: date, today: date) -> str:
    """Return the visible date group label for a task."""
    delta_days = (today - task_date).days
    if delta_days <= 0:
        return "今天"
    if delta_days == 1:
        return "昨天"
    if delta_days == 2:
        return "前天"
    return task_date.strftime("%Y-%m-%d")


def _task_display_date(task: TaskHandle) -> date:
    """Return the date used for task-center filtering and grouping."""
    return _task_sort_key(task).date()


def _task_sort_key(task: TaskHandle) -> datetime:
    """Return a parsed task timestamp for deterministic ordering."""
    for value in (task.finished_at, task.started_at, task.created_at):
        if not value:
            continue
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return datetime.min


def _task_module_title(task: TaskHandle) -> str:
    """Return the visible module title for a task."""
    module_key = _module_key_for_task_type(task.task_type)
    if module_key in {module.key for module in MODULES}:
        return _module_by_key(module_key).title
    return "任务"


def _task_time_label(task: TaskHandle) -> str:
    """Return a task timestamp label based on status."""
    if task.started_at and task.finished_at:
        return f"开始于 {task.started_at} · 完成于 {task.finished_at}"
    if task.finished_at:
        return f"完成于 {task.finished_at}"
    if task.started_at:
        return f"开始于 {task.started_at}"
    return f"创建于 {task.created_at}"


def _append_output_line(
    lines: list[str], result: dict[str, object], key: str
) -> None:
    """Append a compact output path line if present."""
    value = result.get(key)
    if not value:
        return
    lines.append(f"输出：{_compact_path(str(value))}")


def _compact_path(value: str) -> str:
    """Compact long local paths for row display."""
    normalized = value.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    if len(parts) <= 3:
        return normalized
    if normalized.startswith("/"):
        return f"/{parts[0]}/.../{parts[-1]}"
    return f"{parts[0]}/{parts[1]}/.../{parts[-1]}"


def _dict_value(source: dict[str, object], key: str) -> dict[str, object]:
    """Return a nested dict value or an empty dict."""
    value = source.get(key)
    return value if isinstance(value, dict) else {}


def _int_value(source: dict[str, object], *keys: str) -> int:
    """Return the first integer-like value for any key."""
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def _module_key_for_task_type(task_type: str) -> str:
    """Map task registry types back to visible module keys."""
    mapping = {
        "labeling": "label",
        "labelimg": "label",
        "label_inspector": "review",
    }
    if task_type in {module.key for module in MODULES}:
        return task_type
    return mapping.get(task_type, "home")


def _clear_layout(layout: QVBoxLayout | QGridLayout) -> None:
    """Remove all child widgets/items from a Qt layout."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()


def _task_empty_state(message: str) -> QLabel:
    """Build a compact empty state for the task center."""
    label = QLabel(message)
    label.setObjectName("formPlaceholder")
    label.setWordWrap(True)
    return label


def _stylesheet() -> str:
    return """
    QWidget {
        color: #202b33;
        background: #eef3f4;
        font-family: "Microsoft YaHei UI";
        font-size: 13px;
    }
    QLabel {
        background: transparent;
    }
    QScrollArea#toolScrollArea {
        border: none;
        background: transparent;
    }
    QScrollArea#toolScrollArea QWidget {
        background: transparent;
    }
    QFrame#sideNav {
        min-width: 238px;
        max-width: 238px;
        background: #17242d;
        border-right: 1px solid #101a21;
    }
    QLabel#navMark {
        min-width: 34px;
        max-width: 34px;
        min-height: 34px;
        max-height: 34px;
        border-radius: 8px;
        background: #007b78;
        color: #eefaf9;
        font-weight: 800;
    }
    QLabel#navBrand {
        color: #f2f7f8;
        font-size: 15px;
        font-weight: 700;
        line-height: 1.25;
    }
    QLabel#navSection {
        color: #93a6af;
        font-size: 12px;
        padding: 10px 8px 4px;
    }
    QPushButton#navButton,
    QPushButton#navUtilityButton,
    QPushButton#navFlowButton {
        min-height: 42px;
        padding: 8px 12px;
        border: 1px solid transparent;
        border-radius: 8px;
        background: transparent;
        color: #d9e6ea;
        text-align: left;
    }
    QPushButton#navButton:hover,
    QPushButton#navUtilityButton:hover,
    QPushButton#navFlowButton:hover {
        background: #243641;
    }
    QPushButton#navButton[selected="true"] {
        background: #23333d;
        border-color: #567981;
        color: #f8fbfb;
    }
    QPushButton#navUtilityButton[selected="true"],
    QPushButton#navFlowButton[selected="true"] {
        background: #23333d;
        border-color: #567981;
        color: #f8fbfb;
    }
    QPushButton#navFlowButton {
        min-height: 50px;
        max-height: 56px;
        padding: 0px;
    }
    QPushButton#navUtilityButton {
        min-height: 50px;
        max-height: 56px;
        padding: 0px;
    }
    QLabel#navStepNumber {
        min-width: 32px;
        max-width: 32px;
        min-height: 28px;
        max-height: 28px;
        border-radius: 7px;
        background: #20323c;
        border: 1px solid #39535d;
        color: #a9c4ca;
        font-size: 12px;
        font-weight: 800;
    }
    QLabel#navUtilityBadge {
        min-width: 32px;
        max-width: 32px;
        min-height: 28px;
        max-height: 28px;
        border-radius: 7px;
        background: #263844;
        border: 1px solid #3a4f5a;
        color: #a9c4ca;
        font-size: 12px;
        font-weight: 800;
    }
    QLabel#navStepTitle {
        color: #edf6f7;
        font-size: 13px;
        font-weight: 800;
    }
    QLabel#navStepSubtitle {
        color: #9fb4bb;
        font-size: 12px;
        font-weight: 500;
    }
    QPushButton#navFlowButton[selected="true"] QLabel#navStepNumber {
        background: #008981;
        border-color: #31aaa0;
        color: #f2fbfb;
    }
    QPushButton#navFlowButton[selected="true"] QLabel#navStepTitle {
        color: #f8fbfb;
    }
    QPushButton#navFlowButton[selected="true"] QLabel#navStepSubtitle {
        color: #cce2e4;
    }
    QFrame#loginStory,
    QFrame#loginCard,
    QFrame#homeHero,
    QFrame#homeModulePanel,
    QFrame#homeSupportPanel,
    QFrame#homeRulePanel,
    QFrame#flowStrip,
    QFrame#leftMainPanel,
    QFrame#rightSupportPanel,
    QFrame#aiPreview,
    QFrame#loginWorkflowPanel,
    QFrame#loginBoundaryPanel,
    QFrame#manualStepsPanel,
    QFrame#settingsStatusPanel,
    QFrame#taskCenterSummaryPanel,
    QFrame#taskRow,
    QFrame#scanStructureExample,
    QFrame#reviewEmptyState,
    QFrame#reviewStatusPanel {
        background: #fbfdfd;
        border: 1px solid #cfdade;
        border-radius: 8px;
    }
    QFrame#homeRulePanel {
        min-width: 258px;
        max-width: 258px;
        background: #f4f8f8;
    }
    QLabel#loginBrand,
    QLabel#eyebrow {
        color: #287c78;
        font-weight: 700;
    }
    QLabel#homeEyebrow {
        color: #287c78;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0px;
    }
    QLabel#loginHeadline {
        font-size: 38px;
        font-weight: 800;
        line-height: 1.2;
    }
    QLabel#homeTitle {
        font-size: 23px;
        font-weight: 800;
    }
    QLabel#toolTitle {
        font-size: 30px;
        font-weight: 800;
    }
    QLabel#panelTitle {
        font-size: 20px;
        font-weight: 720;
    }
    QLabel#smallTitle {
        font-size: 15px;
        font-weight: 700;
    }
    QLabel#homeSectionTitle,
    QLabel#flowTitle {
        color: #26333b;
        font-size: 16px;
        font-weight: 800;
    }
    QLabel#mutedText,
    QLabel#footnote {
        color: #607078;
        line-height: 1.5;
    }
    QLabel#loginStripTile,
    QLabel#strengthPill,
    QLabel#formPlaceholder,
    QLabel#flowStep {
        padding: 10px 12px;
        background: #edf5f4;
        border: 1px solid #d2e1df;
        border-radius: 8px;
        color: #2c5559;
    }
    QLabel#strengthPill {
        min-height: 38px;
        max-height: 42px;
        font-size: 12px;
    }
    QLabel#flowStep {
        min-height: 38px;
        max-height: 44px;
        padding: 6px 6px;
        background: #f7fbfa;
        color: #33575a;
        font-size: 12px;
    }
    QPushButton#moduleTile {
        min-height: 84px;
        max-height: 92px;
        padding: 11px 14px;
        border: 1px solid #cfdade;
        border-radius: 8px;
        background: #fbfdfd;
        color: #25323a;
        text-align: left;
        font-weight: 660;
    }
    QPushButton#moduleTile:hover {
        border-color: #6ca8a3;
        background: #f2faf8;
    }
    QPushButton#moduleTile:pressed {
        background: #e6f4f2;
    }
    QPushButton#primaryButton {
        min-height: 36px;
        padding: 8px 16px;
        border: 1px solid #1f6c68;
        border-radius: 8px;
        background: #007b78;
        color: #f7fbfb;
        font-weight: 700;
    }
    QPushButton#secondaryButton,
    QPushButton#supportActionButton,
    QPushButton#manualNavButton,
    QPushButton#manualStepButton,
    QPushButton#tabButton,
    QPushButton#tabButtonActive {
        min-height: 34px;
        padding: 7px 13px;
        border: 1px solid #cfd9dd;
        border-radius: 8px;
        background: #f8fbfb;
        color: #40515a;
    }
    QPushButton#secondaryButton:hover,
    QPushButton#supportActionButton:hover,
    QPushButton#manualNavButton:hover,
    QPushButton#manualStepButton:hover,
    QPushButton#tabButton:hover {
        border-color: #9eb7bd;
        background: #eef5f4;
    }
    QPushButton#manualNavButton {
        text-align: left;
        color: #236d69;
        border: 0px;
        border-radius: 6px;
        background: transparent;
        min-height: 28px;
        padding: 5px 8px;
        font-weight: 700;
    }
    QPushButton#manualNavButton:hover {
        background: #eef7f6;
        color: #174f4d;
    }
    QPushButton#manualStepButton {
        min-height: 58px;
        padding: 8px 10px;
        text-align: left;
        font-weight: 700;
        color: #17343d;
        background: #f6faf9;
    }
    QPushButton#secondaryButton:checked,
    QPushButton#tabButton:checked {
        background: #dcefed;
        border-color: #5ea9a5;
        color: #236d69;
        font-weight: 700;
    }
    QPushButton#advancedToggleButton {
        min-height: 34px;
        padding: 7px 13px;
        border: 1px solid #cfd9dd;
        border-radius: 8px;
        background: #f8fbfb;
        color: #40515a;
        text-align: left;
    }
    QPushButton#advancedToggleButton:hover {
        border-color: #9eb7bd;
        background: #eef5f4;
    }
    QPushButton#advancedToggleButton:checked {
        background: #dcefed;
        border-color: #5ea9a5;
        color: #236d69;
        font-weight: 700;
    }
    QPushButton#tabButtonActive {
        background: #e7f3f1;
        color: #236d69;
        font-weight: 700;
    }
    QPushButton#primaryButton:hover {
        background: #226f6b;
    }
    QPushButton#primaryButton:pressed {
        background: #1d625f;
    }
    QLineEdit#formInput:focus,
    QComboBox#formInput:focus,
    QTextEdit#logBox:focus,
    QTextEdit:focus {
        border-color: #5ea9a5;
    }
    QPushButton:disabled,
    QTextEdit:disabled {
        color: #8b989e;
        background: #eef2f3;
    }
    QLineEdit#formInput,
    QComboBox#formInput,
    QTextEdit#logBox,
    QTextEdit {
        border: 1px solid #cfd9dd;
        border-radius: 8px;
        background: #fdfefe;
        padding: 8px;
    }
    QScrollArea#manualContentScroll {
        border: 0px;
        background: transparent;
    }
    QFrame#manualSection {
        border: 1px solid #d5e0e3;
        border-radius: 8px;
        background: #fbfdfd;
    }
    QLabel#manualSectionTitle {
        color: #18242c;
        font-size: 17px;
        font-weight: 800;
    }
    QFrame#manualParamTable {
        background: #fdfefe;
        border: 1px solid #dce6e8;
        border-radius: 8px;
        padding: 8px;
    }
    QLabel#manualTableHeader {
        color: #236d69;
        font-size: 12px;
        font-weight: 800;
        padding: 5px 6px;
        background: #eef7f6;
        border-radius: 6px;
    }
    QLabel#manualTableCell {
        color: #33434b;
        padding: 5px 6px;
        line-height: 1.35;
    }
    QFrame#manualNote {
        background: #f2f8f7;
        border: 1px solid #d5e4e2;
        border-radius: 8px;
    }
    QProgressBar#taskProgressBar {
        min-height: 18px;
        max-height: 18px;
        border: 1px solid #cfd9dd;
        border-radius: 8px;
        background: #f7fbfb;
        color: #26333b;
        text-align: center;
        font-size: 12px;
        font-weight: 700;
    }
    QProgressBar#taskProgressBar::chunk {
        border-radius: 7px;
        background: #4c9d97;
    }
    QLineEdit#formInput {
        min-height: 24px;
    }
    QComboBox#formInput {
        min-height: 24px;
        padding: 6px 8px;
    }
    QCheckBox#formCheckBox {
        color: #33434b;
        spacing: 8px;
    }
    QCheckBox#formCheckBox::indicator {
        width: 15px;
        height: 15px;
    }
    QFrame#pathPicker {
        min-height: 34px;
        border: 1px solid #cfd9dd;
        border-radius: 8px;
        background: #fdfefe;
    }
    QFrame#pathPicker QLineEdit#formInput {
        border: none;
        background: transparent;
        padding: 8px 10px;
    }
    QToolButton#pathBrowseButton {
        min-width: 58px;
        border: none;
        border-left: 1px solid #d4dfe2;
        border-top-right-radius: 8px;
        border-bottom-right-radius: 8px;
        background: #f5f9f8;
        color: #2f6663;
        font-weight: 700;
    }
    QToolButton#pathBrowseButton:hover {
        background: #eaf4f2;
    }
    QToolButton#pathBrowseButton:pressed {
        background: #ddeceb;
    }
    QTreeWidget#reviewNodeTree {
        border: 1px solid #cfd9dd;
        border-radius: 8px;
        background: #fdfefe;
        alternate-background-color: #f7fbfa;
        padding: 4px;
    }
    QTreeWidget#reviewNodeTree::item {
        padding: 6px 8px;
    }
    QTreeWidget#reviewNodeTree::item:selected {
        background: #dcefed;
        color: #236d69;
    }
    QHeaderView::section {
        border: none;
        border-bottom: 1px solid #d3dfe2;
        background: #f4f8f8;
        padding: 6px 8px;
        color: #526269;
        font-weight: 700;
    }
    QFrame#sourceChoicePanel,
    QFrame#commonOptionsPanel,
    QFrame#advancedOptionsPanel,
    QFrame#reviewSelectionPanel {
        border: 1px solid #d3dfe2;
        border-radius: 8px;
        background: #f8fbfb;
    }
    QWidget#homePage {
        background: #eef3f4;
    }
    QFrame#homeHero {
        border-radius: 8px;
        border: 1px solid #c7d7d9;
        background: #fbfdfd;
    }
    QLabel#homeEyebrow {
        color: #257b76;
        font-size: 15px;
        font-weight: 800;
    }
    QLabel#homeTitle {
        color: #18242c;
        font-size: 30px;
        font-weight: 800;
    }
    QFrame#homeModulePanel {
        background: transparent;
        border: none;
    }
    QPushButton#moduleCardButton {
        border: 1px solid #cfdade;
        border-radius: 8px;
        background: #fbfdfd;
        text-align: center;
    }
    QPushButton#moduleCardButton:hover {
        border-color: #73aaa5;
        background: #f2faf8;
    }
    QPushButton#moduleCardButton:pressed {
        border-color: #4f8f88;
        background: #e5f3f1;
    }
    QLabel#moduleTitleText {
        min-height: 30px;
        padding: 3px 4px;
        border: none;
        border-radius: 7px;
        background: transparent;
        color: #17242d;
        font-size: 16px;
        font-weight: 800;
    }
    QLabel#moduleDescription {
        color: #5d6f78;
        font-size: 14px;
        line-height: 1.35;
    }
    QFrame#aiPreview {
        border-radius: 8px;
        border: 1px solid #cfdade;
        background: #fbfdfd;
    }
    QLabel#aiTitle {
        color: #18242c;
        font-size: 19px;
        font-weight: 800;
    }
    QLabel#aiStatus {
        color: #667981;
        font-size: 12px;
        font-weight: 800;
    }
    QLabel#aiChip {
        min-height: 22px;
        padding: 2px 8px;
        border: 1px solid #bddbd6;
        border-radius: 11px;
        color: #257b76;
        background: #eef8f5;
        font-size: 12px;
        font-weight: 700;
    }
    QFrame#aiThread {
        background: transparent;
        border: none;
    }
    QLabel#aiBubbleUser {
        padding: 8px 10px;
        border-radius: 8px;
        color: #f6fbfb;
        background: #146e69;
        font-size: 13px;
    }
    QLabel#aiBubbleBot {
        padding: 8px 10px;
        border: 1px solid #c5dfda;
        border-radius: 8px;
        color: #24333a;
        background: #eef8f5;
        font-size: 13px;
    }
    QFrame#aiInput {
        border: 1px solid #b6c7cc;
        border-radius: 9px;
        background: #fbfdfd;
    }
    QLabel#aiInputHint {
        color: #617179;
        font-size: 13px;
    }
    QPushButton#aiSendButton {
        min-height: 32px;
        padding: 6px 10px;
        border: 1px solid #bddbd6;
        border-radius: 8px;
        color: #257b76;
        background: #eef8f5;
        font-weight: 700;
    }
    QPushButton#aiSendButton:disabled {
        color: #7b8b92;
        border-color: #cbd8dc;
        background: #eef2f3;
    }
    QFrame#homeSupportPanel {
        border: 1px solid #cfdade;
        border-radius: 8px;
        background: #fbfdfd;
    }
    QLabel#supportCore {
        color: #a05d15;
        font-size: 12px;
        font-weight: 800;
    }
    QFrame#homeStrengthBand {
        border: 1px solid #d5e0e3;
        border-radius: 8px;
        background: #f8fbfb;
    }
    QFrame#strengthItem {
        border: none;
        background: transparent;
        min-height: 86px;
    }
    QFrame#strengthDivider {
        color: #d7e2e4;
        max-width: 1px;
    }
    QLabel#loginWorkflowStep,
    QLabel#loginBoundaryItem,
    QFrame#settingsStatusItem {
        border: 1px solid #d5e0e3;
        border-radius: 8px;
        background: #f6faf9;
        color: #17343d;
        padding: 8px;
    }
    QFrame#taskRow {
        background: #fdfefe;
    }
    QFrame#taskRowActions {
        background: transparent;
        border: none;
    }
    QFrame#taskCenterSummaryPanel {
        background: #f8fbfb;
    }
    QFrame#taskSummaryItem {
        border: 1px solid #d5e0e3;
        border-radius: 8px;
        background: #fdfefe;
    }
    QFrame#taskSummaryItem[selected="true"] {
        border-color: #2a8f89;
        background: #eef8f7;
    }
    QPushButton#taskSummaryButton {
        border: none;
        background: transparent;
        text-align: left;
    }
    QPushButton#taskSummaryButton:hover {
        border: 1px solid #9eb7bd;
        border-radius: 8px;
        background: rgba(42, 143, 137, 0.04);
    }
    QLabel#taskSummaryLabel {
        color: #236d69;
        font-size: 12px;
        font-weight: 800;
    }
    QLabel#taskSummaryValue {
        color: #18242c;
        font-size: 16px;
        font-weight: 800;
        line-height: 1.25;
    }
    QLabel#taskRowTitle {
        color: #18242c;
        font-size: 15px;
        font-weight: 800;
    }
    QLabel#taskDateHeader {
        color: #257b76;
        font-size: 12px;
        font-weight: 800;
        padding: 8px 2px 2px;
    }
    QPushButton#taskBackButton,
    QPushButton#taskDeleteButton {
        min-height: 30px;
        padding: 5px 10px;
        border: 1px solid #cfd9dd;
        border-radius: 8px;
        background: #f8fbfb;
        color: #236d69;
        font-weight: 700;
    }
    QPushButton#taskDeleteButton {
        color: #8a4f1e;
    }
    QPushButton#taskBackButton:hover,
    QPushButton#taskDeleteButton:hover {
        border-color: #9eb7bd;
        background: #eef5f4;
    }
    QCheckBox#riskCheckbox {
        color: #17343d;
        spacing: 8px;
        padding: 6px 0px;
    }
    QCheckBox#riskCheckbox:disabled {
        color: #7b8b92;
    }
    QCheckBox#riskCheckbox::indicator {
        width: 16px;
        height: 16px;
    }
    QCheckBox#riskCheckbox::indicator:disabled {
        border: 1px solid #cbd8dc;
        background: #eef2f3;
    }
    QLabel#strengthBadge {
        min-width: 34px;
        max-width: 34px;
        min-height: 34px;
        max-height: 34px;
        border-radius: 8px;
        color: #f7fbfb;
        background: #007b78;
        font-size: 12px;
        font-weight: 800;
    }
    QLabel#strengthTitle {
        color: #202b33;
        font-size: 15px;
        font-weight: 800;
    }
    QLabel#strengthBody {
        color: #607078;
        font-size: 12px;
        line-height: 1.25;
    }
    QLabel#developerLabel {
        color: #607078;
        font-size: 13px;
        font-weight: 700;
    }
    QFrame#rightSupportPanel {
        border: 1px solid #cfdade;
        border-radius: 8px;
        background: #fbfdfd;
    }
    QLabel#aiRailTitle {
        color: #18242c;
        font-size: 22px;
        font-weight: 800;
    }
    QLabel#aiRailBadge {
        min-height: 24px;
        padding: 2px 8px;
        border: 1px solid #bddbd6;
        border-radius: 12px;
        color: #257b76;
        background: #eef8f5;
        font-size: 12px;
        font-weight: 800;
    }
    QTextEdit#aiRailThread,
    QTextEdit#aiRailInput {
        border: 1px solid #c4d3d8;
        border-radius: 8px;
        background: #fbfdfd;
        padding: 10px;
        color: #27363d;
    }
    QFrame#preflightPanel,
    QFrame#runtimePanel {
        border: 1px solid #d3dfe2;
        border-radius: 8px;
        background: #f8fbfb;
    }
    QLabel#preflightSummary {
        padding: 8px 10px;
        border: 1px solid #d7e2e5;
        border-radius: 8px;
        background: #fbfdfd;
        color: #40515a;
    }
    QFrame#railDivider {
        color: #d3dfe2;
    }
    QWidget#loginView {
        background: #e9eff1;
    }
    QFrame#loginStory[surfaceRole="product"] {
        background: #f8fbfa;
        border: 1px solid #b8c8cd;
        border-radius: 8px;
    }
    QFrame#loginCard[surfaceRole="access"] {
        min-width: 326px;
        max-width: 372px;
        background: #fcfdfc;
        border: 1px solid #aebec5;
        border-radius: 8px;
    }
    QFrame#loginWorkflowPanel[surfaceRole="workflow"] {
        background: #eef6fb;
        border: 1px solid #b5d0e2;
        border-radius: 8px;
    }
    QFrame#loginBoundaryPanel[surfaceRole="boundary"] {
        background: #fff7e8;
        border: 1px solid #dfbb72;
        border-radius: 8px;
    }
    QLabel#loginWorkflowStep {
        border: 1px solid #c4dbe7;
        border-radius: 8px;
        background: #f8fcfe;
        color: #214d63;
        font-weight: 800;
        padding: 9px 10px;
    }
    QLabel#loginBoundaryItem {
        border: 1px solid #e6cd96;
        border-radius: 8px;
        background: #fffaf0;
        color: #684913;
        font-weight: 700;
        padding: 9px 10px;
    }
    QPushButton#primaryButton[buttonRole="primaryAccess"] {
        min-height: 42px;
        background: #075f6a;
        border-color: #064c55;
        color: #f7fbfb;
        font-size: 14px;
    }
    QPushButton#secondaryButton[buttonRole="reservedAccess"] {
        min-height: 38px;
        background: #eef2f3;
        border-color: #c5d0d5;
        color: #77868d;
    }
    QFrame#leftMainPanel {
        background: #fcfdfc;
        border: 1px solid #becdd2;
    }
    QFrame#rightSupportPanel[surfaceRole="support"] {
        background: #f6f9f9;
        border: 1px solid #c2d0d5;
    }
    QFrame#preflightPanel,
    QFrame#runtimePanel,
    QFrame#sourceChoicePanel,
    QFrame#commonOptionsPanel,
    QFrame#advancedOptionsPanel,
    QFrame#reviewStatusPanel,
    QFrame#reviewEmptyState,
    QFrame#scanStructureExample {
        background: #f5f8f9;
        border: 1px solid #c4d1d7;
        border-radius: 8px;
    }
    QLabel#fieldLabel {
        color: #2b3f49;
        font-weight: 800;
    }
    QLineEdit#formInput,
    QComboBox#formInput,
    QTextEdit {
        border: 1px solid #b7c5cb;
        border-radius: 8px;
        background: #fdfefe;
        color: #1f2e36;
        padding: 8px;
    }
    QLineEdit#formInput:focus,
    QComboBox#formInput:focus,
    QTextEdit:focus {
        border-color: #347f8a;
    }
    QFrame#pathPicker {
        min-height: 36px;
        border: 1px solid #aebec5;
        border-radius: 8px;
        background: #fdfefe;
    }
    QToolButton#pathBrowseButton {
        min-width: 62px;
        border-left: 1px solid #c6d2d7;
        background: #edf3f4;
        color: #245d64;
        font-weight: 800;
    }
    QToolButton#pathBrowseButton:hover {
        background: #e1ecee;
    }
    QLabel[feedbackRole="explanation"] {
        padding: 9px 11px;
        border: 1px solid #d4dee3;
        border-radius: 8px;
        background: #f4f7f8;
        color: #4b5c65;
        line-height: 1.45;
    }
    QLabel[feedbackRole="status"] {
        padding: 8px 11px;
        border: 1px solid #b7d2e3;
        border-radius: 8px;
        background: #eef6fb;
        color: #214f68;
        line-height: 1.4;
    }
    QLabel[feedbackRole="result"] {
        padding: 10px 12px;
        border: 1px solid #9fcfbe;
        border-radius: 8px;
        background: #edf8f4;
        color: #174f46;
        font-weight: 800;
        line-height: 1.45;
    }
    QLabel[feedbackRole="output"] {
        padding: 10px 12px;
        border: 1px solid #abcfe3;
        border-radius: 8px;
        background: #f0f7fb;
        color: #1e526b;
        line-height: 1.45;
    }
    QLabel[feedbackRole="risk"] {
        padding: 10px 12px;
        border: 1px solid #dfbb72;
        border-radius: 8px;
        background: #fff7e8;
        color: #684913;
        font-weight: 800;
        line-height: 1.45;
    }
    QTextEdit#logBox[surfaceRole="log"] {
        border: 1px solid #bdc9cf;
        background: #f6f8f9;
        color: #24343c;
        font-family: "Cascadia Mono", "Consolas", monospace;
        font-size: 12px;
    }
    QCheckBox[feedbackRole="riskConfirm"],
    QPushButton#confirmCheckbox[buttonRole="riskConfirm"] {
        min-height: 34px;
        padding: 7px 10px;
        border: 1px solid #dfbb72;
        border-radius: 8px;
        background: #fff8ec;
        color: #684913;
        font-weight: 800;
    }
    QPushButton#confirmCheckbox[buttonRole="riskConfirm"]:checked {
        background: #e7c878;
        border-color: #b9872d;
        color: #2f240a;
    }
    QCheckBox[feedbackRole="riskConfirm"]:disabled {
        color: #8b989e;
        background: #eef2f3;
        border-color: #cbd8dc;
    }
    QPushButton#tabButtonActive {
        background: #d9ece8;
        border-color: #4d9186;
        color: #165c55;
        font-weight: 800;
    }
    QPushButton#tabButton {
        background: #f8fbfb;
        border-color: #c8d4d9;
        color: #40515a;
    }
    QPushButton#secondaryButton:checked,
    QPushButton#tabButton:checked {
        background: #d9ece8;
        border-color: #4d9186;
        color: #165c55;
        font-weight: 800;
    }
    QProgressBar#taskProgressBar {
        border: 1px solid #b8c8cd;
        background: #f5f8f9;
        color: #22343c;
    }
    QProgressBar#taskProgressBar::chunk {
        background: #3f8f86;
    }
    QPushButton#moduleCardButton {
        border: 1px solid #c8d5da;
        background: #fcfdfc;
    }
    QLabel#moduleDescription {
        color: #526872;
    }
    """
