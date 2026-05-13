# AutoLabeler 进度文档维护规范

> 文档版本：v1.0
> 创建日期：2026-05-13
> 目标读者：负责重写本项目的开发者（默认无业务背景）
> 配套文档：`01-requirements.md`、`02-constraints.md`

---

## 0. 阅读须知

每次提 PR**必须**更新本节列出的文档。这是硬性合并条件，不是建议。

文档没更新的 PR 会被 reject，无论代码多正确。

---

## 1. 必须维护的 3 份"活"文档

| 文件 | 路径 | 更新时机 | 谁负责 |
|------|------|----------|--------|
| **CURRENT_STATE.md** | `docs/dev/CURRENT_STATE.md` | 每次 PR 必更 | PR 作者 |
| **CHANGELOG.md** | `CHANGELOG.md`（仓库根） | 每次 PR 必更 | PR 作者 |
| **01-requirements.md** | `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/01-requirements.md` | 接口变更必更 | PR 作者 |

---

## 2. CURRENT_STATE.md 模板与规则

### 2.1 文件位置

`docs/dev/CURRENT_STATE.md`

### 2.2 用途

让任何新人 / 接手者**在 5 分钟内**知道当前项目走到了哪一步、下一步要做什么。

### 2.3 文件结构

```markdown
# AutoLabeler 当前进度

> 最后更新：YYYY-MM-DD
> 当前里程碑：M1 / M2 / M3
> 当前分支：main

---

## 1. 一句话现状

（在两行内说清楚：哪些模块已重写完毕，哪个模块正在做，下一个要做什么）

例：Scanner / Sampler / TaskRegistry 重写完成；Trainer 进行中（约 60%）；
    下一步 Inferencer。

---

## 2. 模块状态总览

| 模块 | 重写状态 | 测试覆盖 | 文档 | 备注 |
|------|----------|----------|------|------|
| Scanner | ✅ 完成 | 85% | ✅ | - |
| Sampler | ✅ 完成 | 78% | ✅ | - |
| Trainer | 🟡 进行中 | 50% | 🟡 部分 | cache 参数待补 |
| Inferencer | ⬜ 待开始 | 0% | ⬜ | - |
| LabelInspector | ⬜ 待开始 | 0% | ⬜ | - |
| Restorer | ⬜ 待开始 | 0% | ⬜ | - |
| Converter | ⬜ 待开始 | 0% | ⬜ | - |
| LabelImgLauncher | ⬜ 待开始 | 0% | ⬜ | - |
| TaskRegistry | ✅ 完成 | 90% | ✅ | - |
| MappingManager | ✅ 完成 | 95% | ✅ | - |
| api/ HTTP 入口 | ⬜ 待开始 | 0% | ⬜ | - |

图例：✅ 完成 / 🟡 进行中 / ⬜ 待开始 / ❌ 阻塞

---

## 3. 已完成（本里程碑内）

- 2026-05-15 完成 Scanner 重写（PR #12）
- 2026-05-17 完成 Sampler 重写（PR #14）
- 2026-05-18 完成 TaskRegistry（PR #15）

---

## 4. 进行中

### 4.1 Trainer 重写
- 负责人：@xxx
- 开始日期：2026-05-19
- 预计完成：2026-05-23
- 当前进度：
  - [x] TrainConfig / TrainResult 定义
  - [x] 单元测试骨架
  - [ ] 进度回调集成
  - [ ] cache 参数补齐
  - [ ] 取消机制
- 阻塞项：无

---

## 5. 下一步（按优先级）

1. 完成 Trainer（预计 5-23）
2. Inferencer 重写（预计 5-24 开始）
3. Restorer 重写
4. Converter 重写
5. LabelInspector 重写
6. api/ 薄壳 + 集成测试

---

## 6. 已知问题 / 风险

- ultralytics 8.3.x 在 CPU 模式下 cache="ram" 偶发 OOM，已在 Trainer 内做降级（PR #18）
- mapping.json 兼容旧版本字段会有 deprecation warning，待统一处理（issue #25）

---

## 7. 当前里程碑定义

### M1（当前）：Core 模块解耦
**完成标准**：
- 所有 8 个 core 模块按 02-constraints.md 第 5 节交付
- 集成测试 4 个场景全部通过
- mypy/ruff/pytest 全过

### M2：HTTP 入口
**完成标准**：
- api/ 目录下 8 个 route 文件
- HTTP 集成测试通过
- OpenAPI 文档可访问

### M3：桌面 GUI 接入新 core
**完成标准**：
- gui/workers/ 全部用 TaskHandle 替代旧信号
- 桌面端 4 个场景手工验证通过
```

### 2.4 更新规则

| 触发 | 必改字段 |
|------|----------|
| 完成一个 PR | "最后更新"日期、模块状态总览、已完成清单 |
| 开始新模块 | 模块状态总览（⬜ → 🟡）、进行中段落 |
| 遇到阻塞 | 进行中段落"阻塞项"、模块状态总览（🟡 → ❌） |
| 完成里程碑 | "当前里程碑"字段、"下一步"重排 |
| 发现风险 | 已知问题段落 |

