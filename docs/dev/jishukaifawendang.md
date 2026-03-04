# AutoLabeler 技术开发文档

---

## 1. 技术选型

| 层次 | 技术 | 版本 | 理由 |
|------|------|------|------|
| 编程语言 | Python | 3.11 | YOLO生态完善，开发效率高 |
| GUI框架 | PySide6 | ≥6.5 | Qt官方绑定，跨平台稳定 |
| UI组件库 | QFluentWidgets | ≥1.4 | Fluent风格，开箱即用 |
| 目标检测 | Ultralytics YOLO | 8.3.236 | 业界主流，API友好 |
| 图像处理 | Pillow | - | 图片读取与尺寸获取 |
| 配置管理 | PyYAML | - | YAML配置解析 |
| 数据序列化 | json | 标准库 | mapping文件读写 |
| XML处理 | xml.etree | 标准库 | VOC格式生成 |

---

## 2. 系统架构

```
┌─────────────────┐
│   GUI Layer     │  PySide6 + QFluentWidgets
│  (主窗口/页面)    │
└────────┬────────┘
         │
┌────────▼────────┐
│  Controller     │  页面控制器、信号槽
│  (业务流程控制)  │
└────────┬────────┘
         │
┌────────▼─────────────────────┐
│        Core Modules          │
│  Scanner | Sampler | Trainer  │
│  Inferencer | Restorer | Converter │
└────────┬─────────────────────┘
         │
┌────────▼────────┐
│  Utils Layer    │
│ PathEncoder     │
│ MappingManager  │
│ Device          │
│ ImageUtils      │
└────────┬────────┘
         │
┌────────▼────────┐
│  File System    │
└─────────────────┘
```

---

## 3. 项目结构

```
auto_yolo_label/
├── core/                # 核心业务模块
│   ├── base.py         # BaseModule基类
│   ├── scanner.py      # 扫描
│   ├── sampler.py      # 抽样
│   ├── trainer.py      # 训练
│   ├── inferencer.py   # 推理
│   ├── restorer.py     # 还原
│   └── converter.py    # 转换
├── utils/               # 工具模块
│   ├── path_encoder.py      # 路径编码/解码
│   ├── mapping_manager.py   # 映射管理（线程安全）
│   ├── device.py            # 设备检测
│   ├── image_utils.py       # 图片工具
│   └── exceptions.py        # 自定义异常
├── gui/                 # 图形界面
│   ├── pages/          # 功能页面
│   ├── widgets/        # 自定义组件
│   └── workers/        # 后台线程
└── tests/              # 单元测试
```

---

## 4. 核心设计

### 4.1 模块基类 (BaseModule)
```python
# 所有核心模块继承BaseModule
- report_progress(current, total, message)  # 进度报告
- cancel() / reset()                        # 取消/重置
- set_progress_callback(callback)          # 进度回调
```

### 4.2 路径编码器 (PathEncoder)
```python
# 三级路径编码为单一文件名
encode("CodeA", "ProductB", "IMG_001.jpg")
→ "CodeA__ProductB__IMG_001.jpg"
```

### 4.3 映射管理器 (MappingManager)
```python
# 线程安全的mapping.json管理
- dual locking: RLock + FileLock
- CRUD operations
- status updates: mark_sampled(), mark_inferred(), mark_restored()
```

### 4.4 设备管理 (device.py)
```python
# 自动设备检测与优化
- get_optimal_device()   # 返回最优设备
- get_optimal_batch_size()  # 根据显存计算batch size
- 支持 GPU/CPU/MPS
```

### 4.5 自定义异常 (exceptions.py)
```python
AutoLabelerError (base)
├── ScanError
├── SampleError
├── TrainError
├── InferenceError
├── RestoreError
├── ConvertError
└── MappingError
```

---

## 5. 开发规范

### 5.1 代码规范
```yaml
# 使用 black 格式化
line-length: 100

# 类型注解
使用 typing 模块

# 文档字符串
Google 风格 docstring

# 命名规范
类名: PascalCase
函数: snake_case
常量: UPPER_SNAKE_CASE
```

### 5.2 错误处理
- 使用自定义异常类
- GUI层捕获异常，友好提示
- 日志记录详细错误信息

### 5.3 线程安全
- `MappingManager` 使用双重锁
- GUI操作通过 QThread Worker
- 信号槽机制通信

---

## 6. 测试要点

### 6.1 单元测试覆盖

| 模块 | 关键测试点 |
|------|-----------|
| PathEncoder | 编码/解码正确性、特殊字符 |
| MappingManager | CRUD操作、线程安全 |
| Scanner | 目录遍历、统计准确性 |
| Sampler | 抽样逻辑、train/val分配 |
| Trainer | 设备检测、配置解析 |
| Inferencer | 批处理、进度跟踪 |
| Restorer | 路径还原、多格式处理 |
| Converter | 坐标转换、XML有效性 |

### 6.2 集成测试场景
- 完整流程：扫描→抽样→标注→训练→推理→还原→转换
- 断点续传：中途中断后继续处理
- 异常恢复：各种异常情况处理
- 大规模数据：10000+图片性能测试

---

## 7. 开发计划

### 7.1 优先级
```
P0 (必须):
├── 基础设施 (path_encoder, mapping_manager, exceptions)
├── 数据处理 (scanner, sampler, restorer)
├── 训练推理 (trainer, inferencer)
└── GUI基础 (主窗口、Worker、核心页面)

P1 (重要):
├── 格式转换 (converter)
└── 完整GUI (所有页面、组件)

P2 (优化):
├── 训练曲线可视化
└── 性能优化
```

### 7.2 关键风险
| 风险 | 应对措施 |
|------|----------|
| YOLO环境配置 | 详细文档、自动检测脚本 |
| 大规模数据性能 | 分批处理、进度反馈 |
| 多线程文件冲突 | 文件锁+线程锁双重保护 |
| GPU内存不足 | 自动降级CPU/减小batch size |

---

## 8. 部署打包

```bash
# 使用 PyInstaller 打包为单文件可执行程序
pyinstaller --onefile --windowed \
  --icon=resources/icons/logo.ico \
  --add-data "resources;resources" \
  --name AutoLabeler \
  main.py
```

**运行环境要求**：
- 最低：CPU 4核、内存 8GB
- 推荐：GPU NVIDIA GTX 1060 6GB、CUDA 11.7+

---

## 9. 功能增强 (2025-01-14)

### 9.1 已有标注优先抽样
- 检测产品文件夹中XML/TXT标注
- 自动转换XML→YOLO TXT
- 优先抽取已标注样本
- 删除空标注文件

### 9.2 推理结果分区存储
- 推理结果保存到时间戳目录
- 保留原始Code/Product结构
- 生成inference_config.json
- 支持多次推理对比
- 用户选择最佳结果还原
