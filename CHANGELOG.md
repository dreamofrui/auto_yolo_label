# Changelog

本项目所有显著变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### Added
- (docs) 新增 `docs/superpowers/skills/auto-yolo-boundary-review/`，用于统一边界审查、企业级纪律检查和临时 worker 交接。
- 初始化重构基线（2026-05-13）
- 新增规范文档目录 `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/`
  - `README.md`：阅读顺序索引
  - `01-requirements.md`：8 大模块详细 I/O + 数据模型 + 异常表 + 新旧差异
  - `02-constraints.md`：5 角度强约束 + 10 条强制纪律 + Git 规范
  - `03-progress-template.md`：CURRENT_STATE / CHANGELOG / requirements 维护规则
- 重写 `CLAUDE.md`，加入「REFACTOR ACTIVE」硬注入段 + Behavioral Guidelines
- 新建 `CHANGELOG.md`（本文件）
- (docs) 新增 `AGENTS.md`，记录 Codex / agents 接手重构时必须遵守的执行纪律（本地阶段 0 提交）
- (utils) 新增 `utils/exceptions.py`，提供 `ErrorCode`、`ErrorInfo`、`AutoLabelerError` 和通用任务异常（本地 M1.1 提交）
- (utils) 新增 `utils/logging_setup.py`，提供 loguru 统一初始化和幂等 sink 管理（本地 M1.1 提交）
- (utils) 新增 `utils/device.py`，提供 CPU/CUDA/MPS 检测、设备解析和自动 batch size 建议（本地 M1.1 提交）
- (utils) 新增 `utils/path_encoder.py`，提供路径扁平化编码、解码和分隔符冲突校验（本地 M1.1 提交）
- (utils) 新增 `utils/mapping_manager.py`，提供 mapping.json dataclass 缓存、原子保存和状态标记查询（本地 M1.1 提交）
- (utils) 新增 `utils/task_registry.py`，提供 `TaskHandle`、任务生命周期状态、取消标记和 JSON 持久化（本地 M1.1 提交）
- (scanner) 新增 `core/scanner.py`，实现 Code/Product 站点扫描、`mapping.json` / `classes.txt` 输出、XML 标签一致性校验和 TaskHandle 取消检查（本地 M1.2 提交）
- (sampler) 新增 `core/sampler.py`，实现基于 `mapping.json` 的 Code/Product 抽样、YOLO `database/` 输出、预标注 TXT/XML 处理和映射状态更新（本地 M1.2 提交）
- (converter) 新增 `core/converter.py`，实现 YOLO TXT → VOC XML 批量转换、VOC XML → YOLO TXT 单文件转换、MappingManager classes 解析、备份删除和 TaskHandle 取消检查（本地 M1.2 提交）
- (trainer) 新增 `core/trainer.py`，实现 data.yaml / base model 校验、Ultralytics YOLO 训练薄包装、metrics 解析、OOM/取消异常映射和 TaskHandle epoch 进度（本地 M1.2 提交）
- (inferencer) 新增 `core/inferencer.py`，实现 mapping/custom 图片推理、`inference_results/run_*` 输出、空预测 TXT、推理参数快照和 inferred 统计标记（本地 M1.2 提交）
- (label-inspector) 新增 `core/label_inspector.py`，实现推理 run 列表、Code/Product 树统计、产品标签读取、控制文件过滤和原图路径推断（本地 M1.2 提交）
- (restorer) 新增 `core/restorer.py`，实现 database/inference 标签还原、目标跳过/覆盖、单文件失败不中断、TaskHandle 进度取消和 mapping restored 标记（本地 M1.2 提交）
- (labelimg-launcher) 新增 `core/labelimg_launcher.py`，实现外部 Python / LabelImg 校验、LabelImg 子进程启动和结构化异常映射（本地 M1.2 提交）
- (tests) 新增 M1 四个集成场景，覆盖完整流程、跳过扫描、跳过训练和纯格式转换（本地 M1 提交）
- (entry) 新增 scan HTTP route、pydantic camelCase schema、桌面 worker 适配和桌面/HTTP examples（本地 M1.3 提交）
- (entry) 新增 sample HTTP route、pydantic camelCase schema、桌面 worker 适配和共享 TaskRegistry service（本地 M1.3 提交）
- (entry) 新增 train/infer/restore/convert HTTP route、pydantic camelCase schema、桌面 worker 适配和共享 TaskRegistry service（本地 M1.3 提交）
- (entry) 新增 label inspector 与 LabelImg HTTP route、pydantic camelCase schema、桌面 worker 适配和共享 service，并统一注册到 `api/main.py`（本地 M1.3 提交）

