# AutoLabeler Web API 文档

> 生成日期：2026-05-11  
> 目标读者：Next.js 前端工程师、后端 API 封装工程师、后续维护者  
> 范围：基于当前 `auto_yolo_label` 桌面项目代码，整理现有功能模块、输入输出、文件产物、状态流转，并给出 Web 化时建议暴露的 API 契约。

---

## 1. 项目定位

AutoLabeler 是一个基于 YOLO 的半自动图片标注工具。现有实现是 PySide6 桌面应用，核心业务逻辑集中在 `core/`，GUI 页面通过 `gui/workers/` 后台线程调用核心模块。Web 重写时，推荐保留 Python 核心模块作为后端服务层，Next.js 前端通过 API 触发扫描、抽样、训练、推理、还原、转换等任务。

核心工作流：

```text
扫描站点文件夹
  -> 抽样生成 database
  -> 人工标注样本
  -> 训练 YOLO 模型
  -> 推理未抽样图片
  -> 检查/选择推理结果
  -> 还原标注到原始目录
  -> 可选：YOLO txt 转 VOC xml
```

---

## 2. 当前架构

```text
main.py
  -> gui/app.py
    -> gui/main_window.py
      -> gui/pages/*          # 桌面页面层，负责表单、按钮、结果展示
      -> gui/workers/*        # QThread 工作线程，负责校验输入、组装配置、调用 core
        -> core/*             # 核心业务模块，可直接封装为后端 service
          -> utils/*          # 映射管理、路径编码、设备检测、LabelImg、站点检测等
```

建议 Web 化后的分层：

```text
Next.js Frontend
  -> REST API / SSE / WebSocket
    -> Backend Route/Controller
      -> Service wrapper around core/*
        -> File system + YOLO + mapping.json
```

当前模块与 Web 后端服务映射：

| 功能 | 当前页面 | 当前 Worker | 核心模块 | Web 服务建议 |
|------|----------|-------------|----------|--------------|
| 首页/流程 | `gui/pages/home_page.py` | 无 | 无 | 静态流程、项目概览 |
| 扫描 | `scan_page.py` | `ScanWorker` | `core.scanner.Scanner` | `ScanService` |
| 抽样 | `sample_page.py` | `SampleWorker` | `core.sampler.Sampler` | `SampleService` |
| 训练 | `train_page.py` | `TrainWorker` | `core.trainer.Trainer` | `TrainService` |
| 推理 | `inference_page.py` | `InferenceWorker` | `core.inferencer.Inferencer` | `InferenceService` |
| 标注检查 | `label_viewer_page.py` | 无 | `core.label_inspector.LabelInspector` | `InferenceBrowserService` |
| 还原 | `restore_page.py` | `RestoreWorker` | `core.restorer.Restorer` | `RestoreService` |
| 转换 | `convert_page.py` | `ConvertWorker` | `core.converter.Converter` | `ConvertService` |
| 设置 | `settings_page.py` | 无 | 部分使用 `utils.labelimg_config` | `SettingsService` |

---

## 3. 文件与目录约定

### 3.1 站点文件夹

站点文件夹必须是三级结构：

```text
site_folder/
  CodeA/
    ProductA/
      image001.jpg
      image001.xml    # 可选，已有 VOC 标注
      image002.png
    ProductB/
      ...
  CodeB/
    ProductC/
      ...
```

约定：

- `Code` 文件夹名就是类别名。
- `Product` 是产品目录名。
- 当前扫描只读取 `Code/Product` 两级下直接存在的图片，不递归扫描更深层图片。
- 支持图片格式：`.jpg`、`.jpeg`、`.png`、`.bmp`。
- 以 `.` 开头的隐藏目录会被扫描模块跳过。

### 3.2 `.autolabeler` 工作目录

扫描后在站点目录下生成：

```text
site_folder/.autolabeler/
  mapping.json
  classes.txt
  site_config.yaml                 # 可选，站点类型
  inference_results/
    run_YYYYMMDD_HHMMSS/
      inference_config.json
      CodeA/ProductA/*.txt
      CodeB/ProductB/*.txt
```

### 3.3 抽样输出 `database`

抽样后生成 YOLO 训练数据集：

```text
database/
  data.yaml
  images/
    train/
      Code__Product__Image.jpg
    vals/
      Code__Product__Image.jpg
  labels/
    train/
      Code__Product__Image.txt
    vals/
      Code__Product__Image.txt
```

注意：验证集目录名是 `vals`，`data.yaml` 中写的是 `val: images/vals`。

### 3.4 路径编码

抽样会将 `Code/Product/Filename` 扁平化成文件名：

```text
原始路径：AS_CV_PI_P/H4A238FDF04/IMG_001.jpg
编码名：  AS_CV_PI_P__H4A238FDF04__IMG_001.jpg
```

实现：`utils.path_encoder.PathEncoder`。后端和前端都不要自行猜测原路径，应通过 `mapping.json` 查询。

---

## 4. 通用 API 设计建议

现有核心任务大多耗时较长，Web API 推荐采用异步任务模式。

### 4.1 通用响应格式

```json
{
  "success": true,
  "data": {},
  "error": null,
  "requestId": "req_20260511_001"
}
```

