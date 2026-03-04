# AutoLabeler 项目交接文档

> 用途：新 Claude 窗口快速了解项目状态并继续开发

## 项目概述

**AutoLabeler** 是一个桌面智能标注工具，结合手动标注和 YOLO 自动推理来大幅减少标注工作量。

**核心工作流**: 扫描 → 抽样 → 手动标注 → 训练 → 推理 → 还原 → (可选) 转换为 VOC

## 当前状态 (2025-01-28)

### 完成度: 100%

**最新更新**: PyInstaller 打包问题修复 + 功能增强

| 阶段 | 模块 | 状态 | 测试 |
|------|------|------|------|
| 1 | 核心基础设施 | ✅ | 46/46 |
| 2 | 数据处理 | ✅ | 23/23 |
| 3 | 训练与推理 | ✅ | 12/12 |
| 4 | 格式转换 | ✅ | 19/19 |
| 5-6 | GUI | ✅ | - |

**总测试数**: 111/111 全部通过

### 最近更新

**功能增强** (2025-01-14):

**问题1：已有标注样本优先抽样**
- **功能**：
  - 自动检测产品文件夹中的已有标注文件（VOC XML / YOLO TXT）
  - XML 格式自动转换为 YOLO TXT
  - 抽样时优先提取已标注样本，减轻人工标注压力
  - 已标注样本同样按 train_ratio 随机分配到 train/vals
- **配置项**：`SampleConfig(pre_labeled_priority=True)`
- **数据结构**：`ImageInfo.label_source` 字段记录标注来源
- **相关文件**：[sampler.py](core/sampler.py), [converter.py](core/converter.py)

**问题2：推理结果分区存储**
- **功能**：
  - 推理结果保存到独立目录 `.autolabeler/inference_results/run_YYYYMMDD_HHMMSS/`
  - 每次推理生成 `inference_config.json` 记录参数（置信度、IoU、设备等）
  - 保留所有历史推理结果，便于对比不同阈值效果
  - 支持从推理结果目录还原到原位置
- **目录结构**：
  ```
  .autolabeler/
  ├── inference_results/
  │   ├── run_20250114_143022/
  │   │   ├── inference_config.json
  │   │   ├── Code1/ProductA/*.txt
  │   │   └── Code2/ProductB/*.txt
  │   └── run_20250114_150135/
  └── mapping.json
  ```
- **配置项**：`InferenceConfig(save_to_separate_dir=True)`
- **相关文件**：[inferencer.py](core/inferencer.py), [restorer.py](core/restorer.py)

---

**PyInstaller 打包问题修复** (2025-01-28):
- **问题**: 打包后的 exe 训练时报错 `AttributeError: 'NoneType' object has no attribute 'write'`
- **根本原因**:
  - PyInstaller 使用 `console=False`（无控制台模式）打包
  - Windows 将 `sys.stdout` 和 `sys.stderr` 设置为 `None`
  - ultralytics 使用 tqdm 显示进度条，tqdm 尝试向 stderr/stdout 调用 `write()` 方法导致报错
- **解决方案**:
  - 在 [main.py](main.py) 中添加 `NullWriter` 类
  - 检测 `sys.frozen` 判断是否为打包环境
  - 仅在 `sys.stdout` 或 `sys.stderr` 为 `None` 时替换为 `NullWriter`
- **相关文件**：[main.py](main.py), [build_exe.spec](build_exe.spec)

---

**小目标检测优化** (2025-01-12):
- **问题**: YOLO 训练 mAP50=0，即使损失下降
- **原因**:
  1. YOLO 过滤 < 2% 图像尺寸的框（640px 约 13px）
  2. 小数据集需要更多轮次（50-100+ epochs）
- **解决方案**:
  - 添加小目标参数: `box=2.0`, `cls=0.3`
  - 创建诊断工具: `debug_training_data.py`
  - 创建修复工具: `fix_small_boxes.py`
  - 创建配置指南: `SMALL_OBJECT_DETECTION.md`
- **测试验证**: 3 epochs 产生 423 个预测 (conf=0.001)，证明模型在学习

**推荐配置**:
```python
# 小目标检测
TrainConfig(image_size=640, box=2.0, cls=0.3, epochs=50)

# 最佳效果
TrainConfig(image_size=1280, box=2.0, cls=0.3, epochs=100)
```

**推理界面参数完善** (2025-01-09):
- 推理界面添加 `device_combo` 下拉框（同训练界面）
- 推理界面 `batch_spin` 改为 -1（自动检测）
- 参数隔离：训练和推理使用各自的 Worker/Config，互不影响

