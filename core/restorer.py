"""Restore YOLO label files as VOC XML beside matching source images."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeAlias

from loguru import logger
from PIL import Image

from core.annotation_formats import parse_yolo_label_text, yolo_boxes_to_voc_xml
from utils.exceptions import (
    AutoLabelerError,
    ErrorCode,
    PathNotFoundError,
    TaskCancelledError,
)
from utils.mapping_manager import ImageInfo, MappedImage, MappingManager
from utils.task_registry import TaskHandle

_VALID_SOURCE_TYPES = frozenset({"database", "inference"})
_CONTROL_FILE_NAMES = frozenset({"classes.txt", "data.yaml", "readme.txt"})
_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp")


@dataclass(frozen=True)
class RestoreConfig:
    """Configuration for flow-mode label restore."""

    site_folder: Path
    source_type: str
    database_dir: Path | None = None
    inference_run_dir: Path | None = None
    run_id: str | None = None
    overwrite: bool = False


@dataclass(frozen=True)
class IndependentRestoreConfig:
    """Configuration for independent label restore."""

    image_root: Path
    label_root: Path
    overwrite: bool = False
    classes_file: Path | None = None


@dataclass(frozen=True)
class RestoreFileIssue:
    """One per-file restore failure."""

    source_path: Path
    target_path: Path | None
    reason: str


RestoreError: TypeAlias = RestoreFileIssue


@dataclass
class RestoreResult:
    """Aggregate restore result counters."""

    total: int
    success: int
    skipped: int
    failed: int
    errors: list[RestoreFileIssue] = field(default_factory=list)


@dataclass(frozen=True)
class RestorePreflightIssue:
    """One restore preflight warning or blocker for desktop UI."""

    severity: str
    code: str
    message: str
    detail: str


@dataclass(frozen=True)
class RestorePreflightResult:
    """Non-writing restore impact summary."""

    mode: str
    can_execute: bool
    total_labels: int
    matched_images: int
    xml_to_write: int
    classes_path: Path
    target_folders: list[Path]
    issues: list[RestorePreflightIssue] = field(default_factory=list)


@dataclass(frozen=True)
class _RestoreTarget:
    """One source label and its resolved target."""

    source_path: Path
    target_path: Path | None
    encoded_name: str | None
    info: ImageInfo | None


@dataclass(frozen=True)
class _RestoreWrite:
    """Prepared XML payload ready to be written."""

    source_path: Path
    target_path: Path
    encoded_name: str | None
    xml_text: str


class RestorerError(AutoLabelerError):
    """Base class for restorer business errors."""

    code = ErrorCode.INTERNAL_ERROR


class RestoreSourceNotFoundError(RestorerError):
    """Raised when restore source data is missing or unusable."""

    code = ErrorCode.RESTORE_SOURCE_NOT_FOUND


class RestoreMappingNotFoundError(RestorerError):
    """Raised when mapping.json cannot be loaded."""

    code = ErrorCode.RESTORE_MAPPING_NOT_FOUND


class RestoreInvalidSourceTypeError(RestorerError):
    """Raised when source_type is not supported."""

    code = ErrorCode.RESTORE_INVALID_SOURCE_TYPE


class Restorer:
    """Restore reviewed labels from datasets or inference runs."""

    def __init__(
        self,
        mapping_manager: MappingManager | None = None,
        task_handle: TaskHandle | None = None,
    ) -> None:
        """Create a restorer with optional mapping and task dependencies."""
        self._mapping_manager = mapping_manager
        self._task_handle = task_handle

    def restore(self, config: RestoreConfig) -> RestoreResult:
        """Restore flow-mode YOLO labels as VOC XML beside original images."""
        if config.source_type not in _VALID_SOURCE_TYPES:
            raise RestoreInvalidSourceTypeError(
                "Restore source type is invalid", details=config.source_type
            )
        manager = self._load_mapping(config.site_folder)
        source_root = self._resolve_source_root(config)
        self._raise_if_cancelled()

        source_paths = _source_label_files(source_root, config.source_type)
        classes = _load_classes(source_root, _flow_classes_path(config))
        self._set_progress(0, len(source_paths), "Preparing restore")
        targets = [
            self._resolve_target(source_path, source_root, config, manager)
            for source_path in source_paths
        ]
        writes = _preflight_restore_targets(targets, classes, config.overwrite)

        result = RestoreResult(total=len(source_paths), success=0, skipped=0, failed=0)
        created_targets: list[Path] = []
        try:
            for index, write in enumerate(writes, start=1):
                self._raise_if_cancelled()
                existed_before = write.target_path.exists()
                _write_xml_text(write.target_path, write.xml_text)
                if not existed_before:
                    created_targets.append(write.target_path)
                if write.encoded_name is not None:
                    manager.mark_restored(write.encoded_name)
                result.success += 1
                self._set_progress(
                    index,
                    len(source_paths),
                    f"Restored {index}/{len(source_paths)}",
                )
        except AutoLabelerError:
            _rollback_created_xml(created_targets)
            raise

        if writes:
            manager.save(config.site_folder / ".autolabeler" / "mapping.json")
        self._set_progress(len(source_paths), len(source_paths), "Restore complete")
        return result

    def preflight(self, config: RestoreConfig) -> RestorePreflightResult:
        """Return Flow restore impact without writing XML or changing mapping."""
        if config.source_type not in _VALID_SOURCE_TYPES:
            raise RestoreInvalidSourceTypeError(
                "Restore source type is invalid", details=config.source_type
            )
        manager = self._load_mapping(config.site_folder)
        source_root = self._resolve_source_root(config)
        source_paths = _source_label_files(source_root, config.source_type)
        classes_path = _find_classes_path(source_root, _flow_classes_path(config))
        classes = _load_classes_from_path(classes_path)
        targets = [
            self._resolve_target(source_path, source_root, config, manager)
            for source_path in source_paths
        ]
        writes = _preflight_restore_targets(targets, classes, config.overwrite)
        return _preflight_result(
            mode=f"flow-{config.source_type}",
            total_labels=len(source_paths),
            classes_path=classes_path,
            writes=writes,
        )

    def restore_independent(self, config: IndependentRestoreConfig) -> RestoreResult:
        """Restore independent YOLO labels as VOC XML beside matching images."""
        image_root = config.image_root
        label_root = config.label_root
        if not image_root.exists() or not image_root.is_dir():
            raise RestoreSourceNotFoundError(
                "image_root does not exist", details=str(image_root)
            )
        if not label_root.exists() or not label_root.is_dir():
            raise RestoreSourceNotFoundError(
                "label_root does not exist", details=str(label_root)
            )

        classes = _load_classes(label_root, config.classes_file, prefer_extra=True)
        source_paths = _source_label_files(label_root, "independent")
        self._set_progress(0, len(source_paths), "Preparing restore")
        targets = [
            _independent_target(source_path, label_root, image_root)
            for source_path in source_paths
        ]
        writes = _preflight_restore_targets(targets, classes, config.overwrite)

        result = RestoreResult(total=len(source_paths), success=0, skipped=0, failed=0)
        created_targets: list[Path] = []
        try:
            for index, write in enumerate(writes, start=1):
                self._raise_if_cancelled()
                existed_before = write.target_path.exists()
                _write_xml_text(write.target_path, write.xml_text)
                if not existed_before:
                    created_targets.append(write.target_path)
                result.success += 1
                self._set_progress(
                    index,
                    len(source_paths),
                    f"Restored {index}/{len(source_paths)}",
                )
        except AutoLabelerError:
            _rollback_created_xml(created_targets)
            raise
        return result

    def preflight_independent(
        self, config: IndependentRestoreConfig
    ) -> RestorePreflightResult:
        """Return Independent restore impact without writing XML."""
        image_root = config.image_root
        label_root = config.label_root
        if not image_root.exists() or not image_root.is_dir():
            raise RestoreSourceNotFoundError(
                "image_root does not exist", details=str(image_root)
            )
        if not label_root.exists() or not label_root.is_dir():
            raise RestoreSourceNotFoundError(
                "label_root does not exist", details=str(label_root)
            )

        classes_path = _find_classes_path(
            label_root, config.classes_file, prefer_extra=True
        )
        classes = _load_classes_from_path(classes_path)
        source_paths = _source_label_files(label_root, "independent")
        targets = [
            _independent_target(source_path, label_root, image_root)
            for source_path in source_paths
        ]
        writes = _preflight_restore_targets(targets, classes, config.overwrite)
        return _preflight_result(
            mode="independent",
            total_labels=len(source_paths),
            classes_path=classes_path,
            writes=writes,
        )

    def _load_mapping(self, site_folder: Path) -> MappingManager:
        """Load mapping data using MappingManager."""
        mapping_path = site_folder / ".autolabeler" / "mapping.json"
        manager = self._mapping_manager or MappingManager(mapping_path)
        manager.mapping_path = mapping_path
        try:
            return manager.load()
        except PathNotFoundError as exc:
            raise RestoreMappingNotFoundError(
                "mapping.json does not exist", details=str(mapping_path)
            ) from exc

    def _resolve_source_root(self, config: RestoreConfig) -> Path:
        """Resolve and validate the source directory."""
        if config.source_type == "database":
            if config.database_dir is None:
                raise RestoreSourceNotFoundError("database_dir is required")
            source_root = config.database_dir
        else:
            source_root = _inference_source_root(config)
        if not source_root.exists() or not source_root.is_dir():
            raise RestoreSourceNotFoundError(
                "Restore source directory does not exist", details=str(source_root)
            )
        return source_root

    def _resolve_target(
        self,
        source_path: Path,
        source_root: Path,
        config: RestoreConfig,
        manager: MappingManager,
    ) -> _RestoreTarget:
        """Resolve one source label to a mapping entry and target path."""
        if config.source_type == "database":
            return _database_target(source_path, config.site_folder, manager)
        return _inference_target(source_path, source_root, config.site_folder, manager)

    def _raise_if_cancelled(self) -> None:
        """Raise TaskCancelledError when the injected task has been cancelled."""
        if self._task_handle is not None and self._task_handle.is_cancel_requested:
            logger.warning("Restore task was cancelled")
            raise TaskCancelledError("Restore task was cancelled")

    def _set_progress(self, current: int, total: int, message: str) -> None:
        """Update task progress fields when a task handle is available."""
        if self._task_handle is None:
            return
        self._task_handle.progress_current = current
        self._task_handle.progress_total = total
        self._task_handle.progress_message = message


def _inference_source_root(config: RestoreConfig) -> Path:
    """Resolve inference label root from explicit run directory or run id."""
    if config.inference_run_dir is not None:
        return config.inference_run_dir / "labels"
    if config.run_id is None:
        raise RestoreSourceNotFoundError("run_id or inference_run_dir is required")
    return (
        config.site_folder
        / ".autolabeler"
        / "inference_results"
        / config.run_id
        / "labels"
    )


def _source_label_files(source_root: Path, source_type: str) -> list[Path]:
    """Collect source label TXT files after filtering control files."""
    if source_type == "database":
        roots = (source_root / "labels" / "train", source_root / "labels" / "val")
        return sorted(
            path
            for root in roots
            if root.exists() and root.is_dir()
            for path in root.glob("*.txt")
            if _is_label_file(path)
        )
    return sorted(path for path in source_root.rglob("*.txt") if _is_label_file(path))


def _is_label_file(path: Path) -> bool:
    """Return whether path is a non-control TXT file."""
    return path.is_file() and path.name.lower() not in _CONTROL_FILE_NAMES


def _database_target(
    source_path: Path, site_folder: Path, manager: MappingManager
) -> _RestoreTarget:
    """Resolve a dataset label path to a mapping entry."""
    encoded_name = f"{source_path.stem}{_image_suffix_for_stem(source_path.stem, manager)}"
    info = manager.get_image_info(encoded_name)
    if info is None:
        return _RestoreTarget(
            source_path=source_path, target_path=None, encoded_name=None, info=None
        )
    return _RestoreTarget(
        source_path=source_path,
        target_path=site_folder / Path(info.original_relative).with_suffix(".xml"),
        encoded_name=encoded_name,
        info=info,
    )


def _image_suffix_for_stem(encoded_stem: str, manager: MappingManager) -> str:
    """Find the original image suffix for a flattened dataset label stem."""
    for mapped in _all_mapped_images(manager):
        if Path(mapped.encoded_name).stem == encoded_stem:
            return Path(mapped.encoded_name).suffix
    return ""


def _inference_target(
    source_path: Path,
    source_root: Path,
    site_folder: Path,
    manager: MappingManager,
) -> _RestoreTarget:
    """Resolve an inference label path to a mapping entry."""
    try:
        relative = source_path.relative_to(source_root)
    except ValueError:
        return _RestoreTarget(
            source_path=source_path, target_path=None, encoded_name=None, info=None
        )
    parts = relative.parts
    if len(parts) < 3:
        return _RestoreTarget(
            source_path=source_path, target_path=None, encoded_name=None, info=None
        )
    code = parts[0]
    product = parts[1]
    stem = source_path.stem
    for mapped in _all_mapped_images(manager):
        info = mapped.info
        if (
            info.code == code
            and info.product == product
            and Path(info.original_name).stem == stem
        ):
            return _RestoreTarget(
                source_path=source_path,
                target_path=site_folder
                / Path(info.original_relative).with_suffix(".xml"),
                encoded_name=mapped.encoded_name,
                info=info,
            )
    return _RestoreTarget(
        source_path=source_path, target_path=None, encoded_name=None, info=None
    )


def _all_mapped_images(manager: MappingManager) -> list[MappedImage]:
    """Return all mapped images through public MappingManager queries."""
    return sorted(
        manager.get_sampled_images() + manager.get_unsampled_images(),
        key=lambda mapped: mapped.encoded_name,
    )


def _flow_classes_path(config: RestoreConfig) -> Path | None:
    """Return the flow-mode classes file candidate for inference restore."""
    if config.source_type != "inference":
        return None
    return config.site_folder / ".autolabeler" / "classes.txt"


def _load_classes(
    source_root: Path,
    extra_classes_file: Path | None = None,
    *,
    prefer_extra: bool = False,
) -> list[str]:
    """Load non-empty classes.txt from a dataset, run, or labels directory."""
    return _load_classes_from_path(
        _find_classes_path(
            source_root,
            extra_classes_file,
            prefer_extra=prefer_extra,
        )
    )


def _find_classes_path(
    source_root: Path,
    extra_classes_file: Path | None = None,
    *,
    prefer_extra: bool = False,
) -> Path:
    """Return the first non-empty classes.txt candidate."""
    if prefer_extra and extra_classes_file is not None:
        if extra_classes_file.exists() and extra_classes_file.is_file():
            if _load_classes_from_path(extra_classes_file):
                return extra_classes_file
        raise RestoreSourceNotFoundError(
            "classes.txt is missing or empty", details=str(extra_classes_file)
        )

    candidates = [
        source_root / "classes.txt",
        source_root.parent / "classes.txt",
    ]
    if extra_classes_file is not None:
        candidates.append(extra_classes_file)
    for path in candidates:
        if path.exists() and path.is_file():
            if _load_classes_from_path(path):
                return path
    raise RestoreSourceNotFoundError(
        "classes.txt is missing or empty", details=str(source_root)
    )


def _load_classes_from_path(path: Path) -> list[str]:
    """Read non-empty class names from one classes.txt file."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _independent_target(
    source_path: Path, label_root: Path, image_root: Path
) -> _RestoreTarget:
    """Resolve an independent label path to a same-relative image XML target."""
    relative = source_path.relative_to(label_root)
    image_matches = [
        image_root / relative.with_suffix(suffix)
        for suffix in _IMAGE_SUFFIXES
        if (image_root / relative.with_suffix(suffix)).exists()
    ]
    if len(image_matches) != 1:
        return _RestoreTarget(
            source_path=source_path, target_path=None, encoded_name=None, info=None
        )
    return _RestoreTarget(
        source_path=source_path,
        target_path=image_matches[0].with_suffix(".xml"),
        encoded_name=None,
        info=None,
    )


