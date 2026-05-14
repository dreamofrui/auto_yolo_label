"""Dataset sampling module for YOLO training data."""

from __future__ import annotations

import math
import shutil
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from utils.exceptions import (
    AutoLabelerError,
    ErrorCode,
    PathNotFoundError,
    TaskCancelledError,
)
from utils.mapping_manager import ImageInfo, MappingManager
from utils.task_registry import TaskHandle

_VALID_MODES = {"count", "ratio", "mixed"}
_IGNORED_TXT_NAMES = {"classes.txt", "data.yaml", "readme.txt"}


@dataclass(frozen=True)
class SampleConfig:
    """Sampler input contract."""

    site_folder: Path
    output_dir: Path
    mode: str = "count"
    count: int = 40
    ratio: float = 0.3
    min_count: int = 20
    max_count: int = 50
    full_threshold: int = 35
    train_ratio: float = 0.9
    pre_labeled_priority: bool = True


@dataclass(frozen=True)
class SamplePaths:
    """YOLO dataset output paths."""

    images_train: Path
    images_val: Path
    labels_train: Path
    labels_val: Path


@dataclass(frozen=True)
class SampleStatistics:
    """Aggregate sampling counters."""

    total_products: int
    sampled_count: int
    train_count: int
    val_count: int
    pre_labeled_count: int


@dataclass(frozen=True)
class SampleResult:
    """Sampler output contract."""

    mapping_path: Path
    dataset_dir: Path
    data_yaml: Path
    paths: SamplePaths
    statistics: SampleStatistics


@dataclass(frozen=True)
class _SampleCandidate:
    """Internal sample candidate with resolved source metadata."""

    encoded_name: str
    info: ImageInfo
    source_image: Path
    label_source: str
    label_path: Path | None


@dataclass(frozen=True)
class _PlannedSample:
    """Internal selected sample with target split."""

    candidate: _SampleCandidate
    split: str


class SampleError(AutoLabelerError):
    """Base class for sampler business errors."""

    code = ErrorCode.INTERNAL_ERROR


class SampleMappingNotFoundError(SampleError):
    """Raised when mapping.json is missing."""

    code = ErrorCode.SAMPLE_MAPPING_NOT_FOUND


class SampleInvalidConfigError(SampleError):
    """Raised when sample configuration is invalid."""

    code = ErrorCode.SAMPLE_INVALID_CONFIG


class SampleXmlConvertError(SampleError):
    """Raised when pre-existing XML labels cannot be converted."""

    code = ErrorCode.SAMPLE_XML_CONVERT


class SampleIOError(SampleError):
    """Raised when sampling cannot read or write required files."""

    code = ErrorCode.SAMPLE_IO


