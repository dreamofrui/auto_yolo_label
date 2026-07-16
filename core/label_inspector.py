"""Read-only preparation of inference labels for LabelImg review."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from utils.exceptions import AutoLabelerError, ErrorCode, PathNotFoundError
from utils.mapping_manager import MappedImage, MappingManager

_CONTROL_FILE_NAMES = {"classes.txt", "data.yaml", "readme.txt"}


@dataclass(frozen=True)
class ListRunsConfig:
    """Configuration for listing inference runs under a site."""

    site_folder: Path


@dataclass(frozen=True)
class GetRunTreeConfig:
    """Configuration for reading one inference run tree."""

    site_folder: Path
    run_id: str


@dataclass(frozen=True)
class GetProductLabelsConfig:
    """Configuration for reading labels from one Code/Product directory."""

    site_folder: Path
    run_id: str
    code: str
    product: str


@dataclass(frozen=True)
class InferenceRun:
    """One inference run discovered on disk."""

    run_id: str
    path: Path
    config_exists: bool
    config: dict[str, object] | None
    created_at: str


@dataclass(frozen=True)
class RunTreeNode:
    """Summary for one Code/Product node inside an inference run."""

    code: str
    product: str
    label_count: int
    empty_count: int
    path: Path


@dataclass(frozen=True)
class ProductLabel:
    """One review image and its editable label path."""

    image_name: str
    image_path: Path
    label_path: Path
    object_count: int
    missing_label: bool = False


class InspectorError(AutoLabelerError):
    """Base class for label inspector business errors."""

    code = ErrorCode.INTERNAL_ERROR


class InspectorRunNotFoundError(InspectorError):
    """Raised when an inference run directory cannot be found."""

    code = ErrorCode.INSPECTOR_RUN_NOT_FOUND


class InspectorProductNotFoundError(InspectorError):
    """Raised when a Code/Product label directory cannot be found."""

    code = ErrorCode.INSPECTOR_PRODUCT_NOT_FOUND


class InspectorMappingNotFoundError(InspectorError):
    """Raised when flow review cannot load mapping.json."""

    code = ErrorCode.INSPECTOR_MAPPING_NOT_FOUND


class InspectorClassesNotFoundError(InspectorError):
    """Raised when flow review cannot load a non-empty classes.txt."""

    code = ErrorCode.INSPECTOR_CLASSES_NOT_FOUND


class InspectorOriginalImageMissingError(InspectorError):
    """Raised when mapped source images are missing from disk."""

    code = ErrorCode.INSPECTOR_ORIGINAL_IMAGE_MISSING


class LabelInspector:
    """Prepare flow-mode inference runs for LabelImg review."""

    def list_runs(self, config: ListRunsConfig) -> list[InferenceRun]:
        """List inference runs under `site_folder`."""
        inference_root = _inference_root(config.site_folder)
        if not inference_root.exists() or not inference_root.is_dir():
            return []
        runs: list[InferenceRun] = []
        for path in sorted(
            (item for item in inference_root.iterdir() if item.is_dir()), reverse=True
        ):
            config_data = _read_config(path / "inference_config.json")
            runs.append(
                InferenceRun(
                    run_id=path.name,
                    path=path,
                    config_exists=config_data is not None,
                    config=config_data,
                    created_at=_created_at(path),
                )
            )
        return runs

    def get_run_tree(self, config: GetRunTreeConfig) -> list[RunTreeNode]:
        """Return Code/Product label counts from `run/labels/...`."""
        labels_root = _labels_root(config.site_folder, config.run_id)
        if not labels_root.exists() or not labels_root.is_dir():
            raise InspectorRunNotFoundError(
                "Inference run labels do not exist", details=str(labels_root)
            )

        nodes: list[RunTreeNode] = []
        for code_dir in sorted(item for item in labels_root.iterdir() if item.is_dir()):
            for product_dir in sorted(
                item for item in code_dir.iterdir() if item.is_dir()
            ):
                labels = _label_files(product_dir)
                nodes.append(
                    RunTreeNode(
                        code=code_dir.name,
                        product=product_dir.name,
                        label_count=len(labels),
                        empty_count=sum(
                            1 for label_path in labels if _object_count(label_path) == 0
                        ),
                        path=product_dir,
                    )
                )
        return nodes

    def get_product_labels(self, config: GetProductLabelsConfig) -> list[ProductLabel]:
        """Return mapped review images and editable label paths for one node."""
        labels_root = _labels_root(config.site_folder, config.run_id)
        if not labels_root.exists() or not labels_root.is_dir():
            raise InspectorRunNotFoundError(
                "Inference run labels do not exist", details=str(labels_root)
            )
        product_dir = labels_root / config.code / config.product
        if not product_dir.exists() or not product_dir.is_dir():
            raise InspectorProductNotFoundError(
                "Inference product labels do not exist", details=str(product_dir)
            )

        _load_classes(config.site_folder)
        mapped_images = _mapped_product_images(
            _load_mapping(config.site_folder), config.code, config.product
        )
        missing_images = [
            config.site_folder / Path(mapped.info.original_relative)
            for mapped in mapped_images
            if not (config.site_folder / Path(mapped.info.original_relative)).is_file()
        ]
        if missing_images:
            raise InspectorOriginalImageMissingError(
                "Original images are missing",
                details=", ".join(path.as_posix() for path in missing_images),
            )

        labels: list[ProductLabel] = []
        for mapped in mapped_images:
            image_path = config.site_folder / Path(mapped.info.original_relative)
            label_path = product_dir / f"{Path(mapped.info.original_name).stem}.txt"
            missing_label = not label_path.exists()
            labels.append(
                ProductLabel(
                    image_name=image_path.name,
                    image_path=image_path,
                    label_path=label_path,
                    object_count=0 if missing_label else _object_count(label_path),
                    missing_label=missing_label,
                )
            )
        return sorted(labels, key=lambda item: item.label_path.name)


def _inference_root(site_folder: Path) -> Path:
    """Return the inference results root for a site."""
    return site_folder / ".autolabeler" / "inference_results"


def _run_dir(site_folder: Path, run_id: str) -> Path:
    """Return one inference run directory."""
    return _inference_root(site_folder) / run_id


def _labels_root(site_folder: Path, run_id: str) -> Path:
    """Return one inference run labels root."""
    return _run_dir(site_folder, run_id) / "labels"


def _load_mapping(site_folder: Path) -> MappingManager:
    """Load flow-mode mapping for review."""
    mapping_path = site_folder / ".autolabeler" / "mapping.json"
    try:
        return MappingManager(mapping_path).load()
    except PathNotFoundError as exc:
        raise InspectorMappingNotFoundError(
            "mapping.json does not exist", details=str(mapping_path)
        ) from exc


def _load_classes(site_folder: Path) -> list[str]:
    """Load non-empty flow-mode classes.txt for review."""
    classes_path = site_folder / ".autolabeler" / "classes.txt"
    if not classes_path.exists() or not classes_path.is_file():
        raise InspectorClassesNotFoundError(
            "classes.txt does not exist", details=str(classes_path)
        )
    classes = [
        line.strip()
        for line in classes_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not classes:
        raise InspectorClassesNotFoundError(
            "classes.txt is empty", details=str(classes_path)
        )
    return classes


def _mapped_product_images(
    manager: MappingManager, code: str, product: str
) -> list[MappedImage]:
    """Return mapping records for one Code/Product pair."""
    return sorted(
        (
            mapped
            for mapped in manager.get_sampled_images() + manager.get_unsampled_images()
            if mapped.info.code == code and mapped.info.product == product
        ),
        key=lambda mapped: mapped.info.original_name,
    )


def _read_config(config_path: Path) -> dict[str, object] | None:
    """Read a config snapshot, returning None for all read or parse failures."""
    if not config_path.exists() or not config_path.is_file():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return cast(dict[str, object], data)


def _created_at(run_dir: Path) -> str:
    """Derive a stable created-at string from run id or filesystem metadata."""
    try:
        parsed = datetime.strptime(run_dir.name, "run_%Y%m%d_%H%M%S")
    except ValueError:
        return datetime.fromtimestamp(run_dir.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _label_files(folder: Path) -> list[Path]:
    """Return sorted TXT label files after filtering known control files."""
    return sorted(
        path
        for path in folder.glob("*.txt")
        if path.is_file() and path.name.lower() not in _CONTROL_FILE_NAMES
    )


def _object_count(label_path: Path) -> int:
    """Count non-empty YOLO annotation rows in a label file."""
    try:
        return sum(
            1
            for line in label_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    except OSError:
        return 0
