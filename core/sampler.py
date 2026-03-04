"""
AutoLabeler 抽样模块
负责从各产品文件夹抽取样本图片
支持已有标注样本优先抽取
"""

import random
import shutil
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from .base import BaseModule
from utils.mapping_manager import MappingManager
from utils.exceptions import SampleError
from core.converter import Converter

logger = logging.getLogger(__name__)


@dataclass
class SampleConfig:
    """抽样配置"""
    mode: str = "count"        # count / ratio / mixed
    count: int = 40            # 固定数量模式的数量
    ratio: float = 0.3         # 比例模式的比例
    min_count: int = 20        # 混合模式最小数量
    max_count: int = 50        # 混合模式最大数量
    full_threshold: int = 35   # 低于此数量全部抽取
    train_ratio: float = 0.9   # 训练集比例
    pre_labeled_priority: bool = True  # 是否优先抽取已标注样本


class Sampler(BaseModule):
    """
    抽样模块
    负责从各产品文件夹抽取样本图片
    支持已有标注样本（VOC XML/YOLO TXT）优先抽取
    """

    # 支持的标注格式
    SUPPORTED_LABEL_FORMATS = {'.xml', '.txt'}

    def __init__(self, config: SampleConfig = None):
        super().__init__()
        self.config = config or SampleConfig()
        self.converter = Converter()
        self._temp_conversion_dir: Optional[Path] = None

    def sample(
        self,
        mapping: MappingManager,
        site_folder: Path,
        output_dir: Path
    ) -> None:
        """
        执行抽样

        Args:
            mapping: 映射管理器
            site_folder: 站点文件夹
            output_dir: 输出目录（database目录）
        """
        self.reset()

        # 创建目录结构
        (output_dir / "images" / "train").mkdir(parents=True, exist_ok=True)
        (output_dir / "images" / "vals").mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / "train").mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / "vals").mkdir(parents=True, exist_ok=True)

        # 创建临时转换目录
        self._temp_conversion_dir = output_dir / ".temp_conversion"
        self._temp_conversion_dir.mkdir(exist_ok=True)

        # 获取类别列表
        classes = mapping.get_class_list()

        # 按产品分组，区分已标注和未标注
        products = self._group_by_product_with_labels(mapping, site_folder)

        # 计算总工作量
        total_samples = 0
        sample_plan = {}  # {product_key: {"labeled": [...], "unlabeled": [...]}}

        for product_key, product_data in products.items():
            labeled = product_data["labeled"]
            unlabeled = product_data["unlabeled"]
            target_count = self._calculate_sample_count(len(labeled) + len(unlabeled))

            # 优先抽取已标注样本
            # 所有已标注样本必须被抽取，不计入 target_count 限制
            if self.config.pre_labeled_priority:
                # 所有已标注样本都要抽取
                sampled_labeled = labeled
                # 再根据目标数量补充未标注样本
                needed = max(0, target_count - len(labeled))
                if needed > 0:
                    sampled_unlabeled = random.sample(
                        unlabeled, min(needed, len(unlabeled))
                    )
                else:
                    sampled_unlabeled = []
            else:
                # 不优先抽取，按原逻辑随机抽取
                all_images = labeled + unlabeled
                sampled = random.sample(all_images, min(target_count, len(all_images)))
                # 区分已标注和未标注
                sampled_labeled = [img for img in sampled if img in labeled]
                sampled_unlabeled = [img for img in sampled if img in unlabeled]

            sample_plan[product_key] = {
                "labeled": sampled_labeled,
                "unlabeled": sampled_unlabeled
            }
            total_samples += len(sampled_labeled) + len(sampled_unlabeled)

        # 执行抽样
        processed = 0
        for product_key, plan in sample_plan.items():
            for encoded_name in plan["labeled"] + plan["unlabeled"]:
                if self.is_cancelled:
                    break

                img_info = mapping.data.images[encoded_name]
                src_path = site_folder / img_info["original_relative"]

                # 决定放入 train 还是 vals
                split = "train" if random.random() < self.config.train_ratio else "vals"
                dst_img_path = output_dir / "images" / split / encoded_name

                # 复制图片
                shutil.copy2(src_path, dst_img_path)

                # 处理标注文件
                label_source = img_info.get("label_source", "none")
                if label_source in ("pre_existing_xml", "pre_existing_txt"):
                    # 复制已有标注
                    self._copy_existing_label(
                        site_folder, img_info, output_dir / "labels" / split,
                        classes, encoded_name
                    )
                # 无预标注时跳过，不创建空文件（用户标注时由 LabelImg 自动创建）

                # 更新映射（使用 mark_sampled 方法以确保统计正确更新）
                mapping.mark_sampled(encoded_name, split)

                processed += 1
                if processed % 10 == 0 or processed == total_samples:
                    self.report_progress(processed, total_samples, f"抽样: {encoded_name}")

        # 清理临时转换目录
        if self._temp_conversion_dir.exists():
            shutil.rmtree(self._temp_conversion_dir, ignore_errors=True)

        # 保存映射和配置
        with mapping._local_lock:
            mapping.data.config = {
                "sample_mode": self.config.mode,
                "sample_count": self.config.count,
                "sample_ratio": self.config.ratio,
                "full_threshold": self.config.full_threshold,
                "train_ratio": self.config.train_ratio,
                "pre_labeled_priority": self.config.pre_labeled_priority
            }

        mapping.save()

        # 生成 data.yaml
        self._generate_data_yaml(output_dir, mapping)

    def _group_by_product_with_labels(
        self,
        mapping: MappingManager,
        site_folder: Path
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        按产品分组图片，区分已标注和未标注

        Returns:
            {
                "CodeA/ProductA": {
                    "labeled": [encoded_name1, ...],  # 已标注
                    "unlabeled": [encoded_name2, ...]  # 未标注
                },
                ...
            }
        """
        products = {}

        for encoded_name, info in mapping.data.images.items():
            # 只分组未被抽样的图片
            if info.get("sampled", False):
                continue

            key = f"{info['code']}/{info['product']}"
            if key not in products:
                products[key] = {"labeled": [], "unlabeled": []}

            # 检测是否有已有标注
            label_source = self._detect_existing_label(site_folder, info)

            # 更新映射中的 label_source
            with mapping._local_lock:
                mapping.data.images[encoded_name]["label_source"] = label_source

            if label_source != "none":
                products[key]["labeled"].append(encoded_name)
            else:
                products[key]["unlabeled"].append(encoded_name)

        return products

    def _detect_existing_label(
        self,
        site_folder: Path,
        img_info: Dict
    ) -> str:
        """
        检测图片是否有已有标注文件
        如果标注文件为空（无标签），会删除该文件并返回 "none"

        Args:
            site_folder: 站点文件夹
            img_info: 图片信息字典

        Returns:
            标注来源: "none" | "pre_existing_xml" | "pre_existing_txt"
        """
        # 构建图片路径
        img_path = site_folder / img_info["original_relative"]

        # 检查是否存在同名的 .xml 文件
        xml_path = img_path.with_suffix('.xml')
        if xml_path.exists():
            # 检查 XML 文件是否为空（无对象标签）
            if self._is_empty_xml(xml_path):
                # 删除空标注文件
                try:
                    xml_path.unlink()
                    logger.info(f"删除空标注文件: {xml_path.relative_to(site_folder)}")
                except Exception as e:
                    logger.warning(f"删除空标注文件失败 {xml_path}: {e}")
                return "none"
            return "pre_existing_xml"

        # 检查是否存在同名的 .txt 文件
        txt_path = img_path.with_suffix('.txt')
        if txt_path.exists():
            # 验证是否为有效的标注文件（不是 classes.txt 等）
            if self._is_valid_label_file(txt_path):
                # 检查 TXT 文件是否为空
                if self._is_empty_txt(txt_path):
                    # 删除空标注文件
                    try:
                        txt_path.unlink()
                        logger.info(f"删除空标注文件: {txt_path.relative_to(site_folder)}")
                    except Exception as e:
                        logger.warning(f"删除空标注文件失败 {txt_path}: {e}")
                    return "none"
                return "pre_existing_txt"

        return "none"

    def _is_empty_xml(self, xml_path: Path) -> bool:
        """
        检查 XML 文件是否为空（无对象标签）

        Args:
            xml_path: XML 文件路径

        Returns:
            True 如果 XML 没有对象标签或对象标签为空
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            objects = root.findall("object")
            # 没有对象标签即为空
            return len(objects) == 0
        except ET.ParseError:
            # XML 解析失败，视为空文件
            return True
        except Exception:
            # 其他异常，视为空文件
            return True

    def _is_empty_txt(self, txt_path: Path) -> bool:
        """
        检查 TXT 文件是否为空（无标注内容）

        Args:
            txt_path: TXT 文件路径

        Returns:
            True 如果文件为空或只有空白字符
        """
        try:
            content = txt_path.read_text(encoding='utf-8').strip()
            return len(content) == 0
        except Exception:
            # 读取失败，视为空文件
            return True

    def _is_valid_label_file(self, txt_path: Path) -> bool:
        """判断 txt 文件是否为有效的标注文件"""
        # 排除已知的非标注文件名
        exclude_names = {
            'classes.txt', 'data.yaml', 'README.txt', 'readme.txt',
            'license.txt', 'LICENSE.txt', 'requirements.txt'
        }

        if txt_path.name in exclude_names:
            return False

        # 文件名包含特殊字符的通常是配置文件
        if txt_path.name.startswith('.'):
            return False

        return True

    def _copy_existing_label(
        self,
        site_folder: Path,
        img_info: Dict,
        dst_dir: Path,
        classes: List[str],
        encoded_name: str
    ) -> None:
        """
        复制已有标注文件到目标目录

        Args:
            site_folder: 站点文件夹
            img_info: 图片信息
            dst_dir: 目标目录
            classes: 类别列表
            encoded_name: 编码后的文件名
        """
        original_name = img_info["original_name"]
        label_source = img_info.get("label_source", "none")

        # 构建源标注文件路径
        img_path = site_folder / img_info["original_relative"]

        if label_source == "pre_existing_xml":
            # XML 文件，需要转换
            xml_path = img_path.with_suffix('.xml')
            txt_name = f"{encoded_name.rsplit('.', 1)[0]}.txt"
            dst_path = dst_dir / txt_name

            try:
                self.converter.xml_to_txt(xml_path, classes, dst_path)
            except Exception as e:
                # 转换失败，创建空文件
                dst_path.touch()
                raise SampleError(f"XML转换失败 {xml_path.name}: {str(e)}")

        elif label_source == "pre_existing_txt":
            # TXT 文件，直接复制
            txt_path = img_path.with_suffix('.txt')
            txt_name = f"{encoded_name.rsplit('.', 1)[0]}.txt"
            dst_path = dst_dir / txt_name

            shutil.copy2(txt_path, dst_path)

    def _calculate_sample_count(self, total: int) -> int:
        """计算应抽取的数量"""
        # 确定抽取数量基准：全抽阈值优先
        # 如果全抽阈值大于固定数量，以全抽阈值为基准
        if self.config.mode == "count":
            sample_count = max(self.config.count, self.config.full_threshold)
            if total <= sample_count:
                return total
            return sample_count
        elif self.config.mode == "ratio":
            if total <= self.config.full_threshold:
                return total
            return max(1, int(total * self.config.ratio))
        else:  # mixed
            if total <= self.config.full_threshold:
                return total
            ratio_count = int(total * self.config.ratio)
            return max(self.config.min_count, min(self.config.max_count, ratio_count))

    def _generate_data_yaml(self, output_dir: Path, mapping: MappingManager) -> None:
        """生成 YOLO data.yaml"""
        classes = mapping.get_class_list()
        content = f"""# Auto-generated by AutoLabeler
path: {output_dir.absolute()}
train: images/train
val: images/vals

nc: {len(classes)}

names:
"""
        for idx, name in enumerate(classes):
            content += f"  {idx}: {name}\n"

        with open(output_dir / "data.yaml", 'w', encoding='utf-8') as f:
            f.write(content)
