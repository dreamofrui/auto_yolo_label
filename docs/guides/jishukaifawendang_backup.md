# 文档二：技术开发文档

```markdown
# AutoLabeler 智能标注工具 - 技术开发文档

| 文档信息 | |
|---------|---------|
| 文档版本 | v1.0 |
| 创建日期 | 2024-01-15 |
| 文档状态 | 初稿 |

---

## 1. 技术选型

### 1.1 技术栈总览

| 层次 | 技术选型 | 版本要求 | 选型理由 |
|------|----------|----------|----------|
| 编程语言 | Python | 3.11 | YOLO生态完善，开发效率高 |
| GUI框架 | PySide6 | ≥6.5 | Qt官方绑定，跨平台，稳定 |
| UI组件库 | QFluentWidgets | ≥1.4 | 现代化Fluent风格，开箱即用 |
| 目标检测 | Ultralytics YOLO | 8.3.236 | 业界主流，API友好 |
| 图像处理 | Pillow / OpenCV | - | 图片读取与尺寸获取 |
| 配置管理 | PyYAML | - | YAML格式配置文件解析 |
| 数据序列化 | json (标准库) | - | mapping文件读写 |
| XML处理 | xml.etree (标准库) | - | VOC格式生成 |

### 1.2 开发环境要求

```yaml
# 开发环境
Python: 3.11
Python解释器：D:\miniforge3\envs\yolo\python.exe 
IDE: PyCharm / VSCode
OS: Windows 10/11

# GPU环境（可选）
CUDA: ≥11.7
cuDNN: ≥8.5
显卡: NVIDIA GTX 1060 及以上
```

### 1.3 依赖包清单

```txt
# requirements.txt

# GUI
PySide6>=6.5.0
PySide6-Fluent-Widgets>=1.4.0

# 深度学习
ultralytics>=8.3.236
torch>=2.0.0
torchvision>=0.15.0

# 图像处理
Pillow>=9.0.0
opencv-python>=4.7.0

# 配置与工具
PyYAML>=6.0
tqdm>=4.65.0

# 开发工具
pytest>=7.0.0  # 测试
black>=23.0.0  # 代码格式化
```

---

## 2. 系统架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AutoLabeler 系统架构                            │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   GUI Layer     │
                              │  (PySide6 +     │
                              │   QFluentWidgets)│
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │  Controller     │
                              │  (页面控制器)    │
                              └────────┬────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│  Core Module  │            │  Core Module  │            │  Core Module  │
│   Scanner     │            │   Sampler     │            │   Trainer     │
└───────────────┘            └───────────────┘            └───────────────┘
        │                              │                              │
        ▼                              ▼                              ▼
┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│  Core Module  │            │  Core Module  │            │  Core Module  │
│  Inferencer   │            │   Restorer    │            │   Converter   │
└───────────────┘            └───────────────┘            └───────────────┘
        │                              │                              │
        └──────────────────────────────┼──────────────────────────────┘
                                       │
                              ┌────────▼────────┐
                              │  Utils Layer    │
                              │ ┌─────────────┐ │
                              │ │PathEncoder  │ │
                              │ │MappingMgr   │ │
                              │ │FileHandler  │ │
                              │ │ConfigMgr   │ │
                              │ └─────────────┘ │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │  File System    │
                              └─────────────────┘
```

### 2.2 分层说明

| 层次 | 职责 | 主要组件 |
|------|------|----------|
| GUI Layer | 用户界面展示与交互 | 主窗口、各功能页面、自定义组件 |
| Controller | 业务流程控制、GUI与Core的桥梁 | 页面控制器、信号槽管理 |
| Core Module | 核心业务逻辑实现 | 6大功能模块 |
| Utils Layer | 通用工具与基础设施 | 路径编码、映射管理、文件操作、配置管理 |

---

## 3. 项目结构

```
AutoLabeler/
│
├── main.py                          # 程序入口
├── requirements.txt                 # 依赖清单
├── README.md                        # 项目说明
│
├── config/                          # 配置模块
│   ├── __init__.py
│   ├── settings.py                  # 配置类定义（Settings单例）
│   └── default_config.yaml          # 默认配置模板
│
├── core/                            # 核心业务模块
│   ├── __init__.py
│   ├── base.py                      # 模块基类（定义通用接口）
│   ├── scanner.py                   # 扫描模块
│   ├── sampler.py                   # 抽样模块
│   ├── trainer.py                   # 训练模块
│   ├── inferencer.py                # 推理模块
│   ├── restorer.py                  # 还原模块
│   └── converter.py                 # 格式转换模块
│
├── utils/                           # 工具模块
│   ├── __init__.py
│   ├── path_encoder.py              # 路径编码/解码器
│   ├── mapping_manager.py           # mapping.json 管理器（带线程安全）
│   ├── device.py                    # 设备检测与管理
│   ├── image_utils.py               # 图片工具（读取尺寸等）
│   ├── exceptions.py                # 自定义异常
│   ├── file_handler.py              # 文件操作封装
│   └── validators.py                # 输入校验器
│
├── config/                          # 配置模块
│   ├── __init__.py
│   ├── settings.py                  # 配置类定义（Settings单例）
│   └── default_config.yaml          # 默认配置模板
│
├── gui/                             # 图形界面模块
│   ├── __init__.py
│   ├── app.py                       # QApplication 封装
│   ├── main_window.py               # 主窗口
│   │
│   ├── pages/                       # 功能页面
│   │   ├── __init__.py
│   │   ├── base_page.py             # 页面基类
│   │   ├── home_page.py             # 首页
│   │   ├── scan_page.py             # 扫描页
│   │   ├── sample_page.py           # 抽样页
│   │   ├── train_page.py            # 训练页
│   │   ├── inference_page.py        # 推理页
│   │   ├── restore_page.py          # 还原页
│   │   ├── convert_page.py          # 转换页
│   │   └── settings_page.py         # 设置页
│   │
│   ├── widgets/                     # 自定义组件
│   │   ├── __init__.py
│   │   ├── folder_picker.py         # 文件夹选择器
│   │   ├── progress_card.py         # 进度卡片
│   │   ├── log_viewer.py            # 日志查看器
│   │   ├── stats_card.py            # 统计卡片
│   │   └── step_indicator.py        # 步骤指示器
│   │
│   ├── workers/                     # 后台工作线程
│   │   ├── __init__.py
│   │   ├── base_worker.py           # Worker基类
│   │   ├── scan_worker.py           # 扫描线程
│   │   ├── sample_worker.py         # 抽样线程
│   │   ├── train_worker.py          # 训练线程
│   │   ├── inference_worker.py      # 推理线程
│   │   └── restore_worker.py        # 还原线程
│   │
│   └── styles/                      # 样式资源
│       ├── __init__.py
│       └── theme.py                 # 主题配置
│
├── resources/                       # 静态资源
│   ├── icons/                       # 图标文件
│   │   ├── logo.png
│   │   ├── scan.svg
│   │   └── ...
│   └── templates/                   # 模板文件
│       └── annotation_template.xml  # XML模板
│
└── tests/                           # 单元测试
    ├── __init__.py
    ├── test_path_encoder.py
    ├── test_mapping_manager.py
    ├── test_scanner.py
    ├── test_sampler.py
    └── ...
```

---

## 4. 核心模块设计

### 4.1 模块基类

```python
# core/base.py

from abc import ABC, abstractmethod
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class ProgressInfo:
    """进度信息"""
    current: int           # 当前进度
    total: int             # 总数
    message: str           # 进度消息
    percentage: float      # 百分比 0-100


class BaseModule(ABC):
    """核心模块基类"""
    
    def __init__(self):
        self._progress_callback: Optional[Callable[[ProgressInfo], None]] = None
        self._is_cancelled: bool = False
    
    def set_progress_callback(self, callback: Callable[[ProgressInfo], None]):
        """设置进度回调函数"""
        self._progress_callback = callback
    
    def report_progress(self, current: int, total: int, message: str = ""):
        """报告进度"""
        if self._progress_callback:
            info = ProgressInfo(
                current=current,
                total=total,
                message=message,
                percentage=round(current / total * 100, 2) if total > 0 else 0
            )
            self._progress_callback(info)
    
    def cancel(self):
        """取消操作"""
        self._is_cancelled = True
    
    def reset(self):
        """重置状态"""
        self._is_cancelled = False
    
    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled
```