### Changed
- (api) LabelImg HTTP `launch` 默认禁用，只有本地 GUI-capable 部署显式传入 `allow_labelimg_launch=True` 时才允许从 API 启动本机 LabelImg。
- (docs) 同步 `docs/dev/CURRENT_STATE.md` 的 M1 验收状态，记录本地全量测试、类型检查、纪律检查和覆盖率结果，并进入 PR 边界复核阶段。
- (inferencer) custom 图片位于 `site_folder/Code/Product/` 下时，推理输出保留 Code/Product 相对结构，便于直接交给 Restorer（本地 M1 提交）
- (docs) `docs/dev/CURRENT_STATE.md` 重置为重构基线状态（2026-05-13）
- (legacy) 将旧代码、旧测试、旧配置和旧桌面资产归档到 `legacy/`，后续仅作只读参考（本地阶段 0 提交）
- (dev) `.gitignore` 增加 pytest/mypy 本地缓存和 `pytest_tmp_codex/` 临时目录（本地 M1.1 提交）
- (utils) 调整 `TaskRegistry.cancel()` 为取消请求语义，新增 `finish_cancelled_task()` 确认取消终态，避免运行中任务被提前释放或晚到成功覆盖（本地 M1.1 修复）

### Deprecated
- 重构前旧 `core/`、`utils/`、`gui/`、`tests/` 目录已在阶段 0 归档至 `legacy/`；当前同名目录均为新实现。
- 旧目录命名 `vals/`（将在新版改为 `val/`，与 YOLO 标准一致）
- 旧 `Converter.convert_folder()` 默认删除源 TXT 的行为（新版默认 `delete_source=False`）

### Removed
- 已随旧代码归档到 `legacy/`：`utils/site_detector.py`、`core/conversion_rule.py`、`config/A9950_conversion_rules.yaml`

---

## 历史版本（重构前）

> 本节仅保留作为旧版本历史参考。新版本所有变更进入上方 `[Unreleased]` 节。

### 2026-03-06
- External LabelImg environment support (avoid package conflicts with yolo_new)
- `LabelImgConfig` class for configuration management (project > global priority)
- GUI configuration dialog for selecting external Python interpreter
- Configuration stored in `~/.autolabeler/labelimg.json`

### 2025-03-05
- Empty prediction now creates empty `.txt` files (for LabelImg compatibility)
- Label Inspector page for viewing inference results
- LabelImg integration with auto-copy classes.txt
- Inference result browser with Code/Product tree structure

### 2025-01-21
- Homepage quick actions (开始扫描, 使用文档 buttons)
- Navigation API: `navigationInterface.setCurrentItem(page_name)`
- Restore function improvements for inference mode

### 2025-01-14
- Pre-labeled priority sampling (XML/TXT detection)
- Inference result separation (timestamped directories)
- `ImageInfo.label_source`: `"none"` / `"pre_existing_xml"` / `"pre_existing_txt"`

---

## 条目规则速查

提交 PR 时，在 `[Unreleased]` 节下加条目：

| Section | 含义 | 示例 |
|---------|------|------|
| `Added` | 新功能 | `- (scanner) 支持自定义 output_dir (PR #12)` |
| `Changed` | 行为/接口变更 | `- (converter) delete_source 默认改为 False，破坏性变更 (PR #14)` |
| `Deprecated` | 即将移除的接口 | `- 旧 vals/ 目录将在 v2.0 移除` |
| `Removed` | 已移除的接口 | `- (utils) 删除 site_detector.py (PR #11)` |
| `Fixed` | bug 修复 | `- (sampler) 修复 mode='ratio' 时未触发全抽 (PR #16)` |
| `Security` | 安全相关 | `- 无` |

格式：`- (模块名) 描述 (PR #编号)`

破坏性变更必须明确标注，并在 PR 描述中说明迁移方案。

详细规则见 `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/03-progress-template.md` 第 3 节。
