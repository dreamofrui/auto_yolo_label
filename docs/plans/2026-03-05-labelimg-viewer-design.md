# 标注检查功能设计文档

## 概述

**功能名称**：标注检查

**目的**：让用户能够用 LabelImg 查看推理生成的标注结果，方便比较多次推理的效果并选择最佳结果。

**创建日期**：2026-03-05

---

## 需求背景

### 问题描述

1. 推理结果保存在时间戳目录中，但缺少 `classes.txt`
2. LabelImg 需要 `classes.txt` 才能正确打开标注文件
3. 用户需要比较多次推理结果，选择最佳的一次进行还原

### 解决方案

新增"标注检查"页面，支持：
- 选择推理记录
- 选择 Code/Product
- 自动复制 `classes.txt` 并启动 LabelImg

---

## 页面结构

### UI 布局

```
┌─────────────────────────────────────────────────┐
│  站点选择: [下拉选择框]                           │
├─────────────────────────────────────────────────┤
│  ┌─────────────┬──────────────────────────────┐ │
│  │ 推理记录列表  │  产品树形结构                  │ │
│  │ ┌───────────┐│  ┌─────────────────────────┐│ │
│  │ │ run_0305  ││  │ ▼ Code_A               ││ │
│  │ │ run_0304  ││  │   ▶ Product_1          ││ │
│  │ │ run_0303  ││  │   ▶ Product_2 ✓        ││ │
│  │ └───────────┘│  │ ▶ Code_B               ││ │
│  │              │  └─────────────────────────┘│ │
│  └─────────────┴──────────────────────────────┘ │
├─────────────────────────────────────────────────┤
│  [用 LabelImg 打开]  [在文件管理器中查看]        │
└─────────────────────────────────────────────────┘
```

### 交互流程

1. 用户选择站点
2. 左侧显示该站点的推理记录列表（按时间倒序）
3. 右侧显示选中推理记录的产品树（三级：Code → Product）
4. 用户选择产品后，点击"用 LabelImg 打开"
5. 系统自动复制 `classes.txt` 并启动 LabelImg

---

## 文件结构

```
gui/
├── pages/
│   └── label_viewer_page.py      # 标注检查页面
├── workers/
│   └── (无需新 worker，操作轻量)
└── widgets/
    └── (可选：复用现有树形组件)

utils/
└── labelimg_launcher.py          # LabelImg 启动器
```

---

## 核心类设计

### 1. LabelViewerPage

**位置**：`gui/pages/label_viewer_page.py`

```python
class LabelViewerPage(ScrollArea):
    """标注检查页面"""

    def __init__(self, parent=None):
        # UI 组件
        self.site_combo          # 站点下拉框
        self.inference_list      # 推理记录列表
        self.product_tree        # 产品树形结构
        self.open_labelimg_btn   # 打开 LabelImg 按钮
        self.open_folder_btn     # 打开文件夹按钮

    def _on_site_changed(self):
        """站点切换 → 加载推理记录"""

    def _on_inference_selected(self):
        """推理记录选中 → 加载产品树"""

    def _on_product_selected(self):
        """产品选中 → 启用按钮"""

    def _open_with_labelimg(self):
        """启动 LabelImg"""

    def _open_in_file_manager(self):
        """在文件管理器中打开"""
```

### 2. LabelImgLauncher

**位置**：`utils/labelimg_launcher.py`

```python
class LabelImgLaunchError(Exception):
    """LabelImg 启动失败"""
    pass


class LabelImgLauncher:
    """LabelImg 启动器"""

    @classmethod
    def check_labelimg_available(cls) -> tuple[bool, str]:
        """检查 LabelImg 是否可用"""

    @classmethod
    def launch(cls, site_dir: Path, inference_run: str, code: str, product: str) -> bool:
        """
        启动 LabelImg

        Args:
            site_dir: 站点根目录
            inference_run: 推理记录名 (如 "run_20250305_143022")
            code: Code 文件夹名
            product: Product 文件夹名

        Returns:
            bool: 启动是否成功
        """
```

---

## 数据流

```
┌─────────────┐    选择站点     ┌──────────────────┐
│  站点下拉框  │ ──────────────▶│ 加载推理记录列表  │
└─────────────┘                └──────────────────┘
                                       │
                                       ▼ 选择推理记录
                               ┌──────────────────┐
                               │  扫描推理结果目录  │
                               │  构建产品树结构    │
                               └──────────────────┘
                                       │
                                       ▼ 选择产品
                               ┌──────────────────┐
                               │  启用"打开"按钮   │
                               └──────────────────┘
                                       │
                                       ▼ 点击按钮
                               ┌──────────────────┐
                               │ 1. 复制classes.txt│
                               │ 2. 启动LabelImg   │
                               └──────────────────┘
```