### 4.2 路径编码器

```python
# utils/path_encoder.py

from pathlib import Path
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class DecodedPath:
    """解码后的路径信息"""
    code: str
    product: str
    filename: str
    extension: str


class PathEncoder:
    """
    路径编码器
    负责将 Code/Product/Filename 三级路径编码为单一文件名，以及反向解码
    """
    
    DEFAULT_SEPARATOR = "__"
    
    def __init__(self, separator: str = None):
        """
        初始化编码器
        
        Args:
            separator: 路径层级分隔符，默认 "__"
        """
        self.separator = separator or self.DEFAULT_SEPARATOR
    
    def encode(self, code: str, product: str, filename: str) -> str:
        """
        将路径编码为文件名
        
        Args:
            code: Code文件夹名
            product: 产品文件夹名
            filename: 原始文件名
            
        Returns:
            编码后的文件名
            
        Example:
            encode("AS_CV_PI_P", "H4A238FDF04", "IMG_001.jpg")
            -> "AS_CV_PI_P__H4A238FDF04__IMG_001.jpg"
        """
        name, ext = self._split_extension(filename)
        encoded = f"{code}{self.separator}{product}{self.separator}{name}{ext}"
        return encoded
    
    def decode(self, encoded_name: str) -> Optional[DecodedPath]:
        """
        解码文件名为路径组件
        
        Args:
            encoded_name: 编码后的文件名
            
        Returns:
            DecodedPath 对象，解码失败返回 None
            
        Example:
            decode("AS_CV_PI_P__H4A238FDF04__IMG_001.jpg")
            -> DecodedPath(code="AS_CV_PI_P", product="H4A238FDF04", 
                          filename="IMG_001.jpg", extension=".jpg")
        """
        name, ext = self._split_extension(encoded_name)
        parts = name.split(self.separator)
        
        if len(parts) < 3:
            return None
        
        code = parts[0]
        product = parts[1]
        original_name = self.separator.join(parts[2:]) + ext
        
        return DecodedPath(
            code=code,
            product=product,
            filename=original_name,
            extension=ext
        )
    
    def to_relative_path(self, encoded_name: str) -> Optional[Path]:
        """
        将编码文件名转换为相对路径
        
        Returns:
            Path对象: Code/Product/Filename
        """
        decoded = self.decode(encoded_name)
        if not decoded:
            return None
        return Path(decoded.code) / decoded.product / decoded.filename
    
    def _split_extension(self, filename: str) -> Tuple[str, str]:
        """分离文件名和扩展名"""
        p = Path(filename)
        return p.stem, p.suffix
```

### 4.3 映射管理器（带线程安全）

```python
# utils/mapping_manager.py

import json
import threading
import fcntl  # Unix 文件锁，Windows 使用 msvcrt
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import sys

# Windows 文件锁兼容
if sys.platform == 'win32':
    import msvcrt
    import os

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
                msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
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
```

### 4.4 图片工具模块（新增）

```python
# utils/image_utils.py

from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def get_image_size(image_path: Path) -> Tuple[int, int, int]:
    """
    获取图片尺寸信息

    Args:
        image_path: 图片文件路径

    Returns:
        (width, height, depth) 元组
        - width: 图片宽度（像素）
        - height: 图片高度（像素）
        - depth: 通道数（通常为 3 表示 RGB）

    Raises:
        FileNotFoundError: 图片不存在
        IOError: 图片无法读取
    """
    if not image_path.exists():
        raise FileNotFoundError(f"图片不存在: {image_path}")

    try:
        with Image.open(image_path) as img:
            width, height = img.size
            # 获取模式以确定通道数
            mode = img.mode
            if mode in ('RGB', 'RGBA'):
                depth = 3 if mode == 'RGB' else 4
            elif mode == 'L':
                depth = 1
            elif mode == 'P':
                # 调色板模式，转换为 RGB 获取通道数
                depth = 3
            else:
                depth = 3  # 默认值

            return width, height, depth
    except Exception as e:
        raise IOError(f"无法读取图片 {image_path}: {str(e)}")


def validate_image(image_path: Path) -> bool:
    """
    验证图片文件是否有效

    Args:
        image_path: 图片文件路径

    Returns:
        True 如果图片有效，False 否则
    """
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def get_image_format(image_path: Path) -> Optional[str]:
    """
    获取图片格式

    Args:
        image_path: 图片文件路径

    Returns:
        格式字符串（如 "JPEG", "PNG"），无法识别返回 None
    """
    try:
        with Image.open(image_path) as img:
            return img.format
    except Exception:
        return None


class ImageInfo:
    """图片信息缓存类"""

    def __init__(self, path: Path):
        self.path = path
        self._width = None
        self._height = None
        self._depth = None
        self._format = None

    def load(self) -> bool:
        """加载图片信息"""
        try:
            self._width, self._height, self._depth = get_image_size(self.path)
            self._format = get_image_format(self.path)
            return True
        except Exception:
            return False

    @property
    def width(self) -> Optional[int]:
        if self._width is None:
            self.load()
        return self._width

    @property
    def height(self) -> Optional[int]:
        if self._height is None:
            self.load()
        return self._height

    @property
    def depth(self) -> Optional[int]:
        if self._depth is None:
            self.load()
        return self._depth

    @property
    def format(self) -> Optional[str]:
        if self._format is None:
            self.load()
        return self._format
```

### 4.5 异常处理模块（新增）

```python
# utils/exceptions.py

"""
AutoLabeler 自定义异常类
提供清晰的错误分类和错误信息
"""


class AutoLabelerError(Exception):
    """基础异常类"""

    def __init__(self, message: str, details: str = ""):
        self.message = message
        self.details = details
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class DeviceError(AutoLabelerError):
    """设备相关错误"""
    pass


class ScanError(AutoLabelerError):
    """扫描相关错误"""
    pass


class SampleError(AutoLabelerError):
    """抽样相关错误"""
    pass


class TrainError(AutoLabelerError):
    """训练相关错误"""
    pass


class InferenceError(AutoLabelerError):
    """推理相关错误"""
    pass


class RestoreError(AutoLabelerError):
    """还原相关错误"""
    pass


class ConvertError(AutoLabelerError):
    """格式转换相关错误"""
    pass


class MappingError(AutoLabelerError):
    """映射文件相关错误"""
    pass


class ValidationError(AutoLabelerError):
    """输入验证错误"""
    pass


class FileOperationError(AutoLabelerError):
    """文件操作错误"""
    pass


class ImageLoadError(AutoLabelerError):
    """图片加载错误"""
    pass
```

### 4.6 扫描模块

```python
# core/scanner.py

from pathlib import Path
from typing import Set
from .base import BaseModule
from utils.path_encoder import PathEncoder
from utils.mapping_manager import MappingManager, ImageInfo


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
            if not code_dir.is_dir() or code_dir.name.startswith('.'):
                continue

            code_name = code_dir.name
            codes.add(code_name)
            products[code_name] = {}

            for product_dir in code_dir.iterdir():
                if not product_dir.is_dir():
                    continue

                product_name = product_dir.name
                product_images = []

                for img_file in product_dir.iterdir():
                    if img_file.is_file() and img_file.suffix.lower() in self.formats:
                        product_images.append(img_file)

                if product_images:
                    products[code_name][product_name] = len(product_images)
                    images_to_scan.extend([
                        (code_name, product_name, img)
                        for img in product_images
                    ])

        # 添加类别
        for idx, code_name in enumerate(sorted(codes)):
            mapping.add_class(idx, code_name)

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
```

### 4.7 抽样模块

