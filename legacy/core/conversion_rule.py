"""
Code转换规则模块

负责管理站点特定的Code转换规则，支持原始code与转换后code之间的互相转换。
"""

from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field
import yaml


@dataclass
class ConversionMapping:
    """Code转换映射规则"""
    original_code_prefix: str          # 原始code前缀
    converted_code_prefix: str         # 转换后code前缀
    pro_pattern: List[str] = field(default_factory=list)  # 产品型号列表（["*"]表示全部）
    exclude_products: List[str] = field(default_factory=list)  # 排除的产品列表


@dataclass
class ConversionConfig:
    """站点转换配置"""
    site_name: str = ""
    description: str = ""
    product_mappings: List[ConversionMapping] = field(default_factory=list)


class ConversionRule:
    """
    Code转换规则管理器
    负责加载站点配置，提供原始code与转换后code的互相转换
    """

    def __init__(self, config_path: Path = None):
        """
        初始化转换规则管理器

        Args:
            config_path: 配置文件路径，为空时使用default规则
        """
        self.config_path = config_path
        self.config: ConversionConfig = ConversionConfig()
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                mappings = []
                for m in data.get('product_mappings', []):
                    mappings.append(ConversionMapping(
                        original_code_prefix=m['original_code_prefix'],
                        converted_code_prefix=m['converted_code_prefix'],
                        pro_pattern=m.get('pro_pattern', ['*']),
                        exclude_products=m.get('exclude_products', [])
                    ))

                self.config = ConversionConfig(
                    site_name=data.get('site_name', ''),
                    description=data.get('description', ''),
                    product_mappings=mappings
                )
            except Exception as e:
                # 配置文件加载失败，使用默认配置
                self.config = ConversionConfig(
                    site_name='default',
                    description='默认站点，无Code转换',
                    product_mappings=[]
                )
        else:
            # 默认配置：无转换规则
            self.config = ConversionConfig(
                site_name='default',
                description='默认站点，无Code转换',
                product_mappings=[]
            )

    def get_original_code(self, current_code: str, product: str) -> str:
        """
        获取原始code（转换后code → 原始code）

        Args:
            current_code: 当前的code名称
            product: 产品名称（如H4A238HDF13）

        Returns:
            原始code名称
        """
        if not self.config.product_mappings:
            return current_code

        # 提取产品型号（第4-6位）
        pro = self._extract_pro(product)

        for mapping in self.config.product_mappings:
            # 检查是否匹配
            if not self._match_pro(pro, mapping):
                continue

            # 检查是否在排除列表
            if mapping.exclude_products and pro in mapping.exclude_products:
                continue

            # 检查当前code是否匹配转换后的code
            if current_code.startswith(mapping.converted_code_prefix):
                # 提取后缀部分（如_P, _G, _S等）
                suffix = current_code[len(mapping.converted_code_prefix):]
                return mapping.original_code_prefix + suffix

        return current_code

    def get_converted_code(self, original_code: str, product: str) -> str:
        """
        获取转换后code（原始code → 转换后code）

        Args:
            original_code: 原始code名称
            product: 产品名称

        Returns:
            转换后code名称
        """
        if not self.config.product_mappings:
            return original_code

        pro = self._extract_pro(product)

        for mapping in self.config.product_mappings:
            if not self._match_pro(pro, mapping):
                continue

            if mapping.exclude_products and pro in mapping.exclude_products:
                continue

            if original_code.startswith(mapping.original_code_prefix):
                suffix = original_code[len(mapping.original_code_prefix):]
                return mapping.converted_code_prefix + suffix

        return original_code

    def _extract_pro(self, product: str) -> str:
        """从产品名称中提取型号（H4A238HDF13 → 238）"""
        if len(product) >= 6:
            return product[3:6]
        return product

    def _match_pro(self, pro: str, mapping: ConversionMapping) -> bool:
        """判断产品是否匹配规则"""
        return "*" in mapping.pro_pattern or pro in mapping.pro_pattern

    @classmethod
    def load(cls, site_type: str) -> 'ConversionRule':
        """
        加载指定站点的转换规则

        Args:
            site_type: 站点类型（如"A9950"）

        Returns:
            ConversionRule实例
        """
        config_dir = Path(__file__).parent.parent / "config"
        config_path = config_dir / f"{site_type}_conversion_rules.yaml"

        if config_path.exists():
            return cls(config_path)
        else:
            return cls(None)

    def needs_conversion(self, code: str, product: str) -> bool:
        """
        判断是否需要转换

        Args:
            code: 当前code
            product: 产品名称

        Returns:
            是否需要转换
        """
        original = self.get_original_code(code, product)
        return original != code

    def get_site_name(self) -> str:
        """获取站点名称"""
        return self.config.site_name