失败：

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "SCAN_LABEL_MISMATCH",
    "message": "已有标注文件中的标签与 Code 文件夹名称不一致",
    "details": "Code 文件夹: 'M1_SP_PI_P' ...",
    "retryable": false
  },
  "requestId": "req_20260511_002"
}
```

### 4.2 异步任务格式

任务创建返回：

```json
{
  "taskId": "task_scan_20260511_101530_abc123",
  "type": "scan",
  "status": "queued",
  "createdAt": "2026-05-11T10:15:30+08:00"
}
```

任务状态：

```json
{
  "taskId": "task_scan_20260511_101530_abc123",
  "type": "scan",
  "status": "running",
  "progress": {
    "current": 120,
    "total": 500,
    "percentage": 24.0,
    "message": "扫描中: IMG_0120.jpg"
  },
  "logs": [
    "开始扫描: D:/data/A9950"
  ],
  "result": null,
  "error": null
}
```

任务状态枚举：

| 状态 | 说明 |
|------|------|
| `queued` | 已提交，等待执行 |
| `running` | 正在执行 |
| `succeeded` | 成功结束 |
| `failed` | 执行失败 |
| `cancelled` | 用户取消 |

推荐通用任务端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/tasks/{taskId}` | 获取任务状态、进度、结果 |
| `GET` | `/api/tasks/{taskId}/events` | SSE 实时进度、日志、指标 |
| `POST` | `/api/tasks/{taskId}/cancel` | 取消任务 |

SSE 事件示例：

```json
{
  "event": "progress",
  "data": {
    "current": 3,
    "total": 100,
    "percentage": 3.0,
    "message": "训练中: Epoch 3/100 - mAP50: 0.421"
  }
}
```

---

## 5. 核心数据模型

### 5.1 MappingData

来源：`utils.mapping_manager.MappingData`

```json
{
  "version": "1.0",
  "project_name": "A9950",
  "site_folder": "D:/data/A9950",
  "created_time": "2026-05-11 10:00:00",
  "updated_time": "2026-05-11 10:05:00",
  "classes": {
    "0": "AS_CV_PI_P",
    "1": "M1_SP_PI_P"
  },
  "config": {
    "sample_mode": "count",
    "sample_count": 40,
    "sample_ratio": 0.3,
    "full_threshold": 35,
    "train_ratio": 0.9,
    "pre_labeled_priority": true
  },
  "statistics": {
    "total_images": 1000,
    "total_codes": 2,
    "total_products": 20,
    "sampled_count": 200,
    "labeled_count": 0,
    "inferred_count": 800,
    "restored_count": 600
  },
  "products": {
    "AS_CV_PI_P": {
      "H4A238FDF04": 120
    }
  },
  "images": {
    "AS_CV_PI_P__H4A238FDF04__IMG_001.jpg": {
      "original_relative": "AS_CV_PI_P/H4A238FDF04/IMG_001.jpg",
      "code": "AS_CV_PI_P",
      "product": "H4A238FDF04",
      "original_name": "IMG_001.jpg",
      "format": ".jpg",
      "sampled": false,
      "split": null,
      "manual_labeled": false,
      "inferred": false,
      "restored": false,
      "label_source": "none"
    }
  }
}
```

### 5.2 ImageInfo 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `original_relative` | string | 相对站点目录的原始路径 |
| `code` | string | Code 文件夹名，也是类别名 |
| `product` | string | 产品文件夹名 |
| `original_name` | string | 原始图片文件名 |
| `format` | string | 图片扩展名 |
| `sampled` | boolean | 是否已抽样到 database |
| `split` | `"train"` / `"vals"` / null | 抽样后的数据集划分 |
| `manual_labeled` | boolean | 是否已标记为人工标注，目前没有自动更新流程 |
| `inferred` | boolean | 是否执行过推理标注，用于统计；当前不阻止重新推理 |
| `restored` | boolean | 是否已还原到原始目录 |
| `label_source` | string | `none`、`pre_existing_xml`、`pre_existing_txt`、预留 `manual_later`、`auto_inferred` |

### 5.3 DeviceInfo

来源：`utils.device.get_device_info()`

```json
{
  "device": "cuda",
  "deviceId": "0",
  "isAvailable": true,
  "name": "NVIDIA GeForce RTX ... x1",
  "memory": 8192
}
```

---

## 6. 子功能模块详解

### 6.1 扫描模块

核心文件：`core/scanner.py`  
当前调用：`gui/workers/scan_worker.py`

作用：

- 扫描站点文件夹，建立全局图片索引。
- 识别 Code/Product/Image 结构。
- 生成类别列表。
- 验证已有 XML 标注中的 `<object><name>` 是否与 Code 文件夹名一致。

核心输入：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `siteFolder` | string | 是 | - | 站点文件夹路径 |
| `outputDir` | string | 否 | `siteFolder/.autolabeler` | mapping/classes 输出目录 |
| `supportedFormats` | string[] | 否 | `.jpg,.jpeg,.png,.bmp` | 支持图片格式 |

核心输出：

| 字段 | 类型 | 说明 |
|------|------|------|
| `mappingPath` | string | `mapping.json` 路径 |
| `classesPath` | string | `classes.txt` 路径 |
| `statistics` | object | 图片、Code、产品数量 |
| `classes` | string[] | 类别名，按 class id 排序 |
| `products` | object | Code/Product 图片数量统计 |

文件产物：

```text
siteFolder/.autolabeler/mapping.json
siteFolder/.autolabeler/classes.txt
```

重要行为：

- 每次扫描会创建新的 `mapping.json`，同目录旧状态会被覆盖。
- 如果 XML 标注类别与 Code 不一致，会抛出 `ScanError` 并停止。
- 扫描不会修改原图片或原标注文件。

建议 API：

```http
POST /api/scan
```

请求：

```json
{
  "siteFolder": "D:/data/A9950",
  "outputDir": null,
  "supportedFormats": [".jpg", ".jpeg", ".png", ".bmp"]
}
```

任务成功结果：

