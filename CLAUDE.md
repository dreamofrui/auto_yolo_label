# CLAUDE.md

> 本文件每次会话自动注入到 context。**任何与本项目相关的工作开始前必须先读完本文件**。

---

## ⚠️ 0. REFACTOR ACTIVE（最高优先级，违反即返工）

**当前状态**：项目正在从「强制顺序的单体桌面应用」**完全重写**为「模块解耦、企业级、桌面优先 + CLI/Node 调用预留」的新版本。**所有现有代码已归档到 `legacy/`，仅供参考。不允许 copy-paste 整段实现。**

**2026-05-14 范围重置**：本期目标不是 Web 平台。FastAPI/HTTP 入口不再作为 M1/M2 主线验收目标；已有 `api/` 代码只作为候选/实验入口冻结参考。当前优先级是：

1. `core/` 业务能力稳定、测试扎实。
2. 共享运行层从 `api.services` 迁到中立命名空间，供 GUI 和未来 CLI 共用。
3. 后续提供面向 Node.js 子进程调用的薄 CLI/JSON 边界。
4. 桌面 GUI 接入新 core/runtime，形成可用本地工具。

### 0.1 必读规范文档（动手前全部读完）

| 文档 | 内容 | 何时读 |
|------|------|--------|
| `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/README.md` | 三份规范的阅读顺序索引 | 第一次进项目 |
| `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/01-requirements.md` | 8 大模块详细 I/O + 数据模型 + 异常表（注意 Web/API 部分已降级为未来扩展） | 实现任何模块前 |
| `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/02-constraints.md` | 5 角度强约束 + 10 条强制纪律 + Git 规范 | 完整通读，背下第 6 节十条 |
| `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/03-progress-template.md` | CURRENT_STATE / CHANGELOG / requirements 维护规则 | 提任何 PR 前 |
| `docs/dev/CURRENT_STATE.md` | 当前重构进度（哪个模块做完了、哪个在做） | **每次会话开头第一件事** |

### 0.2 十条强制纪律（违反即拒绝合并）

1. `core/` **禁止** import `PySide6 / PyQt / fastapi / flask / uvicorn`
2. 模块入口只接受单个 `@dataclass` 参数，**禁止** `**kwargs`
3. **禁止** `os.environ` / `os.getcwd()` / 全局可变 singleton
4. 路径一律 `pathlib.Path`，**禁止**字符串拼路径
5. `mapping.json` 必须经 `MappingManager`，**禁止**裸 `json.load`
6. 异常必须继承 `AutoLabelerError` 且带 `code` 字段
7. 公共函数必须 type hint + Google docstring
8. CLI/Node JSON 边界必须自动、集中转换；HTTP/API 边界本期冻结，不作为新增主线
9. 耗时 > 1 秒任务必须通过统一 `TaskHandle`
10. **不允许**假设前置模块跑过（解耦的硬底线）

### 0.3 每次新会话的第一动作（按顺序）

1. 读 `docs/dev/CURRENT_STATE.md`，确认当前里程碑和模块状态
2. 确认本次会话要做的模块/任务
3. 如果是实现新模块 → 调用 `Skill: superpowers:writing-plans` 制定计划
4. 如果是修 bug → 调用 `Skill: superpowers:systematic-debugging`
5. 如果是 review/完成判定 → 调用 `Skill: superpowers:verification-before-completion`
6. **任何**创作性工作前 → 调用 `Skill: superpowers:brainstorming`

### 0.4 模块开发的 13 步顺序（02-constraints.md 第 10 节浓缩）

```
1. 读 01-requirements.md 对应模块章节
2. 写 XxxConfig / XxxResult dataclass
3. 写异常类（XxxError 基类 + 子类 + 错误码）
4. 把错误码加到 utils/exceptions.py:ErrorCode 枚举
5. 写 tests/test_<module>.py（成功路径 + 每个异常 + 取消）
6. 实现 Xxx 类，让测试通过
7. 写必要 examples 或 CLI/JSON 调用样例
8. 写 gui/workers/<module>_worker.py 或中立 runtime/service 适配
9. 不再默认新增 api/routes 和 api/schemas；除非负责人明确恢复 Web/API 目标
10. 跑 mypy --strict / ruff / pytest / pytest --cov
11. 更新 01-requirements.md（如有偏差）
12. 更新 CURRENT_STATE.md 和 CHANGELOG.md
13. 按 02-constraints.md 第 9.3 PR 模板提 PR
```

### 0.5 不允许做的事

- ❌ 从 `legacy/` copy-paste 整段函数体到新代码
- ❌ 跳过 brainstorming/writing-plans 直接动手
- ❌ 声明"模块完成"前没跑完测试和 mypy
- ❌ 合并任何没更新 CURRENT_STATE / CHANGELOG / requirements 的 PR
- ❌ 把十条纪律当"建议"
- ❌ 私自变更 02-constraints.md 中的强制约束（需走第 11 节豁免流程）

### 0.6 何时停下来问负责人

- 01-requirements.md 描述与 legacy 实际行为有冲突
- 某条强制纪律实在做不到（走豁免流程）
- 准备引入新第三方依赖
- 对"用户要的到底是什么"有 1% 怀疑
- 跨会话失忆找不到接力点

---

## 1. Behavioral Guidelines（通用 LLM 行为约束）

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1.1 Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 1.2 Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 1.3 Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 1.4 Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## 2. Project Overview

**AutoLabeler** - YOLO 半自动图像标注工具。目标：用户手工标注 10-20% 样本，模型自动标注剩余。

**典型工作流（仅一种，每模块可独立使用）**：
```
Scan → Sample → Manual Label → Train → Infer → Restore → (optional) Convert to VOC
```

**核心价值**：模块解耦、桌面/Web 双调用、企业级规范。