class Sampler:
    """Sample mapped images into a YOLO training dataset."""

    def __init__(
        self,
        mapping_manager: MappingManager | None = None,
        task_handle: TaskHandle | None = None,
    ) -> None:
        """Create a sampler with optional mapping and task dependencies.

        Args:
            mapping_manager: Optional mapping manager for tests or callers.
            task_handle: Optional task state used for progress and cancellation.
        """
        self._mapping_manager = mapping_manager
        self._task_handle = task_handle

    def sample(self, config: SampleConfig) -> SampleResult:
        """Sample images into a YOLO dataset.

        Args:
            config: Sampling configuration.

        Returns:
            Paths and statistics for the generated dataset.

        Raises:
            SampleMappingNotFoundError: If mapping.json does not exist.
            SampleInvalidConfigError: If config or mapping data is invalid.
            SampleXmlConvertError: If a selected XML label cannot be converted.
            SampleIOError: If required filesystem operations fail.
            TaskCancelledError: If the injected task requests cancellation.
        """
        self._validate_config(config)
        self._raise_if_cancelled()
        mapping_path = config.site_folder / ".autolabeler" / "mapping.json"
        manager = self._mapping_manager or MappingManager(mapping_path)
        manager.mapping_path = mapping_path
        self._load_mapping(manager, mapping_path)

        classes = manager.get_class_list()
        if not classes:
            raise SampleInvalidConfigError(
                "mapping 中没有类别信息", details=str(mapping_path)
            )

        candidates = self._build_candidates(config, manager)
        plan = self._build_plan(config, candidates)
        paths = _sample_paths(config.output_dir)
        self._ensure_output_dirs(paths)
        self._set_progress(0, len(plan), "准备抽样")

        processed: list[_PlannedSample] = []
        try:
            for index, planned in enumerate(plan, start=1):
                self._raise_if_cancelled()
                self._set_progress(
                    index - 1, len(plan), f"抽样 {planned.candidate.encoded_name}"
                )
                self._copy_planned_sample(planned, paths, classes)
                manager.mark_sampled(
                    planned.candidate.encoded_name,
                    planned.split,
                    planned.candidate.label_source,
                )
                processed.append(planned)
                self._set_progress(index, len(plan), f"已抽样 {index}/{len(plan)}")

            statistics = _statistics(
                processed, total_products=len(_group_by_product(candidates))
            )
            self._write_data_yaml(config.output_dir, classes)
            self._update_mapping_snapshot(manager, config, statistics)
            manager.save(mapping_path)
        except OSError as exc:
            logger.error("抽样文件操作失败: {}", exc)
            raise SampleIOError("抽样文件操作失败", details=str(exc)) from exc

        self._set_progress(len(plan), len(plan), "抽样完成")
        logger.info("抽样完成: {} 张图片", len(plan))
        return SampleResult(
            mapping_path=mapping_path,
            dataset_dir=config.output_dir,
            data_yaml=config.output_dir / "data.yaml",
            paths=paths,
            statistics=statistics,
        )

    def _validate_config(self, config: SampleConfig) -> None:
        """Validate public sampling configuration."""
        if not config.site_folder.exists() or not config.site_folder.is_dir():
            raise SampleInvalidConfigError(
                "站点目录无效", details=str(config.site_folder)
            )
        if config.mode not in _VALID_MODES:
            raise SampleInvalidConfigError("抽样模式无效", details=config.mode)
        if config.count < 1:
            raise SampleInvalidConfigError("count 必须 >= 1")
        if config.ratio <= 0 or config.ratio > 1:
            raise SampleInvalidConfigError("ratio 必须在 (0, 1] 范围内")
        if config.min_count < 1 or config.max_count < config.min_count:
            raise SampleInvalidConfigError("min_count / max_count 无效")
        if config.full_threshold < 1:
            raise SampleInvalidConfigError("full_threshold 必须 >= 1")
        if config.train_ratio < 0.5 or config.train_ratio > 1.0:
            raise SampleInvalidConfigError("train_ratio 必须在 [0.5, 1.0] 范围内")

    def _load_mapping(self, manager: MappingManager, mapping_path: Path) -> None:
        """Load mapping data and translate missing mapping errors."""
        try:
            manager.load()
        except PathNotFoundError as exc:
            raise SampleMappingNotFoundError(
                "mapping.json 不存在", details=str(mapping_path)
            ) from exc

    def _build_candidates(
        self,
        config: SampleConfig,
        manager: MappingManager,
    ) -> list[_SampleCandidate]:
        """Resolve unsampled mapping images to source files and label metadata."""
        mapped_images = manager.get_unsampled_images()
        candidates: list[_SampleCandidate] = []
        for mapped in mapped_images:
            self._raise_if_cancelled()
            source_image = config.site_folder / Path(mapped.info.original_relative)
            if not source_image.exists():
                raise SampleIOError("源图片不存在", details=str(source_image))
            label_source, label_path = _detect_label(source_image)
            candidates.append(
                _SampleCandidate(
                    encoded_name=mapped.encoded_name,
                    info=mapped.info,
                    source_image=source_image,
                    label_source=label_source,
                    label_path=label_path,
                )
            )
        return candidates

    def _build_plan(
        self, config: SampleConfig, candidates: list[_SampleCandidate]
    ) -> list[_PlannedSample]:
        """Select candidates and assign train/val splits."""
        selected_by_code: dict[str, list[_SampleCandidate]] = {}
        for product_candidates in _group_by_product(candidates).values():
            ordered = _ordered_candidates(
                product_candidates, config.pre_labeled_priority
            )
            count = _target_count(config, len(ordered))
            for candidate in ordered[:count]:
                selected_by_code.setdefault(candidate.info.code, []).append(candidate)

        plan: list[_PlannedSample] = []
        for code in sorted(selected_by_code):
            code_candidates = sorted(
                selected_by_code[code], key=lambda candidate: candidate.encoded_name
            )
            train_count = _train_count(len(code_candidates), config.train_ratio)
            for index, candidate in enumerate(code_candidates):
                split = "train" if index < train_count else "val"
                plan.append(_PlannedSample(candidate=candidate, split=split))
        return plan

    def _ensure_output_dirs(self, paths: SamplePaths) -> None:
        """Create the YOLO output directory tree."""
        for path in (
            paths.images_train,
            paths.images_val,
            paths.labels_train,
            paths.labels_val,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def _copy_planned_sample(
        self,
        planned: _PlannedSample,
        paths: SamplePaths,
        classes: list[str],
    ) -> None:
        """Copy one image and optional label into the target split."""
        candidate = planned.candidate
        image_dir = paths.images_train if planned.split == "train" else paths.images_val
        label_dir = paths.labels_train if planned.split == "train" else paths.labels_val
        shutil.copy2(candidate.source_image, image_dir / candidate.encoded_name)

        if candidate.label_path is None:
            return
        label_output = label_dir / f"{Path(candidate.encoded_name).stem}.txt"
        if candidate.label_source == "pre_existing_txt":
            shutil.copy2(candidate.label_path, label_output)
            return
        if candidate.label_source == "pre_existing_xml":
            _xml_to_yolo_txt(candidate.label_path, label_output, classes)

    def _write_data_yaml(self, dataset_dir: Path, classes: list[str]) -> None:
        """Write the YOLO data.yaml file."""
        dataset_dir.mkdir(parents=True, exist_ok=True)
        content = "\n".join(
            (
                f"path: {dataset_dir.resolve()}",
                "train: images/train",
                "val: images/val",
                f"nc: {len(classes)}",
                f"names: [{', '.join(classes)}]",
                "",
            )
        )
        (dataset_dir / "data.yaml").write_text(content, encoding="utf-8")

    def _update_mapping_snapshot(
        self,
        manager: MappingManager,
        config: SampleConfig,
        statistics: SampleStatistics,
    ) -> None:
        """Write sampler config and statistics into MappingData."""
        manager.data.config.update(
            {
                "sample_mode": config.mode,
                "sample_count": config.count,
                "sample_ratio": config.ratio,
                "sample_min_count": config.min_count,
                "sample_max_count": config.max_count,
                "full_threshold": config.full_threshold,
                "train_ratio": config.train_ratio,
                "pre_labeled_priority": config.pre_labeled_priority,
            }
        )
        manager.data.statistics.update(
            {
                "sample_total_products": statistics.total_products,
                "sampled_count": statistics.sampled_count,
                "sample_train_count": statistics.train_count,
                "sample_val_count": statistics.val_count,
                "sample_pre_labeled_count": statistics.pre_labeled_count,
            }
        )

    def _raise_if_cancelled(self) -> None:
        """Raise TaskCancelledError when the injected task has been cancelled."""
        if self._task_handle is not None and self._task_handle.is_cancel_requested:
            logger.warning("抽样任务已取消")
            raise TaskCancelledError("抽样任务已取消")

    def _set_progress(self, current: int, total: int, message: str) -> None:
        """Update task progress fields when a task handle is available."""
        if self._task_handle is None:
            return
        self._task_handle.progress_current = current
        self._task_handle.progress_total = total
        self._task_handle.progress_message = message


def _sample_paths(dataset_dir: Path) -> SamplePaths:
    """Build standard YOLO dataset paths."""
    return SamplePaths(
        images_train=dataset_dir / "images" / "train",
        images_val=dataset_dir / "images" / "val",
        labels_train=dataset_dir / "labels" / "train",
        labels_val=dataset_dir / "labels" / "val",
    )


def _detect_label(image_path: Path) -> tuple[str, Path | None]:
    """Return pre-existing label source and path for an image."""
    xml_path = image_path.with_suffix(".xml")
    if _non_empty_file(xml_path):
        return "pre_existing_xml", xml_path
    txt_path = image_path.with_suffix(".txt")
    if txt_path.name.lower() not in _IGNORED_TXT_NAMES and _non_empty_file(txt_path):
        return "pre_existing_txt", txt_path
    return "none", None


def _non_empty_file(path: Path) -> bool:
    """Return whether a path is a non-empty regular file."""
    return path.is_file() and bool(path.read_text(encoding="utf-8").strip())


def _group_by_product(
    candidates: list[_SampleCandidate],
) -> dict[tuple[str, str], list[_SampleCandidate]]:
    """Group sample candidates by Code/Product."""
    grouped: dict[tuple[str, str], list[_SampleCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault((candidate.info.code, candidate.info.product), []).append(
            candidate
        )
    return grouped


def _ordered_candidates(
    candidates: list[_SampleCandidate], pre_labeled_priority: bool
) -> list[_SampleCandidate]:
    """Return stable candidate ordering with optional pre-labeled priority."""
    priority = {"pre_existing_xml": 0, "pre_existing_txt": 1, "none": 2}
    if pre_labeled_priority:
        return sorted(
            candidates,
            key=lambda candidate: (
                priority[candidate.label_source],
                candidate.encoded_name,
            ),
        )
    return sorted(candidates, key=lambda candidate: candidate.encoded_name)


def _target_count(config: SampleConfig, total: int) -> int:
    """Calculate per-product sample count."""
    if total == 0:
        return 0
    if config.mode == "count":
        target = max(config.count, config.full_threshold)
        return total if total <= target else target
    if total <= config.full_threshold:
        return total
    if config.mode == "ratio":
        return max(1, int(total * config.ratio))
    ratio_count = int(total * config.ratio)
    return min(total, max(config.min_count, min(config.max_count, ratio_count)))


def _train_count(total: int, train_ratio: float) -> int:
    """Calculate train count while preserving a val sample when possible."""
    if total <= 1:
        return total
    return max(1, min(total - 1, math.floor(total * train_ratio)))


def _statistics(plan: list[_PlannedSample], total_products: int) -> SampleStatistics:
    """Build aggregate sampling statistics."""
    return SampleStatistics(
        total_products=total_products,
        sampled_count=len(plan),
        train_count=sum(1 for item in plan if item.split == "train"),
        val_count=sum(1 for item in plan if item.split == "val"),
        pre_labeled_count=sum(
            1 for item in plan if item.candidate.label_source != "none"
        ),
    )


def _xml_to_yolo_txt(xml_path: Path, output_path: Path, classes: list[str]) -> None:
    """Convert a minimal VOC XML file into a YOLO TXT label."""
    try:
        root = ElementTree.parse(xml_path).getroot()
        width = _positive_float(root.findtext("size/width"), "width", xml_path)
        height = _positive_float(root.findtext("size/height"), "height", xml_path)
        lines = [
            _object_to_yolo_line(obj, classes, width, height, xml_path)
            for obj in root.findall("object")
        ]
    except (ElementTree.ParseError, ValueError) as exc:
        raise SampleXmlConvertError("XML 标签转换失败", details=str(xml_path)) from exc
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def _object_to_yolo_line(
    obj: ElementTree.Element,
    classes: list[str],
    width: float,
    height: float,
    xml_path: Path,
) -> str:
    """Convert one VOC object element to a YOLO label line."""
    class_name = (obj.findtext("name") or "").strip()
    if class_name not in classes:
        raise ValueError(f"{xml_path}: unknown class {class_name}")
    class_id = classes.index(class_name)
    xmin = _float_text(obj.findtext("bndbox/xmin"), "xmin", xml_path)
    ymin = _float_text(obj.findtext("bndbox/ymin"), "ymin", xml_path)
    xmax = _float_text(obj.findtext("bndbox/xmax"), "xmax", xml_path)
    ymax = _float_text(obj.findtext("bndbox/ymax"), "ymax", xml_path)
    if xmax <= xmin or ymax <= ymin:
        raise ValueError(f"{xml_path}: invalid bbox")
    x_center = ((xmin + xmax) / 2) / width
    y_center = ((ymin + ymax) / 2) / height
    box_width = (xmax - xmin) / width
    box_height = (ymax - ymin) / height
    return f"{class_id} {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}"


def _positive_float(text: str | None, field_name: str, xml_path: Path) -> float:
    """Parse a positive float XML field."""
    value = _float_text(text, field_name, xml_path)
    if value <= 0:
        raise ValueError(f"{xml_path}: {field_name} must be positive")
    return value


def _float_text(text: str | None, field_name: str, xml_path: Path) -> float:
    """Parse a required float XML field."""
    if text is None or not text.strip():
        raise ValueError(f"{xml_path}: missing {field_name}")
    return float(text)
