"""
AutoLabeler 还原模块
将标注文件还原回原始目录
支持从 database/labels/ 和 inference_results/ 还原
"""

import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
from .base import BaseModule
from utils.path_encoder import PathEncoder
from utils.mapping_manager import MappingManager
from utils.exceptions import RestoreError


@dataclass
class RestoreResult:
    """还原结果"""
    total: int = 0
    success: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class Restorer(BaseModule):
    """
    还原模块
    将标注文件还原回原始目录
    支持两种来源：
    1. database/labels/ (人工标注)
    2. inference_results/run_xxx/ (推理结果)
    """

    def __init__(self):
        super().__init__()
        self.encoder = PathEncoder()

    def restore(
        self,
        mapping: MappingManager,
        database_dir: Path,
        site_folder: Path
    ) -> RestoreResult:
        """
        从 database/labels/ 还原标注文件

        Args:
            mapping: 映射管理器
            database_dir: database目录（包含labels文件夹）
            site_folder: 站点文件夹

        Returns:
            RestoreResult: 还原结果统计
        """
        self.reset()
        result = RestoreResult()

        # 收集所有需要还原的标注文件
        label_files = []
        for split in ["train", "vals"]:
            labels_dir = database_dir / "labels" / split
            if labels_dir.exists():
                label_files.extend(list(labels_dir.glob("*.txt")))

        result.total = len(label_files)

        if result.total == 0:
            self.report_progress(1, 1, "没有需要还原的标注文件")
            return result

        # 逐个还原
        for i, label_file in enumerate(label_files):
            if self.is_cancelled:
                break

            encoded_stem = label_file.stem  # 不含扩展名

            # 从 mapping 中查找该编码对应的图片信息
            img_info, full_encoded_name = self._find_image_info(mapping, encoded_stem)

            if not img_info:
                result.failed += 1
                result.errors.append(f"在映射中找不到: {encoded_stem}")
                continue

            # 构建目标路径
            original_name = img_info["original_name"]
            code = img_info["code"]
            product = img_info["product"]
            txt_name = Path(original_name).stem + ".txt"
            dst_path = site_folder / code / product / txt_name

            # 检查是否已还原过
            if img_info.get("restored", False) or dst_path.exists():
                result.skipped += 1
                continue

            # 确保目标目录存在
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            # 复制文件
            try:
                shutil.copy2(label_file, dst_path)
                result.success += 1

                # 更新映射
                mapping.mark_restored(full_encoded_name)

            except Exception as e:
                result.failed += 1
                result.errors.append(f"复制失败 {label_file.name}: {str(e)}")

            if (i + 1) % 10 == 0 or i + 1 == result.total:
                self.report_progress(i + 1, result.total, f"还原: {txt_name}")

        # 批量保存
        if result.success > 0:
            mapping.save()

        return result

    def restore_from_inference(
        self,
        mapping: MappingManager,
        inference_run_dir: Path,
        site_folder: Path
    ) -> RestoreResult:
        """
        从推理结果目录还原标注到原位置

        Args:
            mapping: 映射管理器
            inference_run_dir: 推理结果目录（如 .../inference_results/run_xxx）
            site_folder: 站点文件夹

        Returns:
            RestoreResult: 还原结果统计
        """
        self.reset()
        result = RestoreResult()

        # 验证推理目录
        if not inference_run_dir.exists():
            result.failed = 0
            result.errors.append(f"推理目录不存在: {inference_run_dir}")
            return result

        # 读取推理配置
        config_path = inference_run_dir / "inference_config.json"
        if config_path.exists():
            try:
                import json
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                # 可以在这里验证配置
            except Exception:
                pass  # 配置文件可选

        # 收集所有待还原的标注文件
        txt_files = list(inference_run_dir.glob("**/*.txt"))
        # 排除配置文件
        txt_files = [f for f in txt_files if f.name != "inference_config.json"]

        result.total = len(txt_files)

        if result.total == 0:
            self.report_progress(1, 1, "没有需要还原的标注文件")
            return result

        # 逐个还原
        for i, txt_file in enumerate(txt_files):
            if self.is_cancelled:
                break

            # 从文件路径反推图片信息
            # txt_file: run_xxx/CodeA/ProductA/IMG_001.txt
            try:
                relative_parts = txt_file.relative_to(inference_run_dir).parts
                if len(relative_parts) < 3:
                    result.failed += 1
                    result.errors.append(f"路径格式不正确: {txt_file}")
                    continue

                code = relative_parts[0]
                product = relative_parts[1]
                txt_filename = relative_parts[2]

                # 在 mapping 中查找匹配的图片
                encoded_name = self._find_encoded_name(
                    mapping, code, product, txt_filename
                )

                if not encoded_name:
                    result.failed += 1
                    result.errors.append(f"找不到匹配: {code}/{product}/{txt_filename}")
                    continue

                # 获取图片信息
                img_info = mapping.get_image_info(encoded_name)
                if not img_info:
                    result.failed += 1
                    result.errors.append(f"获取图片信息失败: {encoded_name}")
                    continue

                # 构建目标路径
                original_name = img_info["original_name"]
                txt_name = Path(original_name).stem + ".txt"
                dst_path = site_folder / code / product / txt_name

                # 检查是否已还原过
                if img_info.get("restored", False) or dst_path.exists():
                    result.skipped += 1
                    continue

                # 确保目标目录存在
                dst_path.parent.mkdir(parents=True, exist_ok=True)

                # 复制文件
                shutil.copy2(txt_file, dst_path)
                result.success += 1

                # 更新映射
                mapping.mark_restored(encoded_name)

            except Exception as e:
                result.failed += 1
                result.errors.append(f"还原失败 {txt_file.name}: {str(e)}")

            if (i + 1) % 10 == 0 or i + 1 == result.total:
                self.report_progress(i + 1, result.total, f"还原: {txt_filename}")

        # 批量保存
        if result.success > 0:
            mapping.save()

        return result

    def _find_image_info(
        self,
        mapping: MappingManager,
        encoded_stem: str
    ) -> tuple:
        """
        查找图片信息

        Returns:
            (img_info, full_encoded_name) 或 (None, None)
        """
        # 首先尝试直接使用 encoded_stem（可能已包含扩展名）
        info = mapping.get_image_info(encoded_stem)
        if info:
            return info, encoded_stem

        # 如果没找到，尝试添加扩展名
        for ext in [".jpg", ".jpeg", ".png", ".bmp"]:
            candidate = encoded_stem + ext
            info = mapping.get_image_info(candidate)
            if info:
                return info, candidate

        return None, None

    def _find_encoded_name(
        self,
        mapping: MappingManager,
        code: str,
        product: str,
        txt_filename: str
    ) -> Optional[str]:
        """
        根据 code/product/txt_filename 查找 encoded_name

        Args:
            mapping: 映射管理器
            code: Code名称
            product: 产品名称
            txt_filename: 标注文件名（如 IMG_001.txt）

        Returns:
            encoded_name 或 None
        """
        target_stem = Path(txt_filename).stem

        for encoded_name, info in mapping.data.images.items():
            if (info.get("code") == code and
                info.get("product") == product and
                Path(info.get("original_name", "")).stem == target_stem):
                return encoded_name
        return None