**推理模块性能优化** (2025-01-09):
- 添加 `device` 参数 (`auto`/`cpu`/`0`/`mps`)
- 添加 `batch_size=-1` 自动检测
- CPU 默认 batch_size=8 (原32，避免卡顿)
- GPU 根据显存自动选择 (4-32)
- 显式调用 `model.to(device)`

## 开发环境

```bash
# Python 环境
D:\miniforge3\envs\yolo\python.exe

# 激活环境
conda activate yolo

# 运行应用
python main.py

# 运行测试 (只测相关模块)
pytest tests/test_<module>.py -v
```

## 关键设计模式

### 1. 路径编码 (双下划线分隔)

```
原始:  AS_CV_PI_P/H4A238FDF04/IMG_001.jpg
编码:   AS_CV_PI_P__H4A238FDF04__IMG_001.jpg
目的:   避免扁平化复制时文件名冲突
```

**重要**: 解码时永远从 `MappingManager.get_image_info()` 获取 `format` 字段，不要硬编码扩展名。

### 2. 线程安全 (MappingManager)

双重锁机制:
1. `threading.RLock()` - 实例级操作
2. `FileLock` - 跨进程文件 I/O
3. `_global_mapping_lock` - 全局协调

**始终使用管理器方法**，不要直接访问 `data`:
```python
# 正确
info = mapping.get_image_info(encoded_name)

# 错误 (不线程安全)
info = mapping.data.images.get(encoded_name)
```

### 3. 设备自动检测

```python
# 配置使用
device: str = "auto"    # 触发自动检测
batch_size: int = -1    # -1 表示自动计算

# 工具函数
from utils.device import get_optimal_device, get_optimal_batch_size
```

## 核心模块

| 模块 | 文件 | 功能 | 新功能 |
|------|------|------|--------|
| Scanner | core/scanner.py | 扫描站点文件夹，构建映射 | - |
| Sampler | core/sampler.py | 按产品抽样到 train/vals | ✅ 已标注优先 + XML转TXT |
| Trainer | core/trainer.py | YOLO 训练，自动设备检测 | - |
| Inferencer | core/inferencer.py | 批量推理 | ✅ 分区存储 + 历史管理 |
| Restorer | core/restorer.py | 还原标注到原始位置 | ✅ 支持从推理结果还原 |
| Converter | core/converter.py | YOLO txt ↔ VOC xml | ✅ 新增 XML→TXT 转换 |

## 抽样逻辑确认

**抽样是按产品进行的**，不是从所有图片随机抽取：

```python
# core/sampler.py:_group_by_product_with_labels()
key = f"{info['code']}/{info['product']}"
```

每个 code/product 组合单独计算抽样数量，确保所有产品都有代表样本。

**已标注样本优先抽取**：
1. 扫描产品文件夹，检测 `.xml` 和 `.txt` 标注文件
2. 已标注样本标记为 `label_source: "pre_existing_xml/txt"`
3. 抽样时优先提取已标注样本
4. 如果已标注样本数量 ≥ 设定数量 → 全抽已标注的
5. 如果已标注样本数量 < 设定数量 → 已标注全抽 + 随机抽取不足数量

## 推理位置确认

**新逻辑 (2025-01-14)**：推理后标注文件保存到独立目录

```
# core/inferencer.py
if save_to_separate_dir:
    output_dir = ".autolabeler/inference_results/run_YYYYMMDD_HHMMSS/"
    # 保持原目录结构: CodeA/ProductA/IMG_001.txt
else:
    # 兼容旧逻辑：直接保存到原位置
    txt_path = img_path.with_suffix('.txt')
```

**还原功能**：
- `restore()` - 从 `database/labels/` 还原人工标注
- `restore_from_inference()` - 从 `inference_results/run_xxx/` 还原推理结果

## 小目标检测诊断工具

**问题场景**: 训练时 mAP50=0，即使损失在下降

**诊断工具** (位于 `tools/` 和 `tests/` 目录):
```bash
# 1. 深度诊断训练数据
cd tools
python debug_training_data.py ../database/data.yaml

# 2. 修复过小的标注框
python fix_small_boxes.py ../database/labels/train 0.05 3.0

# 3. 对比不同配置效果
cd ../tests
python test_small_object_config.py
```

**关键配置参数**:
```python
# core/trainer.py:TrainConfig
box: float = 7.5   # 小目标建议 2.0
cls: float = 0.5   # 小目标建议 0.3
scale: float = 0.5 # 图像缩放增强
```