```json
{
  "mappingPath": "D:/data/A9950/.autolabeler/mapping.json",
  "classesPath": "D:/data/A9950/.autolabeler/classes.txt",
  "statistics": {
    "total_images": 1200,
    "total_codes": 8,
    "total_products": 64,
    "sampled_count": 0,
    "labeled_count": 0,
    "inferred_count": 0,
    "restored_count": 0
  },
  "classes": ["AS_CV_PI_P", "M1_SP_PI_P"],
  "products": {
    "AS_CV_PI_P": {
      "H4A238FDF04": 120
    }
  }
}
```

---

### 6.2 抽样模块

核心文件：`core/sampler.py`  
当前调用：`gui/workers/sample_worker.py`

作用：

- 按 `Code/Product` 维度抽取样本。
- 生成 YOLO 训练集目录。
- 自动检测已有 XML/TXT 标注。
- 已有标注样本优先抽取，XML 自动转 YOLO TXT。

核心输入：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `siteFolder` | string | 是 | - | 已扫描的站点目录 |
| `outputDir` | string | 是 | - | database 输出目录 |
| `config.mode` | string | 否 | `count` | `count`、`ratio`、`mixed` |
| `config.count` | int | 否 | 40 | 固定数量模式的抽样数量 |
| `config.ratio` | float | 否 | 0.3 | 比例模式抽样比例 |
| `config.minCount` | int | 否 | 20 | mixed 模式最小数量，当前 GUI 未暴露 |
| `config.maxCount` | int | 否 | 50 | mixed 模式最大数量，当前 GUI 未暴露 |
| `config.fullThreshold` | int | 否 | 35 | 图片数小于等于该阈值时全抽 |
| `config.trainRatio` | float | 否 | 0.9 | 训练集比例 |
| `config.preLabeledPriority` | boolean | 否 | true | 是否优先抽取已有标注 |

抽样数量规则：

| 模式 | 规则 |
|------|------|
| `count` | `sample_count = max(count, fullThreshold)`；总数小于等于该值则全抽 |
| `ratio` | 总数小于等于 `fullThreshold` 全抽，否则 `int(total * ratio)`，最少 1 |
| `mixed` | 总数小于等于 `fullThreshold` 全抽，否则 `ratio` 结果限制在 `[minCount, maxCount]` |

已有标注处理：

- 同名 `.xml` 存在且非空：`label_source = pre_existing_xml`，抽样时转成 YOLO TXT。
- 同名 `.txt` 存在且非空且不是 `classes.txt` 等配置文件：`label_source = pre_existing_txt`，抽样时直接复制。
- 空 XML/TXT 会被删除，并视为无标注。
- 无预标注的图片只复制图片，不创建空 label 文件，等待人工标注工具生成。

核心输出：

| 字段 | 类型 | 说明 |
|------|------|------|
| `mappingPath` | string | 更新后的 mapping 路径 |
| `dataYaml` | string | 训练配置文件路径 |
| `datasetDir` | string | database 目录 |
| `statistics.totalProducts` | int | 产品数量 |
| `statistics.sampledCount` | int | 已抽样总数 |
| `statistics.trainCount` | int | train 图片数 |
| `statistics.valCount` | int | vals 图片数 |

文件产物：

```text
database/images/train/*
database/images/vals/*
database/labels/train/*
database/labels/vals/*
database/data.yaml
siteFolder/.autolabeler/mapping.json   # 更新 sampled/split/label_source/config/statistics
```

建议 API：

```http
POST /api/sample
```

请求：

```json
{
  "siteFolder": "D:/data/A9950",
  "outputDir": "D:/data/A9950_database",
  "config": {
    "mode": "count",
    "count": 40,
    "ratio": 0.3,
    "minCount": 20,
    "maxCount": 50,
    "fullThreshold": 35,
    "trainRatio": 0.9,
    "preLabeledPriority": true
  }
}
```

任务成功结果：

```json
{
  "mappingPath": "D:/data/A9950/.autolabeler/mapping.json",
  "datasetDir": "D:/data/A9950_database",
  "dataYaml": "D:/data/A9950_database/data.yaml",
  "paths": {
    "imagesTrain": "D:/data/A9950_database/images/train",
    "imagesVals": "D:/data/A9950_database/images/vals",
    "labelsTrain": "D:/data/A9950_database/labels/train",
    "labelsVals": "D:/data/A9950_database/labels/vals"
  },
  "statistics": {
    "totalProducts": 64,
    "sampledCount": 320,
    "trainCount": 288,
    "valCount": 32
  }
}
```

---

### 6.3 人工标注模块

当前状态：

- 桌面版主要依赖外部 LabelImg。
- 抽样后用户打开 `database/images/train|vals` 标注，保存到 `database/labels/train|vals`。
- `MappingManager.mark_labeled()` 已存在，但当前 GUI 没有自动扫描 labels 后更新 `manual_labeled` 的流程。

Web 重写建议：

如果 Next.js 要内置标注器，需要新增图片和标签读写 API；这部分当前 core 没有完整模块。

