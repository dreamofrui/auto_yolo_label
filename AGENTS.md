# AGENTS.md

> Codex / agents 接手本项目时必须先读本文件。本文继承 `CLAUDE.md` 的项目规则，并把本次重构的执行纪律写成 agent 可直接遵守的清单。

---

## 0. REFACTOR ACTIVE

AutoLabeler 正在从「强制顺序的单体桌面应用」完全重写为「模块解耦、企业级、桌面 + Web 双调用」的新版本。

当前阶段的最高优先级：

1. 旧代码和旧资产统一归档到 `legacy/`，仅作只读参考。
2. 新代码必须重新实现，不允许从 `legacy/` copy-paste 整段函数体。
3. 所有开发必须遵守 `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/02-constraints.md`，尤其第 6 节十条强制纪律。
4. 每次交付必须同步 `docs/dev/CURRENT_STATE.md` 和 `CHANGELOG.md`；接口契约变化还必须同步 `01-requirements.md`。

---

## 1. 会话启动顺序

每次开始与本项目相关的工作，按顺序执行：

1. 读 `docs/dev/CURRENT_STATE.md`，确认当前里程碑、分支、下一步。
2. 读 `CLAUDE.md` 和本文件，确认项目规则。
3. 若是第一次接手或进入新阶段，读完整规范：
   - `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/README.md`
   - `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/01-requirements.md`
   - `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/02-constraints.md`
   - `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/03-progress-template.md`
4. 调用适用的 Superpowers 技能，并明确告诉负责人正在使用什么技能。
5. 动手前说明计划；有 1% 不确定就先问负责人。

---

## 2. 十条强制纪律

1. `core/` 禁止 import `PySide6` / `PyQt` / `fastapi` / `flask` / `uvicorn`。
2. 模块入口只接受单个 `@dataclass` 参数，禁止 `**kwargs`。
3. 禁止 `os.environ` / `os.getcwd()` / 全局可变 singleton。
4. 路径一律使用 `pathlib.Path`，禁止字符串拼路径。
5. `mapping.json` 必须经 `MappingManager`，禁止裸 `json.load`。
6. 异常必须继承 `AutoLabelerError`，并带 `code` 字段。
7. 公共函数必须有 type hint 和 Google 风格 docstring。
8. API 边界 camelCase 与 snake_case 必须通过 pydantic v2 自动转换。
9. 耗时超过 1 秒的任务必须通过统一 `TaskHandle`。
10. 不允许假设前置模块已经跑过。

这些纪律不是建议。违反即返工。

---

## 3. Legacy 规则

`legacy/` 是 2026-05-13 重构前的旧代码和旧资产归档。

允许：

- 阅读架构、命名、调用流程、文件产物示意。
- 在 PR 描述中引用，格式为：`参考 legacy/xxx.py:LineN，新实现已重写`。
- 开发确实需要旧资源时，先复制到新目录，再按新规范改造。

禁止：

- 修改 `legacy/` 内任何文件。
- 从 `legacy/` copy-paste 整段函数体到新代码。
- 把旧版命名风格、隐式状态、顺序耦合带进新实现。

---

## 4. 阶段工作流

### 阶段 0：归档

- 创建 `refactor/scaffold-v2` 分支。
- 用 `git mv` 把旧代码和旧资产移动到 `legacy/`，保留历史。
- 运行 `python scripts/check_disciplines.py`，预期机械纪律检查通过。
- 更新 `CURRENT_STATE.md` 和 `CHANGELOG.md`。
- 提交：`chore: archive legacy code to legacy/ for reference-only`。

### 阶段 1：架构摸底

时间盒不超过 4 小时。只做：

- 生成 `notes/legacy-map.md`，列旧模块主类和 public 方法签名。
- 画 worker 到 core 到 utils 的文字调用图。
- grep 隐藏耦合点：`json.load.*mapping`、`os.environ`、`os.getcwd`、全局变量。
- 生成 `notes/legacy-diff.md`，记录旧行为与 `01-requirements.md` 的差异。

禁止逐文件细读旧实现；禁止阅读超过 100 行的旧方法体；禁止改 `legacy/`。

### 阶段 2：从 0 实现

每个模块开始前调用 `superpowers:writing-plans`，实现时遵守 TDD：

1. 读 `01-requirements.md` 对应章节。
2. 写 `XxxConfig` / `XxxResult` dataclass。
3. 写异常类和错误码。
4. 先写测试，再写实现。
5. 写 examples、gui worker、api route/schema。
6. 跑 black、ruff、mypy、pytest、coverage。
7. 更新文档后再提 PR。

实现顺序：

1. `utils/exceptions.py`
2. `utils/logging_setup.py`
3. `utils/device.py`
4. `utils/path_encoder.py`
5. `utils/mapping_manager.py`
6. `utils/task_registry.py`
7. `core/scanner.py`
8. `core/sampler.py`
9. `core/converter.py`
10. `core/trainer.py`
11. `core/inferencer.py`
12. `core/label_inspector.py`
13. `core/restorer.py`
14. `core/labelimg_launcher.py`

---

## 5. 验证命令

常用验证：

```bash
python scripts/check_disciplines.py
black .
ruff check .
mypy --strict core/ utils/
pytest tests/ -v
pytest --cov=core --cov=utils --cov-report=term-missing
```

声明“完成”前必须调用 `superpowers:verification-before-completion`，并用真实命令输出作为依据。

---

## 6. 必须停下来问负责人

遇到下面任一情况，停止实现并问负责人：

1. `01-requirements.md` 与 `legacy/` 行为冲突。
2. 任一强制纪律做不到。
3. 阶段 1 架构摸底超过 4 小时。
4. 准备引入新第三方依赖。
5. 对用户真实意图有 1% 怀疑。
6. 跨会话找不到接力点。

---

## 7. 企业级编码底线

- 代码要有清晰边界：`core/` 不知道 GUI/HTTP，`utils/` 不反向依赖 `core/`。
- 契约要显式：输入输出 dataclass，异常错误码，路径类型统一。
- 失败要可诊断：禁止裸 `Exception`、禁止静默吞错、禁止 `print()`。
- 测试要覆盖风险：成功路径、失败路径、取消路径、集成场景。
- 文档要与代码同步：代码、测试、文档三者一起才算交付。
