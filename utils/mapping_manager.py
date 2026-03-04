"""
AutoLabeler 映射文件管理器
负责 mapping.json 的创建、读取、更新、保存
支持线程安全的文件操作
"""

import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import sys


# Windows 文件锁兼容
if sys.platform == 'win32':
    import msvcrt

    class FileLock:
        """Windows 文件锁"""
        def __init__(self, f):
            self.f = f
            self.locked = False

        def acquire(self):
            try:
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
                self.locked = True
            except IOError:
                raise IOError("无法获取文件锁")

        def release(self):
            if self.locked:
                try:
                    msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
                self.locked = False

        def __enter__(self):
            self.acquire()
            return self

        def __exit__(self, *args):
            self.release()
else:
    import fcntl

    class FileLock:
        """Unix 文件锁"""
        def __init__(self, f):
            self.f = f

        def acquire(self):
            fcntl.flock(self.f.fileno(), fcntl.LOCK_EX)

        def release(self):
            fcntl.flock(self.f.fileno(), fcntl.LOCK_UN)

        def __enter__(self):
            self.acquire()
            return self

        def __exit__(self, *args):
            self.release()


@dataclass
class ImageInfo:
    """单张图片的信息"""
    original_relative: str      # 相对路径
    code: str                   # Code名称
    product: str                # 产品名称
    original_name: str          # 原始文件名
    format: str                 # 文件格式 (如 ".jpg")
    sampled: bool = False       # 是否已抽样
    split: Optional[str] = None # train/vals/None
    manual_labeled: bool = False # 是否已人工标注
    inferred: bool = False      # 是否已推理
    restored: bool = False      # 是否已还原
    label_source: str = "none"  # 标注来源: none/pre_existing_xml/pre_existing_txt/manual_later/auto_inferred


@dataclass
class MappingData:
    """完整的映射数据结构"""
    version: str = "1.0"
    project_name: str = ""
    site_folder: str = ""
    created_time: str = ""
    updated_time: str = ""
    classes: Dict[str, str] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, int] = field(default_factory=dict)
    images: Dict[str, Dict] = field(default_factory=dict)
    products: Dict[str, Dict] = field(default_factory=dict)


# 全局锁，用于保护所有 MappingManager 实例的文件操作
_global_mapping_lock = threading.RLock()


