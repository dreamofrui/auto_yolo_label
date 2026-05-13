# AutoLabeler 重构需求规范

> 文档版本：v1.0
> 创建日期：2026-05-13
> 目标读者：负责重写本项目的开发者（默认无业务背景）
> 配套文档：`02-constraints.md`（强制约束），`03-progress-template.md`（进度维护）

---

## 0. 阅读须知

这份文档**只描述「要做什么」**，不描述「怎么做」。「怎么做」的硬约束在 `02-constraints.md`。

如果你在本文档里看到任何模棱两可的描述（例如"建议"、"可以考虑"、"通常"），停下来问负责人，不要自行决定。

模块之间**只通过本文档定义的输入输出 dataclass 通信**，不允许通过共享变量、全局状态、隐式约定通信。

---

## 1. 项目背景与定位

### 1.1 是什么

AutoLabeler 是一个**单机本地**的半自动图像标注工具，面向 YOLO 目标检测训练数据准备。

核心价值：用户只需手工标注 10-20% 的样本，模型自动标注剩余样本，节省标注工时。

### 1.2 谁在用

- **标注员**（不懂机器学习）：执行扫描→抽样→标注→训练→推理→还原全流程
- **算法工程师**：调参数、跑实验、对比不同 conf/iou 阈值的推理效果
- **项目维护开发者**：扩展功能、接入 Web、修 bug

### 1.3 工作流（典型路径）

```
扫描站点目录 → 抽样生成训练集 → 人工标注样本 → 训练 YOLO →
推理未标注图 → 检查推理结果 → 还原标注到原目录 → （可选）转 VOC XML
```

### 1.4 不是单一路径

**核心原则：上述工作流只是一种典型用法，每个模块必须能独立使用。**

合法的非典型场景：
- 用户已有 `mapping.json` + `database/`，直接训练，跳过扫描和抽样
- 用户从别处拿到一个 `best.pt`，直接对任意文件夹推理，跳过训练
- 用户手动整理了标注文件夹，直接还原到原始目录
- 用户只想用 YOLO↔VOC 格式转换功能，与本项目其他流程完全无关

---

## 2. 总体架构

### 2.1 三层结构

```
┌────────────────────────────────────────────────────────┐
│  Presentation Layer                                    │
│  - gui/   PySide6 桌面 GUI（开发调试入口）              │
│  - api/   FastAPI HTTP 路由（Web 接入入口）             │
└────────────────────┬───────────────────────────────────┘
                     │ 直接 import / 路由调用
┌────────────────────▼───────────────────────────────────┐
│  Business Layer (core/)                                │
│  - Scanner / Sampler / Trainer / Inferencer            │
│  - Restorer / Converter / LabelInspector / LabelImg    │
│  零 GUI/HTTP 框架依赖                                   │
└────────────────────┬───────────────────────────────────┘
                     │
┌────────────────────▼───────────────────────────────────┐
│  Infrastructure Layer (utils/)                         │
│  - MappingManager / PathEncoder / TaskRegistry         │
│  - Device / Logging / Exceptions                       │
└────────────────────────────────────────────────────────┘
```

### 2.2 目标目录结构

```
auto_yolo_label/
├── core/                       # 业务模块（每个文件一个模块入口类）
│   ├── __init__.py
│   ├── scanner.py              # Scanner + ScanConfig + ScanResult
│   ├── sampler.py
│   ├── trainer.py
│   ├── inferencer.py
│   ├── label_inspector.py
│   ├── restorer.py
│   ├── converter.py
│   └── labelimg_launcher.py    # 外部 LabelImg 启动与即时标注
├── utils/                      # 基础设施
│   ├── __init__.py
│   ├── mapping_manager.py      # mapping.json 读写（线程安全）
│   ├── path_encoder.py         # Code/Product/Filename 编解码
│   ├── task_registry.py        # 进程内任务管理（新增）
│   ├── device.py               # GPU/CPU 检测
│   ├── exceptions.py           # AutoLabelerError + 子类 + 错误码枚举
│   ├── logging_setup.py        # 统一 logging 配置
│   └── image_utils.py
├── gui/                        # PySide6 桌面 GUI
│   ├── app.py
│   ├── main_window.py
│   ├── pages/
│   └── workers/                # 调用 core，向 UI 推进度
├── api/                        # FastAPI HTTP 路由（新增）
│   ├── __init__.py
│   ├── main.py                 # uvicorn 启动入口
│   ├── routes/                 # 每个模块一个路由文件
│   │   ├── scan.py
│   │   ├── sample.py
│   │   └── ...
│   ├── schemas/                # pydantic 请求/响应模型
│   └── tasks.py                # 任务查询、取消、SSE
├── tests/
├── docs/
└── main.py                     # 桌面入口（默认）
```

### 2.3 模块对应表

| 业务功能 | core 模块 | 主要类 | 调用方 |
|----------|-----------|--------|--------|
| 扫描站点 | `core/scanner.py` | `Scanner` | gui/workers/scan_worker.py, api/routes/scan.py |
| 抽样 | `core/sampler.py` | `Sampler` | sample_worker.py, sample.py |
| 训练 | `core/trainer.py` | `Trainer` | train_worker.py, train.py |
| 推理 | `core/inferencer.py` | `Inferencer` | inference_worker.py, infer.py |
| 推理检查 | `core/label_inspector.py` | `LabelInspector` | label_viewer_page.py, inference.py |
| 还原 | `core/restorer.py` | `Restorer` | restore_worker.py, restore.py |
| 转换 | `core/converter.py` | `Converter` | convert_worker.py, convert.py |
| LabelImg | `core/labelimg_launcher.py` | `LabelImgLauncher` | settings_page.py, labelimg.py |

