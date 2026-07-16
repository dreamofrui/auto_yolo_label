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
_VALID_INDEPENDENT_OUTPUT_FORMATS = {"xml", "yolo"}
_IGNORED_TXT_NAMES = {"classes.txt", "data.yaml", "readme.txt"}
_SUPPORTED_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp")


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
    overwrite_output: bool = False


@dataclass(frozen=True)
class IndependentSampleConfig:
    """Standalone sampler input contract without mapping."""

    source_dir: Path
    output_dir: Path
    output_format: str = "xml"
    mode: str = "count"
    count: int = 40
    ratio: float = 0.3
    min_count: int = 20
    max_count: int = 50
    full_threshold: int = 35
    train_ratio: float = 0.9
    classes: list[str] | None = None
    pre_labeled_priority: bool = True
    overwrite_output: bool = False


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

    mapping_path: Path | None
    dataset_dir: Path
    data_yaml: Path
    paths: SamplePaths
    statistics: SampleStatistics
    output_format: str = "yolo"


@dataclass(frozen=True)
class SamplePreflightIssue:
    """One preflight issue for the desktop UI."""

    severity: str
    code: str
    message: str
    detail: str


@dataclass(frozen=True)
class SamplePreflightResult:
    """Preflight estimate and risk summary."""

    mode: str
    output_format: str
    can_execute: bool
    output_dir: Path
    statistics: SampleStatistics
    total_groups: int
    copy_count: int
    move_count: int
    issues: list[SamplePreflightIssue]


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


@dataclass(frozen=True)
class _IndependentSampleCandidate:
    """Internal standalone sample candidate."""

    source_image: Path
    relative_image_path: Path
    group_dir: Path
    label_source: str
    label_path: Path | None