建议 API：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/datasets/images?datasetDir=...&split=train` | 列出抽样图片 |
| `GET` | `/api/files/image?path=...` | 流式读取图片，后端必须做路径校验 |
| `GET` | `/api/labels/yolo?datasetDir=...&split=train&encodedName=...` | 读取 YOLO TXT 标签 |
| `PUT` | `/api/labels/yolo` | 保存 YOLO TXT 标签 |
| `POST` | `/api/labels/mark-labeled` | 更新 mapping 的 `manual_labeled` |

YOLO 标签格式：

```text
class_id x_center y_center width height
```

坐标均为 0 到 1 的归一化值。

---

### 6.4 训练模块

核心文件：`core/trainer.py`  
当前调用：`gui/workers/train_worker.py`

作用：

- 使用 Ultralytics YOLO 训练模型。
- 自动检测设备和 batch size。
- 每个 epoch 报告进度和指标。
- 输出 `best.pt`。

核心输入：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `dataYaml` | string | 是 | - | 抽样生成的 `data.yaml` |
| `baseModel` | string | 是 | - | 预训练模型 `.pt` |
| `outputDir` | string | 是 | - | 训练输出目录 |
| `config.epochs` | int | 否 | 100 | 训练轮次 |
| `config.batchSize` | int | 否 | -1 | -1 表示自动检测 |
| `config.imageSize` | int | 否 | 640 | 训练图片尺寸 |
| `config.device` | string | 否 | `auto` | `auto`、`cpu`、`0`、`0,1`、`mps` |
| `config.patience` | int | 否 | 50 | 早停轮数 |
| `config.workers` | int | 否 | 8 | 数据加载 worker 数 |
| `config.optimizer` | string | 否 | `AdamW` | YOLO optimizer |
| `config.lr0` | float | 否 | 0.01 | 初始学习率 |
| `config.box` | float | 否 | 7.5 | box loss gain，小目标可降到 1.5-3.0 |
| `config.cls` | float | 否 | 0.5 | cls loss gain，小目标可降到 0.3-0.5 |
| `config.dfl` | float | 否 | 1.5 | distribution focal loss gain |
| `config.scale` | float | 否 | 0.5 | 数据增强缩放幅度 |
| `config.cache` | string/boolean | 否 | `ram` | `ram`、`disk`、`false` |

进度/指标输出：

```json
{
  "epoch": 12,
  "totalEpochs": 100,
  "metrics": {
    "mAP50": 0.421,
    "mAP50-95": 0.213
  }
}
```

核心输出：

| 字段 | 类型 | 说明 |
|------|------|------|
| `bestModel` | string | `outputDir/train/weights/best.pt` |
| `lastModel` | string | `outputDir/train/weights/last.pt`，如果存在 |
| `outputDir` | string | YOLO run 输出目录 |
| `config` | object | 实际训练配置 |

文件产物：

```text
outputDir/train/
  weights/best.pt
  weights/last.pt
  results.csv
  args.yaml
  ...
```

建议 API：

```http
POST /api/train
```

请求：

```json
{
  "dataYaml": "D:/data/A9950_database/data.yaml",
  "baseModel": "D:/models/yolov8n.pt",
  "outputDir": "D:/models/A9950_run_001",
  "config": {
    "epochs": 100,
    "batchSize": -1,
    "imageSize": 640,
    "device": "auto",
    "patience": 50,
    "workers": 8,
    "optimizer": "AdamW",
    "lr0": 0.01,
    "box": 7.5,
    "cls": 0.5,
    "dfl": 1.5,
    "scale": 0.5,
    "cache": "ram"
  }
}
```

任务成功结果：

```json
{
  "bestModel": "D:/models/A9950_run_001/train/weights/best.pt",
  "lastModel": "D:/models/A9950_run_001/train/weights/last.pt",
  "outputDir": "D:/models/A9950_run_001/train",
  "config": {
    "epochs": 100,
    "batchSize": 8,
    "imageSize": 640,
    "device": "0"
  }
}
```

实现注意：

- 当前 `TrainPage` 有 `cache` 控件，但 `TrainWorker` 组装 `TrainConfig` 时没有把 `cache` 传入核心模块；Web 后端封装时建议补齐。
- 当前 `TrainWorker` 只透传了 `epochs`、`batch_size`、`image_size`、`device`、`patience`、`box`、`cls`、`scale`，没有透传 `workers`、`optimizer`、`lr0`、`dfl`、`cache`。

---

### 6.5 推理模块

核心文件：`core/inferencer.py`  
当前调用：`gui/workers/inference_worker.py`

作用：

- 使用训练好的模型对未抽样图片批量推理。
- 结果保存到独立时间戳目录。
- 空预测也生成空 `.txt`，便于标注工具识别。
- 支持多次推理同一批未抽样图片，便于比较不同阈值。

核心输入：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `modelPath` | string | 是 | - | `.pt` 模型文件 |
| `siteFolder` | string | 是 | - | 已扫描站点目录 |
| `outputBaseDir` | string | 否 | `siteFolder/.autolabeler/inference_results` | 推理结果根目录 |
| `config.confidence` | float | 否 | 0.25 | 置信度阈值 |
| `config.iou` | float | 否 | 0.7 | NMS IoU 阈值 |
| `config.batchSize` | int | 否 | -1 | -1 表示自动检测 |
| `config.device` | string | 否 | `auto` | `auto`、`cpu`、`0`、`mps` |
| `config.saveToSeparateDir` | boolean | 否 | true | 是否保存到独立 run 目录 |

待推理图片筛选：

- 当前 `MappingManager.get_pending_inference_images()` 只筛选 `sampled == false`。
- 不再根据 `inferred` 跳过图片，所以可以重复推理。
- 已还原图片也不会被自动排除。

核心输出：

| 字段 | 类型 | 说明 |
|------|------|------|
| `mappingPath` | string | 更新后的 mapping 路径 |
| `runId` | string | `run_YYYYMMDD_HHMMSS` |
| `inferenceOutputDir` | string | 本次推理目录 |
| `configPath` | string | `inference_config.json` 路径 |
| `statistics.processed` | int | 实际处理图片数 |
| `statistics.predicted` | int | 有预测结果图片数，可从 config 文件读取 |
| `statistics.emptyPrediction` | int | 空预测图片数，可从 config 文件读取 |
| `statistics.missing` | int | 原图缺失数量，当前 core 仅日志报告 |

文件产物：

```text
siteFolder/.autolabeler/inference_results/run_YYYYMMDD_HHMMSS/
  inference_config.json
  CodeA/ProductA/Image001.txt
  CodeB/ProductB/Image002.txt
