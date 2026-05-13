"""
AutoLabeler 扫描模块
负责扫描站点文件夹，建立图片索引
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Set, List, Dict
from .base import BaseModule
from utils.path_encoder import PathEncoder
from utils.mapping_manager import MappingManager, ImageInfo
from utils.exceptions import ScanError

logger = logging.getLogger(__name__)


class Scanner(BaseModule):
    """
    扫描模块
    负责扫描站点文件夹，建立图片索引
    """

    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp'}

    def __init__(self, supported_formats: Set[str] = None):
        super().__init__()
        self.formats = supported_formats or self.SUPPORTED_FORMATS
        self.encoder = PathEncoder()

    def scan(self, site_folder: Path, output_dir: Path = None) -> MappingManager:
        """
        扫描站点文件夹

        Args:
            site_folder: 站点文件夹路径
            output_dir: 输出目录，默认在站点文件夹下创建 .autolabeler 目录

        Returns:
            MappingManager: 包含扫描结果的映射管理器
        """
        self.reset()

        # 初始化输出目录
        output_dir = output_dir or (site_folder / ".autolabeler")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 创建映射管理器
        mapping = MappingManager(output_dir / "mapping.json")
        mapping.create_new(site_folder)

        # 收集所有图片
        images_to_scan = []
        codes = set()
        products = {}

        # 第一遍：收集所有图片路径
        for code_dir in site_folder.iterdir():
            if self.is_cancelled:
                break
            if not code_dir.is_dir():
                continue
            # 跳过隐藏文件夹（以 . 开头）
            if code_dir.name.startswith('.'):
                continue

            code_name = code_dir.name
            codes.add(code_name)
            products[code_name] = {}

            for product_dir in code_dir.iterdir():
                if self.is_cancelled:
                    break
                if not product_dir.is_dir():
                    continue

                product_name = product_dir.name
                product_images = []

                for img_file in product_dir.iterdir():
                    if self.is_cancelled:
                        break
                    if img_file.is_file() and img_file.suffix.lower() in self.formats:
                        product_images.append(img_file)

                if product_images:
                    products[code_name][product_name] = len(product_images)
                    images_to_scan.extend([
                        (code_name, product_name, img)
                        for img in product_images
                    ])

            if self.is_cancelled:
                break

        # 添加类别
        for idx, code_name in enumerate(sorted(codes)):
            mapping.add_class(idx, code_name)

        # 验证已有标注文件的标签与 Code 文件夹名称是否一致
        self._validate_existing_labels(site_folder, codes)

        # 第二遍：添加图片到映射
        total = len(images_to_scan)
        for i, (code, product, img_path) in enumerate(images_to_scan):
            if self.is_cancelled:
                break

            encoded_name = self.encoder.encode(code, product, img_path.name)
            relative_path = f"{code}/{product}/{img_path.name}"

            info = ImageInfo(
                original_relative=relative_path,
                code=code,
                product=product,
                original_name=img_path.name,
                format=img_path.suffix.lower()
            )
            mapping.add_image(encoded_name, info)

            if i % 100 == 0 or i == total - 1:
                self.report_progress(i + 1, total, f"正在扫描: {img_path.name}")

        # 更新统计信息
        with mapping._local_lock:
            mapping.data.statistics["total_codes"] = len(codes)
            mapping.data.statistics["total_products"] = sum(
                len(prods) for prods in products.values()
            )
            mapping.data.products = products

        # 保存
        mapping.save()

        # 生成 classes.txt
        self._save_classes(output_dir / "classes.txt", mapping.get_class_list())

        return mapping

    def _save_classes(self, path: Path, classes: list) -> None:
        """保存类别文件"""
        with open(path, 'w', encoding='utf-8') as f:
            for cls in classes:
                f.write(f"{cls}\n")

    def _validate_existing_labels(self, site_folder: Path, codes: Set[str]) -> None:
        """
        验证已有标注文件中的标签与 Code 文件夹名称是否一致

        Args:
            site_folder: 站点文件夹路径
            codes: 所有 Code 文件夹名称的集合

        Raises:
            ScanError: 如果发现标注文件中的标签与 Code 文件夹名称不一致
        """
        # 存储标签不一致的错误信息
        # 格式: {code_name: [(xml_path, [expected_label, actual_label]), ...]}
        mismatched_labels: Dict[str, List[tuple]] = {}

        for code_dir in site_folder.iterdir():
            if self.is_cancelled:
                break
            if not code_dir.is_dir() or code_dir.name.startswith('.'):
                continue

            code_name = code_dir.name
            if code_name not in codes:
                continue

            # 遍历该 Code 下的所有产品文件夹
            for product_dir in code_dir.iterdir():
                if self.is_cancelled:
                    break
                if not product_dir.is_dir():
                    continue

                # 查找该产品文件夹中的所有 XML 文件
                xml_files = list(product_dir.glob("*.xml"))

                for xml_file in xml_files:
                    if self.is_cancelled:
                        break

                    try:
                        # 获取 XML 中的所有标签名称
                        xml_labels = self._get_xml_labels(xml_file)

                        # 检查是否有标签与 code_name 不一致
                        for label in xml_labels:
                            if label != code_name:
                                if code_name not in mismatched_labels:
                                    mismatched_labels[code_name] = []
                                mismatched_labels[code_name].append(
                                    (xml_file.relative_to(site_folder), label)
                                )
                    except ET.ParseError as e:
                        logger.warning(f"无法解析 XML 文件 {xml_file}: {e}")
                    except Exception as e:
                        logger.warning(f"读取 XML 文件 {xml_file} 时出错: {e}")

        # 如果发现标签不一致，抛出异常
        if mismatched_labels:
            error_details = self._format_label_mismatch_error(mismatched_labels)
            raise ScanError(
                message="已有标注文件中的标签与 Code 文件夹名称不一致",
                details=error_details
            )

        logger.info("已有标注文件验证通过：所有标签与 Code 文件夹名称一致")

    def _get_xml_labels(self, xml_path: Path) -> Set[str]:
        """
        从 XML 文件中提取所有标签名称

        Args:
            xml_path: XML 文件路径

        Returns:
            标签名称的集合

        Raises:
            ET.ParseError: XML 解析失败
        """
        labels = set()
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for obj in root.findall("object"):
            name_elem = obj.find("name")
            if name_elem is not None and name_elem.text:
                labels.add(name_elem.text.strip())

        return labels

    def _format_label_mismatch_error(self, mismatched_labels: Dict[str, List[tuple]]) -> str:
        """
        格式化标签不匹配的错误信息

        Args:
            mismatched_labels: 标签不匹配的信息字典

        Returns:
            格式化的错误信息字符串
        """
        lines = ["\n发现以下标注文件的标签与 Code 文件夹名称不一致：\n"]

        for code_name, issues in mismatched_labels.items():
            lines.append(f"Code 文件夹: '{code_name}' (期望的标签)")
            lines.append("-" * 60)

            # 去重并排序
            unique_issues = {}
            for xml_path, label in issues:
                if xml_path not in unique_issues:
                    unique_issues[xml_path] = set()
                unique_issues[xml_path].add(label)

            for xml_path, labels in sorted(unique_issues.items()):
                labels_str = ", ".join(f"'{l}'" for l in sorted(labels))
                lines.append(f"  文件: {xml_path}")
                lines.append(f"    检测到标签: {labels_str}")
                lines.append("")

        lines.append("请检查并修正标注文件，确保标签名称与 Code 文件夹名称一致。")
        lines.append("\n提示：Code 文件夹名称即为该文件夹下所有图片的正确标注类别。")

        return "\n".join(lines)
