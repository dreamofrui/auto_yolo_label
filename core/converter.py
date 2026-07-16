"""Annotation format conversion module."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence, TypeAlias

from loguru import logger
from PIL import Image

from core.annotation_formats import (
    AnnotationFormatError,
    parse_voc_xml_text,
    voc_objects_to_yolo_label_text,
)
from utils.exceptions import (
    AutoLabelerError,
    ErrorCode,
    PathNotFoundError,
    TaskCancelledError,
)
from utils.mapping_manager import MappingManager
from utils.task_registry import TaskHandle

_SUPPORTED_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp")
_CONTROL_FILE_NAMES = {"classes.txt", "data.yaml", "readme.txt"}


@dataclass(frozen=True)
class TxtToXmlConfig:
    """Batch YOLO TXT to VOC XML conversion config."""

    folder: Path
    recursive: bool = True
    classes: list[str] | None = None
    delete_source: bool = False
    backup_dir: Path | None = None


@dataclass(frozen=True)
class XmlToTxtConfig:
    """Single VOC XML to YOLO TXT conversion config."""

    xml_path: Path
    classes: list[str]
    output_path: Path


@dataclass(frozen=True)
class XmlDatasetAnalyzeConfig:
    """Preflight config for XML directory to YOLO dataset conversion."""

    source_dir: Path
    output_dir: Path
    train_ratio: float = 0.9
    classes: list[str] | None = None
    overwrite_output: bool = False


@dataclass(frozen=True)
class XmlDatasetAnalysis:
    """Preflight result for XML directory to YOLO dataset conversion."""

    collected_classes: list[str]
    valid_pair_count: int
    skipped_image_count: int
    skipped_xml_count: int
    blocking_issues: list[str] = field(default_factory=list)
    output_conflicts: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class XmlDatasetConvertConfig:
    """Conversion config after class confirmation."""

    source_dir: Path
    output_dir: Path
    confirmed_classes: list[str]
    train_ratio: float = 0.9
    overwrite_output: bool = False


@dataclass(frozen=True)
class XmlDatasetPaths:
    """Standard YOLO dataset output paths."""

    images_train: Path
    images_val: Path
    labels_train: Path
    labels_val: Path
    classes_txt: Path
    data_yaml: Path


@dataclass(frozen=True)
class XmlDatasetConvertResult:
    """Result of XML directory to YOLO dataset conversion."""

    dataset_dir: Path
    paths: XmlDatasetPaths
    total_pairs: int
    train_count: int
    val_count: int
    class_count: int
    skipped_image_count: int
    skipped_xml_count: int


@dataclass(frozen=True)
class ConvertFileIssue:
    """One per-file conversion failure."""

    path: Path
    code: ErrorCode
    message: str
    details: str | None = None


ConvertFileError: TypeAlias = ConvertFileIssue


@dataclass
class ConvertResult:
    """Batch conversion counters and per-file errors."""

    total: int
    success: int
    skipped: int
    failed: int
    errors: list[ConvertFileIssue] = field(default_factory=list)


@dataclass(frozen=True)
class _YoloBox:
    """Parsed YOLO annotation row."""

    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float


@dataclass(frozen=True)
class _ImageSize:
    """Image dimensions for VOC output."""

    width: int
    height: int
    depth: int


class ConvertError(AutoLabelerError):
    """Base class for converter business errors."""

    code = ErrorCode.INTERNAL_ERROR


class ConvertFolderNotFoundError(ConvertError):
    """Raised when the target conversion folder does not exist."""

    code = ErrorCode.CONVERT_FOLDER_NOT_FOUND


class ConvertClassesNotFoundError(ConvertError):
    """Raised when classes cannot be resolved."""

    code = ErrorCode.CONVERT_CLASSES_NOT_FOUND


class ConvertClassIdOutOfRangeError(ConvertError):
    """Raised when a YOLO class id is not in classes."""

    code = ErrorCode.CONVERT_CLASS_ID_OUT_OF_RANGE


class ConvertXmlParseError(ConvertError):
    """Raised when VOC XML cannot be parsed or converted."""

    code = ErrorCode.CONVERT_XML_PARSE


class XmlDatasetPreflightError(ConvertError):
    """Raised when XML dataset preflight blocks conversion."""

    code = ErrorCode.VALIDATION_ERROR


@dataclass(frozen=True)
class _XmlDatasetPair:
    """One valid source image/XML pair."""

    image_path: Path
    xml_path: Path
    group_dir: Path


@dataclass(frozen=True)
class _PlannedXmlDatasetPair:
    """One valid source pair assigned to a dataset split."""

    pair: _XmlDatasetPair
    split: str


@dataclass(frozen=True)
class _XmlDatasetPreflight:
    """Internal preflight data for analysis and conversion."""

    analysis: XmlDatasetAnalysis
    pairs: list[_XmlDatasetPair]


class Converter:
    """Convert annotations between YOLO TXT and VOC XML formats."""

    def __init__(
        self,
        mapping_manager: MappingManager | None = None,
        task_handle: TaskHandle | None = None,
    ) -> None:
        """Create a converter with optional mapping and task dependencies.

        Args:
            mapping_manager: Optional manager for class resolution.
            task_handle: Optional task state used for progress and cancellation.
        """
        self._mapping_manager = mapping_manager
        self._task_handle = task_handle

    def analyze_xml_dataset(
        self, config: XmlDatasetAnalyzeConfig
    ) -> XmlDatasetAnalysis:
        """Analyze an image/XML directory before building a YOLO dataset."""
        return _preflight_xml_dataset(config).analysis

    def convert_xml_dataset(
        self, config: XmlDatasetConvertConfig
    ) -> XmlDatasetConvertResult:
        """Convert confirmed image/XML pairs into a standard YOLO dataset."""
        self._raise_if_cancelled()
        if not config.confirmed_classes:
            raise XmlDatasetPreflightError("confirmed_classes must not be empty")
        analyze_config = XmlDatasetAnalyzeConfig(
            source_dir=config.source_dir,
            output_dir=config.output_dir,
            train_ratio=config.train_ratio,
            classes=config.confirmed_classes,
            overwrite_output=config.overwrite_output,
        )
        preflight = _preflight_xml_dataset(analyze_config)
        blocking = (
            preflight.analysis.blocking_issues + preflight.analysis.output_conflicts
        )
        if blocking:
            raise XmlDatasetPreflightError(
                "XML dataset preflight failed", details="; ".join(blocking)
            )

        if config.output_dir.exists() and config.overwrite_output:
            shutil.rmtree(config.output_dir)

        paths = _xml_dataset_paths(config.output_dir)
        _ensure_xml_dataset_dirs(paths)
        plan = _plan_xml_dataset_pairs(preflight.pairs, config.train_ratio)
        self._set_progress(0, len(plan), "Preparing XML dataset conversion")
        for index, planned in enumerate(plan, start=1):
            self._raise_if_cancelled()
            self._set_progress(
                index - 1, len(plan), f"Converting {planned.pair.image_path.name}"
            )
            _write_xml_dataset_pair(planned, paths, config.confirmed_classes)
            self._set_progress(index, len(plan), f"Converted {index}/{len(plan)}")

        _write_xml_dataset_classes(paths.classes_txt, config.confirmed_classes)
        _write_xml_dataset_yaml(paths.data_yaml, config.output_dir, config.confirmed_classes)
        self._set_progress(len(plan), len(plan), "XML dataset conversion complete")
        return XmlDatasetConvertResult(
            dataset_dir=config.output_dir,
            paths=paths,
            total_pairs=len(plan),
            train_count=sum(1 for item in plan if item.split == "train"),
            val_count=sum(1 for item in plan if item.split == "val"),
            class_count=len(config.confirmed_classes),
            skipped_image_count=preflight.analysis.skipped_image_count,
            skipped_xml_count=preflight.analysis.skipped_xml_count,
        )

    def txt_to_xml(self, config: TxtToXmlConfig) -> ConvertResult:
        """Convert YOLO TXT files under a folder to VOC XML files.

        Args:
            config: Batch conversion configuration.

        Returns:
            Conversion counters and per-file errors.

        Raises:
            ConvertFolderNotFoundError: If folder is missing.
            ConvertClassesNotFoundError: If classes cannot be resolved.
            TaskCancelledError: If the injected task requests cancellation.
        """
        if not config.folder.exists() or not config.folder.is_dir():
            raise ConvertFolderNotFoundError(
                "转换目录不存在", details=str(config.folder)
            )
        classes = self._resolve_classes(config)
        txt_paths = _annotation_txt_files(config.folder, config.recursive)
        result = ConvertResult(total=len(txt_paths), success=0, skipped=0, failed=0)
        self._set_progress(0, len(txt_paths), "准备转换")

        for index, txt_path in enumerate(txt_paths, start=1):
            self._raise_if_cancelled()
            self._set_progress(index - 1, len(txt_paths), f"转换 {txt_path.name}")
            image_path = _find_image_for_txt(txt_path)
            if image_path is None:
                result.skipped += 1
                self._set_progress(index, len(txt_paths), f"跳过 {txt_path.name}")
                continue
            xml_path: Path | None = None
            try:
                xml_path = self._convert_one_txt(txt_path, image_path, classes)
                if config.delete_source:
                    self._delete_source(txt_path, config.folder, config.backup_dir)
            except ConvertError as exc:
                result.failed += 1
                result.errors.append(
                    ConvertFileError(
                        path=txt_path,
                        code=exc.code,
                        message=exc.message,
                        details=exc.details,
                    )
                )
            except OSError as exc:
                result.failed += 1
                result.errors.append(
                    ConvertFileError(
                        path=txt_path,
                        code=ErrorCode.INTERNAL_ERROR,
                        message="文件操作失败",
                        details=str(exc),
                    )
                )
                if config.delete_source and xml_path is not None:
                    xml_path.unlink(missing_ok=True)
            else:
                result.success += 1
            self._set_progress(
                index, len(txt_paths), f"已转换 {index}/{len(txt_paths)}"
            )

        self._set_progress(len(txt_paths), len(txt_paths), "转换完成")
        return result

    def xml_to_txt(self, config: XmlToTxtConfig) -> Path:
        """Convert one VOC XML file to YOLO TXT.

        Args:
            config: XML conversion configuration.

        Returns:
            The written YOLO TXT path.

        Raises:
            ConvertClassesNotFoundError: If classes is empty.
            ConvertXmlParseError: If XML cannot be converted.
            TaskCancelledError: If the injected task requests cancellation.
        """
        self._raise_if_cancelled()
        if not config.classes:
            raise ConvertClassesNotFoundError("类别列表不能为空")
        try:
            lines = _xml_to_yolo_lines(config.xml_path, config.classes)
        except ConvertXmlParseError:
            raise
        except (ElementTree.ParseError, OSError, ValueError) as exc:
            raise ConvertXmlParseError(
                "XML 解析失败", details=str(config.xml_path)
            ) from exc
        config.output_path.parent.mkdir(parents=True, exist_ok=True)
        config.output_path.write_text(
            "".join(f"{line}\n" for line in lines), encoding="utf-8"
        )
        return config.output_path

    def _resolve_classes(self, config: TxtToXmlConfig) -> list[str]:
        """Resolve class names from config or MappingManager."""
        if config.classes:
            return config.classes
        manager = self._mapping_manager or MappingManager(
            config.folder / ".autolabeler" / "mapping.json"
        )
        try:
            manager.load()
        except PathNotFoundError as exc:
            raise ConvertClassesNotFoundError(
                "找不到类别配置", details=str(manager.mapping_path)
            ) from exc
        classes = manager.get_class_list()
        if not classes:
            raise ConvertClassesNotFoundError(
                "类别列表为空", details=str(manager.mapping_path)
            )
        return classes

    def _convert_one_txt(
        self, txt_path: Path, image_path: Path, classes: list[str]
    ) -> Path:
        """Convert one YOLO TXT file to a VOC XML file."""
        size = _read_image_size(image_path)
        boxes = _read_yolo_boxes(txt_path, classes)
        xml_text = _voc_xml_text(image_path, size, boxes, classes)
        xml_path = txt_path.with_suffix(".xml")
        xml_path.write_text(xml_text, encoding="utf-8")
        return xml_path

    def _delete_source(
        self, txt_path: Path, folder: Path, backup_dir: Path | None
    ) -> None:
        """Backup and delete a source TXT file after successful conversion."""
        if backup_dir is not None:
            backup_path = backup_dir / txt_path.relative_to(folder)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(txt_path, backup_path)
        txt_path.unlink()

    def _raise_if_cancelled(self) -> None:
        """Raise TaskCancelledError when the injected task has been cancelled."""
        if self._task_handle is not None and self._task_handle.is_cancel_requested:
            logger.warning("转换任务已取消")
            raise TaskCancelledError("转换任务已取消")

    def _set_progress(self, current: int, total: int, message: str) -> None:
        """Update task progress fields when a task handle is available."""
        if self._task_handle is None:
            return
        self._task_handle.progress_current = current
        self._task_handle.progress_total = total
        self._task_handle.progress_message = message


def _annotation_txt_files(folder: Path, recursive: bool) -> list[Path]:
    """Return sorted annotation TXT files after filtering control files."""
    pattern = folder.rglob("*.txt") if recursive else folder.glob("*.txt")
    return sorted(
        path for path in pattern if path.name.lower() not in _CONTROL_FILE_NAMES
    )


def _preflight_xml_dataset(
    config: XmlDatasetAnalyzeConfig,
) -> _XmlDatasetPreflight:
    """Collect all issues before any XML dataset writes happen."""
    blocking_issues: list[str] = []
    output_conflicts: list[str] = []
    pairs: list[_XmlDatasetPair] = []
    classes_seen: set[str] = set()

    if not config.source_dir.exists() or not config.source_dir.is_dir():
        blocking_issues.append(f"source_dir does not exist: {config.source_dir}")
    if config.train_ratio <= 0 or config.train_ratio > 1:
        blocking_issues.append("train_ratio must be in (0, 1]")

    images: list[Path] = []
    xmls: list[Path] = []
    if not blocking_issues:
        images = _xml_dataset_images(config.source_dir)
        xmls = _xml_dataset_xmls(config.source_dir)
        xml_keys = {_same_stem_key(path) for path in xmls}
        image_keys = {_same_stem_key(path) for path in images}
        skipped_image_count = sum(1 for image in images if _same_stem_key(image) not in xml_keys)
        skipped_xml_count = sum(1 for xml_path in xmls if _same_stem_key(xml_path) not in image_keys)

        for image_path in images:
            xml_path = image_path.with_suffix(".xml")
            if not xml_path.exists():
                continue
            try:
                annotation = parse_voc_xml_text(xml_path.read_text(encoding="utf-8"))
            except (AnnotationFormatError, OSError) as exc:
                blocking_issues.append(f"{xml_path}: {exc}")
                continue
            pairs.append(
                _XmlDatasetPair(
                    image_path=image_path,
                    xml_path=xml_path,
                    group_dir=image_path.parent,
                )
            )
            classes_seen.update(obj.name for obj in annotation.objects)
    else:
        skipped_image_count = 0
        skipped_xml_count = 0

    if not blocking_issues and not pairs:
        blocking_issues.append("no valid image/XML pairs found")

    classes = list(config.classes) if config.classes is not None else sorted(classes_seen)
    missing_classes = sorted(classes_seen.difference(classes))
    if missing_classes:
        blocking_issues.append(f"XML classes missing from provided classes: {', '.join(missing_classes)}")

    if not config.overwrite_output and _is_non_empty_dir(config.output_dir):
        output_conflicts.append(f"output directory is not empty: {config.output_dir}")
    output_conflicts.extend(_xml_dataset_name_conflicts(pairs))

    analysis = XmlDatasetAnalysis(
        collected_classes=classes,
        valid_pair_count=len(pairs),
        skipped_image_count=skipped_image_count,
        skipped_xml_count=skipped_xml_count,
        blocking_issues=blocking_issues,
        output_conflicts=output_conflicts,
    )
    return _XmlDatasetPreflight(analysis=analysis, pairs=pairs)


def _xml_dataset_images(source_dir: Path) -> list[Path]:
    """Return supported images under source_dir in stable order."""
    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in _SUPPORTED_IMAGE_SUFFIXES
    )


def _xml_dataset_xmls(source_dir: Path) -> list[Path]:
    """Return XML files under source_dir in stable order."""
    return sorted(path for path in source_dir.rglob("*.xml") if path.is_file())


def _same_stem_key(path: Path) -> tuple[Path, str]:
    """Match same-stem image/XML files within the same directory."""
    return (path.parent, path.stem)


def _is_non_empty_dir(path: Path) -> bool:
    """Return whether a directory exists and contains any entry."""
    return path.exists() and path.is_dir() and any(path.iterdir())


def _xml_dataset_name_conflicts(pairs: Sequence[_XmlDatasetPair]) -> list[str]:
    """Find output filename conflicts before split assignment."""
    image_names: dict[str, Path] = {}
    label_names: dict[str, Path] = {}
    conflicts: list[str] = []
    for pair in pairs:
        image_name = pair.image_path.name
        label_name = f"{pair.image_path.stem}.txt"
        if image_name in image_names:
            conflicts.append(f"duplicate output image filename: {image_name}")
        else:
            image_names[image_name] = pair.image_path
        if label_name in label_names:
            conflicts.append(f"duplicate output label filename: {label_name}")
        else:
            label_names[label_name] = pair.image_path
    return conflicts


def _xml_dataset_paths(dataset_dir: Path) -> XmlDatasetPaths:
    """Build standard YOLO dataset paths."""
    return XmlDatasetPaths(
        images_train=dataset_dir / "images" / "train",
        images_val=dataset_dir / "images" / "val",
        labels_train=dataset_dir / "labels" / "train",
        labels_val=dataset_dir / "labels" / "val",
        classes_txt=dataset_dir / "classes.txt",
        data_yaml=dataset_dir / "data.yaml",
    )


def _ensure_xml_dataset_dirs(paths: XmlDatasetPaths) -> None:
    """Create standard YOLO dataset directories."""
    for path in (
        paths.images_train,
        paths.images_val,
        paths.labels_train,
        paths.labels_val,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _plan_xml_dataset_pairs(
    pairs: Sequence[_XmlDatasetPair], train_ratio: float
) -> list[_PlannedXmlDatasetPair]:
    """Assign every valid pair to train/val, split within each image folder."""
    grouped: dict[Path, list[_XmlDatasetPair]] = {}
    for pair in pairs:
        grouped.setdefault(pair.group_dir, []).append(pair)

    plan: list[_PlannedXmlDatasetPair] = []
    for group_dir in sorted(grouped):
        group_pairs = sorted(grouped[group_dir], key=lambda pair: pair.image_path.name)
        train_count = _xml_dataset_train_count(len(group_pairs), train_ratio)
        for index, pair in enumerate(group_pairs):
            split = "train" if index < train_count else "val"
            plan.append(_PlannedXmlDatasetPair(pair=pair, split=split))
    return plan


def _xml_dataset_train_count(total: int, train_ratio: float) -> int:
    """Calculate train count while preserving a val sample when possible."""
    if total <= 1:
        return total
    return max(1, min(total - 1, int(total * train_ratio)))


def _write_xml_dataset_pair(
    planned: _PlannedXmlDatasetPair, paths: XmlDatasetPaths, classes: Sequence[str]
) -> None:
    """Copy one source image and write its converted YOLO label."""
    image_dir = paths.images_train if planned.split == "train" else paths.images_val
    label_dir = paths.labels_train if planned.split == "train" else paths.labels_val
    image_path = planned.pair.image_path
    xml_path = planned.pair.xml_path
    annotation = parse_voc_xml_text(xml_path.read_text(encoding="utf-8"))
    label_text = voc_objects_to_yolo_label_text(
        annotation.objects,
        annotation.image_size,
        classes,
    )
    shutil.copy2(image_path, image_dir / image_path.name)
    (label_dir / f"{image_path.stem}.txt").write_text(label_text, encoding="utf-8")


def _write_xml_dataset_classes(classes_path: Path, classes: Sequence[str]) -> None:
    """Write classes.txt with one class per line."""
    classes_path.write_text("".join(f"{name}\n" for name in classes), encoding="utf-8")


def _write_xml_dataset_yaml(
    data_yaml: Path, dataset_dir: Path, classes: Sequence[str]
) -> None:
    """Write the small YOLO data.yaml file."""
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
    data_yaml.write_text(content, encoding="utf-8")


def _yaml_single_quote(value: str) -> str:
    """Return a minimal single-quoted YAML scalar."""
    return "'" + value.replace("'", "''") + "'"


def _find_image_for_txt(txt_path: Path) -> Path | None:
    """Find a same-stem image for a YOLO TXT file."""
    candidates = [
        path
        for path in txt_path.parent.iterdir()
        if path.is_file()
        and path.stem == txt_path.stem
        and path.suffix.lower() in _SUPPORTED_IMAGE_SUFFIXES
    ]
    if not candidates:
        return None
    suffix_order = {
        suffix: index for index, suffix in enumerate(_SUPPORTED_IMAGE_SUFFIXES)
    }
    return sorted(
        candidates, key=lambda path: (suffix_order[path.suffix.lower()], path.name)
    )[0]


def _read_image_size(image_path: Path) -> _ImageSize:
    """Read image dimensions with Pillow."""
    with Image.open(image_path) as image:
        width, height = image.size
        return _ImageSize(width=width, height=height, depth=len(image.getbands()) or 3)


def _read_yolo_boxes(txt_path: Path, classes: list[str]) -> list[_YoloBox]:
    """Parse YOLO TXT annotation rows."""
    boxes: list[_YoloBox] = []
    for line_number, line in enumerate(
        txt_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) < 5:
            raise ConvertError("YOLO 行格式无效", details=f"{txt_path}:{line_number}")
        try:
            class_id = int(parts[0])
            values = [float(value) for value in parts[1:5]]
        except ValueError as exc:
            raise ConvertError(
                "YOLO 行格式无效", details=f"{txt_path}:{line_number}"
            ) from exc
        if class_id < 0 or class_id >= len(classes):
            raise ConvertClassIdOutOfRangeError(
                "类别 id 超出范围",
                details=f"{txt_path}:{line_number}: {class_id}",
            )
        boxes.append(
            _YoloBox(
                class_id=class_id,
                x_center=values[0],
                y_center=values[1],
                width=values[2],
                height=values[3],
            )
        )
    return boxes


def _voc_xml_text(
    image_path: Path, size: _ImageSize, boxes: list[_YoloBox], classes: list[str]
) -> str:
    """Build VOC XML text without an XML declaration."""
    root = ElementTree.Element("annotation")
    ElementTree.SubElement(root, "folder").text = image_path.parent.name
    ElementTree.SubElement(root, "filename").text = image_path.name
    ElementTree.SubElement(root, "path").text = str(image_path)
    source = ElementTree.SubElement(root, "source")
    ElementTree.SubElement(source, "database").text = "Unknown"
    size_node = ElementTree.SubElement(root, "size")
    ElementTree.SubElement(size_node, "width").text = str(size.width)
    ElementTree.SubElement(size_node, "height").text = str(size.height)
    ElementTree.SubElement(size_node, "depth").text = str(size.depth)
    ElementTree.SubElement(root, "segmented").text = "0"
    for box in boxes:
        _append_object(root, box, size, classes)
    return ElementTree.tostring(root, encoding="unicode", short_empty_elements=False)


def _append_object(
    root: ElementTree.Element, box: _YoloBox, size: _ImageSize, classes: list[str]
) -> None:
    """Append one VOC object node."""
    xmin = round((box.x_center - box.width / 2) * size.width)
    ymin = round((box.y_center - box.height / 2) * size.height)
    xmax = round((box.x_center + box.width / 2) * size.width)
    ymax = round((box.y_center + box.height / 2) * size.height)
    xmin = max(0, min(size.width, xmin))
    ymin = max(0, min(size.height, ymin))
    xmax = max(0, min(size.width, xmax))
    ymax = max(0, min(size.height, ymax))
    if xmax <= xmin or ymax <= ymin:
        raise ConvertError("YOLO 标注框无效")
    obj = ElementTree.SubElement(root, "object")
    ElementTree.SubElement(obj, "name").text = classes[box.class_id]
    ElementTree.SubElement(obj, "pose").text = "Unspecified"
    ElementTree.SubElement(obj, "truncated").text = "0"
    ElementTree.SubElement(obj, "difficult").text = "0"
    bndbox = ElementTree.SubElement(obj, "bndbox")
    ElementTree.SubElement(bndbox, "xmin").text = str(xmin)
    ElementTree.SubElement(bndbox, "ymin").text = str(ymin)
    ElementTree.SubElement(bndbox, "xmax").text = str(xmax)
    ElementTree.SubElement(bndbox, "ymax").text = str(ymax)


def _xml_to_yolo_lines(xml_path: Path, classes: list[str]) -> list[str]:
    """Convert VOC XML object nodes to YOLO lines."""
    root = ElementTree.parse(xml_path).getroot()
    width = _positive_float(root.findtext("size/width"), "width", xml_path)
    height = _positive_float(root.findtext("size/height"), "height", xml_path)
    return [
        _xml_object_to_line(obj, classes, width, height, xml_path)
        for obj in root.findall("object")
    ]


def _xml_object_to_line(
    obj: ElementTree.Element,
    classes: list[str],
    width: float,
    height: float,
    xml_path: Path,
) -> str:
    """Convert one VOC object to a YOLO line."""
    class_name = (obj.findtext("name") or "").strip()
    if class_name not in classes:
        raise ConvertXmlParseError(
            "XML 类别不存在", details=f"{xml_path}: {class_name}"
        )
    xmin = _float_text(obj.findtext("bndbox/xmin"), "xmin", xml_path)
    ymin = _float_text(obj.findtext("bndbox/ymin"), "ymin", xml_path)
    xmax = _float_text(obj.findtext("bndbox/xmax"), "xmax", xml_path)
    ymax = _float_text(obj.findtext("bndbox/ymax"), "ymax", xml_path)
    if xmax <= xmin or ymax <= ymin:
        raise ConvertXmlParseError("XML 标注框无效", details=str(xml_path))
    x_center = ((xmin + xmax) / 2) / width
    y_center = ((ymin + ymax) / 2) / height
    box_width = (xmax - xmin) / width
    box_height = (ymax - ymin) / height
    class_id = classes.index(class_name)
    return f"{class_id} {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}"


def _positive_float(text: str | None, field_name: str, xml_path: Path) -> float:
    """Parse a positive XML float."""
    value = _float_text(text, field_name, xml_path)
    if value <= 0:
        raise ConvertXmlParseError("XML 尺寸无效", details=f"{xml_path}: {field_name}")
    return value


def _float_text(text: str | None, field_name: str, xml_path: Path) -> float:
    """Parse a required XML float."""
    if text is None or not text.strip():
        raise ConvertXmlParseError("XML 字段缺失", details=f"{xml_path}: {field_name}")
    try:
        return float(text)
    except ValueError as exc:
        raise ConvertXmlParseError(
            "XML 字段无效", details=f"{xml_path}: {field_name}"
        ) from exc
