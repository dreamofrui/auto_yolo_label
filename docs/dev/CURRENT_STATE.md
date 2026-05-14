# AutoLabeler 当前进度

> 最后更新：2026-05-14
> 当前里程碑：M1（Core 模块解耦）
> 当前分支：refactor/scaffold-v2

---

## 1. 一句话现状

**阶段 0 / 阶段 1 / M1.1 / M1.2 已完成**。旧代码、旧测试、旧配置和旧桌面资产已移动到 `legacy/`，仅作只读参考；6 个 `utils/` 基础设施模块与 8 个 `core/` 业务模块已完成。

下一步：进入 M1.3 双调用入口，按规范接入桌面 worker 与 HTTP API。

---

## 2. 模块状态总览

| 模块 | 重写状态 | 测试覆盖 | 文档 | 备注 |
|------|----------|----------|------|------|
| **基础设施（utils/）** |  |  |  |  |
| exceptions.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | `ErrorCode` / `ErrorInfo` / `AutoLabelerError` 已实现 |
| logging_setup.py | ✅ 完成 | 目标测试通过 | ✅ | loguru 初始化和幂等 sink 管理 |
| device.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | CPU/CUDA/MPS 检测和 batch size 建议 |
| path_encoder.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | encode/decode/to_relative_path 已实现 |
| mapping_manager.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | MappingData / ImageInfo / 状态查询已实现 |
| task_registry.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | TaskHandle / TaskRegistry / JSON 持久化和取消确认语义已实现 |
| **核心业务（core/）** |  |  |  |  |
| scanner.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | 已实现 Code/Product 扫描、mapping/classes 输出、XML 校验和 TaskHandle 取消 |
| sampler.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | 已实现 mapping 驱动抽样、YOLO database 输出、预标注处理和 TaskHandle 取消 |
| converter.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | 已实现 YOLO TXT ↔ VOC XML 转换，delete_source 默认 False |
| trainer.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | 已实现 Ultralytics YOLO 薄包装、参数校验、结果解析和 TaskHandle epoch 进度 |
| inferencer.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | 已实现 mapping/custom 推理、run 输出、空预测文件和 inferred 标记 |
| label_inspector.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | 已实现 run 列表、Code/Product 树和产品标签查询 |
| restorer.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | 已实现 database/inference 标签还原、跳过/覆盖规则和 mapping restored 标记 |
| labelimg_launcher.py | ✅ 完成 | 目标测试通过 | ✅ 规范已写 | 已实现外部 Python 校验与 LabelImg 子进程启动 |
| **入口层** |  |  |  |  |
| gui/workers/* | 🟡 进行中 | scan worker 通过 | - | 已接入 `gui/workers/scan_worker.py` |
| api/main.py + routes/ | 🟡 进行中 | scan route 通过 | - | 已接入 `api/routes/scan.py` |
| api/schemas/ | 🟡 进行中 | scan schema 通过 | - | 已建立 camelCase schema 基类 |
| **集成测试** |  |  |  |  |
| tests/integration/test_scenario_a.py（完整流程） | ✅ 完成 | 通过 | ✅ 规范已写 | Scan → Sample → Train → Infer → Restore |
| tests/integration/test_scenario_b.py（跳过扫描） | ✅ 完成 | 通过 | ✅ 规范已写 | 手写 mapping + database |
| tests/integration/test_scenario_c.py（跳过训练） | ✅ 完成 | 通过 | ✅ 规范已写 | best.pt + custom images |
| tests/integration/test_scenario_d.py（纯转换） | ✅ 完成 | 通过 | ✅ 规范已写 | Converter 独立调用 |

图例：✅ 完成 / 🟡 进行中 / ⬜ 待开始 / ❌ 阻塞

---

## 3. 已完成（本里程碑内）

- 2026-05-13 完成规范文档 `01-requirements.md` / `02-constraints.md` / `03-progress-template.md` / README.md
- 2026-05-13 重写 `CLAUDE.md`，加入「REFACTOR ACTIVE」硬注入段 + Behavioral Guidelines
- 2026-05-13 创建初始 `CURRENT_STATE.md` 和 `CHANGELOG.md`
- 2026-05-13 完成阶段 0：旧代码、旧测试、旧配置和旧桌面资产归档到 `legacy/`；新增 `AGENTS.md`
- 2026-05-13 完成 `utils/exceptions.py`：新增共享错误码、错误信息 dataclass、业务异常基类和通用任务异常
- 2026-05-13 完成 `utils/logging_setup.py`：新增 loguru 统一初始化、文件 sink、stderr sink 和重复初始化去重
- 2026-05-13 完成 `utils/device.py`：新增可测试的 CPU/CUDA/MPS 检测、显存读取、设备解析和 batch size 建议
- 2026-05-13 完成 `utils/path_encoder.py`：新增路径编码、解码、相对路径转换和分隔符冲突校验
- 2026-05-13 完成 `utils/mapping_manager.py`：新增 mapping.json dataclass 缓存、原子保存、状态标记和推理候选查询
- 2026-05-13 完成 `utils/task_registry.py`：新增任务句柄、生命周期转换、取消标记、错误信息和 JSON 持久化
- 2026-05-13 完成 `core/scanner.py`：新增扫描输入输出 dataclass、Code/Product 两级扫描、mapping/classes 生成、XML 标签一致性校验和 TaskHandle 取消检查
- 2026-05-13 修正 `utils/task_registry.py` 取消语义：运行中任务的 `cancel()` 仅请求 core 循环停止，`finish_cancelled_task()` 负责确认终态，避免晚到成功覆盖取消结果
- 2026-05-13 完成 `core/sampler.py`：新增抽样输入输出 dataclass、基于 mapping 的 Code/Product 抽样、YOLO database 输出、预标注 TXT/XML 处理和映射状态更新
- 2026-05-13 完成 `core/converter.py`：新增 TXT→XML 批量转换、XML→TXT 单文件转换、classes 解析、备份删除和 TaskHandle 取消检查
- 2026-05-13 完成 `core/trainer.py`：新增训练输入输出 dataclass、data.yaml / base model 校验、Ultralytics YOLO 训练薄包装、metrics 解析和 epoch 进度回调
- 2026-05-13 完成 `core/inferencer.py`：新增 mapping/custom 图片推理、run 目录输出、空预测 TXT、推理参数快照和 mapping inferred 统计标记
- 2026-05-14 完成 `core/label_inspector.py`：新增推理 run 列表、Code/Product 树统计、产品标签读取、控制文件过滤和原图路径推断
- 2026-05-14 完成 `core/restorer.py`：新增 database/inference 标签还原、目标跳过/覆盖、单文件失败不中断、TaskHandle 进度取消和 mapping restored 标记
- 2026-05-14 完成 `core/labelimg_launcher.py`：新增外部 Python / LabelImg 校验、LabelImg 启动命令构造、子进程启动异常映射和无 GUI 框架依赖的测试边界
- 2026-05-14 完成 M1 四个集成场景测试：完整流程、跳过扫描、跳过训练和纯格式转换均已自动化覆盖
- 2026-05-14 完成 scan 双调用入口第一版：新增 HTTP route、pydantic camelCase schema、桌面 worker 适配和桌面/HTTP examples

---

## 4. 进行中

### 4.1 M1.3 双调用入口
- 负责人：Codex
- 开始日期：2026-05-14
- 当前进度：
  - [x] 编写 `tests/integration/test_scenario_{a,b,c,d}.py`
  - [x] 设计 `api/` scan 薄入口与 pydantic schema
  - [x] 设计 `gui/workers/` scan 对新 core + TaskHandle 的适配
  - [x] 补齐 examples 桌面/HTTP scan 双调用示例
  - [ ] 推广到 sample/train/infer/restore/convert/label inspector/labelimg launcher
- 阻塞项：无

---

## 5. 下一步（按优先级）

### 5.1 阶段 0：归档旧代码（半天内）

已完成。旧代码和旧资产已归档至 `legacy/`，后续只读参考。

### 5.2 阶段 1：架构摸底（≤ 4 小时，已完成）

- 已完成列模块清单（`notes/legacy-map.md`）
- 已完成 worker → core → utils 调用图（`notes/legacy-callgraph.md`）
- 已完成 grep 隐藏耦合点
- 已完成对照 01-requirements.md 找差异（`notes/legacy-diff.md`）

完成后向负责人做 10 分钟口头汇报。

### 5.3 阶段 2 / M1.1：基础设施实现顺序

```
1. utils/exceptions.py          ← 所有模块的依赖
2. utils/logging_setup.py        ← 所有模块的依赖
3. utils/device.py
4. utils/path_encoder.py
5. utils/mapping_manager.py      ← 依赖 exceptions, path_encoder
6. utils/task_registry.py        ← 依赖 exceptions（新增模块，无旧版参考）
```

### 5.4 阶段 2 / M1.2：核心业务模块（顺序基于依赖图）

```
1. core/scanner.py               ← 依赖 mapping_manager, path_encoder
2. core/sampler.py               ← 依赖 scanner 的产物，但不依赖 scanner
3. core/converter.py             ← 独立，可并行
4. core/trainer.py               ← 依赖 sampler 的产物
5. core/inferencer.py            ← 依赖 trainer 的产物
6. core/label_inspector.py       ← 依赖 inferencer 的产物
7. core/restorer.py              ← 依赖 sampler / inferencer 的产物
8. core/labelimg_launcher.py     ← 独立
```

### 5.5 阶段 2 / M1.3：双调用入口

- gui/workers/ 全部用 TaskHandle 替代旧信号
- api/main.py + 8 个 routes/
- examples/scan_via_desktop.py + examples/scan_via_http.py

---

## 6. 已知问题 / 风险

- **风险**：新人若不读完三份规范文档直接动手，会重蹈旧版覆辙
  - 缓解：CLAUDE.md 顶部「REFACTOR ACTIVE」段强制要求开会话先读 CURRENT_STATE.md；十条纪律靠 pre-commit hook 机器拦截
- **风险**：阶段 1 摸底变成"细读旧代码"，超时
  - 缓解：02-constraints.md 第 10 节和给新人的指令明确 4 小时时间盒
- **风险**：legacy/ 的 `mapping.json` 格式与新版不兼容
  - 缓解：保持 ImageInfo 字段向后兼容，加新字段不删旧字段；遇兼容问题写迁移脚本

---

## 7. 当前里程碑定义

### M1（当前）：Core 模块解耦

**完成标准**：
- 所有 8 个 core 模块和 6 个 utils 模块按 02-constraints.md 第 5 节验收清单交付
- 4 个集成场景测试全部通过
- `mypy --strict core/ utils/` 0 错误
- `pytest --cov` 覆盖率 `core/ ≥ 70%`、`utils/ ≥ 80%`
- 所有 PR 的 CURRENT_STATE / CHANGELOG / requirements 同步完成

**预计**：M1 工作量约 2-3 周（视新人熟练度）。

### M2：HTTP 入口

**完成标准**：
- `api/` 目录下 main.py + 8 个 route 文件
- HTTP 集成测试全部通过
- `examples/*_via_http.py` 可跑
- OpenAPI 文档自动生成可访问

### M3：桌面 GUI 接入新 core

**完成标准**：
- `gui/workers/` 全部用 `TaskHandle` 替代旧 QThread 信号
- 桌面端 4 个场景手工验证通过
- `main.py`（桌面入口）跑起来不依赖 legacy/

---

## 8. 文档维护说明

本文件 (`CURRENT_STATE.md`) **每个 PR 必须更新**：
- 模块状态总览：⬜ → 🟡 → ✅
- "已完成"段落：append 一条
- "进行中"段落：替换为下一个任务
- "最后更新"日期

详细规则见 `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/03-progress-template.md` 第 2 节。

---

## 9. 新人接手快速指南

如果你是第一次进项目，按这个顺序：

1. 读 `CLAUDE.md`（项目根）
2. 读 `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/README.md`
3. 读 `01-requirements.md`、`02-constraints.md`、`03-progress-template.md`（按 README 推荐顺序）
4. 回答 CLAUDE.md 第 0.3 节"五个自检问题"给负责人
5. 调用 `Skill: superpowers:brainstorming` 与负责人对齐阶段 0/1 计划
6. 执行阶段 0（归档 legacy/）
7. 进入阶段 1（架构摸底，时间盒 4 小时）
8. 进入阶段 2（M1.1 基础设施实现）

**记住：宁可多问，不要私自决定。**