```

`inference_config.json` 示例：

```json
{
  "run_id": "run_20260511_103000",
  "timestamp": "2026-05-11 10:30:00",
  "model_path": "D:/models/best.pt",
  "confidence": 0.25,
  "iou": 0.7,
  "device": "0",
  "batch_size": 8,
  "image_count": 800,
  "predicted_count": 620,
  "empty_prediction_count": 180
}
```

建议 API：

```http
POST /api/infer
```

请求：

```json
{
  "modelPath": "D:/models/A9950_run_001/train/weights/best.pt",
  "siteFolder": "D:/data/A9950",
  "outputBaseDir": null,
  "config": {
    "confidence": 0.25,
    "iou": 0.7,
    "batchSize": -1,
    "device": "auto",
    "saveToSeparateDir": true
  }
}
```

任务成功结果：

```json
{
  "mappingPath": "D:/data/A9950/.autolabeler/mapping.json",
  "runId": "run_20260511_103000",
  "inferenceOutputDir": "D:/data/A9950/.autolabeler/inference_results/run_20260511_103000",
  "configPath": "D:/data/A9950/.autolabeler/inference_results/run_20260511_103000/inference_config.json",
  "statistics": {
    "pending": 800,
    "processed": 800,
    "success": 800,
    "failed": 0,
    "predicted": 620,
    "emptyPrediction": 180
  }
}
```

实现注意：

- `InferenceConfig` 类默认 `iou=0.7`，`InferenceWorker` 的 fallback 是 `0.45`，页面默认是 `0.7`。Web API 建议统一默认值。
- 当前推理会调用 `mapping.mark_inferred()`，但该字段只用于统计，不影响下次推理筛选。

---

### 6.6 推理历史与标注检查模块

核心文件：`core/label_inspector.py`、`core/inferencer.py:get_inference_history()`  
当前页面：`gui/pages/label_viewer_page.py`

作用：

- 列出站点下所有推理 run。
- 查看某次 run 下的 Code/Product 树。
- 桌面版可启动 LabelImg 查看某个产品目录的标注。

核心输入：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `siteFolder` | string | 是 | 站点目录 |
| `runId` | string | 部分 API 必填 | 推理运行目录名 |
| `code` | string | 部分 API 必填 | Code 名称 |
| `product` | string | 部分 API 必填 | Product 名称 |

核心输出：

推理 run：

```json
{
  "name": "run_20260511_103000",
  "path": "D:/data/A9950/.autolabeler/inference_results/run_20260511_103000",
  "configExists": true,
  "config": {
    "timestamp": "2026-05-11 10:30:00",
    "model_path": "D:/models/best.pt",
    "image_count": 800,
    "confidence": 0.25,
    "iou": 0.7
  }
}
```

Code/Product 树：

```json
{
  "AS_CV_PI_P": [
    {
      "code": "AS_CV_PI_P",
      "product": "H4A238FDF04",
      "labelCount": 120,
      "path": "D:/data/A9950/.autolabeler/inference_results/run_20260511_103000/AS_CV_PI_P/H4A238FDF04"
    }
  ]
}
```

建议 API：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/inference/history?siteFolder=...` | 列出推理历史 |
| `GET` | `/api/inference/runs/{runId}/tree?siteFolder=...` | 获取 Code/Product 树 |
| `GET` | `/api/inference/runs/{runId}/products/{code}/{product}?siteFolder=...` | 获取产品下图片和标签列表 |
| `GET` | `/api/files/image?...` | 获取原图 |
| `GET` | `/api/files/label?...` | 获取 YOLO TXT |
| `PUT` | `/api/files/label` | Web 标注器保存修改后的标签 |

