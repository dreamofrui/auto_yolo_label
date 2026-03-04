"""
AutoLabeler 格式转换模块
将 YOLO txt 格式转换为 VOC xml 格式
"""

from pathlib import Path
from typing import List, Tuple, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom
from dataclasses import dataclass, field
from .base import BaseModule
from utils.image_utils import get_image_size
from utils.exceptions import ConvertError


@dataclass
class ConvertResult:
    """转换结果"""
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class Converter(BaseModule):
    """
    格式转换模块
    YOLO txt 格式 ↔ VOC xml 格式
    """

    # 支持的图片格式
    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp'}

    def __init__(self):
        super().__init__()

    def xml_to_txt(
        self,
        xml_path: Path,
        classes: List[str],
        output_path: Optional[Path] = None
    ) -> None:
        """
        将单个 VOC xml 转换为 YOLO txt

        Args:
            xml_path: xml文件路径
            classes: 类别列表（用于将类别名称映射到ID）
            output_path: 输出路径，默认与xml同目录同名

        Raises:
            ConvertError: 转换失败时抛出
        """
        output_path = output_path or xml_path.with_suffix('.txt')

        if not xml_path.exists():
            raise ConvertError(f"XML文件不存在: {xml_path}")

        # 解析 XML
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except Exception as e:
            raise ConvertError(f"无法解析XML文件: {xml_path}", str(e))

        # 获取图片尺寸
        size_elem = root.find("size")
        if size_elem is None:
            raise ConvertError(f"XML文件缺少size元素: {xml_path}")

        try:
            width = int(size_elem.find("width").text)
            height = int(size_elem.find("height").text)
        except (AttributeError, ValueError) as e:
            raise ConvertError(f"无法读取图片尺寸: {xml_path}", str(e))

        # 构建类别名称到ID的映射
        class_to_id = {name: idx for idx, name in enumerate(classes)}

        # 转换标注
        lines = []
        for obj in root.findall("object"):
            # 获取类别名称
            name_elem = obj.find("name")
            if name_elem is None:
                continue
            class_name = name_elem.text

            # 验证类别
            if class_name not in class_to_id:
                raise ConvertError(
                    f"未知类别 '{class_name}' 在文件 {xml_path}。"
                    f"有效类别: {list(classes)}"
                )
            cls_id = class_to_id[class_name]

            # 获取边界框
            bndbox = obj.find("bndbox")
            if bndbox is None:
                continue

            try:
                xmin = float(bndbox.find("xmin").text)
                ymin = float(bndbox.find("ymin").text)
                xmax = float(bndbox.find("xmax").text)
                ymax = float(bndbox.find("ymax").text)
            except (AttributeError, ValueError):
                continue

            # 转换为 YOLO 格式（归一化坐标）
            x_center = ((xmin + xmax) / 2) / width
            y_center = ((ymin + ymax) / 2) / height
            box_width = (xmax - xmin) / width
            box_height = (ymax - ymin) / height

            # 边界检查（确保在 [0, 1] 范围内）
            x_center = max(0.0, min(1.0, x_center))
            y_center = max(0.0, min(1.0, y_center))
            box_width = max(0.0, min(1.0, box_width))
            box_height = max(0.0, min(1.0, box_height))

            lines.append(
                f"{cls_id} {x_center:.6f} {y_center:.6f} "
                f"{box_width:.6f} {box_height:.6f}"
            )

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        # 空标注也创建文件
        if not lines:
            output_path.touch()

    def convert_folder(
        self,
        folder: Path,
        classes: List[str],
        recursive: bool = True
    ) -> ConvertResult:
        """
        转换文件夹中的所有标注

        Args:
            folder: 目标文件夹
            classes: 类别列表
            recursive: 是否递归处理子文件夹

        Returns:
            ConvertResult: 转换结果统计
        """
        self.reset()
        result = ConvertResult()

        if not folder.exists():
            result.failed = 0
            result.errors.append(f"文件夹不存在: {folder}")
            return result

        # 收集所有 txt 文件
        pattern = "**/*.txt" if recursive else "*.txt"
        txt_files = list(folder.glob(pattern))

        # 过滤掉非标注文件（如 classes.txt 等）
        txt_files = [f for f in txt_files if self._is_annotation_file(f)]

        result.total = len(txt_files)

        if result.total == 0:
            self.report_progress(1, 1, "没有找到需要转换的标注文件")
            return result

        for i, txt_file in enumerate(txt_files):
            if self.is_cancelled:
                break

            try:
                # 查找对应的图片
                img_path = self._find_image(txt_file)
                if not img_path:
                    result.skipped += 1
                    result.errors.append(f"找不到对应图片: {txt_file.name}")
                    continue

                # 转换
                xml_path = txt_file.with_suffix('.xml')
                self.txt_to_xml(txt_file, img_path, classes, xml_path)

                # 删除原 txt 文件
                if xml_path.exists():
                    try:
                        txt_file.unlink()
                    except Exception:
                        pass  # 如果删除失败也不影响转换结果

                result.success += 1

            except Exception as e:
                result.failed += 1
                result.errors.append(f"转换失败 {txt_file.name}: {str(e)}")

            if (i + 1) % 10 == 0 or i + 1 == result.total:
                self.report_progress(i + 1, result.total, f"转换: {txt_file.name}")

        return result

    def txt_to_xml(
        self,
        txt_path: Path,
        img_path: Path,
        classes: List[str],
        output_path: Optional[Path] = None
    ) -> None:
        """
        将单个 YOLO txt 转换为 VOC xml

        Args:
            txt_path: txt文件路径
            img_path: 图片路径
            classes: 类别列表
            output_path: 输出路径，默认与txt同目录同名

        Raises:
            ConvertError: 转换失败时抛出
        """
        output_path = output_path or txt_path.with_suffix('.xml')

        # 获取图片尺寸
        try:
            width, height, depth = get_image_size(img_path)
        except Exception as e:
            raise ConvertError(f"无法读取图片尺寸: {img_path}", str(e))

        # 读取标注
        annotations = self._parse_yolo_txt(txt_path, width, height)

        # 构建 XML
        root = ET.Element("annotation")

        ET.SubElement(root, "folder").text = str(img_path.parent.name)
        ET.SubElement(root, "filename").text = img_path.name
        ET.SubElement(root, "path").text = str(img_path.absolute())

        source = ET.SubElement(root, "source")
        ET.SubElement(source, "database").text = "AutoLabeler"

        size = ET.SubElement(root, "size")
        ET.SubElement(size, "width").text = str(width)
        ET.SubElement(size, "height").text = str(height)
        ET.SubElement(size, "depth").text = str(depth)

        ET.SubElement(root, "segmented").text = "0"

        # 添加目标对象
        for ann in annotations:
            cls_id, xmin, ymin, xmax, ymax = ann
            cls_name = classes[cls_id] if cls_id < len(classes) else f"class_{cls_id}"

            obj = ET.SubElement(root, "object")
            ET.SubElement(obj, "name").text = cls_name
            ET.SubElement(obj, "pose").text = "Unspecified"
            ET.SubElement(obj, "truncated").text = "0"
            ET.SubElement(obj, "difficult").text = "0"

            bndbox = ET.SubElement(obj, "bndbox")
            ET.SubElement(bndbox, "xmin").text = str(xmin)
            ET.SubElement(bndbox, "ymin").text = str(ymin)
            ET.SubElement(bndbox, "xmax").text = str(xmax)
            ET.SubElement(bndbox, "ymax").text = str(ymax)

        # 格式化输出
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
        # 移除空行
        xml_str = '\n'.join([line for line in xml_str.split('\n') if line.strip()])
        # 移除 XML 声明行（第一行）
        lines = xml_str.split('\n')
        if lines and lines[0].startswith('<?xml'):
            lines = lines[1:]
        xml_str = '\n'.join(lines)

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)

    def _parse_yolo_txt(
        self,
        txt_path: Path,
        img_width: int,
        img_height: int
    ) -> List[Tuple[int, int, int, int, int]]:
        """
        解析 YOLO txt 文件

        Args:
            txt_path: txt文件路径
            img_width: 图片宽度
            img_height: 图片高度

        Returns:
            [(class_id, xmin, ymin, xmax, ymax), ...]
        """
        annotations = []

        if not txt_path.exists():
            return annotations

        with open(txt_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) < 5:
                    # 跳过格式不正确的行
                    continue

                try:
                    cls_id = int(parts[0])
                    x_center = float(parts[1])
                    y_center = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])
                except (ValueError, IndexError):
                    # 跳过解析失败的行
                    continue

                # 转换为像素坐标（整数）
                xmin = int(round((x_center - width / 2) * img_width))
                ymin = int(round((y_center - height / 2) * img_height))
                xmax = int(round((x_center + width / 2) * img_width))
                ymax = int(round((y_center + height / 2) * img_height))

                # 边界检查
                xmin = max(0, xmin)
                ymin = max(0, ymin)
                xmax = min(img_width, xmax)
                ymax = min(img_height, ymax)

                # 检查边界框是否有效
                if xmax > xmin and ymax > ymin:
                    annotations.append((cls_id, xmin, ymin, xmax, ymax))

        return annotations

    def _find_image(self, txt_path: Path) -> Optional[Path]:
        """
        查找 txt 对应的图片文件

        Args:
            txt_path: txt文件路径

        Returns:
            图片路径，找不到返回 None
        """
        for ext in self.SUPPORTED_IMAGE_FORMATS:
            img_path = txt_path.with_suffix(ext)
            if img_path.exists():
                return img_path
        return None

    def _is_annotation_file(self, txt_path: Path) -> bool:
        """
        判断 txt 文件是否为标注文件

        排除一些非标注文件（如 classes.txt, data.yaml 等）

        Args:
            txt_path: txt文件路径

        Returns:
            是否为标注文件
        """
        # 排除已知的非标注文件名
        exclude_names = {
            'classes.txt', 'data.yaml', 'README.txt', 'readme.txt',
            'license.txt', 'LICENSE.txt', 'requirements.txt'
        }

        if txt_path.name in exclude_names:
            return False

        # 排除 YAML 文件
        if txt_path.suffix == '.yaml' or txt_path.suffix == '.yml':
            return False

        return True
