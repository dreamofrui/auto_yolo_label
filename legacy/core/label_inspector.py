"""
AutoLabeler 标签检查器
浏览推理结果并启动 LabelImg 查看标注
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class InferenceRun:
    """推理运行记录"""
    name: str
    path: Path
    config_exists: bool


@dataclass
class ProductInfo:
    """产品信息"""
    code: str
    product: str
    label_count: int
    path: Path


class LabelInspector:
    """
    标签检查器
    扫描推理结果目录，提供浏览和查询功能
    """

    def __init__(self, site_dir: Path):
        """
        初始化标签检查器

        Args:
            site_dir: 站点目录路径
        """
        self.site_dir = Path(site_dir)
        self.inference_base = self.site_dir / ".autolabeler" / "inference_results"

    def get_inference_runs(self) -> List[InferenceRun]:
        """
        获取所有推理运行记录

        Returns:
            推理运行记录列表，按时间倒序排列
        """
        if not self.inference_base.exists():
            return []

        runs = []
        for run_dir in self.inference_base.glob("run_*"):
            if not run_dir.is_dir():
                continue

            config_path = run_dir / "inference_config.json"
            runs.append(InferenceRun(
                name=run_dir.name,
                path=run_dir,
                config_exists=config_path.exists()
            ))

        # 按名称排序（名称包含时间戳）
        runs.sort(key=lambda x: x.name, reverse=True)
        return runs

    def get_code_product_tree(self, run_name: str) -> Dict[str, List[ProductInfo]]:
        """
        获取指定推理运行的 Code/Product 树结构

        Args:
            run_name: 推理运行名称

        Returns:
            字典：{code: [product_info_list]}
        """
        run_dir = self.inference_base / run_name
        if not run_dir.exists():
            return {}

        tree = {}
        for code_dir in sorted(run_dir.iterdir()):
            if not code_dir.is_dir():
                continue

            products = []
            for product_dir in sorted(code_dir.iterdir()):
                if not product_dir.is_dir():
                    continue

                # 统计 txt 文件数量（排除 classes.txt）
                txt_count = len([
                    f for f in product_dir.glob("*.txt")
                    if f.name != "classes.txt"
                ])

                products.append(ProductInfo(
                    code=code_dir.name,
                    product=product_dir.name,
                    label_count=txt_count,
                    path=product_dir
                ))

            if products:
                tree[code_dir.name] = products

        return tree

    def get_product_path(self, run_name: str, code: str, product: str) -> Optional[Path]:
        """
        获取产品标签目录路径

        Args:
            run_name: 推理运行名称
            code: Code 名称
            product: Product 名称

        Returns:
            产品标签目录路径，不存在则返回 None
        """
        product_path = self.inference_base / run_name / code / product
        return product_path if product_path.exists() else None

    def validate_selection(self, run_name: str, code: str, product: str) -> Tuple[bool, str]:
        """
        验证选择是否有效

        Args:
            run_name: 推理运行名称
            code: Code 名称
            product: Product 名称

        Returns:
            (是否有效, 错误消息)
        """
        product_path = self.get_product_path(run_name, code, product)
        if product_path is None:
            return False, f"路径不存在: {run_name}/{code}/{product}"
        return True, ""