---

## 3. Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.11.14（conda 环境 `yolo_new`） |
| GUI | PySide6 ≥ 6.5，PySide6-Fluent-Widgets ≥ 1.4 |
| Deep Learning | ultralytics ≥ 8.3，PyTorch ≥ 2.0（CPU 本地 / GPU 服务器） |
| Image | OpenCV ≥ 4.7，Pillow ≥ 9.0 |
| API | pydantic v2 ≥ 2.0，FastAPI ≥ 0.110，uvicorn ≥ 0.27 |
| Quality | mypy ≥ 1.8，ruff ≥ 0.4，black ≥ 24.0，pytest ≥ 8.0 |
| Logging | loguru ≥ 0.7 |

完整依赖列表见 `02-constraints.md` 第 3.2 / 3.3 节。

---

## 4. Setup & Installation

```bash
# 1. 激活 conda 环境
mamba.exe shell hook -s powershell | Out-String | Invoke-Expression
mamba activate yolo_new

# 2. 安装依赖（先检查再装）
pip show pyinstaller || pip install pyinstaller
pip install -r requirements.txt

# 3. 验证
D:/mniforge3/envs/yolo_new/python.exe main.py     # 启动桌面（M3 完成后可用）
pytest tests/ -v                                   # 跑测试
```

**开发要求**：说话前叫一声"睿少"；调用 superpowers 任何技能时，明确告知用户在用什么技能。

---

## 5. Target Project Structure（重写目标，当前 legacy/ 仍是旧版）

```
auto_yolo_label/
├── legacy/                # 旧代码（只读参考，禁止 copy-paste）
├── core/                  # 业务模块（零 GUI/HTTP 依赖）
│   ├── scanner.py / sampler.py / trainer.py / inferencer.py
│   ├── label_inspector.py / restorer.py / converter.py
│   └── labelimg_launcher.py
├── utils/                 # 基础设施
│   ├── mapping_manager.py / path_encoder.py / task_registry.py
│   ├── device.py / exceptions.py / logging_setup.py
├── gui/                   # PySide6 桌面（调用 core）
│   ├── pages/ / workers/ / widgets/
├── api/                   # FastAPI HTTP 入口（调用 core）
│   ├── main.py / routes/ / schemas/ / tasks.py
├── tests/                 # 单元 + 集成 + API 测试
├── examples/              # 每模块一个最小调用示例
└── docs/                  # 文档（含规范、用户、开发）
```

完整目录约定见 `01-requirements.md` 第 2.2 / 4 节。

---

## 6. Architecture（重写目标）

```
PySide6 桌面 GUI ────┐                ┌──── FastAPI HTTP 路由
                    │  直接 import   │
                    ▼                ▼
              ┌─────────────────────────┐
              │  core/ (零 GUI/HTTP)    │
              └────────────┬────────────┘
                           │
                  ┌────────▼────────┐
                  │  utils/ 基础设施 │
                  └─────────────────┘
```

详见 `01-requirements.md` 第 2 节，调用链与任务模型见 `02-constraints.md` 第 2 节。

---

## 7. Core Principles

### 7.1 包管理
```bash
pip show <package> || pip install <package>     # 装前先查
```

### 7.2 路径编码
```
Original:  AS_CV_PI_P/H4A238FDF04/IMG_001.jpg
Encoded:   AS_CV_PI_P__H4A238FDF04__IMG_001.jpg
```
- 编码只在抽样阶段做；还原阶段查 `mapping.json` 反向，**不允许**反向解析文件名
- 用 `PathEncoder.encode()` / `decode()`，禁止手工拼接

### 7.3 设备自动检测
```python
device: str = "auto"      # auto / cpu / "0" / "0,1" / mps
batch_size: int = -1      # -1 自动检测
```

### 7.4 测试策略
- 针对性测试：改了 `sampler.py` 就跑 `pytest tests/test_sampler.py -v`
- 全量测试：release 前 + CI 上跑

### 7.5 mapping.json 访问
- **永远**通过 `MappingManager`（双锁 RLock + 文件锁）
- **禁止**任何模块裸 `json.load("mapping.json")`

---

## 8. Common Commands

```bash
# 环境
mamba activate yolo_new

# 跑桌面（M3 完成后）
D:/mniforge3/envs/yolo_new/python.exe main.py

# 跑 HTTP 服务（M2 完成后）
D:/mniforge3/envs/yolo_new/python.exe -m uvicorn api.main:app --reload

# 格式 / lint / type / test
black .
ruff check .
mypy --strict core/ utils/
pytest tests/ -v
pytest --cov=core --cov=utils --cov-report=term-missing

# 构建（M1 后）
D:/mniforge3/envs/yolo_new/python.exe build.py
```

---

## 9. Quick References

| 资源 | 路径 |
|------|------|
| **重构需求规范** | `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/01-requirements.md` |
| **重构强制约束** | `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/02-constraints.md` |
| **进度文档维护规则** | `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/03-progress-template.md` |
| **当前进度** | `docs/dev/CURRENT_STATE.md` |
| **变更日志** | `CHANGELOG.md` |
| **旧 API 参考（仅参考）** | `docs/dev/API_REFERENCE_AUTO_YOLO_LABEL.md` |
| **旧代码（仅参考）** | `legacy/` |

---

## 10. Legacy Note

`legacy/` 目录是 2026-05-13 重构开始前的所有代码归档。**只读参考**：

- 允许：读架构、命名、流程示意
- 禁止：copy 整段实现到新代码
- 引用：PR 描述中如引用 legacy，必须写"参考 legacy/xxx.py:LineN，新实现已重写"

旧版 Feature History 不再维护；新版变更全部记录在 `CHANGELOG.md`。