def _preflight_restore_targets(
    targets: list[_RestoreTarget], classes: list[str], overwrite: bool
) -> list[_RestoreWrite]:
    """Validate restore targets and build XML before any output write."""
    writes: list[_RestoreWrite] = []
    seen_targets: set[Path] = set()
    for target in targets:
        if target.target_path is None:
            raise RestoreSourceNotFoundError(
                "Label does not match exactly one image",
                details=str(target.source_path),
            )
        if target.target_path in seen_targets:
            raise RestoreSourceNotFoundError(
                "Multiple labels target the same XML",
                details=str(target.target_path),
            )
        seen_targets.add(target.target_path)
        if target.target_path.exists() and not overwrite:
            raise RestoreSourceNotFoundError(
                "Target XML already exists", details=str(target.target_path)
            )
        xml_text = _restore_xml_text(target.source_path, target.target_path, classes)
        writes.append(
            _RestoreWrite(
                source_path=target.source_path,
                target_path=target.target_path,
                encoded_name=target.encoded_name,
                xml_text=xml_text,
            )
        )
    return writes


def _restore_xml_text(source_path: Path, target_path: Path, classes: list[str]) -> str:
    """Convert one YOLO label file to VOC XML text without writing it."""
    image_path = _image_path_for_xml_target(target_path)
    try:
        with Image.open(image_path) as image:
            image_size = image.size
    except OSError as exc:
        raise RestoreSourceNotFoundError(
            "Matched image cannot be read", details=str(image_path)
        ) from exc
    try:
        label_text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RestoreSourceNotFoundError(
            "Label file cannot be read", details=str(source_path)
        ) from exc
    boxes = parse_yolo_label_text(label_text, classes)
    return yolo_boxes_to_voc_xml(
        filename=image_path.name,
        image_size=image_size,
        boxes=boxes,
        classes=classes,
        folder=image_path.parent.name,
        path=str(image_path.resolve()),
    )