桌面专用 LabelImg API，可选保留：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/labelimg/config` | 获取当前 LabelImg Python 配置 |
| `POST` | `/api/labelimg/validate` | 验证 Python 环境是否安装 LabelImg |
| `POST` | `/api/labelimg/config` | 保存全局配置 |
| `POST` | `/api/labelimg/launch` | 在后端所在机器启动 LabelImg |

`POST /api/labelimg/launch` 请求：

```json
{
  "pythonPath": "D:/miniforge3/envs/labelimg/python.exe",
  "siteFolder": "D:/data/A9950",
  "runId": "run_20260511_103000",
  "code": "AS_CV_PI_P",
  "product": "H4A238FDF04"
}
```

注意：纯 Web 部署通常不能在用户浏览器端启动本机 LabelImg；该能力只适合“后端运行在标注员本机”的本地服务模式。

---

### 6.7 还原模块

核心文件：`core/restorer.py`  
当前调用：`gui/workers/restore_worker.py`

作用：

- 将 `database/labels` 中的人工标注还原到原始图片同级目录。
- 或将某次推理 run 中的 `.txt` 还原到原始图片同级目录。

还原来源：

| 来源 | sourceType | sourcePath |
|------|------------|------------|
| 人工标注 database | `database` | database 目录 |
| 推理结果 | `inference` | `run_YYYYMMDD_HHMMSS` 目录 |

核心输入：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `siteFolder` | string | 是 | 站点目录 |
| `sourceType` | string | 是 | `database` 或 `inference` |
| `databaseDir` | string | `database` 来源必填 | 抽样输出目录 |
| `inferenceRunDir` | string | `inference` 来源必填 | 推理 run 目录 |
| `runId` | string | 可替代 `inferenceRunDir` | 后端可由 `siteFolder + runId` 拼出路径 |

核心输出：

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | int | 待还原文件数 |
| `success` | int | 成功复制数 |
| `skipped` | int | 跳过数 |
| `failed` | int | 失败数 |
| `errors` | string[] | 失败详情，当前 Worker 未返回，Web API 建议返回 |

文件产物：

```text
siteFolder/Code/Product/Image001.txt
siteFolder/.autolabeler/mapping.json   # 更新 restored/statistics
```

跳过规则：

- 如果 `mapping.images[encodedName].restored == true`，跳过。
- 如果目标 `.txt` 已存在，跳过，避免覆盖。

建议 API：

```http
POST /api/restore
```

从 database 还原：

```json
{
  "sourceType": "database",
  "siteFolder": "D:/data/A9950",
  "databaseDir": "D:/data/A9950_database"
}
```

从推理结果还原：

```json
{
  "sourceType": "inference",
  "siteFolder": "D:/data/A9950",
  "runId": "run_20260511_103000"
}
```

任务成功结果：

```json
{
  "total": 800,
  "success": 760,
  "skipped": 35,
  "failed": 5,
  "errors": [
    "找不到匹配: AS_CV_PI_P/H4A238FDF04/classes.txt"
  ]
}
```

实现注意：

- 当前 `restore_from_inference()` 会递归收集 `*.txt`，如果 LabelImg 曾把 `classes.txt` 复制到产品目录，当前代码可能把它当作待还原标签而报错。Web 后端建议显式过滤 `classes.txt`。
- 当前从推理结果还原时只调用 `mark_restored()`，没有额外调用 `mark_inferred()`；通常推理阶段已经标记 `inferred`。

---

### 6.8 格式转换模块

核心文件：`core/converter.py`  
当前调用：`gui/workers/convert_worker.py`

作用：

- YOLO TXT -> VOC XML。
- VOC XML -> YOLO TXT，抽样已有 XML 标注时内部使用。

#### 6.8.1 批量 TXT 转 XML

核心输入：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `folder` | string | 是 | - | 目标文件夹 |
| `recursive` | boolean | 否 | true | 是否递归处理子目录 |
| `classes` | string[] | 否 | 从 `folder/.autolabeler/mapping.json` 读取，否则默认 `class_0..` | 类别名 |

核心输出：

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | int | 待转换 txt 数 |
| `success` | int | 成功转换数 |
| `skipped` | int | 找不到对应图片等跳过数 |
| `failed` | int | 转换失败数 |
| `errors` | string[] | 错误详情，当前 Worker 未返回，Web API 建议返回 |

行为：

- 忽略 `classes.txt`、`data.yaml`、`README.txt` 等非标注文件。
- 查找同名图片：`.jpg`、`.jpeg`、`.png`、`.bmp`。
- 成功生成 XML 后会删除原 `.txt`。
- XML 输出不包含 XML 声明行。

建议 API：

```http
POST /api/convert/yolo-to-voc
```

请求：

```json
{
  "folder": "D:/data/A9950",
  "recursive": true,
  "classes": null
}
```

结果：

```json
{
  "total": 800,
  "success": 790,
  "skipped": 8,
  "failed": 2,
  "errors": [
    "找不到对应图片: IMG_001.txt"
  ]
}
```

#### 6.8.2 单个 XML 转 TXT

当前主要由抽样模块内部调用。

建议 API：

```http
POST /api/convert/voc-to-yolo
```

请求：

```json
{
  "xmlPath": "D:/data/A9950/AS_CV_PI_P/H4A238FDF04/IMG_001.xml",
  "classes": ["AS_CV_PI_P", "M1_SP_PI_P"],
  "outputPath": "D:/tmp/IMG_001.txt"
}
```

结果：

```json
{
  "outputPath": "D:/tmp/IMG_001.txt"
}
```

---

### 6.9 站点检测与 Code 转换规则

核心文件：

- `utils/site_detector.py`
- `core/conversion_rule.py`
- `config/A9950_conversion_rules.yaml`

作用：

- 自动识别站点类型，例如 A9950。
- 管理原始 Code 与转换后 Code 的映射。
- 当前核心扫描/抽样/训练流程没有强依赖该模块，但它对未来“站点特定规则展示、模型输出 Code 解释、还原原始 Code”有价值。

站点检测规则：

- 优先读 `siteFolder/.autolabeler/site_config.yaml`。
- 否则通过 Code 文件夹特征判断：
  - A9950 指示词：`AS_CV_PI`、`T1_SP_PI`、`M2_SP_PI_G`。
- 未匹配则返回 `default`。

建议 API：

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/site/detect` | 检测站点类型 |
| `POST` | `/api/site/config` | 保存站点类型 |
| `POST` | `/api/code-rules/convert` | 原始 Code 与转换后 Code 互转 |

`POST /api/site/detect`：

```json
{
  "siteFolder": "D:/data/A9950"
}
```

响应：

```json
{
  "siteType": "A9950",
  "configPath": "D:/data/A9950/.autolabeler/site_config.yaml"
}
```

`POST /api/code-rules/convert`：

```json
{
  "siteType": "A9950",
  "direction": "toOriginal",
  "code": "T1_SP_PI_P",
  "product": "H4A238HDF13"
}
```

响应：

```json
{
  "inputCode": "T1_SP_PI_P",
  "outputCode": "M1_SP_PI_P",
  "product": "H4A238HDF13",
  "siteType": "A9950",
  "changed": true
}
```

---

### 6.10 设置与设备模块

核心文件：

- `utils/device.py`
- `utils/labelimg_config.py`
- `gui/pages/settings_page.py`

当前状态：