### 2.5 反面教材

❌ 不允许的写法：
- "做了一些 Scanner 重构"（无具体内容）
- "进度大约 50%"（不可验证）
- "Trainer 应该快好了"（无明确日期）
- "@xxx 在做"（无具体任务清单）

✅ 正确的写法：
- "2026-05-19 完成 TrainConfig 定义，待集成进度回调"
- 列具体勾选清单
- 给具体日期或 milestone

---

## 3. CHANGELOG.md 模板与规则

### 3.1 文件位置

`CHANGELOG.md`（仓库根目录）

### 3.2 格式约定

采用 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 1.1.0 + 语义化版本 [SemVer](https://semver.org/lang/zh-CN/) 2.0.0。

### 3.3 文件结构

```markdown
# Changelog

本项目所有显著变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- (scanner) 支持自定义 output_dir 参数（PR #12）

### Changed
- (converter) `delete_source` 默认改为 `False`，破坏性变更（PR #14）

### Deprecated
- 旧版 `vals/` 目录名，将在 v2.0 移除

### Removed
- (utils) 删除 `site_detector.py`（PR #11）
- (core) 删除 `conversion_rule.py`（PR #11）

### Fixed
- (sampler) 修复 XML 类别不在 mapping.classes 时静默吞错（PR #13）

### Security
- 无

---

## [1.0.0] - 2026-05-13

### Added
- 初始重构基线
```

### 3.4 条目规则

| 项 | 规则 |
|----|------|
| 类型 | 必须是 `Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security` 之一 |
| 作用域 | 在描述前用 `(模块名)` 标注，如 `(scanner)`、`(api)`、`(docs)` |
| PR 引用 | 末尾标注 `(PR #编号)` |
| 破坏性变更 | 必须明确写"破坏性变更"，并在迁移说明中给出升级路径 |
| 中文/英文 | 描述用中文，模块名/技术词用英文 |

### 3.5 版本号规则

- 主版本（X.0.0）：破坏性 API 变更
- 次版本（X.Y.0）：向后兼容的新功能
- 修订版本（X.Y.Z）：向后兼容的 bug 修复

合并到 main 后由维护者从 `[Unreleased]` 切到具体版本号并打 git tag。

### 3.6 反面教材

❌ 不允许：
- `- 修了一些 bug`
- `- 更新 Scanner`
- `- 重构（无 PR 编号）`

✅ 正确：
- `- (sampler) 修复 mode='ratio' 且 total <= full_threshold 时未触发全抽 (PR #16)`
- `- (api) 新增 POST /api/scan 端点 (PR #20)`

---

## 4. 01-requirements.md 同步规则

### 4.1 什么时候必须同步

下列任一情况发生时，PR **必须**同时修改 `01-requirements.md`：

1. 新增 / 删除 / 重命名 dataclass 字段
2. 新增 / 删除 / 修改异常类
3. 新增 / 删除 / 修改错误码
4. 修改默认值
5. 修改文件产物路径或格式
6. 修改状态变更行为
7. 增加 / 减少模块

### 4.2 修改方式

- 直接编辑对应模块小节
- 文档头部"文档版本"字段加 1（v1.0 → v1.1）
- 在 PR 描述中专门写一节"文档同步"说明改了哪一节

### 4.3 反面教材

❌ 代码改了 `TrainConfig` 加了 `warmup_epochs` 字段，但 01-requirements.md 5.4.2 节没改
❌ 代码新增 `TrainOOMError`，但文档 5.4.6 节异常表没加

PR review 第一件事就是核对：「代码里改了什么，文档里有没有对应改」。

---

## 5. 三份文档的关系

```
代码改动
    │
    ├─→ CHANGELOG.md            （记录"发生了什么变更"，给用户看）
    │
    ├─→ CURRENT_STATE.md        （记录"现在到哪了"，给维护者看）
    │
    └─→ 01-requirements.md      （记录"系统是什么"，给接手者看）
```

| 关键差异 | CHANGELOG | CURRENT_STATE | requirements |
|----------|-----------|---------------|--------------|
| 时间维度 | 历史日志（append-only） | 当下快照（覆盖式） | 永远当前真理（覆盖式） |
| 读者 | 用户 + 维护者 | 维护者 | 新人 + 接手者 |
| 粒度 | 一个 PR 一条 | 一个里程碑一份 | 系统级 |
| 内容 | 行为变更 | 进度 + 风险 | 契约 + 输入输出 |

---

## 6. PR 检查清单（再次浓缩版）

提交 PR 前**全部**勾上：

- [ ] 代码本身：
  - [ ] `black .` 通过
  - [ ] `ruff check .` 通过
  - [ ] `mypy --strict core/ utils/` 通过
  - [ ] `pytest` 全部通过
  - [ ] 新增 public 函数有 Google docstring
  - [ ] 新增异常继承 `AutoLabelerError` 带 `code`
- [ ] 文档：
  - [ ] CURRENT_STATE.md 已更新（模块状态、已完成清单、最后更新日期）
  - [ ] CHANGELOG.md 已加条目（[Unreleased] 节下）
  - [ ] 01-requirements.md 已同步（如有契约变更）
  - [ ] 02-constraints.md 已更新（如有强制约束变更，需负责人审批）
- [ ] PR 描述：
  - [ ] 变更摘要
  - [ ] 影响模块列表
  - [ ] 测试方式
  - [ ] 验收清单已勾选
  - [ ] 破坏性变更已明确标注（如有）

---

## 7. 一个 PR 的完整生命周期示例

下面演示"完成 Sampler 重写"这个 PR 应该长什么样。

### 7.1 代码变更
```
core/sampler.py                     # 新写
tests/test_sampler.py               # 新写
examples/sampler_example.py         # 新写
gui/workers/sample_worker.py        # 适配新接口
api/routes/sample.py                # 新写
api/schemas/sample.py               # 新写
utils/exceptions.py                 # 加 SAMPLE_* 错误码
```

### 7.2 CHANGELOG.md
```markdown
## [Unreleased]

### Added
- (sampler) 重写 Sampler 模块，支持独立调用（PR #14）
- (sampler) 新增 `SampleStatistics.pre_labeled_count` 字段（PR #14）
- (api) 新增 POST /api/sample 端点（PR #14）

### Changed
- (sampler) 验证集目录名从 `vals/` 改为 `val/`，破坏性变更（PR #14）
- (sampler) 入口签名改为 `sample(config: SampleConfig)`（PR #14）
```

### 7.3 CURRENT_STATE.md 关键修改

```markdown
> 最后更新：2026-05-17           ← 改这里

## 2. 模块状态总览

| Sampler | ✅ 完成 | 78% | ✅ | - |   ← 从 🟡 改为 ✅

## 3. 已完成（本里程碑内）

- 2026-05-17 完成 Sampler 重写（PR #14）   ← 新增这行

## 4. 进行中

### 4.1 Trainer 重写                        ← 改为下一个
...
```

### 7.4 01-requirements.md 修改

需要修改的章节：
- `5.2.2` 输入字段（如改了默认值）
- `5.2.5` 输出 dataclass（如加了 `pre_labeled_count`）
- `5.2.7` 异常表（如加了新异常）
- 文档头部 `文档版本: v1.0` → `v1.1`

### 7.5 PR 描述

```markdown
## 变更摘要
完成 Sampler 模块按 02-constraints.md 第 5 节标准的重写，支持独立调用，
统一使用 SampleConfig dataclass。修复了 mode='ratio' 全抽边界 bug。

## 影响模块
- core/sampler.py（新写）
- utils/exceptions.py（加 SAMPLE_* 错误码）
- gui/workers/sample_worker.py（适配新接口）
- api/routes/sample.py（新写）

## 破坏性变更
- 验证集目录名 `vals/` → `val/`
- 入口签名从 `sample(folder, output, mode, count, ...)` 改为 `sample(config: SampleConfig)`

## 迁移说明
- 旧调用方需改用 `SampleConfig(...)` 包装参数
- 旧 `vals/` 目录如已存在，可手动重命名或重新抽样

## 测试方式
- 单元测试：`pytest tests/test_sampler.py -v` 全过（覆盖率 78%）
- 集成测试：`pytest tests/integration/test_scenario_a.py` 全过
- 手工：通过桌面 GUI 跑一次完整抽样

## 验收清单
- [x] black/ruff/mypy/pytest 全过
- [x] docstring 完整
- [x] CURRENT_STATE.md 已更新
- [x] CHANGELOG.md 已加条目
- [x] 01-requirements.md 已同步（v1.0 → v1.1）
- [x] 破坏性变更已标注
```

---

## 8. 初始化这三份文档

如果当前仓库还没有 CURRENT_STATE.md 或 CHANGELOG.md，**新建仓库后第一个 PR** 必须把这两份建好：

### 8.1 初始 CURRENT_STATE.md

复制本文档第 2.3 节的模板，把所有模块状态填为 ⬜（待开始）。

### 8.2 初始 CHANGELOG.md

```markdown
# Changelog

本项目所有显著变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 初始化重构基线
- 引入 docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/ 规范文档
```

---

## 9. 不写文档的代价

不更新文档的 PR **一定**被 reject。这不是态度问题，是工程问题：

- 三个月后没人记得为什么改了 `delete_source` 默认值
- 接手者读 `01-requirements.md` 发现写的是旧行为，照旧实现，引入新 bug
- 出 bug 时无法快速定位是哪个版本引入的

**写文档不是任务的"额外"，是任务本身。代码 + 测试 + 文档 = 一次完整交付。**