---

## 3. 共享数据模型

所有 dataclass 用 Python `@dataclass`，路径字段统一 `pathlib.Path`。

### 3.1 MappingData

来源：`utils/mapping_manager.py:MappingData`。**唯一允许操作 `mapping.json` 的入口是 `MappingManager`，不允许其他模块直接读写该文件。**

```python
@dataclass
class MappingData:
    version: str                    # 当前固定 "1.0"
    project_name: str
    site_folder: Path
    created_time: str               # "YYYY-MM-DD HH:MM:SS"
    updated_time: str
    classes: dict[str, str]         # {"0": "AS_CV_PI_P", "1": "M1_SP_PI_P"}
    config: dict                    # 抽样配置快照
    statistics: dict                # 计数统计
    products: dict[str, dict[str, int]]  # {Code: {Product: image_count}}
    images: dict[str, ImageInfo]    # key 是编码后文件名
```

### 3.2 ImageInfo

```python
@dataclass
class ImageInfo:
    original_relative: str          # "Code/Product/Filename.jpg"
    code: str                       # Code 文件夹名（同时是类别名）
    product: str                    # Product 文件夹名
    original_name: str              # 原始文件名
    format: str                     # ".jpg"
    sampled: bool = False           # 是否已抽样到 database
    split: str | None = None        # "train" / "val" / None
    manual_labeled: bool = False    # 是否人工标注过
    inferred: bool = False          # 是否推理过（仅统计用，不作筛选）
    restored: bool = False          # 是否已还原
    label_source: str = "none"      # "none"/"pre_existing_xml"/"pre_existing_txt"/"manual"/"inferred"
```

### 3.3 DeviceInfo

```python
@dataclass
class DeviceInfo:
    device: str                     # "cuda" / "cpu" / "mps"
    device_id: str                  # "0" / "0,1" / ""
    is_available: bool
    name: str                       # "NVIDIA GeForce RTX 4090 x1"
    memory_mb: int                  # 显存大小（MB），CPU 时为 0
```

### 3.4 TaskHandle（新增，所有 >1 秒任务统一接口）

```python
@dataclass
class TaskHandle:
    task_id: str                    # "task_scan_20260513_101530_abc123"
    task_type: str                  # "scan"/"sample"/"train"/"infer"/"restore"/"convert"
    status: str                     # "queued"/"running"/"succeeded"/"failed"/"cancelled"
    progress_current: int
    progress_total: int
    progress_message: str
    logs: list[str]
    result: dict | None             # 成功时填，失败时为 None
    error: ErrorInfo | None         # 失败时填
    created_at: str
    started_at: str | None
    finished_at: str | None
```

任务管理由 `utils/task_registry.py:TaskRegistry` 提供，桌面 worker 和 HTTP 路由共用同一个 registry 实例。

### 3.5 ErrorInfo

```python
@dataclass
class ErrorInfo:
    code: str                       # "SCAN_LABEL_MISMATCH" 等错误码枚举
    message: str                    # 人类可读消息（中文）
    details: str | None             # 调试详情（堆栈或附加信息）
    retryable: bool                 # 是否可直接重试
```

---

## 4. 文件与目录约定

### 4.1 站点目录（输入）

站点目录**必须**满足三级结构：

```
site_folder/
├── CodeA/                # Code 层（同时是类别名）
│   ├── ProductA/         # Product 层
│   │   ├── image001.jpg
│   │   ├── image001.xml  # 可选，已有 VOC 标注
│   │   └── image002.png
│   └── ProductB/
└── CodeB/
    └── ProductC/
```

约束：
- 支持图片格式：`.jpg`、`.jpeg`、`.png`、`.bmp`（小写后缀；大写后缀也要识别但落盘统一小写）
- 隐藏目录（以 `.` 开头）跳过
- 扫描**不递归** Product 下面的子目录，只看 Product 直接子文件
- 文件名不允许包含双下划线 `__`（与路径编码冲突）

### 4.2 `.autolabeler/` 工作目录

扫描后在站点目录下自动生成：

```
site_folder/.autolabeler/
├── mapping.json                # 全局状态
├── classes.txt                 # 类别列表（每行一个，按 class_id 排序）
└── inference_results/
    └── run_20260513_103000/    # 一次推理 = 一个时间戳目录
        ├── inference_config.json
        ├── CodeA/ProductA/*.txt
        └── CodeB/ProductB/*.txt
```

### 4.3 抽样输出目录（database）

```
database/
├── data.yaml                   # YOLO 训练配置
├── images/
│   ├── train/Code__Product__Image.jpg
│   └── val/Code__Product__Image.jpg     # 注意：新版用 val，不再用 vals
└── labels/
    ├── train/Code__Product__Image.txt
    └── val/Code__Product__Image.txt
```

**重要：旧版用 `vals/`，新版统一改为 `val/`。data.yaml 中也写 `val: images/val`。**

### 4.4 路径编码规则

