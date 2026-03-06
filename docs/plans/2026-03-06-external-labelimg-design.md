# 外部 LabelImg 环境集成设计文档

## 概述

**功能名称**：外部 LabelImg 环境集成

**目的**：支持调用外部 Python 环境中的 LabelImg，避免与当前 yolo_new 环境的包冲突。

**创建日期**：2026-03-06

---

## 需求背景

### 问题描述

1. 当前 `LabelImgLauncher` 使用 `sys.executable`（yolo_new 环境）调用 LabelImg
2. yolo_new 环境中安装 LabelImg 会导致包冲突
3. 用户需要在独立的 Python 环境中安装 LabelImg，并由 AutoLabeler 调用

### 解决方案

新增配置管理机制，支持：
- 配置外部 Python 解释器路径
- 按优先级加载配置（项目级 > 全局级）
- GUI 界面配置和验证
- 完善的错误提示

---

## 配置文件设计

### 文件路径与优先级

```
项目级：config/labelimg.json（优先）
全局级：~/.autolabeler/labelimg.json（备选）
```

**优先级规则**：
1. 先检查 `config/labelimg.json`
2. 不存在则检查 `~/.autolabeler/labelimg.json`
3. 都不存在则返回空配置（需要用户设置）

### 配置文件格式

```json
{
  "python_path": "D:/mniforge3/envs/labelimg_env/python.exe",
  "last_check": "2026-03-06T10:30:00",
  "is_valid": true
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `python_path` | string | 外部 Python 解释器的完整路径 |
| `last_check` | string | 上次检查可用性的时间（ISO 格式） |
| `is_valid` | bool | 上次检查是否通过 |

---

## 文件结构

```
utils/
├── labelimg_config.py     # 新增：配置管理类
├── labelimg_launcher.py   # 修改：支持外部 Python
└── ...

gui/
├── pages/
│   └── label_viewer_page.py  # 修改：添加配置按钮
└── ...
```

---

## 核心类设计

### 1. LabelImgConfig

**位置**：`utils/labelimg_config.py`

**职责**：
- 管理配置文件的读取、保存
- 提供配置优先级加载
- 验证 Python 路径是否有效

```python
class LabelImgConfig:
    """LabelImg 配置管理器"""

    # 配置文件路径
    PROJECT_CONFIG = "config/labelimg.json"
    GLOBAL_CONFIG = "~/.autolabeler/labelimg.json"

    def __init__(self):
        self._python_path: Optional[str] = None
        self._is_valid: bool = False
        self._last_check: Optional[str] = None

    @property
    def python_path(self) -> Optional[str]:
        """获取配置的 Python 路径"""

    @property
    def is_valid(self) -> bool:
        """配置是否有效"""

    def load(self) -> bool:
        """加载配置（按优先级），返回是否找到有效配置"""

    def save(self, python_path: str) -> Tuple[bool, str]:
        """
        保存配置到用户目录

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """

    def validate_python(self, python_path: str) -> Tuple[bool, str]:
        """
        验证 Python 路径是否有效且包含 labelImg

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """

    def get_effective_python(self) -> Tuple[Optional[str], str]:
        """
        获取有效的 Python 路径

        Returns:
            Tuple[Optional[str], str]: (路径或None, 错误信息)
        """
```

### 2. LabelImgLauncher（修改）

**位置**：`utils/labelimg_launcher.py`

**修改内容**：
- 移除对 `sys.executable` 的依赖
- 接收外部 Python 路径作为参数
- 增强错误提示

```python
class LabelImgLauncher:
    """Launcher for LabelImg annotation tool"""

    @classmethod
    def check_labelimg_available(cls, python_path: str) -> Tuple[bool, str]:
        """
        检查指定 Python 环境中 LabelImg 是否可用

        Args:
            python_path: Python 解释器路径

        Returns:
            Tuple[bool, str]: (是否可用, 错误信息)
        """

    @classmethod
    def launch(
        cls,
        python_path: str,  # 新增参数
        site_dir: Path,
        inference_run: str,
        code: str,
        product: str
    ) -> bool:
        """
        使用指定 Python 启动 LabelImg

        Args:
            python_path: 外部 Python 解释器路径
            site_dir: 站点根目录
            inference_run: 推理记录名
            code: Code 文件夹名
            product: Product 文件夹名

        Returns:
            bool: 启动是否成功

        Raises:
            LabelImgLaunchError: 启动失败
        """