- 设备检测已可作为 API 使用。
- LabelImg 配置会写入用户目录 `~/.autolabeler/labelimg.json`。
- `SettingsPage` 当前只是 UI 表单，保存按钮只弹出“设置已保存”，没有真正持久化通用设置。

建议 API：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/system/device` | 返回当前设备和推荐 batch size |
| `POST` | `/api/system/recommend-batch` | 按设备和图片尺寸计算推荐 batch size |
| `GET` | `/api/settings` | 获取后端持久化设置，需新增实现 |
| `PUT` | `/api/settings` | 保存默认抽样/训练/推理配置，需新增实现 |

`GET /api/system/device` 响应：

```json
{
  "device": {
    "device": "cuda",
    "deviceId": "0",
    "isAvailable": true,
    "name": "NVIDIA GeForce RTX ... x1",
    "memory": 8192
  },
  "optimalDevice": "0",
  "batchSize": {
    "imageSize640": 8,
    "imageSize1280": 8
  }
}
```

---

## 7. 推荐 API 总览

### 7.1 系统与通用

| 方法 | 路径 | 异步 | 说明 |
|------|------|------|------|
| `GET` | `/api/health` | 否 | 服务健康检查 |
| `GET` | `/api/system/device` | 否 | 设备检测 |
| `POST` | `/api/paths/validate` | 否 | 校验路径存在、类型、权限 |
| `GET` | `/api/tasks/{taskId}` | 否 | 获取任务状态 |
| `GET` | `/api/tasks/{taskId}/events` | 否/SSE | 任务进度事件 |
| `POST` | `/api/tasks/{taskId}/cancel` | 否 | 取消任务 |

### 7.2 核心工作流

| 方法 | 路径 | 异步 | 说明 |
|------|------|------|------|
| `POST` | `/api/scan` | 是 | 扫描站点 |
| `POST` | `/api/sample` | 是 | 抽样生成 database |
| `POST` | `/api/train` | 是 | YOLO 训练 |
| `POST` | `/api/infer` | 是 | 批量推理 |
| `POST` | `/api/restore` | 是 | 还原标注 |
| `POST` | `/api/convert/yolo-to-voc` | 是 | 批量 TXT 转 XML |
| `POST` | `/api/convert/voc-to-yolo` | 否/是 | 单个 XML 转 TXT |

### 7.3 查询与浏览

| 方法 | 路径 | 异步 | 说明 |
|------|------|------|------|
| `GET` | `/api/project/mapping?siteFolder=...` | 否 | 读取 mapping |
| `GET` | `/api/project/statistics?siteFolder=...` | 否 | 读取统计 |
| `GET` | `/api/project/classes?siteFolder=...` | 否 | 读取类别 |
| `GET` | `/api/project/products?siteFolder=...` | 否 | 读取 Code/Product 树 |
| `GET` | `/api/inference/history?siteFolder=...` | 否 | 推理历史 |
| `GET` | `/api/inference/runs/{runId}/tree?siteFolder=...` | 否 | 推理结果树 |

### 7.4 Web 标注器扩展

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/files/image` | 返回图片二进制 |
| `GET` | `/api/files/label` | 返回 YOLO 标签内容 |
| `PUT` | `/api/files/label` | 保存 YOLO 标签内容 |
| `POST` | `/api/labels/mark-labeled` | 更新 `manual_labeled` 状态 |

---

## 8. 前端页面字段建议

### 8.1 扫描页

输入：

- `siteFolder`

展示：

- 进度条、日志。
- `total_codes`、`total_products`、`total_images`。
- 扫描生成的类别列表。
- XML 标签不一致错误详情。

### 8.2 抽样页

输入：

- `siteFolder`
- `outputDir`
- `mode`
- `count`
- `ratio`
- `fullThreshold`
- `trainRatio`
- 可选高级项：`minCount`、`maxCount`、`preLabeledPriority`

展示：

- `sampledCount`、`trainCount`、`valCount`。
- `data.yaml` 路径。
- 已有标注优先抽样提示。

### 8.3 训练页

输入：

- `dataYaml`
- `baseModel`
- `outputDir`
- `epochs`
- `batchSize`
- `imageSize`
- `device`
- `patience`
- `box`
- `cls`
- `dfl`
- `scale`
- `cache`

展示：

- 当前 epoch。
- `mAP50`、`mAP50-95`。
- 日志。
- `best.pt` 路径。

### 8.4 推理页

输入：

- `modelPath`
- `siteFolder`
- `confidence`
- `iou`
- `batchSize`
- `device`

展示：

- 处理图片数。
- 有预测/空预测数量。
- 本次 `runId`。
- 推理结果保存路径。

### 8.5 标注检查页

输入：

- `siteFolder`
- `runId`
- `code`
- `product`

展示：

- 推理历史列表：时间、模型、图片数、conf、iou。
- Code/Product 树。
- 产品下图片和标签数量。
- 如果做 Web 标注器，展示原图、YOLO 框、类别列表。

### 8.6 还原页

输入：

- `sourceType`: `database` 或 `inference`
- `siteFolder`
- `databaseDir` 或 `runId`

展示：

- `total`、`success`、`skipped`、`failed`。
- 错误详情列表。
- 跳过原因提示：目标已存在或 mapping 已标记 restored。

### 8.7 转换页

输入：

- `folder`
- `recursive`
- 可选 `classes`

展示：

- `total`、`success`、`skipped`、`failed`。
- 注意转换成功会删除原 `.txt`。

---

## 9. 错误码建议