```python
# core/sampler.py

import random
import shutil
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from .base import BaseModule
from utils.mapping_manager import MappingManager


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


class Sampler(BaseModule):
    """
    抽样模块
    负责从各产品文件夹抽取样本图片
    """
    
    def __init__(self, config: SampleConfig = None):
        super().__init__()
        self.config = config or SampleConfig()
    
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
        
        # 按产品分组
        products = self._group_by_product(mapping)
        
        # 计算总工作量
        total_samples = 0
        sample_plan = {}  # {product_key: [encoded_names]}
        
        for product_key, images in products.items():
            count = self._calculate_sample_count(len(images))
            sampled = random.sample(images, min(count, len(images)))
            sample_plan[product_key] = sampled
            total_samples += len(sampled)
        
        # 执行抽样
        processed = 0
        for product_key, sampled_images in sample_plan.items():
            for encoded_name in sampled_images:
                if self.is_cancelled:
                    break
                
                img_info = mapping.data.images[encoded_name]
                src_path = site_folder / img_info["original_relative"]
                
                # 决定放入 train 还是 vals
                split = "train" if random.random() < self.config.train_ratio else "vals"
                dst_path = output_dir / "images" / split / encoded_name
                
                # 复制文件
                shutil.copy2(src_path, dst_path)
                
                # 更新映射
                mapping.mark_sampled(encoded_name, split)
                
                processed += 1
                if processed % 10 == 0 or processed == total_samples:
                    self.report_progress(processed, total_samples, f"抽样: {encoded_name}")
        
        # 保存映射和配置
        mapping.data.config = {
            "sample_mode": self.config.mode,
            "sample_count": self.config.count,
            "sample_ratio": self.config.ratio,
            "full_threshold": self.config.full_threshold,
            "train_ratio": self.config.train_ratio
        }
        mapping.save()
        
        # 生成 data.yaml
        self._generate_data_yaml(output_dir, mapping)
    
    def _group_by_product(self, mapping: MappingManager) -> Dict[str, List[str]]:
        """按产品分组图片"""
        products = {}
        for encoded_name, info in mapping.data.images.items():
            key = f"{info['code']}/{info['product']}"
            if key not in products:
                products[key] = []
            products[key].append(encoded_name)
        return products
    
    def _calculate_sample_count(self, total: int) -> int:
        """计算应抽取的数量"""
        if total <= self.config.full_threshold:
            return total
        
        if self.config.mode == "count":
            return self.config.count
        elif self.config.mode == "ratio":
            return max(1, int(total * self.config.ratio))
        else:  # mixed
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
```

### 4.8 设备管理模块

```python
# utils/device.py

import torch
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeviceInfo:
    """设备信息"""
    device: str                # "cpu" 或 "cuda"
    device_id: Optional[str]   # GPU ID，如 "0" 或 "0,1"
    is_available: bool         # 是否可用
    name: str                  # 设备名称
    memory: Optional[int]      # 显存大小（MB）


def get_device_info() -> DeviceInfo:
    """
    自动检测并返回最优设备信息

    Returns:
        DeviceInfo: 设备信息对象
    """
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)

        # 多GPU使用所有显卡
        device_id = ",".join(str(i) for i in range(gpu_count)) if gpu_count > 1 else "0"

        return DeviceInfo(
            device="cuda",
            device_id=device_id,
            is_available=True,
            name=f"{gpu_name} x{gpu_count}",
            memory=int(gpu_memory)
        )
    else:
        # 检查是否有 Apple Silicon (MPS)
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return DeviceInfo(
                device="mps",
                device_id=None,
                is_available=True,
                name="Apple Silicon GPU",
                memory=None
            )

        return DeviceInfo(
            device="cpu",
            device_id=None,
            is_available=True,
            name="CPU",
            memory=None
        )


def get_optimal_device() -> str:
    """
    获取最优设备字符串（用于传给 YOLO）

    Returns:
        设备字符串，如 "0" 或 "cpu"
    """
    info = get_device_info()
    if info.device == "cuda":
        return info.device_id or "0"
    elif info.device == "mps":
        return "mps"
    else:
        return "cpu"


def get_optimal_batch_size(device: str = None, image_size: int = 640) -> int:
    """
    根据设备自动计算最优 batch size

    Args:
        device: 设备类型，None 则自动检测
        image_size: 图片尺寸

    Returns:
        推荐的 batch size
    """
    if device is None:
        info = get_device_info()
    else:
        info = get_device_info()  # 简化处理

    if info.device == "cpu":
        return 8
    elif info.device == "cuda":
        # 根据显存估算
        if info.memory and info.memory >= 24000:  # 24GB+
            return 32
        elif info.memory and info.memory >= 12000:  # 12GB+
            return 16
        elif info.memory and info.memory >= 6000:   # 6GB+
            return 8
        else:
            return 4
    else:  # MPS or other
        return 16
```

### 4.9 训练模块

```python
# core/trainer.py

from pathlib import Path
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from .base import BaseModule
from utils.device import get_optimal_device, get_optimal_batch_size, get_device_info


@dataclass
class TrainConfig:
    """训练配置"""
    epochs: int = 100
    batch_size: int = -1        # -1 表示自动检测
    image_size: int = 640
    device: str = "auto"        # "auto" / "cpu" / "0" / "0,1" / "mps"
    patience: int = 50
    workers: int = 8
    optimizer: str = "AdamW"
    lr0: float = 0.01


class Trainer(BaseModule):
    """
    训练模块
    封装 YOLO 训练流程
    """

    def __init__(self, config: TrainConfig = None):
        super().__init__()
        self.config = config or TrainConfig()
        self.model = None
        self._device_info = None

    def _resolve_device(self) -> str:
        """
        解析最终使用的设备

        Returns:
            设备字符串
        """
        if self.config.device == "auto":
            return get_optimal_device()
        return self.config.device

    def _resolve_batch_size(self, device: str) -> int:
        """
        解析最终使用的 batch size

        Args:
            device: 设备字符串

        Returns:
            batch size 数值
        """
        if self.config.batch_size == -1:
            return get_optimal_batch_size(device, self.config.image_size)
        return self.config.batch_size

    def train(
        self,
        data_yaml: Path,
        base_model: Path,
        output_dir: Path,
        epoch_callback: Optional[Callable[[Dict], None]] = None
    ) -> Optional[Path]:
        """
        执行训练

        Args:
            data_yaml: 数据配置文件路径
            base_model: 基础模型路径 (yolo11m.pt)
            output_dir: 输出目录
            epoch_callback: 每个epoch结束时的回调

        Returns:
            best.pt 模型路径，训练取消或失败返回 None
        """
        from ultralytics import YOLO

        self.reset()

        # 检测设备信息
        self._device_info = get_device_info()
        device = self._resolve_device()
        batch_size = self._resolve_batch_size(device)

        # 报告设备信息
        self.report_progress(0, 1,
            f"使用设备: {self._device_info.name}, "
            f"Batch Size: {batch_size}"
        )

        # 加载模型
        self.model = YOLO(str(base_model))

        # 用于跟踪上一个 epoch，避免重复报告
        last_reported_epoch = [-1]  # 使用列表使其在闭包中可变

        # 构建回调
        def on_fit_epoch_end(trainer):
            """使用 on_fit_epoch_end 而非 on_train_epoch_end，避免重复调用"""
            if self.is_cancelled:
                raise KeyboardInterrupt("Training cancelled by user")

            epoch = trainer.epoch
            epochs = trainer.epochs

            # 只在 epoch 变化时报告
            if epoch != last_reported_epoch[0]:
                last_reported_epoch[0] = epoch

                # 获取指标
                metrics_dict = {}
                if hasattr(trainer, 'metrics'):
                    metrics = trainer.metrics
                    # 提取关键指标
                    if hasattr(metrics, 'box'):
                        metrics_dict['mAP50'] = float(metrics.box.map50)
                        metrics_dict['mAP50-95'] = float(metrics.box.map)

                self.report_progress(
                    epoch + 1, epochs,
                    f"Epoch {epoch+1}/{epochs} - "
                    f"mAP50: {metrics_dict.get('mAP50', 0):.3f}"
                )

                if epoch_callback:
                    epoch_callback({
                        "epoch": epoch + 1,
                        "total_epochs": epochs,
                        "metrics": metrics_dict
                    })

        # 添加回调
        self.model.add_callback("on_fit_epoch_end", on_fit_epoch_end)

        # 执行训练
        try:
            results = self.model.train(
                data=str(data_yaml),
                epochs=self.config.epochs,
                batch=batch_size,
                imgsz=self.config.image_size,
                device=device,
                patience=self.config.patience,
                workers=self.config.workers,
                optimizer=self.config.optimizer,
                lr0=self.config.lr0,
                project=str(output_dir),
                name="train",
                exist_ok=True,
                verbose=True
            )
        except KeyboardInterrupt:
            self.report_progress(0, 1, "训练已取消")
            return None
        except Exception as e:
            self.report_progress(0, 1, f"训练失败: {str(e)}")
            raise

        best_model = output_dir / "train" / "weights" / "best.pt"
        if best_model.exists():
            self.report_progress(1, 1, "训练完成")
            return best_model
        return None
```