def _image_path_for_xml_target(xml_path: Path) -> Path:
    """Find the exact same-stem image beside a target XML path."""
    matches = [
        xml_path.with_suffix(suffix)
        for suffix in _IMAGE_SUFFIXES
        if xml_path.with_suffix(suffix).exists()
    ]
    if len(matches) != 1:
        raise RestoreSourceNotFoundError(
            "Matched image does not exist or is ambiguous", details=str(xml_path)
        )
    return matches[0]


def _write_xml_text(target_path: Path, xml_text: str) -> None:
    """Write prepared XML text to disk."""
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(xml_text, encoding="utf-8")
    except OSError as exc:
        raise RestoreSourceNotFoundError(
            "Restored XML cannot be written", details=str(target_path)
        ) from exc


def _rollback_created_xml(paths: list[Path]) -> None:
    """Remove XML files created during a failed restore attempt."""
    for path in reversed(paths):
        try:
            if path.exists():
                path.unlink()
        except OSError:
            logger.warning("Failed to rollback restored XML: {}", path)


def _preflight_result(
    mode: str,
    total_labels: int,
    classes_path: Path,
    writes: list[_RestoreWrite],
) -> RestorePreflightResult:
    """Build a desktop-friendly restore preflight summary."""
    return RestorePreflightResult(
        mode=mode,
        can_execute=True,
        total_labels=total_labels,
        matched_images=len(writes),
        xml_to_write=len(writes),
        classes_path=classes_path,
        target_folders=sorted({write.target_path.parent for write in writes}),
    )