class MappingManager:
    """
    映射文件管理器
    负责 mapping.json 的创建、读取、更新、保存
    支持线程安全的文件操作
    """

    def __init__(self, mapping_path: Path = None):
        """
        初始化管理器

        Args:
            mapping_path: mapping.json 文件路径
        """
        self.mapping_path = mapping_path
        self.data: Optional[MappingData] = None
        self._dirty = False  # 是否有未保存的修改
        self._local_lock = threading.RLock()  # 实例级别的锁

    def create_new(self, site_folder: Path, project_name: str = None) -> 'MappingManager':
        """
        创建新的映射数据

        Args:
            site_folder: 站点文件夹路径
            project_name: 项目名称，默认使用文件夹名
        """
        with self._local_lock:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.data = MappingData(
                project_name=project_name or site_folder.name,
                site_folder=str(site_folder.absolute()),
                created_time=now,
                updated_time=now,
                statistics={
                    "total_images": 0,
                    "total_codes": 0,
                    "total_products": 0,
                    "sampled_count": 0,
                    "labeled_count": 0,
                    "inferred_count": 0,
                    "restored_count": 0
                }
            )
            self._dirty = True
        return self

    def load(self) -> 'MappingManager':
        """从文件加载映射数据（线程安全）"""
        with self._local_lock, _global_mapping_lock:
            if not self.mapping_path or not self.mapping_path.exists():
                raise FileNotFoundError(f"Mapping file not found: {self.mapping_path}")

            with open(self.mapping_path, 'r', encoding='utf-8') as f:
                with FileLock(f):
                    raw_data = json.load(f)

            self.data = MappingData(**raw_data)
            self._dirty = False
        return self

    def save(self, path: Path = None) -> None:
        """
        保存映射数据到文件（线程安全）

        Args:
            path: 保存路径，默认使用初始化时的路径
        """
        save_path = path or self.mapping_path
        if not save_path:
            raise ValueError("No save path specified")

        with self._local_lock, _global_mapping_lock:
            self.data.updated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 先写入临时文件，然后原子性替换
            temp_path = save_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                with FileLock(f):
                    json.dump(asdict(self.data), f, indent=2, ensure_ascii=False)

            # 原子性替换
            temp_path.replace(save_path)

            self._dirty = False

    def add_image(self, encoded_name: str, info: ImageInfo) -> None:
        """添加图片到映射"""
        with self._local_lock:
            self.data.images[encoded_name] = asdict(info)
            self._update_statistics()
            self._dirty = True

    def add_class(self, class_id: int, class_name: str) -> None:
        """添加类别"""
        with self._local_lock:
            self.data.classes[str(class_id)] = class_name
            self._dirty = True

    def mark_sampled(self, encoded_name: str, split: str) -> None:
        """标记图片已被抽样"""
        with self._local_lock:
            if encoded_name in self.data.images:
                self.data.images[encoded_name]["sampled"] = True
                self.data.images[encoded_name]["split"] = split
                self._update_statistics()
                self._dirty = True

    def mark_labeled(self, encoded_name: str) -> None:
        """标记图片已被人工标注"""
        with self._local_lock:
            if encoded_name in self.data.images:
                self.data.images[encoded_name]["manual_labeled"] = True
                self._update_statistics()
                self._dirty = True

    def mark_inferred(self, encoded_name: str) -> None:
        """标记图片已被推理标注"""
        with self._local_lock:
            if encoded_name in self.data.images:
                self.data.images[encoded_name]["inferred"] = True
                self._update_statistics()
                self._dirty = True

    def mark_restored(self, encoded_name: str) -> None:
        """标记标注文件已还原"""
        with self._local_lock:
            if encoded_name in self.data.images:
                self.data.images[encoded_name]["restored"] = True
                self._update_statistics()
                self._dirty = True

    def get_image_info(self, encoded_name: str) -> Optional[Dict]:
        """获取图片信息"""
        with self._local_lock:
            return self.data.images.get(encoded_name)

    def get_unsampled_images(self) -> List[Dict]:
        """获取未被抽样的图片列表"""
        with self._local_lock:
            return [
                {"encoded_name": k, **v}
                for k, v in self.data.images.items()
                if not v.get("sampled", False)
            ]

    def get_pending_inference_images(self) -> List[Dict]:
        """
        获取待推理的图片列表（未被抽样的图片）

        注意：不再检查 inferred 字段，允许用户多次推理并对比不同参数效果
        推理结果保存在时间戳目录，还原时由用户选择使用哪次结果

        Returns:
            待推理的图片列表（sampled=false）
        """
        with self._local_lock:
            return [
                {"encoded_name": k, **v}
                for k, v in self.data.images.items()
                if not v.get("sampled", False)
            ]

    def get_sampled_images(self, split: str = None) -> List[Dict]:
        """
        获取已抽样的图片列表

        Args:
            split: 筛选数据集类型 (train/vals)，None则返回全部
        """
        with self._local_lock:
            result = []
            for k, v in self.data.images.items():
                if v.get("sampled", False):
                    if split is None or v.get("split") == split:
                        result.append({"encoded_name": k, **v})
            return result

    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        with self._local_lock:
            return self.data.statistics.copy()

    def get_classes(self) -> Dict[str, str]:
        """获取类别映射"""
        with self._local_lock:
            return self.data.classes.copy()

    def get_class_list(self) -> List[str]:
        """获取类别名称列表（按ID排序）"""
        with self._local_lock:
            sorted_items = sorted(self.data.classes.items(), key=lambda x: int(x[0]))
            return [name for _, name in sorted_items]

    def _update_statistics(self) -> None:
        """更新统计信息"""
        images = self.data.images
        self.data.statistics.update({
            "total_images": len(images),
            "sampled_count": sum(1 for v in images.values() if v.get("sampled")),
            "labeled_count": sum(1 for v in images.values() if v.get("manual_labeled")),
            "inferred_count": sum(1 for v in images.values() if v.get("inferred")),
            "restored_count": sum(1 for v in images.values() if v.get("restored")),
        })

    @property
    def is_dirty(self) -> bool:
        """是否有未保存的修改"""
        with self._local_lock:
            return self._dirty