### 4.10 推理模块

```python
# core/inferencer.py

from pathlib import Path
from typing import List
from dataclasses import dataclass
from .base import BaseModule
from utils.mapping_manager import MappingManager


@dataclass
class InferenceConfig:
    """推理配置"""
    confidence: float = 0.25
    iou: float = 0.45
    batch_size: int = 32


class Inferencer(BaseModule):
    """
    推理模块
    使用训练好的模型标注剩余图片
    """
    
    def __init__(self, config: InferenceConfig = None):
        super().__init__()
        self.config = config or InferenceConfig()
    
    def infer(
        self,
        model_path: Path,
        mapping: MappingManager,
        site_folder: Path
    ) -> int:
        """
        执行推理
        
        Args:
            model_path: 模型文件路径
            mapping: 映射管理器
            site_folder: 站点文件夹
            
        Returns:
            成功处理的图片数量
        """
        from ultralytics import YOLO
        
        self.reset()
        
        # 加载模型
        model = YOLO(str(model_path))
        
        # 获取未抽样的图片
        unsampled = mapping.get_unsampled_images()
        total = len(unsampled)
        
        if total == 0:
            self.report_progress(1, 1, "没有需要推理的图片")
            return 0
        
        # 构建图片路径列表
        image_paths = []
        encoded_names = []
        for img in unsampled:
            path = site_folder / img["original_relative"]
            if path.exists():
                image_paths.append(str(path))
                encoded_names.append(img["encoded_name"])
        
        # 批量推理
        processed = 0
        batch_size = self.config.batch_size
        
        for i in range(0, len(image_paths), batch_size):
            if self.is_cancelled:
                break
            
            batch_paths = image_paths[i:i+batch_size]
            batch_names = encoded_names[i:i+batch_size]
            
            # 执行推理
            results = model.predict(
                source=batch_paths,
                conf=self.config.confidence,
                iou=self.config.iou,
                save=False,
                verbose=False
            )
            
            # 保存标注结果
            for j, result in enumerate(results):
                img_path = Path(batch_paths[j])
                txt_path = img_path.with_suffix('.txt')
                
                # 写入标注
                self._save_yolo_txt(result, txt_path)
                
                # 更新映射
                mapping.mark_inferred(batch_names[j])
            
            processed += len(batch_paths)
            self.report_progress(
                processed, total, 
                f"推理进度: {processed}/{total}"
            )
        
        mapping.save()
        return processed
    
    def _save_yolo_txt(self, result, txt_path: Path) -> None:
        """保存 YOLO 格式标注文件"""
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            # 空标注也创建文件
            txt_path.touch()
            return
        
        lines = []
        for box in boxes:
            cls_id = int(box.cls[0])
            # 获取归一化的中心点坐标和宽高
            xywhn = box.xywhn[0].tolist()  # [x_center, y_center, width, height]
            line = f"{cls_id} {xywhn[0]:.6f} {xywhn[1]:.6f} {xywhn[2]:.6f} {xywhn[3]:.6f}"
            lines.append(line)
        
        with open(txt_path, 'w') as f:
            f.write('\n'.join(lines))
```

### 4.11 还原模块

```python
# core/restorer.py

import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple
from .base import BaseModule
from utils.path_encoder import PathEncoder
from utils.mapping_manager import MappingManager


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
    将抽样阶段的标注文件还原回原始目录
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
        执行还原

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

            encoded_stem = label_file.stem  # 不含扩展名，如 "AS_CV_PI_P__H4A238FDF04__IMG_001"

            # 从 mapping 中查找该编码对应的图片信息
            # 注意：我们需要查找所有可能的扩展名组合
            img_info = None
            full_encoded_name = None

            for ext in [".jpg", ".jpeg", ".png", ".bmp"]:
                candidate = encoded_stem + ext
                info = mapping.get_image_info(candidate)
                if info:
                    img_info = info
                    full_encoded_name = candidate
                    break

            if not img_info:
                result.failed += 1
                result.errors.append(f"在映射中找不到: {encoded_stem}")
                continue

            # 从 img_info 获取原始文件信息
            original_name = img_info["original_name"]
            original_ext = img_info["format"]  # 如 ".jpg"
            code = img_info["code"]
            product = img_info["product"]

            # 构建目标路径
            txt_name = Path(original_name).stem + ".txt"
            dst_path = site_folder / code / product / txt_name

            # 确保目标目录存在
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            # 复制文件
            try:
                shutil.copy2(label_file, dst_path)
                result.success += 1

                # 更新映射（使用找到的完整编码名）
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
```

### 4.12 格式转换模块

```python
# core/converter.py

from pathlib import Path
from typing import List, Tuple
import xml.etree.ElementTree as ET
from xml.dom import minidom
from dataclasses import dataclass
from .base import BaseModule
from utils.image_utils import get_image_size


@dataclass  
class ConvertResult:
    """转换结果"""
    total: int = 0
    success: int = 0
    failed: int = 0
    errors: list = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class Converter(BaseModule):
    """
    格式转换模块
    YOLO txt 格式 → VOC xml 格式
    """
    
    def __init__(self):
        super().__init__()
    
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
        """
        self.reset()
        result = ConvertResult()
        
        # 收集所有txt文件
        pattern = "**/*.txt" if recursive else "*.txt"
        txt_files = list(folder.glob(pattern))
        result.total = len(txt_files)
        
        for i, txt_file in enumerate(txt_files):
            if self.is_cancelled:
                break
            
            # 查找对应的图片
            img_path = self._find_image(txt_file)
            if not img_path:
                result.failed += 1
                result.errors.append(f"找不到对应图片: {txt_file}")
                continue
            
            try:
                xml_path = txt_file.with_suffix('.xml')
                self.txt_to_xml(txt_file, img_path, classes, xml_path)
                result.success += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(f"转换失败 {txt_file}: {str(e)}")
            
            if (i + 1) % 10 == 0 or i + 1 == result.total:
                self.report_progress(i + 1, result.total, f"转换: {txt_file.name}")
        
        return result
    
    def txt_to_xml(
        self,
        txt_path: Path,
        img_path: Path,
        classes: List[str],
        output_path: Path = None
    ) -> None:
        """
        将单个 YOLO txt 转换为 VOC xml
        
        Args:
            txt_path: txt文件路径
            img_path: 图片路径
            classes: 类别列表
            output_path: 输出路径，默认与txt同目录同名
        """
        output_path = output_path or txt_path.with_suffix('.xml')
        
        # 获取图片尺寸
        width, height, depth = get_image_size(img_path)
        
        # 读取标注
        annotations = self._parse_yolo_txt(txt_path, width, height)
        
        # 构建 XML
        root = ET.Element("annotation")
        
        ET.SubElement(root, "folder").text = img_path.parent.name
        ET.SubElement(root, "filename").text = img_path.name
        ET.SubElement(root, "path").text = str(img_path.absolute())
        
        source = ET.SubElement(root, "source")
        ET.SubElement(source, "database").text = "AutoLabeler"
        
        size = ET.SubElement(root, "size")
        ET.SubElement(size, "width").text = str(width)
        ET.SubElement(size, "height").text = str(height)
        ET.SubElement(size, "depth").text = str(depth)
        
        ET.SubElement(root, "segmented").text = "0"
        
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
        
        Returns:
            [(class_id, xmin, ymin, xmax, ymax), ...]
        """
        annotations = []
        
        with open(txt_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) < 5:
                    continue
                
                cls_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
                
                # 转换为像素坐标
                xmin = int((x_center - width / 2) * img_width)
                ymin = int((y_center - height / 2) * img_height)
                xmax = int((x_center + width / 2) * img_width)
                ymax = int((y_center + height / 2) * img_height)
                
                # 边界检查
                xmin = max(0, xmin)
                ymin = max(0, ymin)
                xmax = min(img_width, xmax)
                ymax = min(img_height, ymax)
                
                annotations.append((cls_id, xmin, ymin, xmax, ymax))
        
        return annotations
    
    def _find_image(self, txt_path: Path) -> Path:
        """查找txt对应的图片文件"""
        for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            img_path = txt_path.with_suffix(ext)
            if img_path.exists():
                return img_path
        return None
```

