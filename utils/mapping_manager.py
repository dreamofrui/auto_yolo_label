"""Thread-safe mapping.json management."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Self

from utils.exceptions import PathNotFoundError, ValidationError

_MAPPING_VERSION = "1.0"
_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
_FILE_LOCK = threading.RLock()


@dataclass
class ImageInfo:
    """Metadata for one source image."""

    original_relative: str
    code: str
    product: str
    original_name: str
    format: str
    sampled: bool = False
    split: str | None = None
    manual_labeled: bool = False
    inferred: bool = False
    restored: bool = False
    label_source: str = "none"


@dataclass
class MappingData:
    """Complete mapping.json data model."""

    version: str = _MAPPING_VERSION
    project_name: str = ""
    site_folder: Path = Path()
    created_time: str = ""
    updated_time: str = ""
    classes: dict[str, str] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    statistics: dict[str, int] = field(default_factory=dict)
    products: dict[str, dict[str, int]] = field(default_factory=dict)
    images: dict[str, ImageInfo] = field(default_factory=dict)


@dataclass(frozen=True)
class MappedImage:
    """ImageInfo together with its encoded mapping key."""

    encoded_name: str
    info: ImageInfo


class MappingManager:
    """Read, write, and mutate one mapping.json file."""

    def __init__(self, mapping_path: Path) -> None:
        """Create a manager for a mapping path.

        Args:
            mapping_path: Path to mapping.json.
        """
        self.mapping_path = mapping_path
        self.data = MappingData()
        self._dirty = False
        self._lock = threading.RLock()

    def create_new(self, site_folder: Path, project_name: str | None = None) -> Self:
        """Create a new in-memory mapping.

        Args:
            site_folder: Site root folder.
            project_name: Optional display name. Defaults to folder name.

        Returns:
            This manager for fluent setup.
        """
        now = _now()
        with self._lock:
            self.data = MappingData(
                project_name=project_name or site_folder.name,
                site_folder=site_folder,
                created_time=now,
                updated_time=now,
                statistics=_empty_statistics(),
            )
            self._dirty = True
        return self

    def load(self) -> Self:
        """Load mapping data from disk.

        Returns:
            This manager with loaded data.

        Raises:
            PathNotFoundError: If mapping.json does not exist.
        """
        with self._lock, _FILE_LOCK:
            if not self.mapping_path.exists():
                raise PathNotFoundError(
                    "mapping.json 不存在", details=str(self.mapping_path)
                )
            raw = json.loads(self.mapping_path.read_text(encoding="utf-8"))
            self.data = _mapping_from_dict(raw)
            self._dirty = False
        return self

    def save(self, path: Path | None = None) -> None:
        """Save the current mapping data to disk.

        Args:
            path: Optional path override. Defaults to this manager's path.

        Raises:
            ValidationError: If no save path is available.
        """
        save_path = path or self.mapping_path
        if save_path is None:
            raise ValidationError("mapping 保存路径不能为空")
        with self._lock, _FILE_LOCK:
            self.data.updated_time = _now()
            payload = _mapping_to_dict(self.data)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = save_path.with_name(f"{save_path.name}.tmp")
            temp_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            temp_path.replace(save_path)
            self.mapping_path = save_path
            self._dirty = False

    def add_class(self, class_id: int, class_name: str) -> None:
        """Add or replace a class name."""
        with self._lock:
            self.data.classes[str(class_id)] = class_name
            self._dirty = True

    def add_image(self, encoded_name: str, info: ImageInfo) -> None:
        """Add or replace image metadata."""
        with self._lock:
            self.data.images[encoded_name] = info
            self._update_products()
            self._update_statistics()
            self._dirty = True

    def mark_sampled(
        self,
        encoded_name: str,
        split: str,
        label_source: str | None = None,
    ) -> None:
        """Mark one image as sampled."""
        with self._lock:
            image = self.data.images.get(encoded_name)
            if image is None:
                return
            image.sampled = True
            image.split = split
            if label_source is not None:
                image.label_source = label_source
            self._update_statistics()
            self._dirty = True

    def mark_labeled(self, encoded_name: str) -> None:
        """Mark one image as manually labeled."""
        with self._lock:
            image = self.data.images.get(encoded_name)
            if image is None:
                return
            image.manual_labeled = True
            image.label_source = "manual"
            self._update_statistics()
            self._dirty = True

    def mark_inferred(self, encoded_names: list[str]) -> None:
        """Mark images as inferred for statistics only."""
        with self._lock:
            for encoded_name in encoded_names:
                image = self.data.images.get(encoded_name)
                if image is not None:
                    image.inferred = True
            self._update_statistics()
            self._dirty = True

    def mark_restored(self, encoded_name: str) -> None:
        """Mark one image as restored."""
        with self._lock:
            image = self.data.images.get(encoded_name)
            if image is None:
                return
            image.restored = True
            self._update_statistics()
            self._dirty = True

    def get_image_info(self, encoded_name: str) -> ImageInfo | None:
        """Return image metadata by encoded name."""
        with self._lock:
            return self.data.images.get(encoded_name)

    def get_unsampled_images(self) -> list[MappedImage]:
        """Return images that have not been sampled."""
        with self._lock:
            return [
                MappedImage(encoded_name=key, info=value)
                for key, value in self.data.images.items()
                if not value.sampled
            ]

    def get_pending_inference_images(self) -> list[MappedImage]:
        """Return images eligible for inference.

        The inferred flag is intentionally ignored so users can rerun inference.
        """
        return self.get_unsampled_images()

    def get_sampled_images(self, split: str | None = None) -> list[MappedImage]:
        """Return sampled images, optionally filtered by split."""
        with self._lock:
            return [
                MappedImage(encoded_name=key, info=value)
                for key, value in self.data.images.items()
                if value.sampled and (split is None or value.split == split)
            ]

    def get_statistics(self) -> dict[str, int]:
        """Return a copy of aggregate statistics."""
        with self._lock:
            return dict(self.data.statistics)

    def get_classes(self) -> dict[str, str]:
        """Return a copy of class id to name mapping."""
        with self._lock:
            return dict(self.data.classes)

    def get_class_list(self) -> list[str]:
        """Return class names sorted by numeric class id."""
        with self._lock:
            return [
                name
                for _, name in sorted(
                    self.data.classes.items(), key=lambda item: int(item[0])
                )
            ]

    @property
    def is_dirty(self) -> bool:
        """Return whether the cache has unsaved changes."""
        with self._lock:
            return self._dirty

    def _update_products(self) -> None:
        """Rebuild product counts from image metadata."""
        products: dict[str, dict[str, int]] = {}
        for image in self.data.images.values():
            code_products = products.setdefault(image.code, {})
            code_products[image.product] = code_products.get(image.product, 0) + 1
        self.data.products = products

    def _update_statistics(self) -> None:
        """Rebuild aggregate statistics from image metadata."""
        images = list(self.data.images.values())
        self.data.statistics.update(
            {
                "total_images": len(images),
                "total_codes": len({image.code for image in images}),
                "total_products": len(
                    {(image.code, image.product) for image in images}
                ),
                "sampled_count": sum(1 for image in images if image.sampled),
                "labeled_count": sum(1 for image in images if image.manual_labeled),
                "inferred_count": sum(1 for image in images if image.inferred),
                "restored_count": sum(1 for image in images if image.restored),
            }
        )


def _empty_statistics() -> dict[str, int]:
    """Return zeroed mapping statistics."""
    return {
        "total_images": 0,
        "total_codes": 0,
        "total_products": 0,
        "sampled_count": 0,
        "labeled_count": 0,
        "inferred_count": 0,
        "restored_count": 0,
    }


def _mapping_to_dict(data: MappingData) -> dict[str, Any]:
    """Convert MappingData to a JSON-compatible dict."""
    raw = asdict(data)
    raw["site_folder"] = str(data.site_folder)
    return raw


def _mapping_from_dict(raw: dict[str, Any]) -> MappingData:
    """Convert a JSON dict to MappingData."""
    images_raw = raw.get("images", {})
    images = {
        str(key): ImageInfo(**value)
        for key, value in images_raw.items()
        if isinstance(value, dict)
    }
    return MappingData(
        version=str(raw.get("version", _MAPPING_VERSION)),
        project_name=str(raw.get("project_name", "")),
        site_folder=Path(str(raw.get("site_folder", ""))),
        created_time=str(raw.get("created_time", "")),
        updated_time=str(raw.get("updated_time", "")),
        classes={str(key): str(value) for key, value in raw.get("classes", {}).items()},
        config=dict(raw.get("config", {})),
        statistics={
            str(key): int(value) for key, value in raw.get("statistics", {}).items()
        },
        products={
            str(code): {
                str(product): int(count) for product, count in product_counts.items()
            }
            for code, product_counts in raw.get("products", {}).items()
            if isinstance(product_counts, dict)
        },
        images=images,
    )


def _now() -> str:
    """Return the current wall-clock timestamp."""
    return datetime.now().strftime(_TIME_FORMAT)
