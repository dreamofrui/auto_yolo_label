"""Site scanning module for building image mappings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from utils.exceptions import (
    AutoLabelerError,
    ErrorCode,
    TaskCancelledError,
    ValidationError,
)
from utils.mapping_manager import ImageInfo, MappingManager
from utils.path_encoder import PathEncoder
from utils.task_registry import TaskHandle


@dataclass(frozen=True)
class ScanConfig:
    """Scanner input contract."""

    site_folder: Path
    output_dir: Path | None = None
    supported_formats: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".bmp")


@dataclass(frozen=True)
class ScanStatistics:
    """Aggregate scanner counters."""

    total_images: int
    total_codes: int
    total_products: int


@dataclass(frozen=True)
class ScanResult:
    """Scanner output contract."""

    mapping_path: Path
    classes_path: Path
    statistics: ScanStatistics
    classes: list[str]
    products: dict[str, dict[str, int]]


@dataclass(frozen=True)
class _ImageCandidate:
    """Internal representation of a supported image under Code/Product."""

    path: Path
    code: str
    product: str


class ScannerError(AutoLabelerError):
    """Base class for scanner business errors."""

    code = ErrorCode.INTERNAL_ERROR


class ScanPathNotFoundError(ScannerError):
    """Raised when the site folder does not exist."""

    code = ErrorCode.SCAN_PATH_NOT_FOUND


class ScanInvalidStructureError(ScannerError):
    """Raised when the site tree cannot be encoded as Code/Product/images."""

    code = ErrorCode.SCAN_INVALID_STRUCTURE


class ScanEmptyError(ScannerError):
    """Raised when no supported images are found."""

    code = ErrorCode.SCAN_EMPTY


class Scanner:
    """Build mapping.json and classes.txt from a Code/Product site tree."""

    def __init__(
        self,
        mapping_manager: MappingManager | None = None,
        task_handle: TaskHandle | None = None,
    ) -> None:
        """Create a scanner with optional mapping and task dependencies.

        Args:
            mapping_manager: Optional mapping writer for tests or callers.
            task_handle: Optional task state used for progress and cancellation.
        """
        self._mapping_manager = mapping_manager
        self._task_handle = task_handle
        self._path_encoder = PathEncoder()

    def scan(self, config: ScanConfig) -> ScanResult:
        """Scan a site folder and write mapping.json plus classes.txt.

        Args:
            config: Scanner configuration.

        Returns:
            Paths, classes, products, and aggregate scan statistics.

        Raises:
            ScanPathNotFoundError: If site_folder does not exist.
            ScanInvalidStructureError: If Code/Product structure is invalid.
            ScanEmptyError: If no supported images are found.
            TaskCancelledError: If the injected task requests cancellation.
        """
        site_folder = config.site_folder
        output_dir = config.output_dir or site_folder / ".autolabeler"
        mapping_path = output_dir / "mapping.json"
        classes_path = output_dir / "classes.txt"
        supported_formats = _normalize_formats(config.supported_formats)

        logger.info("开始扫描站点: {}", site_folder)
        self._raise_if_cancelled()
        if not site_folder.exists():
            logger.error("扫描站点不存在: {}", site_folder)
            raise ScanPathNotFoundError("站点目录不存在", details=str(site_folder))
        if not site_folder.is_dir():
            logger.error("扫描站点不是目录: {}", site_folder)
            raise ScanInvalidStructureError(
                "站点路径不是目录", details=str(site_folder)
            )

        self._validate_supported_images_are_direct_products(
            site_folder, supported_formats
        )
        code_product_dirs = self._find_code_product_dirs(site_folder)
        if not code_product_dirs:
            logger.error("扫描站点缺少 Code/Product 两级目录: {}", site_folder)
            raise ScanInvalidStructureError(
                "找不到 Code/Product 两级目录", details=str(site_folder)
            )

        candidates = self._collect_images(code_product_dirs, supported_formats)
        if not candidates:
            logger.error("扫描站点未找到图片: {}", site_folder)
            raise ScanEmptyError("未找到任何支持的图片", details=str(site_folder))
        self._validate_unique_stems_per_product(candidates)

        self._set_progress(0, len(candidates), "开始扫描")
        classes = sorted({candidate.code for candidate in candidates})
        manager = self._mapping_manager or MappingManager(mapping_path)
        manager.mapping_path = mapping_path
        manager.create_new(site_folder)

        for class_id, class_name in enumerate(classes):
            manager.add_class(class_id, class_name)

        for index, candidate in enumerate(candidates, start=1):
            self._raise_if_cancelled()
            self._set_progress(
                index - 1, len(candidates), f"扫描 {candidate.path.name}"
            )

            encoded_name = self._encode_candidate(candidate)
            manager.add_image(
                encoded_name,
                _image_info(site_folder, candidate),
            )
            self._set_progress(
                index, len(candidates), f"已扫描 {index}/{len(candidates)}"
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        classes_path.write_text(_classes_text(classes), encoding="utf-8")
        manager.save(mapping_path)

        statistics = ScanStatistics(
            total_images=len(candidates),
            total_codes=len(classes),
            total_products=len(
                {(candidate.code, candidate.product) for candidate in candidates}
            ),
        )
        products = _products_from_candidates(candidates)
        self._set_progress(len(candidates), len(candidates), "扫描完成")
        logger.info(
            "扫描完成: {} 张图片, {} 个 Code",
            statistics.total_images,
            statistics.total_codes,
        )
        return ScanResult(
            mapping_path=mapping_path,
            classes_path=classes_path,
            statistics=statistics,
            classes=classes,
            products=products,
        )

    def _find_code_product_dirs(self, site_folder: Path) -> list[tuple[str, str, Path]]:
        """Return Code/Product directory triples sorted by Code then Product."""
        product_dirs: list[tuple[str, str, Path]] = []
        for code_dir in sorted(
            (path for path in site_folder.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        ):
            if code_dir.name == ".autolabeler":
                continue
            self._raise_if_cancelled()
            for product_dir in sorted(
                (path for path in code_dir.iterdir() if path.is_dir()),
                key=lambda path: path.name,
            ):
                product_dirs.append((code_dir.name, product_dir.name, product_dir))
        return product_dirs

    def _collect_images(
        self,
        code_product_dirs: list[tuple[str, str, Path]],
        supported_formats: frozenset[str],
    ) -> list[_ImageCandidate]:
        """Collect direct Product images and reject unsupported Product files."""
        candidates: list[_ImageCandidate] = []
        invalid_files: list[Path] = []
        for code, product, product_dir in code_product_dirs:
            self._raise_if_cancelled()
            for child_path in sorted(
                (path for path in product_dir.iterdir() if path.is_file()),
                key=lambda path: path.name,
            ):
                suffix = child_path.suffix.lower()
                if suffix in supported_formats:
                    candidates.append(
                        _ImageCandidate(path=child_path, code=code, product=product)
                    )
                elif suffix != ".xml":
                    invalid_files.append(child_path)
        if invalid_files:
            details = "; ".join(path.as_posix() for path in invalid_files[:20])
            raise ScanInvalidStructureError(
                "Product folders may contain only supported images and XML labels",
                details=details,
            )
        return candidates

    def _validate_supported_images_are_direct_products(
        self, site_folder: Path, supported_formats: frozenset[str]
    ) -> None:
        """Reject supported images outside the required Code/Product layout."""
        invalid_paths: list[Path] = []
        for image_path in sorted(
            site_folder.rglob("*"), key=lambda path: path.as_posix()
        ):
            self._raise_if_cancelled()
            if (
                not image_path.is_file()
                or image_path.suffix.lower() not in supported_formats
            ):
                continue
            relative = image_path.relative_to(site_folder)
            if len(relative.parts) != 3:
                invalid_paths.append(relative)
        if invalid_paths:
            details = "; ".join(path.as_posix() for path in invalid_paths[:20])
            raise ScanInvalidStructureError(
                "site must use Code/Product/image layout", details=details
            )

    def _validate_unique_stems_per_product(
        self, candidates: list[_ImageCandidate]
    ) -> None:
        """Reject same-stem images inside one Code/Product group."""
        by_group_and_stem: dict[tuple[str, str, str], list[Path]] = {}
        for candidate in candidates:
            key = (candidate.code, candidate.product, candidate.path.stem.lower())
            by_group_and_stem.setdefault(key, []).append(candidate.path)

        conflicts = [
            paths
            for paths in by_group_and_stem.values()
            if len({path.suffix.lower() for path in paths}) > 1
        ]
        if not conflicts:
            return

        details = "; ".join(
            ", ".join(path.as_posix() for path in sorted(paths))
            for paths in conflicts[:20]
        )
        raise ScanInvalidStructureError(
            "same Code/Product cannot contain same-stem images with different suffixes",
            details=details,
        )

    def _encode_candidate(self, candidate: _ImageCandidate) -> str:
        """Encode a candidate path or convert separator errors to scanner errors."""
        try:
            return self._path_encoder.encode(
                candidate.code, candidate.product, candidate.path.name
            )
        except ValidationError as exc:
            logger.error("扫描路径包含保留分隔符: {}", candidate.path)
            raise ScanInvalidStructureError(
                "路径包含保留分隔符", details=str(candidate.path)
            ) from exc

    def _raise_if_cancelled(self) -> None:
        """Raise TaskCancelledError when the injected task has been cancelled."""
        if self._task_handle is not None and self._task_handle.is_cancel_requested:
            logger.warning("扫描任务已取消")
            raise TaskCancelledError("扫描任务已取消")

    def _set_progress(self, current: int, total: int, message: str) -> None:
        """Update task progress fields when a task handle is available."""
        if self._task_handle is None:
            return
        self._task_handle.progress_current = current
        self._task_handle.progress_total = total
        self._task_handle.progress_message = message


def _normalize_formats(supported_formats: tuple[str, ...]) -> frozenset[str]:
    """Normalize configured image suffixes for case-insensitive matching."""
    return frozenset(format_value.lower() for format_value in supported_formats)


def _image_info(site_folder: Path, candidate: _ImageCandidate) -> ImageInfo:
    """Build mapping metadata for a scanned image."""
    return ImageInfo(
        original_relative=candidate.path.relative_to(site_folder).as_posix(),
        code=candidate.code,
        product=candidate.product,
        original_name=candidate.path.name,
        format=candidate.path.suffix.lower(),
    )


def _products_from_candidates(
    candidates: list[_ImageCandidate],
) -> dict[str, dict[str, int]]:
    """Build nested product image counts from scan candidates."""
    products: dict[str, dict[str, int]] = {}
    for candidate in candidates:
        code_products = products.setdefault(candidate.code, {})
        code_products[candidate.product] = code_products.get(candidate.product, 0) + 1
    return products


def _classes_text(classes: list[str]) -> str:
    """Return classes.txt content with one class per line."""
    return "".join(f"{class_name}\n" for class_name in classes)