---

## 5. GUI 层设计

### 5.1 Worker 基类（后台线程）

```python
# gui/workers/base_worker.py

from PySide6.QtCore import QThread, Signal
from typing import Any


class BaseWorker(QThread):
    """
    后台工作线程基类
    所有耗时操作都应在Worker中执行，避免阻塞UI
    """
    
    # 信号定义
    progress = Signal(int, int, str)     # current, total, message
    finished = Signal(bool, object)       # success, result
    error = Signal(str)                   # error message
    log = Signal(str)                     # log message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_cancelled = False
    
    def cancel(self):
        """请求取消"""
        self._is_cancelled = True
    
    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled
    
    def report_progress(self, current: int, total: int, message: str = ""):
        """报告进度"""
        self.progress.emit(current, total, message)
    
    def report_log(self, message: str):
        """报告日志"""
        self.log.emit(message)
    
    def run(self):
        """线程执行入口（子类重写）"""
        raise NotImplementedError
```

### 5.2 页面基类

```python
# gui/pages/base_page.py

from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import ScrollArea


class BasePage(ScrollArea):
    """
    功能页面基类
    提供通用的布局和方法
    """
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        
        # 设置滚动区域
        self.setWidgetResizable(True)
        self.setStyleSheet("background: transparent;")
        
        # 内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(36, 20, 36, 20)
        self.content_layout.setSpacing(16)
        
        self.setWidget(self.content_widget)
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI（子类重写）"""
        pass
    
    def on_enter(self):
        """进入页面时调用（子类重写）"""
        pass
    
    def on_leave(self):
        """离开页面时调用（子类重写）"""
        pass
```

### 5.3 主窗口结构

```python
# gui/main_window.py

from PySide6.QtWidgets import QHBoxLayout, QWidget
from PySide6.QtCore import Qt
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon,
    NavigationInterface, StackedWidget
)

from .pages import (
    HomePage, ScanPage, SamplePage, TrainPage,
    InferencePage, RestorePage, ConvertPage, SettingsPage
)


class MainWindow(FluentWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("AutoLabeler - 智能标注工具")
        self.resize(1200, 800)
        self.setMinimumSize(960, 640)
        
        self._init_navigation()
        self._init_pages()
    
    def _init_navigation(self):
        """初始化导航栏"""
        # 页面映射
        self.pages = {}
    
    def _init_pages(self):
        """初始化页面"""
        # 主要功能页面
        self._add_page(HomePage(self), FluentIcon.HOME, "首页", 
                      NavigationItemPosition.TOP)
        self._add_page(ScanPage(self), FluentIcon.SEARCH, "扫描", 
                      NavigationItemPosition.TOP)
        self._add_page(SamplePage(self), FluentIcon.FILTER, "抽样", 
                      NavigationItemPosition.TOP)
        self._add_page(TrainPage(self), FluentIcon.IOT, "训练", 
                      NavigationItemPosition.TOP)
        self._add_page(InferencePage(self), FluentIcon.ROBOT, "推理", 
                      NavigationItemPosition.TOP)
        self._add_page(RestorePage(self), FluentIcon.SYNC, "还原", 
                      NavigationItemPosition.TOP)
        self._add_page(ConvertPage(self), FluentIcon.CODE, "转换", 
                      NavigationItemPosition.TOP)
        
        # 底部
        self._add_page(SettingsPage(self), FluentIcon.SETTING, "设置", 
                      NavigationItemPosition.BOTTOM)
    
    def _add_page(self, page, icon, text, position):
        """添加页面到导航"""
        self.addSubInterface(page, icon, text, position)
        self.pages[text] = page
```

---

## 6. 开发规范

### 6.1 代码规范

```yaml
# 使用 black 格式化
line-length: 100

# 类型注解
使用 typing 模块进行类型注解

# 文档字符串
使用 Google 风格的 docstring

# 命名规范
类名: PascalCase
函数/方法: snake_case
常量: UPPER_SNAKE_CASE
私有成员: _leading_underscore
```

### 6.2 错误处理规范

```python
# 自定义异常
class AutoLabelerError(Exception):
    """基础异常类"""
    pass

class ScanError(AutoLabelerError):
    """扫描相关错误"""
    pass

class SampleError(AutoLabelerError):
    """抽样相关错误"""
    pass

# ... 其他模块异常
```