---

## LabelImgLauncher 核心逻辑

```python
class LabelImgLauncher:
    @classmethod
    def launch(cls, site_dir: Path, inference_run: str, code: str, product: str) -> bool:
        # 1. 定位路径
        label_dir = site_dir / ".autolabeler" / "inference_results" / inference_run / code / product
        image_dir = site_dir / code / product  # 原始图片位置

        # 2. 复制 classes.txt
        src_classes = site_dir / "classes.txt"
        dst_classes = label_dir / "classes.txt"
        shutil.copy(src_classes, dst_classes)

        # 3. 启动 LabelImg
        cmd = [
            sys.executable, "-m", "labelImg",
            str(image_dir),
            str(label_dir),
            str(dst_classes)
        ]
        subprocess.Popen(cmd, detached=True)

        return True
```

---

## 错误处理

### 错误类型

```python
class LabelImgLaunchError(Exception):
    """LabelImg 启动失败"""
    pass
```

### 检查逻辑

```python
@classmethod
def check_labelimg_available(cls) -> tuple[bool, str]:
    """检查 LabelImg 是否可用"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "labelImg", "--help"],
            capture_output=True, timeout=5
        )
        return True, ""
    except FileNotFoundError:
        return False, "LabelImg 未安装，请运行: pip install labelImg"
    except Exception as e:
        return False, f"LabelImg 检查失败: {e}"
```

### UI 错误反馈

| 场景 | UI 反馈 |
|------|---------|
| LabelImg 未安装 | 按钮禁用，显示黄色提示条 |
| classes.txt 不存在 | 弹窗提示"请先执行扫描" |
| 产品下无标注文件 | 禁用打开按钮 |
| 启动失败 | 弹窗显示具体错误信息 |

---

## 测试策略

### 单元测试

```python
# tests/test_labelimg_launcher.py

class TestLabelImgLauncher:
    def test_check_labelimg_available(self):
        """测试 LabelImg 可用性检查"""

    def test_launch_with_valid_paths(self, tmp_path):
        """测试正常启动流程"""

    def test_launch_without_classes_txt(self, tmp_path):
        """测试 classes.txt 不存在时的错误处理"""

    def test_launch_with_empty_label_dir(self, tmp_path):
        """测试空标注目录的错误处理"""
```

### GUI 测试（可选）

```python
# tests/test_label_viewer_page.py

class TestLabelViewerPage:
    def test_site_selection_loads_inference_list(self):
        """测试站点选择后加载推理记录"""

    def test_inference_selection_loads_product_tree(self):
        """测试推理记录选择后加载产品树"""
```

---

## 实现步骤

| 步骤 | 内容 | 文件 |
|------|------|------|
| 1 | 创建 `LabelImgLauncher` 工具类 | `utils/labelimg_launcher.py` |
| 2 | 编写 Launcher 单元测试 | `tests/test_labelimg_launcher.py` |
| 3 | 创建页面 UI 框架 | `gui/pages/label_viewer_page.py` |
| 4 | 实现推理记录列表加载 | 页面内 |
| 5 | 实现产品树加载 | 页面内 |
| 6 | 连接打开按钮与 Launcher | 页面内 |
| 7 | 注册导航项 | `main.py` 或导航配置 |
| 8 | 集成测试 | 手动测试 |

### 依赖关系

```
步骤 1 ──▶ 步骤 2 (测试)
    │
    ▼
步骤 3 ──▶ 步骤 4 ──▶ 步骤 5 ──▶ 步骤 6
                                        │
                                        ▼
                                   步骤 7 ──▶ 步骤 8
```

---

## 注意事项

1. **classes.txt 来源**：由扫描阶段生成在站点根目录，直接复制即可
2. **LabelImg 安装**：通过 `pip install labelImg` 安装
3. **路径编码**：注意处理编码后的文件名（使用 `PathEncoder`）
4. **线程安全**：页面操作在主线程，LabelImg 启动为独立进程

---

## 后续扩展

- 支持查看已还原的标注文件
- 支持批量导出选中的标注结果
- 支持标注结果对比视图（并排显示多次推理结果）