```
原始：    AS_CV_PI_P/H4A238FDF04/IMG_001.jpg
编码后：  AS_CV_PI_P__H4A238FDF04__IMG_001.jpg
```

实现：`utils/path_encoder.py:PathEncoder.encode()` / `decode()`。

- 分隔符：双下划线 `__`
- 编码方向：**仅在抽样阶段做**。还原阶段通过 `mapping.json` 查原路径，不允许反向解析文件名
- 不允许任何模块自行字符串拼接编码/解码

### 4.5 配置存储

| 配置 | 路径 | 范围 |
|------|------|------|
| LabelImg Python 路径 | `~/.autolabeler/labelimg.json` | 用户级（跨项目共享） |
| 全局默认参数 | `~/.autolabeler/settings.json` | 用户级（可选实现，本期不强制） |
| 项目状态 | `site_folder/.autolabeler/mapping.json` | 项目级 |

---

## 5. 八大功能模块详解

每个模块的描述都包含：作用 / 输入 / 输出 / 文件产物 / 状态变更 / 异常 / 注意点 / 调用示例。

### 5.1 Scanner（扫描模块）

#### 5.1.1 作用

遍历站点目录，建立全局图片索引，生成 `mapping.json` 和 `classes.txt`。

#### 5.1.2 输入

```python
@dataclass
class ScanConfig:
    site_folder: Path                       # 必填
    output_dir: Path | None = None          # 默认 site_folder/.autolabeler
    supported_formats: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".bmp")
    validate_existing_xml: bool = True      # 是否校验已有 XML 标签与 Code 一致
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `site_folder` | Path | 是 | 站点根目录 |
| `output_dir` | Path \| None | 否 | mapping/classes 输出目录，None 时落到 `site_folder/.autolabeler` |
| `supported_formats` | tuple[str, ...] | 否 | 识别的图片后缀 |
| `validate_existing_xml` | bool | 否 | 若 XML 内 `<object><name>` 与 Code 不一致，则抛 `ScanLabelMismatchError` |

#### 5.1.3 输出

```python
@dataclass
class ScanResult:
    mapping_path: Path
    classes_path: Path
    statistics: ScanStatistics
    classes: list[str]                      # 按 class_id 升序
    products: dict[str, dict[str, int]]     # {Code: {Product: count}}

@dataclass
class ScanStatistics:
    total_images: int
    total_codes: int
    total_products: int
```

#### 5.1.4 文件产物

```
site_folder/.autolabeler/mapping.json   # 创建或完整覆盖
site_folder/.autolabeler/classes.txt
```

#### 5.1.5 状态变更

- 全新创建或**完整覆盖** `mapping.json`（旧的所有状态会丢失，需提示用户）
- 不修改任何原图片或原 XML 文件

#### 5.1.6 异常

| 异常类 | 错误码 | 触发条件 |
|--------|--------|----------|
| `ScanPathNotFoundError` | `SCAN_PATH_NOT_FOUND` | site_folder 不存在 |
| `ScanInvalidStructureError` | `SCAN_INVALID_STRUCTURE` | 找不到 Code/Product 两级目录 |
| `ScanLabelMismatchError` | `SCAN_LABEL_MISMATCH` | XML 标签与 Code 不一致 |
| `ScanEmptyError` | `SCAN_EMPTY` | 未找到任何图片 |

#### 5.1.7 注意点

- 调用方应在覆盖前提醒用户："已有 mapping.json 将被覆盖"
- 文件名校验：包含 `__` 的图片要拒绝（与路径编码冲突），抛 `ScanInvalidStructureError`
- 大小写：磁盘上的 `.JPG` 也要被识别，但 `mapping.json` 内统一记为 `.jpg`

#### 5.1.8 调用示例

```python
from pathlib import Path
from core.scanner import Scanner, ScanConfig

config = ScanConfig(site_folder=Path("D:/data/A9950"))
result = Scanner().scan(config)
print(result.statistics.total_images)
```

---

### 5.2 Sampler（抽样模块）

#### 5.2.1 作用

按 `Code/Product` 维度抽取样本到 `database/`，自动检测并优先抽取已有标注的图片。

#### 5.2.2 输入

```python
@dataclass
class SampleConfig:
    site_folder: Path
    output_dir: Path                        # database 输出目录
    mode: str = "count"                     # "count" / "ratio" / "mixed"
    count: int = 40
    ratio: float = 0.3
    min_count: int = 20                     # mixed 模式下限
    max_count: int = 50                     # mixed 模式上限
    full_threshold: int = 35                # 总数 <= 该值时全抽
    train_ratio: float = 0.9                # 训练集占比
    pre_labeled_priority: bool = True       # 是否优先抽取已有标注的图片