@dataclass(frozen=True)
class _PlannedIndependentSample:
    """Internal standalone selected sample with target split."""

    candidate: _IndependentSampleCandidate
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

    def preflight(self, config: SampleConfig) -> SamplePreflightResult:
        """Return Flow sampling estimates and risks without writing files."""
        issues = _output_dir_issues(config.output_dir, config.overwrite_output)
        self._validate_config(config)
        mapping_path = config.site_folder / ".autolabeler" / "mapping.json"
        manager = self._mapping_manager or MappingManager(mapping_path)
        manager.mapping_path = mapping_path
        self._load_mapping(manager, mapping_path)
        classes = manager.get_class_list()
        if not classes:
            raise SampleInvalidConfigError(
                "mapping has no class information", details=str(mapping_path)
            )
        candidates = self._build_candidates(config, manager)
        plan = self._build_plan(config, candidates)
        issues.extend(_mapped_plan_issues(plan, classes))
        statistics = _statistics(plan, total_products=len(_group_by_product(candidates)))
        return SamplePreflightResult(
            mode="flow",
            output_format="yolo",
            can_execute=not _has_blockers(issues),
            output_dir=config.output_dir,
            statistics=statistics,
            total_groups=len(_group_by_product(candidates)),
            copy_count=len(plan),
            move_count=0,
            issues=issues,
        )

    def preflight_independent(
        self, config: IndependentSampleConfig
    ) -> SamplePreflightResult:
        """Return Independent sampling estimates and risks without moving files."""
        issues = _output_dir_issues(config.output_dir, config.overwrite_output)
        self._validate_independent_config(config)
        candidates = _independent_candidates(config.source_dir)
        plan = self._build_independent_plan(config, candidates)
        issues.extend(_independent_plan_issues(plan, config.output_format))
        if config.output_format == "yolo" and not config.classes:
            issues.append(
                SamplePreflightIssue(
                    severity="warning",
                    code="EMPTY_CLASSES",
                    message="classes.txt will be empty until the user fills classes",
                    detail=str(config.output_dir / "classes.txt"),
                )
            )
        statistics = _independent_statistics(
            plan,
            total_products=len(_group_independent(candidates)),
            output_format=config.output_format,
        )
        return SamplePreflightResult(
            mode="independent",
            output_format=config.output_format,
            can_execute=not _has_blockers(issues),
            output_dir=config.output_dir,
            statistics=statistics,
            total_groups=len(_group_independent(candidates)),
            copy_count=0,
            move_count=len(plan),
            issues=issues,
        )

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
                "mapping has no class information", details=str(mapping_path)
            )

        _validate_output_dir(config.output_dir, config.overwrite_output)
        candidates = self._build_candidates(config, manager)
        plan = self._build_plan(config, candidates)
        self._preflight_mapped_plan(plan, classes)
        if config.output_dir.exists() and config.overwrite_output:
            shutil.rmtree(config.output_dir)
        paths = _sample_paths(config.output_dir)
        self._ensure_output_dirs(paths)
        self._set_progress(0, len(plan), "Preparing sampling")

        processed: list[_PlannedSample] = []
        try:
            for index, planned in enumerate(plan, start=1):
                self._raise_if_cancelled()
                self._set_progress(
                    index - 1, len(plan), f"鎶芥牱 {planned.candidate.encoded_name}"
                )
                self._copy_planned_sample(planned, paths, classes)
                manager.mark_sampled(
                    planned.candidate.encoded_name,
                    planned.split,
                    planned.candidate.label_source,
                )
                processed.append(planned)
                self._set_progress(index, len(plan), f"Sampled {index}/{len(plan)}")

            statistics = _statistics(
                processed, total_products=len(_group_by_product(candidates))
            )
            self._write_dataset_metadata(config.output_dir, classes)
            self._update_mapping_snapshot(manager, config, statistics)
            manager.save(mapping_path)
        except OSError as exc:
            logger.error("sampling file operation failed: {}", exc)
            raise SampleIOError("sampling file operation failed", details=str(exc)) from exc

        self._set_progress(len(plan), len(plan), "Sampling complete")
        logger.info("sampling complete: {} images", len(plan))
        return SampleResult(
            mapping_path=mapping_path,
            dataset_dir=config.output_dir,
            data_yaml=config.output_dir / "data.yaml",
            paths=paths,
            statistics=statistics,
            output_format="yolo",
        )

    def sample_independent(
        self, config: IndependentSampleConfig
    ) -> SampleResult:
        """Sample a standalone image folder without mapping."""
        self._validate_independent_config(config)
        self._raise_if_cancelled()
        _validate_output_dir(config.output_dir, config.overwrite_output)

        candidates = _independent_candidates(config.source_dir)
        plan = self._build_independent_plan(config, candidates)
        _preflight_independent_plan(plan, config.output_format)
        if config.output_dir.exists() and config.overwrite_output:
            shutil.rmtree(config.output_dir)

        paths = (
            _sample_paths(config.output_dir)
            if config.output_format == "yolo"
            else _flat_sample_paths(config.output_dir)
        )
        if config.output_format == "yolo":
            self._ensure_output_dirs(paths)
        else:
            config.output_dir.mkdir(parents=True, exist_ok=True)
        self._set_progress(0, len(plan), "Preparing independent sampling")

        processed: list[_PlannedIndependentSample] = []
        try:
            for index, planned in enumerate(plan, start=1):
                self._raise_if_cancelled()
                self._set_progress(
                    index - 1,
                    len(plan),
                    f"Sampling {planned.candidate.source_image.name}",
                )
                if config.output_format == "yolo":
                    _move_independent_sample_to_yolo(planned, paths)
                else:
                    _move_independent_sample_to_flat_xml(planned, config.output_dir)
                processed.append(planned)
                self._set_progress(index, len(plan), f"Sampled {index}/{len(plan)}")

            statistics = _independent_statistics(
                processed,
                total_products=len(_group_independent(candidates)),
                output_format=config.output_format,
            )
            if config.output_format == "yolo":
                self._write_dataset_metadata(config.output_dir, config.classes or [])
        except OSError as exc:
            logger.error("independent sampling file operation failed: {}", exc)
            raise SampleIOError(
                "independent sampling file operation failed", details=str(exc)
            ) from exc

        self._set_progress(len(plan), len(plan), "Independent sampling complete")
        return SampleResult(
            mapping_path=None,
            dataset_dir=config.output_dir,
            data_yaml=(
                config.output_dir / "data.yaml"
                if config.output_format == "yolo"
                else config.output_dir
            ),
            paths=paths,
            statistics=statistics,
            output_format=config.output_format,
        )

    def _validate_config(self, config: SampleConfig) -> None:
        """Validate public sampling configuration."""
        if not config.site_folder.exists() or not config.site_folder.is_dir():
            raise SampleInvalidConfigError(
                "site folder is invalid", details=str(config.site_folder)
            )
        if config.mode not in _VALID_MODES:
            raise SampleInvalidConfigError("sampling mode is invalid", details=config.mode)
        if config.count < 1:
            raise SampleInvalidConfigError("count must be >= 1")
        if config.ratio <= 0 or config.ratio > 1:
            raise SampleInvalidConfigError("ratio must be in (0, 1]")
        if config.min_count < 1 or config.max_count < config.min_count:
            raise SampleInvalidConfigError("min_count / max_count is invalid")
        if config.full_threshold < 1:
            raise SampleInvalidConfigError("full_threshold must be >= 1")
        if config.train_ratio < 0.5 or config.train_ratio > 1.0:
            raise SampleInvalidConfigError("train_ratio must be in [0.5, 1.0]")

    def _validate_independent_config(self, config: IndependentSampleConfig) -> None:
        """Validate standalone sampling configuration."""
        if not config.source_dir.exists() or not config.source_dir.is_dir():
            raise SampleInvalidConfigError(
                "source_dir is invalid", details=str(config.source_dir)
            )
        if config.mode not in _VALID_MODES:
            raise SampleInvalidConfigError("sampling mode is invalid", details=config.mode)
        if config.output_format not in _VALID_INDEPENDENT_OUTPUT_FORMATS:
            raise SampleInvalidConfigError(
                "independent output format is invalid", details=config.output_format
            )
        if config.count < 1:
            raise SampleInvalidConfigError("count must be >= 1")
        if config.ratio <= 0 or config.ratio > 1:
            raise SampleInvalidConfigError("ratio must be in (0, 1]")
        if config.min_count < 1 or config.max_count < config.min_count:
            raise SampleInvalidConfigError("min_count / max_count is invalid")
        if config.full_threshold < 1:
            raise SampleInvalidConfigError("full_threshold must be >= 1")
        if config.train_ratio < 0.5 or config.train_ratio > 1.0:
            raise SampleInvalidConfigError("train_ratio must be in [0.5, 1.0]")

    def _load_mapping(self, manager: MappingManager, mapping_path: Path) -> None:
        """Load mapping data and translate missing mapping errors."""
        try:
            manager.load()
        except PathNotFoundError as exc:
            raise SampleMappingNotFoundError(
                "mapping.json does not exist", details=str(mapping_path)
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
                raise SampleIOError("婧愬浘鐗囦笉瀛樺湪", details=str(source_image))
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
        selected_by_group: dict[tuple[str, str], list[_SampleCandidate]] = {}
        for product_candidates in _group_by_product(candidates).values():
            ordered = _ordered_candidates(
                product_candidates, config.pre_labeled_priority
            )
            count = _target_count(config, ordered)
            if product_candidates:
                group_key = (
                    product_candidates[0].info.code,
                    product_candidates[0].info.product,
                )
                selected_by_group[group_key] = ordered[:count]

        plan: list[_PlannedSample] = []
        for group_key in sorted(selected_by_group):
            group_candidates = sorted(
                selected_by_group[group_key], key=lambda candidate: candidate.encoded_name
            )
            train_count = _train_count(len(group_candidates), config.train_ratio)
            for index, candidate in enumerate(group_candidates):
                split = "train" if index < train_count else "val"
                plan.append(_PlannedSample(candidate=candidate, split=split))
        return plan

    def _build_independent_plan(
        self,
        config: IndependentSampleConfig,
        candidates: list[_IndependentSampleCandidate],
    ) -> list[_PlannedIndependentSample]:
        """Select standalone candidates and assign train/val splits per folder."""
        plan: list[_PlannedIndependentSample] = []
        for group_dir, group_candidates in sorted(_group_independent(candidates).items()):
            ordered = _ordered_independent(
                group_candidates,
                config.pre_labeled_priority,
                config.output_format,
            )
            count = _target_count(
                config,
                ordered,
                reusable_label_sources=_reusable_independent_label_sources(
                    config.output_format
                ),
            )
            selected = ordered[:count]
            train_count = _train_count(len(selected), config.train_ratio)
            for index, candidate in enumerate(selected):
                split = "train" if index < train_count else "val"
                plan.append(_PlannedIndependentSample(candidate=candidate, split=split))
        return plan

    def _preflight_mapped_plan(
        self, plan: list[_PlannedSample], classes: list[str]
    ) -> None:
        """Validate selected mapped samples before output is touched."""
        for planned in plan:
            candidate = planned.candidate
            if candidate.label_path is None:
                continue
            if candidate.label_source == "invalid_empty_txt":
                raise SampleInvalidConfigError(
                    "empty TXT label requires user confirmation before deletion",
                    details=str(candidate.label_path),
                )
            if candidate.label_source == "pre_existing_xml":
                _xml_to_yolo_lines(candidate.label_path, classes)

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

    def _write_dataset_metadata(self, dataset_dir: Path, classes: list[str]) -> None:
        """Write standard YOLO classes.txt and data.yaml files."""
        dataset_dir.mkdir(parents=True, exist_ok=True)
        (dataset_dir / "classes.txt").write_text(
            "".join(f"{name}\n" for name in classes), encoding="utf-8"
        )
        names = ", ".join(_yaml_single_quote(name) for name in classes)
        content = "\n".join(
            (
                f"path: {dataset_dir.resolve()}",
                "train: images/train",
                "val: images/val",
                f"nc: {len(classes)}",
                f"names: [{names}]",
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
            logger.warning("sampling task was cancelled")
            raise TaskCancelledError("sampling task was cancelled")

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


def _flat_sample_paths(output_dir: Path) -> SamplePaths:
    """Build a flat labeling output path contract."""
    return SamplePaths(
        images_train=output_dir,
        images_val=output_dir,
        labels_train=output_dir,
        labels_val=output_dir,
    )


def _validate_output_dir(output_dir: Path, overwrite_output: bool) -> None:
    """Refuse non-empty output directories unless the user confirmed clearing."""
    if output_dir.exists() and not output_dir.is_dir():
        raise SampleInvalidConfigError("output path is not a directory", details=str(output_dir))
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite_output:
        raise SampleInvalidConfigError("output directory is not empty", details=str(output_dir))


def _output_dir_issues(
    output_dir: Path, overwrite_output: bool
) -> list[SamplePreflightIssue]:
    """Return output directory preflight issues without modifying it."""
    if output_dir.exists() and not output_dir.is_dir():
        return [
            SamplePreflightIssue(
                severity="blocker",
                code="OUTPUT_NOT_DIRECTORY",
                message="output path is not a directory",
                detail=str(output_dir),
            )
        ]
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite_output:
        return [
            SamplePreflightIssue(
                severity="blocker",
                code="OUTPUT_NOT_EMPTY",
                message="output directory is not empty",
                detail=str(output_dir),
            )
        ]
    return []


def _detect_label(image_path: Path) -> tuple[str, Path | None]:
    """Return pre-existing label source and path for an image."""
    txt_path = image_path.with_suffix(".txt")
    if txt_path.name.lower() not in _IGNORED_TXT_NAMES and _non_empty_file(txt_path):
        return "pre_existing_txt", txt_path
    if txt_path.is_file():
        return "invalid_empty_txt", txt_path
    xml_path = image_path.with_suffix(".xml")
    if _non_empty_file(xml_path):
        return "pre_existing_xml", xml_path
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


def _target_count(
    config: SampleConfig | IndependentSampleConfig,
    candidates: list[_SampleCandidate] | list[_IndependentSampleCandidate],
    reusable_label_sources: set[str] | None = None,
) -> int:
    """Calculate per-product sample count."""
    total = len(candidates)
    if total == 0:
        return 0
    if config.mode == "count":
        target = max(config.count, config.full_threshold)
        if reusable_label_sources is None:
            labeled = sum(
                1 for candidate in candidates if candidate.label_source != "none"
            )
        else:
            labeled = sum(
                1
                for candidate in candidates
                if candidate.label_source in reusable_label_sources
            )
        return min(total, max(target, labeled))
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


def _group_independent(
    candidates: list[_IndependentSampleCandidate],
) -> dict[Path, list[_IndependentSampleCandidate]]:
    """Group standalone candidates by the folder that directly contains images."""
    grouped: dict[Path, list[_IndependentSampleCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.group_dir, []).append(candidate)
    return grouped


def _ordered_independent(
    candidates: list[_IndependentSampleCandidate],
    pre_labeled_priority: bool,
    output_format: str,
) -> list[_IndependentSampleCandidate]:
    """Return stable standalone candidate ordering with optional label priority."""
    if output_format == "xml":
        priority = {
            "pre_existing_xml": 0,
            "pre_existing_txt": 1,
            "invalid_empty_txt": 2,
            "none": 3,
        }
    else:
        priority = {
            "pre_existing_txt": 0,
            "pre_existing_xml": 1,
            "invalid_empty_txt": 2,
            "none": 3,
        }
    if pre_labeled_priority:
        return sorted(
            candidates,
            key=lambda candidate: (
                priority[candidate.label_source],
                candidate.source_image.name,
            ),
        )
    return sorted(candidates, key=lambda candidate: candidate.source_image.name)


def _reusable_independent_label_sources(output_format: str) -> set[str]:
    """Return label sources that should be preserved over the target count."""
    if output_format == "xml":
        return {"pre_existing_xml"}
    return {"pre_existing_txt", "pre_existing_xml"}


def _independent_statistics(
    plan: list[_PlannedIndependentSample],
    total_products: int,
    output_format: str = "yolo",
) -> SampleStatistics:
    """Build aggregate standalone sampling statistics."""
    reusable_label_sources = _reusable_independent_label_sources(output_format)
    return SampleStatistics(
        total_products=total_products,
        sampled_count=len(plan),
        train_count=sum(1 for item in plan if item.split == "train"),
        val_count=sum(1 for item in plan if item.split == "val"),
        pre_labeled_count=sum(
            1
            for item in plan
            if item.candidate.label_source in reusable_label_sources
        ),
    )


def _independent_candidates(source_dir: Path) -> list[_IndependentSampleCandidate]:
    """Collect standalone images and detect ambiguous nested image folders."""
    image_paths = _image_files(source_dir)
    if not image_paths:
        raise SampleInvalidConfigError(
            "source_dir contains no supported images", details=str(source_dir)
        )
    image_dirs = {path.parent for path in image_paths}
    for image_dir in image_dirs:
        for other_dir in image_dirs:
            if image_dir != other_dir and other_dir.is_relative_to(image_dir):
                raise SampleInvalidConfigError(
                    "image folders are ambiguous; parent and child both contain images",
                    details=f"{image_dir} -> {other_dir}",
                )

    candidates: list[_IndependentSampleCandidate] = []
    for image_path in image_paths:
        label_source, label_path = _detect_label(image_path)
        candidates.append(
            _IndependentSampleCandidate(
                source_image=image_path,
                relative_image_path=image_path.relative_to(source_dir),
                group_dir=image_path.parent,
                label_source=label_source,
                label_path=label_path,
            )
        )
    return candidates


def _image_files(source_dir: Path) -> list[Path]:
    """Return supported image files under source_dir."""
    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in _SUPPORTED_IMAGE_SUFFIXES
    )


def _preflight_independent_plan(
    plan: list[_PlannedIndependentSample], output_format: str
) -> None:
    """Validate standalone selected samples before any move happens."""
    image_targets: set[str] = set()
    label_names: set[str] = set()
    for planned in plan:
        image_path = planned.candidate.source_image
        label_path = planned.candidate.label_path
        image_target = (
            planned.candidate.relative_image_path.as_posix()
            if output_format == "xml"
            else image_path.name
        )
        if image_target in image_targets:
            raise SampleInvalidConfigError(
                "selected output image filename conflicts", details=image_target
            )
        image_targets.add(image_target)
        if output_format == "xml":
            continue
        label_name = f"{image_path.stem}.txt"
        if label_name in label_names:
            raise SampleInvalidConfigError(
                "selected output label filename conflicts", details=label_name
            )
        label_names.add(label_name)
        if planned.candidate.label_source == "invalid_empty_txt":
            raise SampleInvalidConfigError(
                "empty TXT label requires user confirmation before deletion",
                details=str(label_path),
            )


def _mapped_plan_issues(
    plan: list[_PlannedSample], classes: list[str]
) -> list[SamplePreflightIssue]:
    """Return selected mapped sample issues without raising."""
    issues: list[SamplePreflightIssue] = []
    for planned in plan:
        candidate = planned.candidate
        if candidate.label_path is None:
            continue
        if candidate.label_source == "invalid_empty_txt":
            issues.append(
                SamplePreflightIssue(
                    severity="blocker",
                    code="EMPTY_TXT_LABEL",
                    message="empty TXT label requires user confirmation before deletion",
                    detail=str(candidate.label_path),
                )
            )
        if candidate.label_source == "pre_existing_xml":
            try:
                _xml_to_yolo_lines(candidate.label_path, classes)
            except SampleXmlConvertError as exc:
                issues.append(
                    SamplePreflightIssue(
                        severity="blocker",
                        code="XML_CONVERT_ERROR",
                        message=exc.message,
                        detail=exc.details,
                    )
                )
    return issues


def _independent_plan_issues(
    plan: list[_PlannedIndependentSample], output_format: str = "yolo"
) -> list[SamplePreflightIssue]:
    """Return selected independent sample issues without raising."""
    issues: list[SamplePreflightIssue] = []
    image_targets: set[str] = set()
    label_names: set[str] = set()
    for planned in plan:
        image_path = planned.candidate.source_image
        label_path = planned.candidate.label_path
        image_target = (
            planned.candidate.relative_image_path.as_posix()
            if output_format == "xml"
            else image_path.name
        )
        if image_target in image_targets:
            issues.append(
                SamplePreflightIssue(
                    severity="blocker",
                    code="IMAGE_FILENAME_CONFLICT",
                    message="selected output image filename conflicts",
                    detail=image_target,
                )
            )
        image_targets.add(image_target)
        if output_format == "yolo":
            label_name = f"{image_path.stem}.txt"
            if label_name in label_names:
                issues.append(
                    SamplePreflightIssue(
                        severity="blocker",
                        code="LABEL_FILENAME_CONFLICT",
                        message="selected output label filename conflicts",
                        detail=label_name,
                    )
                )
            label_names.add(label_name)
        if planned.candidate.label_source == "invalid_empty_txt":
            issues.append(
                SamplePreflightIssue(
                    severity="blocker" if output_format == "yolo" else "warning",
                    code="EMPTY_TXT_LABEL",
                    message=(
                        "empty TXT label requires user confirmation before deletion"
                        if output_format == "yolo"
                        else "empty TXT label will stay in the source folder"
                    ),
                    detail="" if label_path is None else str(label_path),
                )
            )
    return issues


def _has_blockers(issues: list[SamplePreflightIssue]) -> bool:
    """Return whether any issue blocks execution."""
    return any(issue.severity == "blocker" for issue in issues)


def _move_independent_sample_to_yolo(
    planned: _PlannedIndependentSample, paths: SamplePaths
) -> None:
    """Move one standalone sample and optional same-stem label into the dataset."""
    image_dir = paths.images_train if planned.split == "train" else paths.images_val
    label_dir = paths.labels_train if planned.split == "train" else paths.labels_val
    image_path = planned.candidate.source_image
    shutil.move(str(image_path), image_dir / image_path.name)
    if planned.candidate.label_path is None:
        return
    label_output = label_dir / f"{image_path.stem}.txt"
    shutil.move(str(planned.candidate.label_path), label_output)


def _move_independent_sample_to_flat_xml(
    planned: _PlannedIndependentSample, output_dir: Path
) -> None:
    """Move one standalone sample and optional XML label preserving structure."""
    image_path = planned.candidate.source_image
    image_output = output_dir / planned.candidate.relative_image_path
    image_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(image_path), image_output)
    label_path = planned.candidate.label_path
    if label_path is None or planned.candidate.label_source != "pre_existing_xml":
        return
    label_output = image_output.with_suffix(".xml")
    shutil.move(str(label_path), label_output)


def _yaml_single_quote(value: str) -> str:
    """Return a minimal single-quoted YAML scalar."""
    return "'" + value.replace("'", "''") + "'"


def _xml_to_yolo_txt(xml_path: Path, output_path: Path, classes: list[str]) -> None:
    """Convert a minimal VOC XML file into a YOLO TXT label."""
    lines = _xml_to_yolo_lines(xml_path, classes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def _xml_to_yolo_lines(xml_path: Path, classes: list[str]) -> list[str]:
    """Convert a minimal VOC XML file into YOLO label lines."""
    try:
        root = ElementTree.parse(xml_path).getroot()
        width = _positive_float(root.findtext("size/width"), "width", xml_path)
        height = _positive_float(root.findtext("size/height"), "height", xml_path)
        return [
            _object_to_yolo_line(obj, classes, width, height, xml_path)
            for obj in root.findall("object")
        ]
    except (ElementTree.ParseError, ValueError) as exc:
        raise SampleXmlConvertError(
            "XML label conversion failed", details=str(xml_path)
        ) from exc




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