```

---

## GUI 配置交互设计

### UI 布局

```
┌─────────────────────────────────────────────────────────────┐
│ 操作按钮区域                                                 │
├─────────────────────────────────────────────────────────────┤
│ [配置 LabelImg]  [用 LabelImg 打开]  [在文件管理器中打开]     │
│                                                             │
│ 状态: 当前配置: D:/mniforge3/envs/labelimg/python.exe       │
└─────────────────────────────────────────────────────────────┘
```

### 配置对话框流程

```
用户点击「配置 LabelImg」
        ↓
打开文件对话框（筛选 python.exe/python）
        ↓
用户选择 Python 路径
        ↓
自动验证路径有效性
    ├─ 成功 → 保存配置 → 更新状态显示
    └─ 失败 → 显示错误 → 让用户重试
```

### 状态显示逻辑

| 状态 | 显示文本 | 按钮状态 |
|------|----------|----------|
| 未配置 | "未配置 LabelImg，请点击配置按钮" | 禁用 |
| 已配置有效 | "当前配置: D:/path/to/python.exe" | 启用 |
| 已配置无效 | "配置无效: labelImg 未安装，请重新配置" | 禁用 |

---

## 数据流

```
┌─────────────────────┐
│ 页面加载             │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ LabelImgConfig.load │
│ 按优先级加载配置      │
└──────────┬──────────┘
           ▼
     配置是否存在？
        │
   ┌────┴────┐
   │ 否      │ 是
   ▼         ▼
┌──────┐  ┌──────────────────────┐
│提示配置│  │ validate_python()    │
└──────┘  │ 验证配置有效性        │
          └──────────┬───────────┘
                     ▼
               验证通过？
                  │
             ┌────┴────┐
             │ 否      │ 是
             ▼         ▼
        ┌────────┐  ┌─────────────┐
        │提示重配│  │启用打开按钮  │
        └────────┘  └─────────────┘
```

---

## 错误处理

### 错误场景与提示

| 场景 | 错误类型 | 用户提示 | 建议 |
|------|----------|----------|------|
| 未配置 | - | "未配置 LabelImg 环境，请先配置" | 提供配置按钮 |
| 路径不存在 | `FileNotFoundError` | "Python 路径不存在: {path}" | 检查路径或重新选择 |
| 非可执行文件 | `InvalidPythonError` | "选择的文件不是有效的 Python 解释器" | 重新选择 |
| labelImg 未安装 | `ModuleNotFoundError` | "该环境中未安装 labelImg" + 安装命令 | 安装后重试 |
| 启动失败 | `LabelImgLaunchError` | "LabelImg 启动失败: {详细错误}" | 检查环境或重试 |
| 标签目录为空 | - | "该产品没有标注文件" | - |

### 提示方式

| 场景 | 提示方式 |
|------|----------|
| 配置验证失败 | `InfoBar.error()` 显示在页面顶部 |
| 启动失败 | 弹窗 `MessageBox.error()` 显示详细信息 |
| 成功 | `InfoBar.success()` 简短提示 |

---

## 实现步骤概览

| 步骤 | 内容 | 文件 |
|------|------|------|
| 1 | 创建 `LabelImgConfig` 配置管理类 | `utils/labelimg_config.py` |
| 2 | 编写 Config 单元测试 | `tests/test_labelimg_config.py` |
| 3 | 修改 `LabelImgLauncher` 支持外部 Python | `utils/labelimg_launcher.py` |
| 4 | 更新 Launcher 单元测试 | `tests/test_labelimg_launcher.py` |
| 5 | 修改 GUI 添加配置按钮和状态显示 | `gui/pages/label_viewer_page.py` |
| 6 | 集成测试 | 手动测试 |

---

## 注意事项

1. **跨平台兼容**：Python 路径在不同系统下格式不同（Windows: `python.exe`, Linux/Mac: `python`）
2. **路径验证**：验证时要检查文件存在且可执行
3. **配置目录创建**：首次保存时需创建 `~/.autolabeler/` 目录
4. **向后兼容**：旧版本配置文件格式要能正确处理

---

## 后续扩展

- 支持多个外部工具的配置管理（统一配置中心）
- 配置导入/导出功能
- 自动检测常见的 conda 环境路径
