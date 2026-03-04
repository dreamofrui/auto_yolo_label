# AutoLabeler 当前开发状态

> 更新日期: 2025-01-19

---

## 项目完成状态

**核心功能已完成**

### 已交付模块
- ✅ 6 个核心模块 (Scanner, Sampler, Trainer, Inferencer, Restorer, Converter)
- ✅ 5 个工具模块 (PathEncoder, MappingManager, Device, ImageUtils, Exceptions)
- ✅ 8 个 GUI 页面 + 8 个后台工作线程
- ✅ 111 个单元测试全部通过

---

## 快速运行

```bash
# 激活环境
conda activate yolo

# 运行应用
python main.py

# 运行测试
pytest tests/ -v
```

---

## 最近更新 (2025-01-19)

### 文档精简
- **CLAUDE.md**: 精简至 127 行，聚焦开发流程与测试要点
- **requirement.md**: 精简至 249 行，聚焦核心功能需求
- **jishukaifawendang.md**: 精简至 242 行，聚焦技术选型与架构

### Bug修复
- **ComboBox 参数错误**: 修复 `addItem()` 方法调用，正确传递 `(icon, text, userData)` 参数

---

## 开发环境

- **Python**: `D:\miniforge3\envs\yolo\python.exe`
- **环境**: `yolo` conda 环境
- **代码格式化**: `black .`

---

## 关键技术点

1. **路径编码**: 使用 `__` 分隔符扁平化 Code/Product/Filename
2. **线程安全**: MappingManager 使用双重锁机制 (RLock + FileLock)
3. **设备检测**: 使用 `device="auto"` 和 `batch_size=-1` 自动检测
4. **推理状态**: 推理不标记 `inferred=True`，允许重新推理；还原时才标记

---

## 功能增强 (2025-01-14)

### 已有标注优先抽样
- 检测产品文件夹中 XML/TXT 标注
- XML 自动转换为 YOLO TXT
- 优先抽取已标注样本（不计入数量限制）
- 空标注文件自动删除

### 推理结果分区存储
- 推理结果保存到 `.autolabeler/inference_results/run_YYYYMMDD_HHMMSS/`
- 保留原始 Code/Product 目录结构
- 生成 `inference_config.json` 记录参数
- 支持多次推理，用户选择最佳结果还原

### 还原功能增强
- 支持从 Database 目录还原（人工标注）
- **新增** 支持从推理结果还原（选择历史 run_xxx）
- GUI 新增来源选择（Database / 推理结果）

