"""Restore YOLO label files back beside original images."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeAlias

from loguru import logger

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


@dataclass(frozen=True)
class RestoreConfig:
    """Configuration for restoring label files."""

    site_folder: Path
    source_type: str
    database_dir: Path | None = None
    inference_run_dir: Path | None = None
    run_id: str | None = None
    overwrite: bool = False


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
class _RestoreTarget:
    """One source label and its resolved target."""

    source_path: Path
    target_path: Path | None
    encoded_name: str | None
    info: ImageInfo | None


class RestorerError(AutoLabelerError):
    """Base class for restorer business errors."""

    code = ErrorCode.INTERNAL_ERROR


class RestoreSourceNotFoundError(RestorerError):
    """Raised when the restore source directory is missing."""

    code = ErrorCode.RESTORE_SOURCE_NOT_FOUND


class RestoreMappingNotFoundError(RestorerError):
    """Raised when mapping.json cannot be loaded."""

    code = ErrorCode.RESTORE_MAPPING_NOT_FOUND


class RestoreInvalidSourceTypeError(RestorerError):
    """Raised when source_type is not supported."""

    code = ErrorCode.RESTORE_INVALID_SOURCE_TYPE


class Restorer:
    """Restore reviewed labels from database or inference results."""

    def __init__(
        self,
        mapping_manager: MappingManager | None = None,
        task_handle: TaskHandle | None = None,
    ) -> None:
        """Create a restorer with optional mapping and task dependencies.

        Args:
            mapping_manager: Optional manager for tests or callers.
            task_handle: Optional task state used for progress and cancellation.
        """
        self._mapping_manager = mapping_manager
        self._task_handle = task_handle

    def restore(self, config: RestoreConfig) -> RestoreResult:
        """Restore label files from the configured source.

        Args:
            config: Restore configuration.

        Returns:
            Aggregate counters and per-file failures.

        Raises:
            RestoreInvalidSourceTypeError: If source_type is unsupported.
            RestoreMappingNotFoundError: If mapping.json cannot be loaded.
            RestoreSourceNotFoundError: If the source directory cannot be resolved.
            TaskCancelledError: If the injected task requests cancellation.
        """
        if config.source_type not in _VALID_SOURCE_TYPES:
            raise RestoreInvalidSourceTypeError(
                "还原来源类型无效", details=config.source_type
            )
        manager = self._load_mapping(config.site_folder)
        source_root = self._resolve_source_root(config)
        self._raise_if_cancelled()

        source_paths = _source_label_files(source_root, config.source_type)
        result = RestoreResult(total=len(source_paths), success=0, skipped=0, failed=0)
        self._set_progress(0, len(source_paths), "准备还原")

        restored_any = False
        for index, source_path in enumerate(source_paths, start=1):
            self._raise_if_cancelled()
            self._set_progress(index - 1, len(source_paths), f"还原 {source_path.name}")
            target = self._resolve_target(source_path, source_root, config, manager)
            if (
                target.target_path is None
                or target.encoded_name is None
                or target.info is None
            ):
                result.failed += 1
                result.errors.append(
                    RestoreFileIssue(
                        source_path=source_path,
                        target_path=None,
                        reason="找不到 mapping 记录",
                    )
                )
                self._set_progress(
                    index, len(source_paths), f"已处理 {index}/{len(source_paths)}"
                )
                continue
            if target.info.restored and not config.overwrite:
                result.skipped += 1
                self._set_progress(index, len(source_paths), f"跳过 {source_path.name}")
                continue
            if target.target_path.exists() and not config.overwrite:
                result.skipped += 1
                self._set_progress(index, len(source_paths), f"跳过 {source_path.name}")
                continue
            try:
                target.target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target.target_path)
            except OSError as exc:
                result.failed += 1
                result.errors.append(
                    RestoreFileIssue(
                        source_path=source_path,
                        target_path=target.target_path,
                        reason=str(exc),
                    )
                )
            else:
                manager.mark_restored(target.encoded_name)
                restored_any = True
                result.success += 1
            self._set_progress(
                index, len(source_paths), f"已处理 {index}/{len(source_paths)}"
            )

        if restored_any:
            manager.save(config.site_folder / ".autolabeler" / "mapping.json")
        self._set_progress(len(source_paths), len(source_paths), "还原完成")
        return result

    def _load_mapping(self, site_folder: Path) -> MappingManager:
        """Load mapping data using MappingManager."""
        mapping_path = site_folder / ".autolabeler" / "mapping.json"
        manager = self._mapping_manager or MappingManager(mapping_path)
        manager.mapping_path = mapping_path
        try:
            return manager.load()
        except PathNotFoundError as exc:
            raise RestoreMappingNotFoundError(
                "mapping.json 不存在", details=str(mapping_path)
            ) from exc

    def _resolve_source_root(self, config: RestoreConfig) -> Path:
        """Resolve and validate the source directory."""
        if config.source_type == "database":
            if config.database_dir is None:
                raise RestoreSourceNotFoundError("database_dir 不能为空")
            source_root = config.database_dir
        else:
            source_root = _inference_source_root(config)
        if not source_root.exists() or not source_root.is_dir():
            raise RestoreSourceNotFoundError(
                "还原源目录不存在", details=str(source_root)
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
            logger.warning("还原任务已取消")
            raise TaskCancelledError("还原任务已取消")

    def _set_progress(self, current: int, total: int, message: str) -> None:
        """Update task progress fields when a task handle is available."""
        if self._task_handle is None:
            return
        self._task_handle.progress_current = current
        self._task_handle.progress_total = total
        self._task_handle.progress_message = message


def _inference_source_root(config: RestoreConfig) -> Path:
    """Resolve inference source root from explicit dir or run id."""
    if config.inference_run_dir is not None:
        return config.inference_run_dir
    if config.run_id is None:
        raise RestoreSourceNotFoundError("run_id 或 inference_run_dir 不能为空")
    return config.site_folder / ".autolabeler" / "inference_results" / config.run_id


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
    """Resolve a database label path to a mapping entry."""
    encoded_name = (
        f"{source_path.stem}{_image_suffix_for_stem(source_path.stem, manager)}"
    )
    info = manager.get_image_info(encoded_name)
    if info is None:
        return _RestoreTarget(
            source_path=source_path, target_path=None, encoded_name=None, info=None
        )
    return _RestoreTarget(
        source_path=source_path,
        target_path=site_folder / Path(info.original_relative).with_suffix(".txt"),
        encoded_name=encoded_name,
        info=info,
    )


def _image_suffix_for_stem(encoded_stem: str, manager: MappingManager) -> str:
    """Find the original image suffix for a flattened database label stem."""
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
                / Path(info.original_relative).with_suffix(".txt"),
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