| 错误码 | 对应异常/场景 | 前端处理建议 |
|--------|---------------|--------------|
| `VALIDATION_ERROR` | 参数缺失、类型错误 | 表单高亮 |
| `PATH_NOT_FOUND` | 文件夹/文件不存在 | 提示用户重新选择 |
| `MAPPING_NOT_FOUND` | 未扫描，找不到 mapping.json | 引导先执行扫描 |
| `SCAN_LABEL_MISMATCH` | XML 标签与 Code 不一致 | 展示 details，可复制 |
| `SAMPLE_ERROR` | 抽样失败、XML 转换失败 | 展示文件名和详情 |
| `TRAIN_ERROR` | YOLO 训练失败 | 展示日志和建议检查 CUDA/数据集 |
| `INFERENCE_ERROR` | 模型加载或推理失败 | 展示模型路径、设备、阈值 |
| `RESTORE_ERROR` | 还原失败 | 展示失败文件列表 |
| `CONVERT_ERROR` | 标签转换失败 | 展示失败文件列表 |
| `DEVICE_ERROR` | 设备不可用 | 提供切换 CPU 入口 |
| `LABELIMG_ERROR` | LabelImg 配置或启动失败 | 本地模式才展示 |

---

## 10. Web 化关键注意事项

1. 浏览器不能直接访问用户本机任意路径。  
   如果后端运行在用户本机，可以让前端传路径字符串；如果是远程部署，需要改成上传文件或挂载共享目录。

2. 不要把原始本地路径直接作为图片 URL。  
   应通过后端文件流 API 返回图片，并做路径白名单、路径穿越校验和权限控制。

3. 所有耗时任务都应异步化。  
   扫描、抽样、训练、推理、还原、转换都可能耗时，前端应使用轮询或 SSE/WebSocket 展示进度。

4. `mapping.json` 是状态源。  
   后端应通过 `MappingManager` 读写，不要让前端直接修改 JSON。

5. 推理可以重复执行。  
   当前逻辑每次推理生成新的 `run_YYYYMMDD_HHMMSS`，还原时由用户选择某次结果。

6. 还原默认不覆盖。  
   目标 `.txt` 已存在会跳过，前端需要展示 `skipped`。

7. 转换会删除原 TXT。  
   `convert_folder()` 成功生成 XML 后会删除原 `.txt`，前端需要明确提示或后端增加 dry-run/backup 参数。

8. 当前设置页没有真正持久化。  
   Web 版如需全局默认参数，需要新增 settings 存储。

9. 当前人工标注状态不自动同步。  
   如果 Web 版内置标注器，应在保存标签后调用状态更新接口，或新增扫描 labels 的同步任务。

10. 注意若保留 LabelImg。  
    LabelImg 启动是后端机器上的 GUI 行为，不适合普通 Web 远程部署。

---

## 11. 建议后端 Service 封装形态

可以先按当前 Worker 的职责拆 service：

```text
services/
  scan_service.py        # 封装 Scanner.scan()
  sample_service.py      # 封装 Sampler.sample()
  train_service.py       # 封装 Trainer.train()
  inference_service.py   # 封装 Inferencer.infer()/history
  restore_service.py     # 封装 Restorer.restore()
  convert_service.py     # 封装 Converter
  project_service.py     # mapping/classes/products 查询
  file_service.py        # 图片/标签安全读取与保存
  task_service.py        # 任务队列、取消、进度、日志
```

每个 service 建议统一接收普通 dict，内部转换为当前 dataclass：

```python
SampleConfig(
    mode=config.get("mode", "count"),
    count=config.get("count", 40),
    ratio=config.get("ratio", 0.3),
    min_count=config.get("minCount", 20),
    max_count=config.get("maxCount", 50),
    full_threshold=config.get("fullThreshold", 35),
    train_ratio=config.get("trainRatio", 0.9),
    pre_labeled_priority=config.get("preLabeledPriority", True),
)
```

命名建议：

- API 使用前端友好的 camelCase。
- Python service 内部转换为现有 snake_case。
- 文件系统路径统一用字符串传输，后端入口处转换成 `Path`。

---

## 12. 当前实现差异与待确认项

这些点建议在真正写后端 API 前确认或修正：

| 项目 | 当前状态 | 建议 |
|------|----------|------|
| 推理 IoU 默认值 | `InferenceConfig` 默认 0.7，`InferenceWorker` fallback 0.45，页面默认 0.7 | Web API 统一为一个默认值 |
| 训练 cache 参数 | 页面有控件，Worker 未传入 `TrainConfig` | 后端封装时补齐 |
| 训练高级参数 | `workers/optimizer/lr0/dfl/cache` core 支持但 GUI 未完整传入 | API 可全部暴露为高级设置 |
| 设置页 | 只展示表单，不持久化 | 新增 settings 存储 |
| `manual_labeled` | 有字段和方法，但未自动更新 | Web 标注器保存后更新 |
| 推理历史还原 | 可能误处理 LabelImg 复制的 `classes.txt` | 后端过滤 `classes.txt` |
| 转换操作 | 成功后删除 TXT | 前端显式确认，或后端增加 `deleteSource` 参数 |
| 路径访问 | 桌面应用天然本地访问 | Web 需要安全文件 API |

---

## 13. 最小首版 API 范围

如果先做可用的 Web 版，建议首版只实现：

1. `POST /api/scan`
2. `POST /api/sample`
3. `POST /api/train`
4. `POST /api/infer`
5. `GET /api/inference/history`
6. `GET /api/inference/runs/{runId}/tree`
7. `POST /api/restore`
8. `POST /api/convert/yolo-to-voc`
9. `GET /api/tasks/{taskId}` + `GET /api/tasks/{taskId}/events`
10. `GET /api/project/statistics` + `GET /api/project/classes`

标注检查和 Web 标注器可以作为第二阶段扩展。