**验证方法**:
```python
# 使用极低置信度阈值检查是否有预测
results = model.predict(img, conf=0.001)
```

**参考资料**:
- `SMALL_OBJECT_DETECTION.md` - 完整配置指南
- `tools/README.md` - 工具集使用说明

## 重要文件

| 文件 | 用途 |
|------|------|
| CLAUDE.md | 完整项目文档（架构、API、测试） |
| requirement.md | 产品需求 |
| jishukaifawendang.md | 技术规范（含新功能设计） |
| CURRENT_STATE.md | 开发状态记录 |
| **SMALL_OBJECT_DETECTION.md** | 小目标检测配置指南 |
| **tools/README.md** | 诊断和修复工具使用说明 |
| **HANDOFF.md** | 本文件，新窗口快速上手 |

## 测试资源

- `tests/test_data/A9950/` - 测试站点文件夹
- `tests/test_data/yolo11n.pt` - 基础训练模型
- `tests/test_data/best.pt` - 训练好的推理模型

## 常见命令

```bash
# 只测试变更的模块
pytest tests/test_sampler.py -v

# 测试多个相关模块
pytest tests/test_inferencer.py tests/test_device.py -v

# 运行所有测试 (不推荐，除非最终验证)
pytest tests/ -v

# 代码格式化
black .
```

## 已知问题和优化方案

### 推理功能：参数调整后无法重新推理 (2025-01-21)

**问题描述**:
- 当前推理时立即标记 `inferred=True`（[inferencer.py:175](core/inferencer.py)）
- `get_pending_inference_images()` 跳过所有已推理图片（[mapping_manager.py:250-262](utils/mapping_manager.py)）
- 用户调整 IOU/置信度参数后无法重新推理相同图片

**当前行为**:
```
推理 → inferred=True → 调整参数 → 再次推理 → 跳过所有图片（0 张）
```

**期望行为**:
```
推理 → 结果保存到时间戳目录 → 调整参数 → 再次推理 → 生成新时间戳目录 → 还原时选择满意的结果
```

**优化方案** (移除筛选条件):
| 文件 | 修改 |
|------|------|
| [utils/mapping_manager.py:250-262](utils/mapping_manager.py) | 移除 `not v.get("inferred", False)` 筛选条件 |

**修改内容**:
```python
# 修改前
def get_pending_inference_images(self) -> List[Dict]:
    return [
        {"encoded_name": k, **v}
        for k, v in self.data.images.items()
        if not v.get("sampled", False) and not v.get("inferred", False)
    ]

# 修改后
def get_pending_inference_images(self) -> List[Dict]:
    return [
        {"encoded_name": k, **v}
        for k, v in self.data.images.items()
        if not v.get("sampled", False)  # 只排除已抽样的图片
    ]
```

**新语义**:
- `inferred` 字段仅用于统计/显示，不再影响推理筛选
- 推理结果保存在时间戳目录，用户可多次推理并对比效果
- 还原时选择使用哪次推理结果

**优势**:
1. 支持任何时候重新推理（包括已还原的图片）
2. 保留多次推理历史，可对比不同参数效果
3. 改动最小：只修改一行筛选条件

**实施状态**: 已实施

## 待办事项 (可选优化)

- 配置持久化 (保存/加载用户配置)
- 训练曲线可视化
- 多语言支持
- 打包为可执行文件

## 异常处理

使用自定义异常而非通用 Exception:
```python
from utils.exceptions import (
    AutoLabelerError, ScanError, SampleError,
    TrainError, InferenceError, RestoreError,
    ConvertError, MappingError, ValidationError,
    FileOperationError, ImageLoadError, DeviceError
)
```

## GUI 开发提醒

- PySide6 + QFluentWidgets
- 所有页面继承 `BasePage`
- 后台任务继承 `BaseWorker` (QThread)
- 工作线程中需要取消支持时检查 `self.is_cancelled`

## 快速检查清单

在新窗口开始工作前：

1. ✅ 确认 Python 环境: `conda activate yolo`
2. ✅ 确认测试通过: `pytest tests/ -v` (或只测相关模块)
3. ✅ 查看最近更新: 阅读本文档 "最近更新" 部分
4. ✅ 查看详细设计: [jishukaifawendang.md](jishukaifawendang.md) 第10章
5. ✅ 修改后更新: CLAUDE.md 和 HANDOFF.md

---

**生成时间**: 2025-01-28
**项目路径**: d:\code\vscode_code\auto_yolo_label
**当前任务**: PyInstaller 打包问题修复 - 修复无控制台模式下 tqdm 报错