### 6.3 日志规范

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('autolabeler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 在模块中使用
logger = logging.getLogger(__name__)
logger.info("开始扫描...")
```

---

## 7. 开发计划

### 7.1 分阶段开发计划（修正版）

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AutoLabeler 开发计划（6阶段）                          │
└─────────────────────────────────────────────────────────────────────────────────┘

阶段0: 环境准备 (1-2天)
├── 创建虚拟环境
├── 安装依赖包
├── 配置 IDE
└── 验证 YOLO 环境

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 阶段1: 核心基础设施 (5-7天)                                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 优先级: P0 | 依赖: 无 | 产出: 可运行的基础框架                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ Day 1-2: 基础结构                                                              │
│ ├── 创建项目目录结构                                                            │
│ ├── utils/exceptions.py        # 自定义异常类                                  │
│ ├── utils/path_encoder.py       # 路径编码/解码                                │
│ ├── utils/mapping_manager.py    # 映射管理器（含线程安全）                      │
│ ├── core/base.py                # 模块基类                                      │
│ └── tests/test_path_encoder.py  # 单元测试                                     │
│                                                                                 │
│ Day 3-4: 图片工具                                                                │
│ ├── utils/image_utils.py        # 图片尺寸读取                                  │
│ ├── utils/device.py             # 设备检测                                      │
│ └── tests/test_image_utils.py   # 单元测试                                     │
│                                                                                 │
│ Day 5-7: 扫描模块                                                                │
│ ├── core/scanner.py             # 扫描实现                                      │
│ ├── 测试：100张图片扫描性能 < 1秒                                               │
│ └── 验证：mapping.json 和 classes.txt 生成正确                                  │
│                                                                                 │
│ 里程碑验收:                                                                     │
│ ✓ 可以扫描一个测试站点文件夹                                                    │
│ ✓ 生成正确的 mapping.json 和 classes.txt                                        │
│ ✓ 单元测试通过率 > 90%                                                         │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 阶段2: 数据处理 (4-5天)                                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 优先级: P0 | 依赖: 阶段1 | 产出: 抽样和还原功能                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ Day 1-2: 抽样模块                                                               │
│ ├── core/sampler.py            # 抽样实现                                      │
│ ├── data.yaml 生成                                                                     │
│ └── 测试：各种抽样模式（count/ratio/mixed）                                    │
│                                                                                 │
│ Day 3-4: 还原模块                                                               │
│ ├── core/restorer.py           # 还原实现（修复扩展名问题）                      │
│ └── 测试：编码文件正确还原到原始路径                                            │
│                                                                                 │
│ Day 5: 集成测试                                                                  │
│ └── 扫描 → 抽样 → 还原 完整流程测试                                             │
│                                                                                 │
│ 里程碑验收:                                                                     │
│ ✓ 抽样生成符合 YOLO 训练规范的 dataset                                          │
│ ✓ 还原将标注文件正确放回原始位置                                                │
│ ✓ 数据一致性验证通过                                                            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 阶段3: 训练与推理 (5-6天)                                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 优先级: P0 | 依赖: 阶段2 | 产出: 训练和推理功能                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ Day 1-3: 训练模块                                                               │
│ ├── core/trainer.py            # 训练实现（含设备检测）                         │
│ ├── 进度回调优化                                                                      │
│ ├── GPU/CPU 自动切换                                                                 │
│ └── 测试：小数据集（100张）完整训练流程                                         │
│                                                                                 │
│ Day 4-5: 推理模块                                                               │
│ ├── core/inferencer.py         # 推理实现                                       │
│ ├── 批处理优化                                                                 │
│ └── 测试：批量推理1000张图片                                                     │
│                                                                                 │
│ Day 6: 集成测试                                                                  │
│ └── 扫描 → 抽样 → 人工标注 → 训练 → 推理 → 还原 全流程                          │
│                                                                                 │
│ 里程碑验收:                                                                     │
│ ✓ 设备自动检测工作正常                                                          │
│ ✓ 训练可以正常完成并生成 best.pt                                                │
│ ✓ 推理可以批量处理图片并生成 .txt                                               │
│ ✓ 全流程端到端测试通过                                                          │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 阶段4: 格式转换 (2-3天)                                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 优先级: P1 | 依赖: 阶段3 | 产出: YOLO→VOC 转换功能                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ Day 1-2: 转换模块                                                               │
│ ├── core/converter.py          # YOLO → VOC 实现                               │
│ ├── 坐标转换精度验证                                                                     │
│ └── 测试：各种边界情况处理                                                      │
│                                                                                 │
│ Day 3: 验证                                                                      │
│ └── 使用工具验证 XML 格式正确性                                                  │
│                                                                                 │
│ 里程碑验收:                                                                     │
│ ✓ YOLO → VOC 转换坐标误差 < 1 像素                                              │
│ ✓ XML 格式符合 Pascal VOC 标准                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 阶段5: GUI 基础框架 (3-4天)                                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 优先级: P0 | 依赖: 阶段1-3 | 产出: 可用的图形界面                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ Day 1: 主框架                                                                  │
│ ├── gui/app.py                  # 应用程序封装                                  │
│ ├── gui/main_window.py          # 主窗口                                        │
│ └── gui/pages/base_page.py      # 页面基类                                      │
│                                                                                 │
│ Day 2: 后台线程                                                                │
│ ├── gui/workers/base_worker.py  # Worker 基类                                  │
│ ├── gui/workers/scan_worker.py  # 扫描线程                                     │
│ ├── gui/workers/train_worker.py # 训练线程                                     │
│ └── gui/workers/inference_worker.py # 推理线程                                  │
│                                                                                 │
│ Day 3-4: 核心页面                                                               │
│ ├── gui/pages/home_page.py    # 首页                                          │
│ ├── gui/pages/scan_page.py    # 扫描页                                         │
│ ├── gui/pages/sample_page.py  # 抽样页                                         │
│ └── gui/pages/train_page.py   # 训练页                                         │
│                                                                                 │
│ 里程碑验收:                                                                     │
│ ✓ 主窗口正常启动                                                                │
│ ✓ 导航栏正常工作                                                                │
│ ✓ 扫描功能可通过 GUI 完成                                                      │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 阶段6: GUI 完善与测试 (4-5天)                                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 优先级: P1 | 依赖: 阶段5 | 产出: 完整的 GUI 应用                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ Day 1-2: 功能页面                                                              │
│ ├── gui/pages/inference_page.py   # 推理页                                     │
│ ├── gui/pages/restore_page.py     # 还原页                                     │
│ ├── gui/pages/convert_page.py     # 转换页                                     │
│ └── gui/pages/settings_page.py    # 设置页                                     │
│                                                                                 │
│ Day 3: 自定义组件                                                              │
│ ├── gui/widgets/folder_picker.py  # 文件夹选择器                               │
│ ├── gui/widgets/progress_card.py  # 进度卡片                                   │
│ ├── gui/widgets/log_viewer.py     # 日志查看器                                  │
│ └── gui/widgets/stats_card.py     # 统计卡片                                   │
│                                                                                 │
│ Day 4-5: 测试与优化                                                            │
│ ├── 端到端 GUI 测试                                                             │
│ ├── 异常处理测试                                                                │
│ ├── 性能优化                                                                    │
│ └── UI/UX 改进                                                                  │
│                                                                                 │
│ 里程碑验收:                                                                     │
│ ✓ 所有功能可通过 GUI 完成                                                      │
│ ✓ 异常情况下程序不会崩溃                                                        │
│ ✓ 进度反馈及时准确                                                              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 开发优先级（修订）

```
P0 (必须 - 核心功能):
├── 阶段1: 基础设施
│   ├── exceptions.py (异常类)
│   ├── path_encoder.py (路径编码)
│   ├── mapping_manager.py (映射管理，含线程安全)
│   ├── image_utils.py (图片工具)
│   ├── device.py (设备检测)
│   └── scanner.py (扫描)
├── 阶段2: 数据处理
│   ├── sampler.py (抽样)
│   └── restorer.py (还原)
├── 阶段3: 训练推理
│   ├── trainer.py (训练，含设备自动检测)
│   └── inferencer.py (推理)
└── 阶段5: GUI基础
    ├── 主窗口框架
    ├── 后台 Worker
    └── 核心功能页面

P1 (重要 - 增强功能):
├── 阶段4: converter.py (格式转换)
├── 阶段6: 完整 GUI
│   ├── 所有功能页面
│   ├── 自定义组件
│   └── 进度显示
└── 配置管理
    ├── settings.py
    └── config.yaml

P2 (优化 - 可选):
├── 训练曲线可视化
├── 配置导入导出
├── 多语言支持
└── 性能优化（大规模数据）
```

### 7.3 关键风险与应对

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| YOLO 环境配置问题 | 高 | 中 | 提供详细文档、自动检测脚本 |
| 大规模数据性能问题 | 中 | 中 | 分批处理、进度反馈 |
| 多线程文件操作冲突 | 高 | 低 | 文件锁 + 线程锁双重保护 |
| GPU 内存不足 | 中 | 中 | 自动降级到 CPU / 减小 batch size |
| 用户数据格式不符合规范 | 中 | 高 | 详细验证 + 友好错误提示 |

---

## 8. 测试要点

### 8.1 单元测试覆盖

| 模块 | 关键测试点 |
|------|------------|
| PathEncoder | 编码/解码正确性, 特殊字符处理, 边界情况 |
| MappingManager | CRUD操作, 状态更新, 文件读写 |
| Scanner | 目录遍历, 格式过滤, 统计准确性 |
| Sampler | 抽样数量, 比例分配, 边界情况 |
| Converter | 坐标转换精度, XML格式正确性 |

### 8.2 集成测试场景

| 场景 | 描述 |
|------|------|
| 完整流程 | 从扫描到转换的完整流程 |
| 断点续传 | 中途中断后继续处理 |
| 大规模数据 | 10000+图片的性能测试 |
| 异常恢复 | 各种异常情况下的恢复能力 |

---

## 9. 部署打包

### 9.1 打包工具

使用 **PyInstaller** 打包为单文件可执行程序：

```bash
pyinstaller --onefile --windowed --icon=resources/icons/logo.ico \
            --add-data "resources;resources" \
            --add-data "config;config" \
            --name AutoLabeler \
            main.py
```

### 9.2 运行环境要求

```
最低配置:
- CPU: 4核
- 内存: 8GB
- 硬盘: 10GB可用空间

推荐配置:
- CPU: 8核
- 内存: 16GB
- GPU: NVIDIA GTX 1060 6GB及以上
- CUDA: 11.7+
```
```

---

## 10. 功能增强设计 (2025-01-14)

### 10.1 已有标注样本优先抽样

#### 10.1.1 需求背景

在实际使用中，用户可能已经对部分样本进行了标注（VOC XML 格式或 YOLO TXT 格式）。为了：
- 减少人工标注工作量
- 充分利用已有标注数据
- 提高训练起点

需要在抽样阶段优先提取已标注样本。

#### 10.1.2 功能描述

1. **检测已有标注**：扫描产品文件夹，检测与图片同名的 `.xml` 或 `.txt` 文件
2. **格式转换**：如果检测到 `.xml`，自动转换为 YOLO `.txt` 格式
3. **优先抽取**：已标注样本优先抽取
4. **补充抽样**：如果已标注样本数量不足设定数量，从未标注样本中随机抽取
5. **按比例分配**：已标注样本同样按照 `train_ratio` 随机分配到 train/vals

#### 10.1.3 数据结构变更

**ImageInfo 新增字段**：
```python
@dataclass
class ImageInfo:
    # ... 原有字段 ...
    label_source: str = "none"  # 新增：标注来源
    # 可选值: "none" | "pre_existing_xml" | "pre_existing_txt" |
    #        "manual_later" | "auto_inferred"
```

**SampleConfig 新增字段**：
```python
@dataclass
class SampleConfig:
    # ... 原有字段 ...
    pre_labeled_priority: bool = True  # 是否优先抽取已标注样本
```

#### 10.1.4 处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│ 已有标注样本优先抽样流程                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Step 1: 检测已有标注                                             │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ for 产品文件夹 in mapping.images:                      │   │
│   │   for 图片 in 产品文件夹:                               │   │
│   │     if 存在 图片.xml:                                   │   │
│   │       label_source = "pre_existing_xml"                 │   │
│   │     elif 存在 图片.txt:                                 │   │
│   │       label_source = "pre_existing_txt"                 │   │
│   │     else:                                               │   │
│   │       label_source = "none"                             │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Step 2: 按产品分组（区分已标注/未标注）                          │
│   products = {                                                   │
│     "CodeA/ProductA": {                                          │
│       "labeled": [encoded_name1, encoded_name2, ...],            │
│       "unlabeled": [encoded_name3, encoded_name4, ...]           │
│     },                                                           │
│     ...                                                          │
│   }                                                               │
│                                                                  │
│ Step 3: 计算抽样计划                                             │
│   for product_key, images in products.items():                  │
│     target_count = _calculate_sample_count(total)               │
│     labeled_count = len(images["labeled"])                      │
│                                                                  │
│     if labeled_count >= target_count:                           │
│       # 已标注样本足够，全部抽取                                 │
│       sampled = images["labeled"][:target_count]                │
│     else:                                                        │
│       # 已标注样本不足，全部抽取 + 补充未标注                     │
│       needed = target_count - labeled_count                     │
│       sampled = images["labeled"] + random.sample(              │
│         images["unlabeled"], min(needed, len(unlabeled))        │
│       )                                                          │
│                                                                  │
│ Step 4: XML 转换（临时区）                                       │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ for encoded_name in sampled:                            │   │
│   │   img_info = mapping.data.images[encoded_name]          │   │
│   │   if img_info["label_source"] == "pre_existing_xml":    │   │
│   │     xml_path = site_folder / img_info["original_relative"]│   │
│   │     xml_path = xml_path.with_suffix('.xml')             │   │
│   │     # 调用 Converter.xml_to_txt()                       │   │
│   │     txt_content = convert_xml_to_yolo(xml_path, classes)│   │
│   │     # 保存到临时区                                       │   │
│   │     temp_txt_path = temp_dir / encoded_name             │   │
│   │     temp_txt_path.write_text(txt_content)               │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Step 5: 复制到 database（按 train_ratio 分配）                   │
│   for encoded_name in sampled:                                  │
│     split = "train" if random.random() < train_ratio else "vals"│
│     # 复制图片                                                  │
│     shutil.copy2(src_img, database/images/split/encoded_name)   │
│     # 复制标注                                                  │
│     if label_source == "pre_existing_xml/txt":                  │
│       shutil.copy2(temp_txt, database/labels/split/encoded_name)│
│     # 更新映射                                                  │
│     mapping.mark_sampled(encoded_name, split)                   │
│     mapping.data.images[encoded_name]["label_source"] = source  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 10.1.5 XML 转换实现

**新增方法**: `Sampler._convert_xml_to_txt()`

```python
def _convert_xml_to_txt(
    self,
    xml_path: Path,
    img_path: Path,
    classes: List[str]
) -> str:
    """
    将 VOC XML 转换为 YOLO TXT

    Args:
        xml_path: XML 文件路径
        img_path: 对应图片路径（用于获取尺寸）
        classes: 类别列表

    Returns:
        YOLO 格式的标注内容字符串

    Raises:
        ValueError: 类别名称不匹配
    """
    from core.converter import Converter

    # 复用 Converter 的坐标转换逻辑
    converter = Converter()

    # 解析 XML
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # 获取图片尺寸
    width = int(root.find("size").find("width").text)
    height = int(root.find("size").find("height").text)

    # 转换标注
    lines = []
    for obj in root.findall("object"):
        class_name = obj.find("name").text

        # 验证类别
        if class_name not in classes:
            raise ValueError(f"未知类别: {class_name}")

        cls_id = classes.index(class_name)

        # 获取边界框
        bndbox = obj.find("bndbox")
        xmin = int(bndbox.find("xmin").text)
        ymin = int(bndbox.find("ymin").text)
        xmax = int(bndbox.find("xmax").text)
        ymax = int(bndbox.find("ymax").text)

        # 转换为 YOLO 格式（归一化坐标）
        x_center = ((xmin + xmax) / 2) / width
        y_center = ((ymin + ymax) / 2) / height
        box_width = (xmax - xmin) / width
        box_height = (ymax - ymin) / height

        lines.append(
            f"{cls_id} {x_center:.6f} {y_center:.6f} "
            f"{box_width:.6f} {box_height:.6f}"
        )

    return "\n".join(lines)
```

#### 10.1.6 目录结构变化

```
.autolabeler/
├── mapping.json
├── classes.txt
├── database/
│   ├── images/
│   │   ├── train/
│   │   │   ├── CodeA__ProductA__img001.jpg  # 已标注（XML）
│   │   │   ├── CodeA__ProductA__img002.jpg  # 已标注（TXT）
│   │   │   └── CodeA__ProductA__img003.jpg  # 新抽样
│   │   └── vals/
│   └── labels/
│       ├── train/
│       │   ├── CodeA__ProductA__img001.txt  # 从 XML 转换
│       │   ├── CodeA__ProductA__img002.txt  # 复制已有
│       │   └── CodeA__ProductA__img003.txt  # 待人工标注
│       └── vals/
└── temp_conversion/  # 临时转换区（可选，转换后可删除）
    └── CodeA__ProductA__img001.txt
```

---

### 10.2 推理结果分区存储

#### 10.2.1 需求背景

当前推理后直接将 `.txt` 文件保存到原图片位置，存在以下问题：
1. 无法使用 LabelImg 预览效果（LabelImg 需要指定图片文件夹路径）
2. 多次推理会覆盖上一次结果
3. 无法对比不同阈值的推理效果
4. 调整阈值后需要重新推理，无法增量更新

#### 10.2.2 功能描述

1. **分区存储**：推理结果保存到独立的 `inference_results/` 目录
2. **时间戳命名**：每次推理创建一个以时间戳命名的子目录
3. **配置记录**：每次推理生成 `inference_config.json` 记录参数
4. **历史管理**：保留所有历史推理结果，便于对比
5. **用户确认**：用户选择某次结果后，手动还原到原位置

#### 10.2.3 目录结构设计

```
.autolabeler/
├── inference_results/               # 所有推理结果
│   ├── run_20250114_143022/        # 第一次推理（时间戳）
│   │   ├── inference_config.json   # 本次推理配置
│   │   │   # {
│   │   │   #   "timestamp": "2025-01-14 14:30:22",
│   │   │   #   "model": "runs/train/train/weights/best.pt",
│   │   │   #   "confidence": 0.25,
│   │   │   #   "iou": 0.45,
│   │   │   #   "device": "0",
│   │   │   #   "image_count": 1500,
│   │   │   #   "predicted_count": 1200
│   │   │   # }
│   │   ├── Code1/
│   │   │   └── ProductA/
│   │   │       ├── IMG_003.txt
│   │   │       └── IMG_004.txt
│   │   ├── Code2/
│   │   └── latest -> run_20250114_143022  # 软链接（Windows 可用快捷方式）
│   ├── run_20250114_150135/        # 第二次推理（不同阈值）
│   │   ├── inference_config.json
│   │   └── ...
│   └── run_20250114_161200/        # 第三次推理
├── pending_restore/                 # 待还原的推理结果（用户选中）
│   └── run_20250114_143022 -> ../inference_results/run_20250114_143022
├── database/
└── mapping.json
```

#### 10.2.4 数据结构变更

**InferenceConfig 新增字段**：
```python
@dataclass
class InferenceConfig:
    # ... 原有字段 ...
    save_to_separate_dir: bool = True  # 是否保存到独立目录
    inference_output_dir: Path = None  # 推理输出目录（自动生成）
```

**inference_config.json 结构**：
```json
{
  "run_id": "run_20250114_143022",
  "timestamp": "2025-01-14 14:30:22",
  "model_path": "runs/train/train/weights/best.pt",
  "confidence": 0.25,
  "iou": 0.45,
  "device": "0",
  "batch_size": 16,
  "image_count": 1500,
  "predicted_count": 1200,
  "empty_prediction_count": 300
}
```

#### 10.2.5 处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│ 推理结果分区存储流程                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Step 1: 创建推理输出目录                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")    │   │
│   │ run_dir = .autolabeler/inference_results/run_{timestamp}│   │
│   │ run_dir.mkdir(parents=True, exist_ok=True)              │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Step 2: 执行推理                                                 │
│   for batch in image_batches:                                   │
│     results = model.predict(batch, conf, iou, device)           │
│                                                                  │
│ Step 3: 保存结果到独立目录                                       │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ for result, img_path in zip(results, image_paths):      │   │
│   │   # 构建目标路径（保持原目录结构）                       │   │
│   │   img_info = mapping.get_image_info(encoded_name)       │   │
│   │   code = img_info["code"]                               │   │
│   │   product = img_info["product"]                         │   │
│   │   original_name = img_info["original_name"]             │   │
│   │                                                          │   │
│   │   # 目标路径：保持 Code/Product 结构                    │   │
│   │   dst_dir = run_dir / code / product                    │   │
│   │   dst_dir.mkdir(parents=True, exist_ok=True)            │   │
│   │   txt_name = Path(original_name).stem + ".txt"          │   │
│   │   dst_path = dst_dir / txt_name                         │   │
│   │                                                          │   │
│   │   # 保存标注                                            │   │
│   │   self._save_yolo_txt(result, dst_path)                 │   │
│   │                                                          │   │
│   │   # 更新映射（推理完成标记）                             │   │
│   │   mapping.mark_inferred(encoded_name)                   │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Step 4: 保存推理配置                                             │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ config_data = {                                         │   │
│   │   "run_id": f"run_{timestamp}",                         │   │
│   │   "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),│
│   │   "model_path": str(model_path),                        │   │
│   │   "confidence": self.config.confidence,                 │   │
│   │   "iou": self.config.iou,                               │   │
│   │   "device": device,                                     │   │
│   │   "batch_size": batch_size,                             │   │
│   │   "image_count": total,                                 │   │
│   │   "predicted_count": predicted_count,                   │   │
│   │   "empty_prediction_count": empty_count                 │   │
│   │ }                                                        │   │
│   │                                                          │   │
│   │ with open(run_dir / "inference_config.json", "w") as f: │   │
│   │   json.dump(config_data, f, indent=2, ensure_ascii=False)│   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Step 5: 更新 latest 软链接/快捷方式                               │
│   _update_latest_link(run_dir)                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 10.2.6 Restorer 功能扩展

**新增方法**: `Restorer.restore_from_inference()`

```python
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

    # 读取推理配置
    config_path = inference_run_dir / "inference_config.json"
    if config_path.exists():
        with open(config_path, "r") as f:
            config = json.load(f)
        # 验证配置

    # 收集所有待还原的标注文件
    txt_files = list(inference_run_dir.glob("**/*.txt"))
    # 排除配置文件
    txt_files = [f for f in txt_files if f.name != "inference_config.json"]

    result.total = len(txt_files)

    for i, txt_file in enumerate(txt_files):
        if self.is_cancelled:
            break

        # 从文件路径反推 encoded_name
        # txt_file: run_xxx/CodeA/ProductA/IMG_001.txt
        relative_parts = txt_file.relative_to(inference_run_dir).parts
        # relative_parts = ["CodeA", "ProductA", "IMG_001.txt"]

        code = relative_parts[0]
        product = relative_parts[1]
        txt_filename = relative_parts[2]

        # 在 mapping 中查找匹配的图片
        # 需要根据 code/product/original_name 匹配
        encoded_name = self._find_encoded_name(
            mapping, code, product, txt_filename
        )

        if not encoded_name:
            result.failed += 1
            result.errors.append(f"找不到匹配: {code}/{product}/{txt_filename}")
            continue

        # 获取目标路径
        img_info = mapping.get_image_info(encoded_name)
        original_name = img_info["original_name"]
        dst_path = site_folder / code / product / txt_filename

        # 复制文件
        try:
            shutil.copy2(txt_file, dst_path)
            result.success += 1
            mapping.mark_restored(encoded_name)
        except Exception as e:
            result.failed += 1
            result.errors.append(f"复制失败: {str(e)}")

        if (i + 1) % 10 == 0 or i + 1 == result.total:
            self.report_progress(i + 1, result.total, f"还原: {txt_filename}")

    if result.success > 0:
        mapping.save()

    return result

def _find_encoded_name(
    self,
    mapping: MappingManager,
    code: str,
    product: str,
    txt_filename: str
) -> Optional[str]:
    """根据 code/product/txt_filename 查找 encoded_name"""
    target_stem = Path(txt_filename).stem

    for encoded_name, info in mapping.data.images.items():
        if (info["code"] == code and
            info["product"] == product and
            Path(info["original_name"]).stem == target_stem):
            return encoded_name
    return None
```

#### 10.2.7 与其他功能的兼容性

| 功能 | 兼容性 | 说明 |
|------|--------|------|
| **Restorer** | ✅ 需扩展 | 新增 `restore_from_inference()` 方法，原有 `restore()` 保持不变 |
| **Converter** | ✅ 无冲突 | 转换在还原后执行，从原位置读取 .txt |
| **mapping.json** | ✅ 无冲突 | `inferred` 字段在推理完成时标记，`restored` 在还原时标记 |

#### 10.2.8 GUI 增强功能

**推理页面新增**：
- 推理历史列表（显示每次推理的时间戳、参数、数量）
- 预览按钮（用 LabelImg 打开选中的推理结果目录）
- 还原按钮（将选中的推理结果还原到原位置）
- 对比功能（同时打开两次推理结果对比）

**还原页面新增**：
- 来源选择：
  - database/labels/（人工标注）
  - inference_results/run_xxx/（推理结果）
- 还原预览（显示将要还原的文件列表）

---

### 10.3 实现优先级

```
P0（核心功能）:
├── 10.1: 已有标注样本优先抽样
│   ├── ImageInfo.label_source 字段
│   ├── Sampler._detect_existing_labels()
│   ├── Sampler._convert_xml_to_txt()
│   └── Sampler.sample() 修改
│
└── 10.2: 推理结果分区存储
    ├── Inferencer.infer() 修改
    ├── 推理配置保存
    └── Restorer.restore_from_inference()

P1（增强体验）:
├── 推理历史 GUI 展示
├── 推理结果预览
└── 还原来源选择

P2（优化）:
├── 推理结果对比
└── 智能抽样建议
```

---

### 10.4 测试要点

**10.1 已有标注优先抽样**：
- XML 转换正确性（坐标精度）
- 已标注样本优先抽取
- 补充抽样逻辑
- train/vals 比例分配

**10.2 推理结果分区存储**：
- 目录结构正确性
- 配置文件完整性
- 还原功能正确性
- 多次推理不覆盖

---