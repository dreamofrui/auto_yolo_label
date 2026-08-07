"""LabelImg launcher pages for free labeling and prediction review."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.label_inspector import (
    GetProductLabelsConfig,
    GetRunTreeConfig,
    InferenceRun,
    ListRunsConfig,
    ProductLabel,
    RunTreeNode,
)
from core.labelimg_launcher import (
    LabelImgConfig,
    LabelImgLaunchResult,
    LabelImgValidateConfig,
    LabelImgValidateResult,
)
from gui.path_picker import PathPicker
from gui.task_runner import ImmediateTaskRunner, TaskRunner
from gui.tool_page_chrome import (
    build_ai_assistant_panel,
    build_log_box,
    configure_left_panel,
    configure_tool_root,
    constrain_feedback_label,
    wrap_scroll_panel,
)
from gui.workers.label_inspector_worker import (
    LabelInspectorWorker,
    LabelInspectorWorkerOutcome,
)
from gui.workers.labelimg_worker import LabelImgWorker, LabelImgWorkerOutcome
from utils.task_registry import TaskRegistry

_LABELIMG_PYTHON = Path("D:/miniforge3/envs/labelimg/python.exe")


class LabelImgWorkerProtocol(Protocol):
    """Worker shape used by LabelImg pages."""

    def validate(self, config: LabelImgValidateConfig) -> LabelImgWorkerOutcome:
        """Validate LabelImg environment."""

    def preflight(self, config: LabelImgConfig) -> LabelImgWorkerOutcome:
        """Preflight LabelImg launch inputs."""

    def launch(self, config: LabelImgConfig) -> LabelImgWorkerOutcome:
        """Launch LabelImg."""


class InspectorWorkerProtocol(Protocol):
    """Worker shape used by Review page."""

    def list_runs(self, config: ListRunsConfig) -> LabelInspectorWorkerOutcome:
        """List inference runs."""

    def get_run_tree(self, config: GetRunTreeConfig) -> LabelInspectorWorkerOutcome:
        """Get inference run tree."""

    def get_product_labels(
        self, config: GetProductLabelsConfig
    ) -> LabelInspectorWorkerOutcome:
        """Get labels for a Code/Product node."""


class LabelImgPage(QWidget):
    """Free LabelImg launch page or Flow prediction review page."""

    def __init__(
        self,
        *,
        default_mode: str,
        labelimg_worker: LabelImgWorkerProtocol | None = None,
        inspector_worker: InspectorWorkerProtocol | None = None,
        registry: TaskRegistry | None = None,
        task_runner: TaskRunner | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("labelImgPage")
        self._mode = default_mode
        self._labelimg_worker = labelimg_worker or LabelImgWorker(registry=registry)
        self._inspector_worker = inspector_worker or LabelInspectorWorker(
            registry=registry
        )
        self._task_runner = task_runner or ImmediateTaskRunner()
        self._annotation_format = "yolo"
        self._prepared_labels: list[ProductLabel] = []
        self._review_image_dir: Path | None = None
        self._review_label_dir: Path | None = None
        self._launch_after_prepare = False

        root = QHBoxLayout(self)
        configure_tool_root(root)

        self.left_main_panel = QFrame()
        self.left_main_panel.setObjectName("leftMainPanel")
        left = QVBoxLayout(self.left_main_panel)
        configure_left_panel(left)

        eyebrow = QLabel("LabelImg launcher")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("标注" if default_mode == "label" else "复核")
        title.setObjectName("toolTitle")
        subtitle = QLabel(
            "打开外部 LabelImg 做人工标注"
            if default_mode == "label"
            else "打开预测结果进行人工复核"
        )
        subtitle.setObjectName("smallTitle")
        copy = QLabel(
            "本模块只负责校验路径并启动外部 LabelImg，不内置框选编辑器。"
            if default_mode == "label"
            else "复核使用 mapping 定位原图，编辑 run/labels 下的预测标签。"
        )
        copy.setObjectName("mutedText")
        copy.setWordWrap(True)

        self.free_form = self._build_free_form()
        self.review_form = self._build_review_form()
        if default_mode == "review":
            self.launch_button = self.review_launch_button

        self.result_summary = QLabel("等待操作。")
        self.result_summary.setObjectName("formPlaceholder")
        self.result_summary.setProperty("feedbackRole", "result")
        constrain_feedback_label(self.result_summary)

        left.addWidget(eyebrow)
        left.addWidget(title)
        left.addWidget(subtitle)
        left.addWidget(copy)
        left.addWidget(self.free_form)
        left.addWidget(self.review_form)
        left.addWidget(self.result_summary)
        if default_mode == "label":
            self.log_box = build_log_box("[ready] 等待 LabelImg 操作")
            left.addWidget(self.log_box, 1)
        left.addStretch(1)

        self.ai_assistant_panel = build_ai_assistant_panel(
            context=(
                "标注页用于打开外部 LabelImg"
                if default_mode == "label"
                else "复核页用于打开预测结果进行人工检查"
            ),
        )
        self.right_support_panel = self.ai_assistant_panel

        root.addWidget(wrap_scroll_panel(self.left_main_panel), 1)
        root.addWidget(self.right_support_panel, 0)
        self._sync_mode()
        self.site_input.textChanged.connect(self._handle_site_changed)

    def _build_free_form(self) -> QWidget:
        wrapper = QWidget()
        form = QGridLayout(wrapper)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)
        self.python_input = PathPicker(
            mode="file",
            value=str(_LABELIMG_PYTHON),
            placeholder="Python",
            dialog_title="选择 Python",
            file_filter="Python executables (*.exe);;All Files (*)",
        )
        self.image_dir_input = PathPicker(
            placeholder="图片目录",
            dialog_title="选择图片目录",
        )
        self.classes_file_input = PathPicker(
            mode="file",
            placeholder="非空 classes.txt",
            dialog_title="选择 classes.txt",
            file_filter="Text files (*.txt);;All Files (*)",
        )
        self.label_dir_input = PathPicker(
            placeholder="标签输出目录",
            dialog_title="选择标签输出目录",
        )
        self.yolo_mode_button = QPushButton("YOLO 标注")
        self.yolo_mode_button.setCheckable(True)
        self.yolo_mode_button.setChecked(True)
        self.yolo_mode_button.setObjectName("tabButtonActive")
        self.voc_mode_button = QPushButton("VOC 标注")
        self.voc_mode_button.setCheckable(True)
        self.voc_mode_button.setObjectName("tabButton")
        mode_group = QButtonGroup(self)
        mode_group.addButton(self.yolo_mode_button)
        mode_group.addButton(self.voc_mode_button)
        self.yolo_mode_button.clicked.connect(lambda: self.set_annotation_format("yolo"))
        self.voc_mode_button.clicked.connect(lambda: self.set_annotation_format("voc"))
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.yolo_mode_button)
        mode_row.addWidget(self.voc_mode_button)
        mode_row.addStretch(1)
        self.mode_note = QLabel("")
        self.mode_note.setObjectName("formPlaceholder")
        self.mode_note.setProperty("feedbackRole", "explanation")
        constrain_feedback_label(self.mode_note)
        self.validate_button = QPushButton("预检")
        self.validate_button.setObjectName("secondaryButton")
        self.validate_button.clicked.connect(self.validate_labelimg)
        self.launch_button = QPushButton("打开 LabelImg")
        self.launch_button.setObjectName("primaryButton")
        self.launch_button.clicked.connect(self.launch_free_labeling)
        fields = (
            ("Python", self.python_input),
            ("图片目录", self.image_dir_input),
        )
        form.addLayout(mode_row, 0, 0, 1, 2)
        form.addWidget(self.mode_note, 1, 0, 1, 2)
        for row, (label, widget) in enumerate(fields):
            form.addWidget(QLabel(label), row + 2, 0)
            form.addWidget(widget, row + 2, 1)
        self.classes_file_label = QLabel("classes.txt")
        self.label_dir_label = QLabel("标签目录")
        form.addWidget(self.classes_file_label, 4, 0)
        form.addWidget(self.classes_file_input, 4, 1)
        form.addWidget(self.label_dir_label, 5, 0)
        form.addWidget(self.label_dir_input, 5, 1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.validate_button)
        actions.addWidget(self.launch_button)
        form.addLayout(actions, 6, 0, 1, 2)
        self.set_annotation_format("yolo")
        return wrapper

    def _build_review_form(self) -> QWidget:
        wrapper = QWidget()
        form = QGridLayout(wrapper)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)
        self.site_input = PathPicker(
            placeholder="已扫描站点路径",
            dialog_title="选择站点路径",
        )
        form.addWidget(QLabel("站点路径"), 0, 0)
        form.addWidget(self.site_input, 0, 1)

        self.load_runs_button = QPushButton("加载 run")
        self.load_runs_button.setObjectName("secondaryButton")
        self.load_runs_button.clicked.connect(self.load_runs)
        self.load_tree_button = QPushButton("加载目录树")
        self.load_tree_button.setObjectName("secondaryButton")
        self.load_tree_button.clicked.connect(self.load_tree)
        self.prepare_button = QPushButton("准备复核")
        self.prepare_button.setObjectName("secondaryButton")
        self.prepare_button.clicked.connect(self.prepare_review)
        self.review_launch_button = QPushButton("打开复核")
        self.review_launch_button.setObjectName("primaryButton")
        self.review_launch_button.clicked.connect(self.launch_review)

        self.run_combo = QComboBox()
        self.run_combo.setObjectName("formInput")
        self.run_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.run_combo.currentIndexChanged.connect(self._handle_run_selected)
        self.review_empty_state_panel = QFrame()
        self.review_empty_state_panel.setObjectName("reviewEmptyState")
        empty_layout = QVBoxLayout(self.review_empty_state_panel)
        empty_layout.setContentsMargins(10, 8, 10, 8)
        empty_layout.setSpacing(3)
        self.review_empty_text = QLabel(
            "先选择站点并加载 run；再选择 Code/Product，准备复核后打开 LabelImg。"
        )
        self.review_empty_text.setObjectName("mutedText")
        self.review_empty_text.setProperty("feedbackRole", "explanation")
        constrain_feedback_label(self.review_empty_text)
        empty_layout.addWidget(self.review_empty_text)
        form.addWidget(self.review_empty_state_panel, 1, 0, 1, 2)

        run_row_widget = QWidget()
        run_row = QHBoxLayout(run_row_widget)
        run_row.setContentsMargins(0, 0, 0, 0)
        run_row.setSpacing(8)
        run_row.addWidget(QLabel("推理 run"))
        run_row.addWidget(self.run_combo, 1)
        run_row.addWidget(self.load_runs_button)
        form.addWidget(run_row_widget, 2, 0, 1, 2)

        self.run_tree = QTreeWidget()
        self.run_tree.setObjectName("reviewNodeTree")
        self.run_tree.setHeaderLabels(["目录"])
        self.run_tree.setMinimumHeight(260)
        self.run_tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.run_tree.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.run_tree.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        tree_header = self.run_tree.header()
        tree_header.setStretchLastSection(False)
        tree_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.run_tree.currentItemChanged.connect(self._handle_tree_selected)
        form.addWidget(QLabel("Code/Product"), 3, 0, 1, 2)
        form.addWidget(self.run_tree, 4, 0, 1, 2)

        self.review_status_panel = QFrame()
        self.review_status_panel.setObjectName("reviewStatusPanel")
        status_layout = QVBoxLayout(self.review_status_panel)
        status_layout.setContentsMargins(10, 8, 10, 8)
        status_layout.setSpacing(4)
        self.review_status_summary = QLabel(
            "准备后显示图片目录、标签目录、classes.txt 和缺失标签数量。"
        )
        self.review_status_summary.setObjectName("mutedText")
        self.review_status_summary.setProperty("feedbackRole", "output")
        constrain_feedback_label(self.review_status_summary)
        status_layout.addWidget(self.review_status_summary)

        self.review_actions_widget = QWidget()
        actions = QHBoxLayout(self.review_actions_widget)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        actions.addWidget(self.load_runs_button)
        actions.addWidget(self.load_tree_button)
        actions.addStretch(1)
        actions.addWidget(self.prepare_button)
        actions.addWidget(self.review_launch_button)
        form.addWidget(self.review_actions_widget, 5, 0, 1, 2)
        form.addWidget(self.review_status_panel, 6, 0, 1, 2)
        form.setRowStretch(4, 1)
        return wrapper

    def validate_labelimg(self) -> None:
        """Preflight configured LabelImg environment and launch inputs."""
        try:
            config = self._build_free_labeling_config()
        except ValueError as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("LabelImg 预检中...")
        self._task_runner.run(
            lambda: self._labelimg_worker.preflight(config),
            self._handle_validate_outcome,
            lambda exc: self._show_error("LabelImg 预检失败", str(exc)),
        )

    def launch_free_labeling(self) -> None:
        """Launch LabelImg for explicit free-labeling paths."""
        try:
            config = self._build_free_labeling_config()
        except ValueError as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("LabelImg 启动中...")
        self._task_runner.run(
            lambda: self._labelimg_worker.launch(config),
            self._show_launch_outcome,
            lambda exc: self._show_error("LabelImg 启动失败", str(exc)),
        )

    def _build_free_labeling_config(self) -> LabelImgConfig:
        """Build the free-labeling launch/preflight config from current fields."""
        python_path = _required_path(self.python_input, "请选择 Python")
        image_dir = _required_path(self.image_dir_input, "请选择图片目录")
        if self._annotation_format == "voc":
            return LabelImgConfig(
                python_path=python_path,
                image_dir=image_dir,
                annotation_format="voc",
            )
        return LabelImgConfig(
            python_path=python_path,
            image_dir=image_dir,
            classes_file=_required_path(
                self.classes_file_input, "请选择 classes.txt"
            ),
            label_dir=_required_path(self.label_dir_input, "请选择标签目录"),
            annotation_format="yolo",
        )

    def set_annotation_format(self, annotation_format: str) -> None:
        """Switch free labeling between YOLO output and same-folder VOC XML."""
        self._annotation_format = annotation_format
        is_voc = annotation_format == "voc"
        self.classes_file_label.setVisible(not is_voc)
        self.classes_file_input.setVisible(not is_voc)
        self.label_dir_label.setVisible(not is_voc)
        self.label_dir_input.setVisible(not is_voc)
        if is_voc:
            self.mode_note.setText(
                "VOC 标注只选择图片目录，LabelImg 保存 Pascal VOC XML，XML 写在图片同级。"
            )
            self.yolo_mode_button.setObjectName("tabButton")
            self.voc_mode_button.setObjectName("tabButtonActive")
        else:
            self.mode_note.setText(
                "YOLO 标注需要图片目录、非空 classes.txt 和标签输出目录，LabelImg 保存 txt 标签。"
            )
            self.yolo_mode_button.setObjectName("tabButtonActive")
            self.voc_mode_button.setObjectName("tabButton")
        for button in (self.yolo_mode_button, self.voc_mode_button):
            button.style().unpolish(button)
            button.style().polish(button)

    def load_runs(self) -> None:
        """Load inference runs into the review list."""
        self._request_load_runs(continue_to_prepare=False)

    def _request_load_runs(self, *, continue_to_prepare: bool) -> None:
        """Load inference runs, optionally continuing into prepare."""
        try:
            config = ListRunsConfig(
                site_folder=_required_path(self.site_input, "请选择站点路径")
            )
        except ValueError as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self._invalidate_review_prepare()
        self.run_combo.clear()
        self.run_tree.clear()
        self.result_summary.setText("加载 run 中...")
        self._task_runner.run(
            lambda: self._inspector_worker.list_runs(config),
            lambda outcome: self._handle_runs_outcome(
                outcome, continue_to_prepare=continue_to_prepare
            ),
            lambda exc: self._show_error("加载 run 失败", str(exc)),
        )

    def _handle_validate_outcome(self, outcome: LabelImgWorkerOutcome) -> None:
        if not outcome.success or outcome.result is None:
            error = outcome.error
            details = "" if error is None else f"{error.code}: {error.message}"
            self._show_error("环境校验失败", details)
            return
        result = outcome.result
        if isinstance(result, LabelImgValidateResult):
            self.result_summary.setText(
                "预检通过：环境和输入可用"
                if result.is_valid
                else f"预检未通过：{result.error_message}"
            )
            self._set_log(
                f"[preflight] python={result.python_version}\nlabelImg={result.labelimg_version}"
            )

    def _handle_runs_outcome(
        self,
        outcome: LabelInspectorWorkerOutcome,
        *,
        continue_to_prepare: bool = False,
    ) -> None:
        if not outcome.success or outcome.result is None:
            self._show_worker_error("加载 run 失败", outcome.error)
            return
        runs = [run for run in outcome.result if isinstance(run, InferenceRun)]
        if not runs:
            self.result_summary.setText("未找到推理 run。")
            self._set_log("[empty] 没有 inference_results")
            return
        first = runs[0]
        for run in runs:
            self.run_combo.addItem(f"{run.run_id}  {run.created_at}", run.run_id)
        self.run_combo.setCurrentIndex(0)
        self.result_summary.setText(f"已加载 {len(runs)} 个 run，默认选择 {first.run_id}")
        self._set_log(
            "\n".join(f"run: {run.run_id} ({run.created_at})" for run in runs)
        )
        if continue_to_prepare:
            self._request_load_tree(continue_to_prepare=True)

    def load_tree(self) -> None:
        """Load Code/Product nodes from the selected run."""
        self._request_load_tree(continue_to_prepare=False)

    def _request_load_tree(self, *, continue_to_prepare: bool) -> None:
        """Load the run tree, optionally continuing into prepare."""
        try:
            run_id = self._current_run_id()
            if run_id is None:
                raise ValueError("请选择推理 run")
            config = GetRunTreeConfig(
                site_folder=_required_path(self.site_input, "请选择站点路径"),
                run_id=run_id,
            )
        except ValueError as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("加载目录树中...")
        self._invalidate_review_prepare()
        self.run_tree.clear()
        self._task_runner.run(
            lambda: self._inspector_worker.get_run_tree(config),
            lambda outcome: self._handle_tree_outcome(
                outcome, continue_to_prepare=continue_to_prepare
            ),
            lambda exc: self._show_error("加载目录树失败", str(exc)),
        )

    def _handle_tree_outcome(
        self,
        outcome: LabelInspectorWorkerOutcome,
        *,
        continue_to_prepare: bool = False,
    ) -> None:
        if not outcome.success or outcome.result is None:
            self._show_worker_error("加载目录树失败", outcome.error)
            return
        nodes = [node for node in outcome.result if isinstance(node, RunTreeNode)]
        if not nodes:
            self.result_summary.setText("该 run 下没有 Code/Product 标签目录。")
            self._set_log("[empty] run/labels 为空")
            return
        first = nodes[0]
        code_items: dict[str, QTreeWidgetItem] = {}
        first_product_item: QTreeWidgetItem | None = None
        for node in nodes:
            code_item = code_items.get(node.code)
            if code_item is None:
                code_item = QTreeWidgetItem([node.code])
                code_item.setToolTip(0, node.code)
                code_items[node.code] = code_item
                self.run_tree.addTopLevelItem(code_item)
            product_item = QTreeWidgetItem([node.product])
            product_item.setToolTip(
                0,
                (
                    f"{node.code}/{node.product}\n"
                    f"标签：{node.label_count}，空标签：{node.empty_count}"
                ),
            )
            product_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                (node.code, node.product),
            )
            code_item.addChild(product_item)
            if first_product_item is None:
                first_product_item = product_item
        self.run_tree.expandAll()
        if first_product_item is not None:
            self.run_tree.setCurrentItem(first_product_item)
        self.result_summary.setText(
            f"已加载 {len(nodes)} 个节点，默认选择 {first.code}/{first.product}"
        )
        self._set_log(
            "\n".join(
                f"{node.code}/{node.product}: labels={node.label_count}, empty={node.empty_count}"
                for node in nodes
            )
        )
        if continue_to_prepare:
            self.prepare_review()

    def prepare_review(self) -> None:
        """Prepare review paths and missing-label warning before launch."""
        try:
            site_folder = _required_path(self.site_input, "请选择站点路径")
            run_id = self._current_run_id()
            if run_id is None:
                self._request_load_runs(continue_to_prepare=True)
                return
            node = self._current_product_node()
            if node is None:
                if self.run_tree.topLevelItemCount() > 0:
                    raise ValueError("请选择 Code/Product 节点")
                self._request_load_tree(continue_to_prepare=True)
                return
            config = GetProductLabelsConfig(
                site_folder=site_folder,
                run_id=run_id,
                code=node[0],
                product=node[1],
            )
        except ValueError as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("准备复核中...")
        self._task_runner.run(
            lambda: self._inspector_worker.get_product_labels(config),
            self._handle_product_labels_outcome,
            lambda exc: self._show_error("准备复核失败", str(exc)),
        )

    def _handle_product_labels_outcome(
        self, outcome: LabelInspectorWorkerOutcome
    ) -> None:
        if not outcome.success or outcome.result is None:
            self._launch_after_prepare = False
            self._show_worker_error("准备复核失败", outcome.error)
            return
        labels = outcome.result
        if not labels:
            self._launch_after_prepare = False
            self.result_summary.setText("该节点没有可复核图片。")
            return
        image_dirs = {label.image_path.parent for label in labels}
        label_dirs = {label.label_path.parent for label in labels}
        if len(image_dirs) != 1 or len(label_dirs) != 1:
            self._launch_after_prepare = False
            self._show_error("准备复核失败", "该节点原图或标签目录不唯一，不能直接打开 LabelImg。")
            return
        self._prepared_labels = labels
        self._review_image_dir = next(iter(image_dirs))
        self._review_label_dir = next(iter(label_dirs))
        missing = sum(1 for label in labels if label.missing_label)
        self.result_summary.setText(
            f"复核准备完成：图片 {len(labels)}，缺少标签 {missing}。"
        )
        classes_path = _required_path(self.site_input, "请选择站点路径") / ".autolabeler" / "classes.txt"
        full_status = "\n".join(
            (
                f"图片目录：{self._review_image_dir}",
                f"标签目录：{self._review_label_dir}",
                f"classes.txt：{classes_path}",
                f"缺少标签：{missing}",
            )
        )
        self.review_status_summary.setText(
            "\n".join(
                (
                    f"图片目录：{_compact_path(self._review_image_dir)}",
                    f"标签目录：{_compact_path(self._review_label_dir)}",
                    f"classes.txt：{_compact_path(classes_path)}",
                    f"缺少标签：{missing}",
                )
            )
        )
        self.review_status_summary.setToolTip(full_status)
        self._set_log(
            "\n".join(
                (
                    "[prepared] 复核准备完成",
                    f"image_dir: {self._review_image_dir}",
                    f"label_dir: {self._review_label_dir}",
                    f"missing_labels: {missing}",
                )
            )
        )
        if self._launch_after_prepare:
            self._launch_after_prepare = False
            self.launch_review()

    def launch_review(self) -> None:
        """Launch LabelImg for prepared Flow prediction review."""
        if self._review_image_dir is None or self._review_label_dir is None:
            self._launch_after_prepare = True
            self.prepare_review()
            return
        try:
            site = _required_path(self.site_input, "请选择站点路径")
            config = LabelImgConfig(
                python_path=Path(self.python_input.text().strip() or _LABELIMG_PYTHON),
                image_dir=self._review_image_dir,
                classes_file=site / ".autolabeler" / "classes.txt",
                label_dir=self._review_label_dir,
            )
        except ValueError as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("LabelImg 启动中...")
        self._task_runner.run(
            lambda: self._labelimg_worker.launch(config),
            self._show_launch_outcome,
            lambda exc: self._show_error("LabelImg 启动失败", str(exc)),
        )

    def _invalidate_review_prepare(self) -> None:
        """Clear prepared review paths when identifying fields change."""
        self._prepared_labels = []
        self._review_image_dir = None
        self._review_label_dir = None
        if hasattr(self, "review_status_summary"):
            self.review_status_summary.setText(
                "准备后显示图片目录、标签目录、classes.txt 和缺失标签数量。"
            )
            self.review_status_summary.setToolTip("")

    def _handle_site_changed(self, *_args: object) -> None:
        """Clear review selections when the site changes."""
        self._invalidate_review_prepare()
        self.run_combo.clear()
        self.run_tree.clear()

    def _handle_run_selected(self, *_args: object) -> None:
        """Clear stale tree and prepared paths after run selection changes."""
        self._invalidate_review_prepare()
        self.run_tree.clear()

    def _handle_tree_selected(self, *_args: object) -> None:
        """Clear prepared paths after Code/Product selection changes."""
        self._invalidate_review_prepare()

    def _current_run_id(self) -> str | None:
        """Return the selected inference run id."""
        run_id = self.run_combo.currentData()
        if not run_id:
            return None
        return str(run_id)

    def _current_product_node(self) -> tuple[str, str] | None:
        """Return the selected Code/Product pair."""
        item = self.run_tree.currentItem()
        if item is None or item.parent() is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, tuple) or len(data) != 2:
            return None
        code, product = data
        if not code or not product:
            return None
        return str(code), str(product)

    def _sync_mode(self) -> None:
        is_label = self._mode == "label"
        self.free_form.setVisible(is_label)
        self.review_form.setVisible(not is_label)

    def _show_launch_outcome(self, outcome: LabelImgWorkerOutcome) -> None:
        if not outcome.success or outcome.result is None:
            self._show_worker_error("LabelImg 启动失败", outcome.error)
            return
        result = outcome.result
        if isinstance(result, LabelImgLaunchResult):
            self.result_summary.setText(f"已启动 LabelImg：PID {result.process_id}")
            self._set_log(
                f"[launched] LabelImg\npid: {result.process_id}\nmode: {self._annotation_format.upper()}"
            )

    def _show_worker_error(self, message: str, error) -> None:
        details = "" if error is None else f"{error.code}: {error.message}"
        if error is not None and error.details:
            details = f"{details} ({error.details})"
        self._show_error(message, details)

    def _show_error(self, message: str, details: str) -> None:
        text = message if not details else f"{message}：{details}"
        self.result_summary.setText(text)
        self._set_log(f"[failed] {text}")

    def _set_log(self, text: str) -> None:
        """Write the optional free-labeling log box."""
        if hasattr(self, "log_box"):
            self.log_box.setPlainText(text)


def _compact_path(path: Path, *, max_chars: int = 26) -> str:
    """Return a bounded path string for narrow review status summaries."""
    text = str(path)
    if len(text) <= max_chars:
        return text
    head = max(8, max_chars // 3)
    tail = max_chars - head - 3
    return f"{text[:head]}...{text[-tail:]}"


def _line_input(value: str = "", placeholder: str = "") -> QLineEdit:
    field = QLineEdit()
    if value:
        field.setText(value)
    if placeholder:
        field.setPlaceholderText(placeholder)
    field.setObjectName("formInput")
    return field


def _required_path(field: QLineEdit, message: str) -> Path:
    text = field.text().strip()
    if not text:
        raise ValueError(message)
    return Path(text)


def _required_text(field: QLineEdit, message: str) -> str:
    text = field.text().strip()
    if not text:
        raise ValueError(message)
    return text
