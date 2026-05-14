"""Read-only inspection of inference label runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from utils.exceptions import AutoLabelerError, ErrorCode

_CONTROL_FILE_NAMES = {"classes.txt", "data.yaml", "readme.txt"}
_SUPPORTED_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp")


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
    """One label file and its best-effort source image path."""

    image_name: str
    image_path: Path | None
    label_path: Path
    object_count: int


class InspectorError(AutoLabelerError):
    """Base class for label inspector business errors."""

    code = ErrorCode.INTERNAL_ERROR


class InspectorRunNotFoundError(InspectorError):
    """Raised when an inference run directory cannot be found."""

    code = ErrorCode.INSPECTOR_RUN_NOT_FOUND


class InspectorProductNotFoundError(InspectorError):
    """Raised when a Code/Product label directory cannot be found."""

    code = ErrorCode.INSPECTOR_PRODUCT_NOT_FOUND


class LabelInspector:
    """Browse inference results without depending on mapping.json."""

    def list_runs(self, config: ListRunsConfig) -> list[InferenceRun]:
        """List inference runs under `site_folder`.

        Args:
            config: Site folder to inspect.

        Returns:
            Run metadata sorted by run id descending. Invalid or missing
            `inference_config.json` files are reported as absent.
        """
        inference_root = _inference_root(config.site_folder)
        if not inference_root.exists() or not inference_root.is_dir():
            return []
        runs: list[InferenceRun] = []
        for path in sorted((item for item in inference_root.iterdir() if item.is_dir()), reverse=True):
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
        """Return Code/Product label counts for one inference run.

        Args:
            config: Site folder and run id to inspect.

        Returns:
            A sorted list of product nodes with TXT and empty-TXT counts.

        Raises:
            InspectorRunNotFoundError: If the run directory does not exist.
        """
        run_dir = _run_dir(config.site_folder, config.run_id)
        if not run_dir.exists() or not run_dir.is_dir():
            raise InspectorRunNotFoundError("推理 run 不存在", details=str(run_dir))

        nodes: list[RunTreeNode] = []
        for code_dir in sorted(item for item in run_dir.iterdir() if item.is_dir()):
            for product_dir in sorted(item for item in code_dir.iterdir() if item.is_dir()):
                labels = _label_files(product_dir)
                nodes.append(
                    RunTreeNode(
                        code=code_dir.name,
                        product=product_dir.name,
                        label_count=len(labels),
                        empty_count=sum(1 for label_path in labels if _object_count(label_path) == 0),
                        path=product_dir,
                    )
                )
        return nodes

    def get_product_labels(self, config: GetProductLabelsConfig) -> list[ProductLabel]:
        """Return labels and source image paths for one product.

        Args:
            config: Site folder, run id, Code, and Product to inspect.

        Returns:
            Sorted label records with object counts.

        Raises:
            InspectorRunNotFoundError: If the run directory does not exist.
            InspectorProductNotFoundError: If the product label directory does not exist.
        """
        run_dir = _run_dir(config.site_folder, config.run_id)
        if not run_dir.exists() or not run_dir.is_dir():
            raise InspectorRunNotFoundError("推理 run 不存在", details=str(run_dir))
        product_dir = run_dir / config.code / config.product
        if not product_dir.exists() or not product_dir.is_dir():
            raise InspectorProductNotFoundError("推理产品目录不存在", details=str(product_dir))

        labels: list[ProductLabel] = []
        for label_path in _label_files(product_dir):
            image_path = _find_original_image(config.site_folder, config.code, config.product, label_path.stem)
            labels.append(
                ProductLabel(
                    image_name=image_path.name if image_path is not None else label_path.stem,
                    image_path=image_path,
                    label_path=label_path,
                    object_count=_object_count(label_path),
                )
            )
        return labels


def _inference_root(site_folder: Path) -> Path:
    """Return the inference results root for a site."""
    return site_folder / ".autolabeler" / "inference_results"


def _run_dir(site_folder: Path, run_id: str) -> Path:
    """Return one inference run directory."""
    return _inference_root(site_folder) / run_id


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
        return datetime.fromtimestamp(run_dir.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
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
        return sum(1 for line in label_path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return 0


def _find_original_image(site_folder: Path, code: str, product: str, stem: str) -> Path | None:
    """Find a source image with a matching stem and supported suffix."""
    product_dir = site_folder / code / product
    if not product_dir.exists() or not product_dir.is_dir():
        return None
    suffix_order = {suffix: index for index, suffix in enumerate(_SUPPORTED_IMAGE_SUFFIXES)}
    candidates = [
        path
        for path in product_dir.iterdir()
        if path.is_file()
        and path.stem == stem
        and path.suffix.lower() in suffix_order
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: (suffix_order[path.suffix.lower()], path.name))[0]