```

| 字段 | 必填 | 取值范围 | 说明 |
|------|------|----------|------|
| `mode` | 否 | `count`/`ratio`/`mixed` | 抽样数量计算方式 |
| `count` | 否 | ≥ 1 | count 模式下每产品抽样数 |
| `ratio` | 否 | (0, 1] | ratio 模式下每产品抽样比例 |
| `min_count` / `max_count` | 否 | min ≤ max | mixed 模式的上下限 |
| `full_threshold` | 否 | ≥ 1 | 产品总图数 ≤ 该阈值时全抽 |
| `train_ratio` | 否 | [0.5, 1.0] | train 集占比，剩余为 val |
| `pre_labeled_priority` | 否 | - | 优先抽取已有 XML/TXT 标注 |

#### 5.2.3 抽样数量规则

| 模式 | 规则 |
|------|------|
| `count` | 实际数 = `max(count, full_threshold)`；产品总数 ≤ 该值则全抽 |
| `ratio` | 总数 ≤ `full_threshold` 全抽；否则 `int(total * ratio)`，最少 1 |
| `mixed` | 总数 ≤ `full_threshold` 全抽；否则 `ratio` 结果 clamp 到 `[min_count, max_count]` |

#### 5.2.4 已有标注处理

- 同名 `.xml` 存在且非空 → `label_source="pre_existing_xml"`，转 YOLO TXT 后复制
- 同名 `.txt` 存在且非空（排除 `classes.txt`/`data.yaml`/`README.txt`）→ `label_source="pre_existing_txt"`，直接复制
- 空 XML/TXT → 视为无标注，不处理（**不删除原文件**，避免破坏用户数据）
- 无预标注图片 → 只复制图片，不创建空 label（等待人工标注工具生成）

#### 5.2.5 输出

```python
@dataclass
class SampleResult:
    mapping_path: Path
    dataset_dir: Path
    data_yaml: Path
    paths: SamplePaths
    statistics: SampleStatistics

@dataclass
class SamplePaths:
    images_train: Path
    images_val: Path
    labels_train: Path
    labels_val: Path

@dataclass
class SampleStatistics:
    total_products: int
    sampled_count: int
    train_count: int
    val_count: int
    pre_labeled_count: int                  # 含预标注的抽样数
