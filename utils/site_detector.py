"""
站点类型检测工具

通过特征文件或Code文件夹结构自动识别站点类型
"""

from pathlib import Path
from typing import Optional
import yaml


class SiteDetector:
    """
    站点类型检测工具
    通过特征文件或Code文件夹结构自动识别站点类型
    """

    # 各站点的特征code标识
    SITE_INDICATORS = {
        'A9950': ['AS_CV_PI', 'T1_SP_PI', 'M2_SP_PI_G'],
    }

    @staticmethod
    def detect(site_folder: Path) -> str:
        """
        检测站点类型

        Args:
            site_folder: 站点文件夹路径

        Returns:
            站点类型标识（如"A9950"、"default"）
        """
        # 方法1: 检查配置文件
        config_file = site_folder / ".autolabeler" / "site_config.yaml"
        if config_file.exists():
            return SiteDetector._read_site_type(config_file)

        # 方法2: 检测Code文件夹特征
        return SiteDetector._detect_by_codes(site_folder)

    @staticmethod
    def _read_site_type(config_path: Path) -> str:
        """从配置文件读取站点类型"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('site_type', 'default')
        except Exception:
            return 'default'

    @staticmethod
    def _detect_by_codes(site_folder: Path) -> str:
        """通过Code文件夹特征检测站点类型"""
        # 收集所有code文件夹名称
        code_folders = []
        for item in site_folder.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                code_folders.append(item.name)

        # 检查各站点特征
        for site_type, indicators in SiteDetector.SITE_INDICATORS.items():
            for indicator in indicators:
                for code in code_folders:
                    if indicator in code:
                        return site_type

        return 'default'

    @staticmethod
    def save_site_config(site_folder: Path, site_type: str) -> None:
        """
        保存站点配置文件

        Args:
            site_folder: 站点文件夹路径
            site_type: 站点类型
        """
        config_dir = site_folder / ".autolabeler"
        config_dir.mkdir(parents=True, exist_ok=True)

        config_file = config_dir / "site_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump({'site_type': site_type}, f, allow_unicode=True)

    @staticmethod
    def get_config_path(site_folder: Path) -> Path:
        """
        获取站点配置文件路径

        Args:
            site_folder: 站点文件夹路径

        Returns:
            配置文件路径
        """
        return site_folder / ".autolabeler" / "site_config.yaml"