```

#### 5.2.6 文件产物

```
database/data.yaml
database/images/train/*
database/images/val/*
database/labels/train/*
database/labels/val/*
site_folder/.autolabeler/mapping.json      # 更新 sampled/split/label_source/config/statistics
```

`data.yaml` 必须包含：

```yaml
path: <database 绝对路径>
train: images/train
val: images/val
nc: <类别数>
names: [<类别名列表>]
```

#### 5.2.7 异常

| 异常类 | 错误码 | 触发条件 |
|--------|--------|----------|
| `SampleMappingNotFoundError` | `SAMPLE_MAPPING_NOT_FOUND` | mapping.json 不存在（未扫描） |
| `SampleInvalidConfigError` | `SAMPLE_INVALID_CONFIG` | 参数越界（如 ratio > 1） |
| `SampleXmlConvertError` | `SAMPLE_XML_CONVERT` | XML 解析失败或类别名不在 mapping.classes 中 |
| `SampleIOError` | `SAMPLE_IO` | 磁盘空间不足 / 权限不足 |

#### 5.2.8 注意点

- 抽样模块**必须**从 `mapping.json` 读 classes 列表；不允许从文件夹名重新生成
- 抽样**不**自动调用扫描；缺 mapping.json 时直接报错，让用户决定是否重扫
- train/val 划分必须保持每个 Code 在两集都有样本（如果该 Code 抽样数 ≥ 2）

#### 5.2.9 调用示例

```python
from core.sampler import Sampler, SampleConfig

result = Sampler().sample(SampleConfig(
    site_folder=Path("D:/data/A9950"),
    output_dir=Path("D:/data/A9950_database"),
    mode="count",
    count=40,
))
```

---

### 5.3 LabelImg 集成模块

#### 5.3.1 作用

- 验证用户配置的外部 Python 环境是否安装 LabelImg
- 启动 LabelImg 打开指定目录（database 或推理结果目录）
- 即时标注：用户选定单个产品目录，直接拉起 LabelImg 标注

#### 5.3.2 输入

```python
@dataclass
class LabelImgConfig:
    python_path: Path                       # 外部 Python 解释器
    image_dir: Path                         # 图片目录
    label_dir: Path | None = None           # 标签目录，None 时与 image_dir 相同
    classes_file: Path | None = None        # classes.txt 路径，None 时从 image_dir 自动查找
```

```python
@dataclass
class LabelImgValidateConfig:
    python_path: Path
```

#### 5.3.3 输出

```python
@dataclass
class LabelImgValidateResult:
    is_valid: bool
    labelimg_version: str | None
    python_version: str
    error_message: str | None

@dataclass
class LabelImgLaunchResult:
    process_id: int
    command: str                            # 实际执行的命令字符串
```

#### 5.3.4 文件产物

- 用户在 LabelImg 内保存的 `.xml` 或 `.txt` 文件落到 `label_dir`
- LabelImg 可能把 `classes.txt` 复制到 `image_dir`（**后续 Restorer / Converter 必须过滤此文件**）
- 用户级配置写到 `~/.autolabeler/labelimg.json`

#### 5.3.5 异常

| 异常类 | 错误码 | 触发条件 |
|--------|--------|----------|
| `LabelImgPythonNotFoundError` | `LABELIMG_PYTHON_NOT_FOUND` | 指定 python 解释器不存在 |
| `LabelImgNotInstalledError` | `LABELIMG_NOT_INSTALLED` | 该 Python 环境未安装 labelImg 包 |
| `LabelImgLaunchError` | `LABELIMG_LAUNCH` | 启动子进程失败 |

#### 5.3.6 注意点

- **只在后端机器有 GUI 的环境下能用**。纯远程 Web 部署时该模块的 launch 接口不可用，应由 API 层判断并禁用
- 启动方式：`subprocess.Popen([python_path, "-m", "labelImg", image_dir, classes_file, label_dir])`
- 不阻塞调用方；返回 `process_id` 后立即返回
- 用户切换标注集时，要传新的 `image_dir`，不要复用进程

#### 5.3.7 调用示例

```python
from core.labelimg_launcher import LabelImgLauncher, LabelImgConfig, LabelImgValidateConfig

launcher = LabelImgLauncher()
validate = launcher.validate(LabelImgValidateConfig(python_path=Path("D:/envs/labelimg/python.exe")))
if validate.is_valid:
    launcher.launch(LabelImgConfig(
        python_path=Path("D:/envs/labelimg/python.exe"),
        image_dir=Path("D:/data/A9950_database/images/train"),
        label_dir=Path("D:/data/A9950_database/labels/train"),
    ))
```

---

### 5.4 Trainer（训练模块）

#### 5.4.1 作用

使用 Ultralytics YOLO 训练模型，自动检测设备和 batch size，逐 epoch 报告进度。

#### 5.4.2 输入

```python
@dataclass
class TrainConfig:
    data_yaml: Path                         # 必填，可以来自 Sampler 输出，也可以用户自备
    base_model: Path                        # 必填，预训练 .pt
    output_dir: Path                        # 必填
    epochs: int = 100
    batch_size: int = -1                    # -1 自动检测
    image_size: int = 640
    device: str = "auto"                    # "auto"/"cpu"/"0"/"0,1"/"mps"
    patience: int = 50
    workers: int = 8
    optimizer: str = "AdamW"
    lr0: float = 0.01
    box: float = 7.5                        # box loss gain（小目标建议 1.5-3.0）
    cls: float = 0.5                        # cls loss gain（小目标建议 0.3-0.5）
    dfl: float = 1.5
    scale: float = 0.5
    cache: str | bool = "ram"               # "ram"/"disk"/False
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `data_yaml` | 是 | 训练配置文件，**不要求**来自 Sampler，用户自备也可 |
| `base_model` | 是 | 预训练权重 `.pt` 路径 |
| `output_dir` | 是 | YOLO run 输出目录 |
| 其他 | 否 | 全部 YOLO 训练超参，default 见 dataclass |

#### 5.4.3 输出

```python
@dataclass
class TrainResult:
    best_model: Path
    last_model: Path | None
    output_dir: Path                        # YOLO run 实际目录
    effective_config: dict                  # 实际生效的训练参数（含自动检测的 batch_size、device）
    metrics: TrainMetrics

@dataclass
class TrainMetrics:
    best_epoch: int
    best_map50: float
    best_map50_95: float
    final_map50: float
    final_map50_95: float
```

#### 5.4.4 进度回调

通过 `TaskHandle.progress_*` 字段实时更新：

```python
# 每个 epoch 结束时
task_handle.progress_current = epoch
task_handle.progress_total = total_epochs
task_handle.progress_message = f"Epoch {epoch}/{total_epochs} - mAP50: {map50:.3f}"
```

#### 5.4.5 文件产物

```
output_dir/train/
├── weights/best.pt
├── weights/last.pt
├── results.csv
└── args.yaml
```

#### 5.4.6 异常

| 异常类 | 错误码 | 触发条件 |
|--------|--------|----------|
| `TrainDataYamlInvalidError` | `TRAIN_DATA_YAML_INVALID` | data.yaml 缺失字段或路径错误 |
| `TrainBaseModelNotFoundError` | `TRAIN_BASE_MODEL_NOT_FOUND` | 预训练权重不存在 |
| `TrainDeviceUnavailableError` | `TRAIN_DEVICE_UNAVAILABLE` | 指定设备不可用 |
| `TrainOOMError` | `TRAIN_OOM` | 显存不足（自动 batch 也失败） |
| `TrainInterruptedError` | `TRAIN_INTERRUPTED` | 用户取消 |

#### 5.4.7 注意点

- 训练**不依赖** `mapping.json`，完全由 `data.yaml` 驱动
- `batch_size=-1` 时由 ultralytics 自动检测；CPU 环境下强制 batch_size ≥ 1
- 用户取消（通过 `TaskRegistry.cancel(task_id)`）必须能干净停下，并保留已生成的 weights/best.pt
- 训练过程中产生的临时缓存（如 `*.cache`）要在异常退出时清理

#### 5.4.8 调用示例

```python
from core.trainer import Trainer, TrainConfig

result = Trainer().train(TrainConfig(
    data_yaml=Path("D:/data/A9950_database/data.yaml"),
    base_model=Path("D:/models/yolov8n.pt"),
    output_dir=Path("D:/models/A9950_run_001"),
    epochs=100,
))
```

---

### 5.5 Inferencer（推理模块）

#### 5.5.1 作用

用训练好的模型对图片批量推理，输出 YOLO TXT 标签到独立时间戳目录。

#### 5.5.2 输入

```python
@dataclass
class InferConfig:
    model_path: Path                        # 必填
    site_folder: Path                       # 必填
    output_base_dir: Path | None = None     # 默认 site_folder/.autolabeler/inference_results
    confidence: float = 0.25
    iou: float = 0.7                        # 统一默认值 0.7（旧版多个地方不一致，新版必须统一）
    batch_size: int = -1
    device: str = "auto"
    save_to_separate_dir: bool = True
    image_source: str = "unsampled"         # "unsampled"/"all"/"custom"
    custom_images: list[Path] | None = None # image_source="custom" 时使用
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `model_path` | 是 | `.pt` 模型文件 |
| `site_folder` | 是 | 站点目录（用于读 mapping 和写结果） |
| `image_source` | 否 | `unsampled`：未抽样图片；`all`：全部图片；`custom`：自定义列表 |
| `custom_images` | 条件必填 | image_source=`custom` 时必填 |

#### 5.5.3 待推理图片筛选规则

| `image_source` | 筛选条件 |
|----------------|----------|
| `unsampled` | `mapping.images[*].sampled == False` |
| `all` | 全部图片 |
| `custom` | 用户传入的 `custom_images` 列表 |

**重要：`inferred=True` 不作为筛选条件。**同一批图片可以反复推理（用不同 conf/iou 阈值对比效果）。

#### 5.5.4 输出

```python
@dataclass
class InferResult:
    mapping_path: Path
    run_id: str                             # "run_20260513_103000"
    inference_output_dir: Path
    config_path: Path                       # 本次推理参数快照
    statistics: InferStatistics

@dataclass
class InferStatistics:
    pending: int
    processed: int
    success: int
    failed: int
    predicted: int                          # 有预测结果的图片数
    empty_prediction: int                   # 空预测图片数
```

#### 5.5.5 文件产物

```
site_folder/.autolabeler/inference_results/run_YYYYMMDD_HHMMSS/
├── inference_config.json                  # 本次推理参数 + 统计快照
├── CodeA/ProductA/Image001.txt
└── CodeB/ProductB/Image002.txt
```

`inference_config.json` 必须包含：`run_id`, `timestamp`, `model_path`, `confidence`, `iou`, `device`, `batch_size`, `image_count`, `predicted_count`, `empty_prediction_count`。

**空预测必须输出空 `.txt` 文件**（不是不输出），便于 LabelImg 识别"已检查但无目标"。

#### 5.5.6 异常

| 异常类 | 错误码 | 触发条件 |
|--------|--------|----------|
| `InferModelNotFoundError` | `INFER_MODEL_NOT_FOUND` | 模型文件不存在 |
| `InferModelLoadError` | `INFER_MODEL_LOAD` | 模型加载失败（格式不匹配） |
| `InferImageNotFoundError` | `INFER_IMAGE_NOT_FOUND` | 待推理图片缺失 |
| `InferDeviceUnavailableError` | `INFER_DEVICE_UNAVAILABLE` | 指定设备不可用 |

#### 5.5.7 注意点

- 推理调用 `MappingManager.mark_inferred(image_keys)` 标记，但**仅作统计**，不影响下次推理筛选
- 当 site_folder 下没有 mapping.json 时，`image_source="all"` 或 `unsampled` 不可用；`custom` 模式可独立工作（接受任意图片列表）
- 推理结果**不**直接落到原图同级目录；必须先到 `inference_results/run_*`，由用户审核后再通过 Restorer 还原

#### 5.5.8 调用示例

```python
from core.inferencer import Inferencer, InferConfig

result = Inferencer().infer(InferConfig(
    model_path=Path("D:/models/A9950_run_001/train/weights/best.pt"),
    site_folder=Path("D:/data/A9950"),
    confidence=0.25,
))
```

---

### 5.6 LabelInspector（推理检查模块）

#### 5.6.1 作用

查询站点下所有推理 run，浏览 Code/Product 树，读取单个产品下的图片与标签列表。

#### 5.6.2 输入

```python
@dataclass
class ListRunsConfig:
    site_folder: Path

@dataclass
class GetRunTreeConfig:
    site_folder: Path
    run_id: str

@dataclass
class GetProductLabelsConfig:
    site_folder: Path
    run_id: str
    code: str
    product: str
```

#### 5.6.3 输出

```python
@dataclass
class InferenceRun:
    run_id: str
    path: Path
    config_exists: bool
    config: dict | None                     # inference_config.json 解析后内容
    created_at: str

@dataclass
class RunTreeNode:
    code: str
    product: str
    label_count: int                        # 该产品下 .txt 文件数
    empty_count: int                        # 空 .txt 数
    path: Path

@dataclass
class ProductLabel:
    image_name: str                         # 原始文件名（不是编码后）
    image_path: Path | None                 # 原图绝对路径，找不到时为 None
    label_path: Path                        # .txt 路径
    object_count: int                       # 该标签内目标数（0 = 空预测）
```

#### 5.6.4 文件产物

无。本模块纯读取。

#### 5.6.5 异常

| 异常类 | 错误码 | 触发条件 |
|--------|--------|----------|
| `InspectorRunNotFoundError` | `INSPECTOR_RUN_NOT_FOUND` | run_id 对应目录不存在 |
| `InspectorProductNotFoundError` | `INSPECTOR_PRODUCT_NOT_FOUND` | Code/Product 对应目录不存在 |

#### 5.6.6 注意点

- 列表 API 不读 `mapping.json`，只扫文件系统（保证 mapping 损坏时仍能浏览）
- 读取 `inference_config.json` 失败时不要抛错，返回 `config_exists=False`
- 必须过滤 `classes.txt`、`data.yaml` 等非标签文件

#### 5.6.7 调用示例

```python
from core.label_inspector import LabelInspector

inspector = LabelInspector()
runs = inspector.list_runs(ListRunsConfig(site_folder=Path("D:/data/A9950")))
tree = inspector.get_run_tree(GetRunTreeConfig(
    site_folder=Path("D:/data/A9950"),
    run_id="run_20260513_103000",
))
```

---

### 5.7 Restorer（还原模块）

#### 5.7.1 作用

把 `database/labels/` 中的人工标注**或**某次推理 run 中的 `.txt` 还原到原始图片同级目录。

#### 5.7.2 输入

```python
@dataclass
class RestoreConfig:
    site_folder: Path
    source_type: str                        # "database" / "inference"
    database_dir: Path | None = None        # source_type="database" 时必填
    inference_run_dir: Path | None = None   # source_type="inference" 时必填
    run_id: str | None = None               # 可替代 inference_run_dir
    overwrite: bool = False                 # 目标已存在时是否覆盖（默认不覆盖）
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `source_type` | 是 | 还原来源类型 |
| `database_dir` | 条件 | source_type=`database` 时必填 |
| `inference_run_dir` 或 `run_id` | 条件 | source_type=`inference` 时二选一 |
| `overwrite` | 否 | 默认 False（安全），True 时覆盖已有 `.txt` |

#### 5.7.3 输出

```python
@dataclass
class RestoreResult:
    total: int                              # 待还原文件总数
    success: int
    skipped: int
    failed: int
    errors: list[RestoreError]              # 失败明细

@dataclass
class RestoreError:
    source_path: Path
    target_path: Path | None
    reason: str
```

#### 5.7.4 文件产物

```
site_folder/Code/Product/Image001.txt       # 复制到原图同级
site_folder/.autolabeler/mapping.json       # 更新 restored / statistics
```

#### 5.7.5 跳过规则

| 条件 | 行为 |
|------|------|
| `mapping.images[name].restored == True` 且 `overwrite=False` | skipped |
| 目标 `.txt` 已存在且 `overwrite=False` | skipped |
| 源文件名是 `classes.txt` / `data.yaml` / `README.txt` | skipped（**必须**过滤，LabelImg 可能把 classes.txt 拷进产品目录） |

#### 5.7.6 异常

| 异常类 | 错误码 | 触发条件 |
|--------|--------|----------|
| `RestoreSourceNotFoundError` | `RESTORE_SOURCE_NOT_FOUND` | 源目录不存在 |
| `RestoreMappingNotFoundError` | `RESTORE_MAPPING_NOT_FOUND` | mapping.json 不存在 |
| `RestoreInvalidSourceTypeError` | `RESTORE_INVALID_SOURCE_TYPE` | source_type 非法值 |

#### 5.7.7 注意点

- 还原**不**修改原图片
- 错误不中断整体流程：单个文件失败计入 `failed`，继续处理下一个
- 推理还原后**不**自动调用 `mark_inferred()`（推理阶段已经标记过）
- 当用户用 `overwrite=True` 覆盖，UI 层**必须**显式二次确认

#### 5.7.8 调用示例

```python
from core.restorer import Restorer, RestoreConfig

# 从 database 还原
Restorer().restore(RestoreConfig(
    site_folder=Path("D:/data/A9950"),
    source_type="database",
    database_dir=Path("D:/data/A9950_database"),
))

# 从推理结果还原
Restorer().restore(RestoreConfig(
    site_folder=Path("D:/data/A9950"),
    source_type="inference",
    run_id="run_20260513_103000",
))
```

---

### 5.8 Converter（转换模块）

#### 5.8.1 作用

- YOLO TXT → VOC XML（批量）
- VOC XML → YOLO TXT（单文件，Sampler 内部使用）

#### 5.8.2 批量 TXT → XML

##### 输入

```python
@dataclass
class TxtToXmlConfig:
    folder: Path                            # 目标文件夹
    recursive: bool = True
    classes: list[str] | None = None        # None 时从 folder/.autolabeler/mapping.json 自动读
    delete_source: bool = False             # 默认 False（保留 TXT），True 才删
    backup_dir: Path | None = None          # delete_source=True 且此项非空时，删前备份
```

##### 输出

```python
@dataclass
class ConvertResult:
    total: int
    success: int
    skipped: int
    failed: int
    errors: list[ConvertError]
```

##### 文件产物

- 每个 `.txt` 转成同名 `.xml`（**不带** `<?xml version=...?>` 声明行，与旧版一致）
- 如果 `delete_source=True`，对应 `.txt` 删除；如果同时有 `backup_dir`，删前复制一份到 backup
- 找不到同名图片的 `.txt` 跳过（不报错）

##### 跳过规则

| 条件 | 行为 |
|------|------|
| 文件名是 `classes.txt`/`data.yaml`/`README.txt` | skipped |
| 找不到同名图片（`.jpg`/`.jpeg`/`.png`/`.bmp`） | skipped |
| TXT 内某行类别 id 超出 classes 长度 | failed（记入 errors） |

#### 5.8.3 单文件 XML → TXT

```python
@dataclass
class XmlToTxtConfig:
    xml_path: Path
    classes: list[str]                      # 必填，用于把类别名映射到 class_id
    output_path: Path                       # 必填
```

返回 `Path`。该接口主要供 Sampler 内部用，但也作为公开 API。

#### 5.8.4 异常

| 异常类 | 错误码 | 触发条件 |
|--------|--------|----------|
| `ConvertFolderNotFoundError` | `CONVERT_FOLDER_NOT_FOUND` | folder 不存在 |
| `ConvertClassesNotFoundError` | `CONVERT_CLASSES_NOT_FOUND` | classes 既未传入也找不到 mapping.json |
| `ConvertClassIdOutOfRangeError` | `CONVERT_CLASS_ID_OUT_OF_RANGE` | TXT 内 class_id ≥ len(classes) |
| `ConvertXmlParseError` | `CONVERT_XML_PARSE` | XML 解析失败 |

#### 5.8.5 注意点

- **默认不删源文件**（与旧版相反，旧版默认删除）。这是关键行为变更，UI 和 API 都要明确告知用户
- `delete_source=True` 时，UI 层**必须**显式二次确认
- 批量转换中单文件失败不中断整体；继续处理下一个

#### 5.8.6 调用示例

```python
from core.converter import Converter, TxtToXmlConfig

result = Converter().txt_to_xml(TxtToXmlConfig(
    folder=Path("D:/data/A9950"),
    recursive=True,
    delete_source=False,
))
```

---

## 6. 异常与错误码总表

所有异常继承 `utils/exceptions.py:AutoLabelerError`，强制带 `code` 字段（值见各模块小节）。

### 6.1 通用错误码

| 错误码 | 含义 |
|--------|------|
| `VALIDATION_ERROR` | 入参类型/取值越界 |
| `PATH_NOT_FOUND` | 通用路径不存在 |
| `PERMISSION_DENIED` | 文件系统权限不足 |
| `INTERNAL_ERROR` | 未分类内部异常（兜底） |

### 6.2 任务级错误码

| 错误码 | 含义 |
|--------|------|
| `TASK_NOT_FOUND` | task_id 不存在 |
| `TASK_ALREADY_RUNNING` | 同类型任务已在运行（如同时跑两次训练） |
| `TASK_CANCELLED` | 任务被用户取消 |

### 6.3 模块级错误码

见各模块小节"异常"表。所有错误码命名规范：`{MODULE}_{REASON}`，全大写下划线。

---

## 7. 与旧版差异对照

| 项 | 旧版行为 | 新版行为 | 原因 |
|----|----------|----------|------|
| 验证集目录名 | `vals/` | `val/` | YOLO 标准，避免误解 |
| 转换删源 TXT | 默认删除 | 默认保留，`delete_source=True` 才删 | 防止破坏用户数据 |
| 推理 IoU 默认 | 多处不一致（0.45 / 0.7） | 统一 `0.7` | 消除歧义 |
| `inferred` 字段 | 仅统计 | 仅统计（保持） | 允许调参对比 |
| `site_detector` | 存在，识别 A9950 等 | **删除** | 与解耦目标冲突，未被核心流程使用 |
| `conversion_rule` | 存在，做 Code 名映射 | **删除** | 同上 |
| `MappingManager` 访问 | 部分模块直接读 json | **必须**经 manager | 并发安全 |
| 任务模型 | QThread + worker 各自管理 | 统一 `TaskRegistry` + `TaskHandle` | 桌面/Web 共用 |
| HTTP API | 无 | 新增 `api/` 目录（FastAPI 薄壳） | Web 接入 |
| 命名 | API/Python 各写各的 | 边界自动 camelCase ↔ snake_case 转换 | 减少手抖 |
| 异常 | 部分裸 `Exception` | 全部继承 `AutoLabelerError` + 错误码 | API 错误处理 |
| 设置持久化 | UI 表单但不落盘 | 可选实现（本期不强制） | 与本期目标无关 |
| 人工标注状态同步 | 不自动 | 不自动（保持），但开放手动接口 `mark_labeled()` | 避免误判 |
| 模块强制顺序 | 必须先扫描 | **解耦**：每个模块独立可用 | 核心重构目标 |

---

## 8. 名词表

| 名词 | 定义 |
|------|------|
| **站点目录 / site folder** | 用户的图片根目录，包含 Code/Product 两级 |
| **Code** | 站点目录下第一级文件夹名，同时作为 YOLO 类别名 |
| **Product** | Code 下第二级文件夹名，代表一个产品批次 |
| **抽样 / sample** | 从全量图片中按规则挑出一部分作为训练集 |
| **database** | 抽样后生成的 YOLO 训练数据集目录 |
| **mapping.json** | 站点级状态文件，记录每张图片的元信息和处理状态 |
| **路径编码** | 把 `Code/Product/Filename` 扁平化为 `Code__Product__Filename` |
| **推理 run** | 一次推理产生的时间戳目录 `run_YYYYMMDD_HHMMSS` |
| **还原 / restore** | 把 database 或推理 run 中的标签复制回原始图片同级目录 |
| **TaskHandle** | 长任务的统一句柄，桌面/Web 通用 |

---

## 9. 后续扩展点（本期不实现，但留口子）

- 设置持久化：`~/.autolabeler/settings.json`
- 内置 Web 标注器（替代 LabelImg）
- 推理结果质量分析（不确定度排序、主动学习）
- 多模型集成推理
- 多站点项目管理

新人不要在本期实现以上内容，**也不要**为它们写"半成品"。需要时另起需求文档。
