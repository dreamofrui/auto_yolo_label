# AutoLabeler 重构强制约束规范

> 文档版本：v1.0
> 创建日期：2026-05-13
> 目标读者：负责重写本项目的开发者（默认无业务背景）
> 配套文档：`01-requirements.md`（需求规范），`03-progress-template.md`（进度维护）

---

## 0. 阅读须知

这是**强制约束**文档。这里写的每一条都是"违反就是错"，不是"建议"。

如果你认为某条约束有问题，**先停下来问负责人**，不要先做后说。

本文档不允许有任何例外，包括但不限于：「这个文件特殊」「这里只是临时方案」「这是别人写的我没改」。

本项目目标不大但**追求工程规范**。规范的价值是让另一个人接手时不需要猜任何东西。

---

## 1. 问题陈述（Problem Statement）

### 1.1 我们要给谁解决什么问题

| 用户类型 | 痛点 | 我们要做什么 |
|----------|------|--------------|
| **标注员**（不懂 ML） | 手工标注 100% 数据太慢 | 提供半自动流程：手标 10-20%，模型推理剩余 |
| **算法工程师** | 调参/对比需要反复跑推理 | 推理结果分时间戳保存，可对比；模块可独立调用 |
| **维护开发者** | 旧代码模块边界模糊，扩展困难 | 重写为解耦架构，桌面/Web 共用 core，所有契约显式 |

### 1.2 旧版本到底"坏"在哪（重写必须解决的具体问题）

下面列的每一条都是已知问题。重写完成后**必须**全部消除。

1. **强制顺序耦合**：必须先 `Scan` 才能 `Sample`/`Train`/`Infer`。用户即使已有 `mapping.json` 也走不通其他模块
2. **隐式状态读取**：`Sampler`、`Inferencer` 等模块各自直接 `json.load(mapping.json)`，绕过了 `MappingManager` 的并发锁
3. **模块边界不清**：`gui/workers/` 里有大量业务逻辑应该属于 `core/`
4. **命名混乱**：API 用 camelCase、Python 用 snake_case，两边没有自动转换，手工对齐易出 bug
5. **异常体系不统一**：部分裸 `raise Exception(...)`，API 层无法分类返回错误
6. **进度推送非标准**：每个 worker 自己定义信号格式，无法被 HTTP/SSE 复用
7. **任务取消能力缺失**：训练/推理一旦开始无法干净停止
8. **路径处理用字符串**：Windows 中文路径、长路径偶发问题
9. **配置非显式**：`TrainWorker` 把页面 cache 控件丢了没传到 `TrainConfig`
10. **破坏性默认行为**：`Converter.convert_folder()` 转完直接删 TXT，无 backup

### 1.3 新人最容易犯的错（写代码前先读一遍）

> 这一节是「不要做什么」的反面教材。每一条都对应一个真实的失败模式。

1. ❌ **在 `core/scanner.py` 里 `import fastapi`** —— 立刻不可移植
2. ❌ **认为"反正 Sampler 之前一定 Scan 过，直接读 mapping.json"** —— 解耦失败
3. ❌ **在 `core/` 模块里 `os.path.join("D:/", folder)`** —— 路径处理用字符串
4. ❌ **觉得"这个错误概率小，先 print 一下"** —— 没有错误码，无法返回 API
5. ❌ **训练 worker 里发个 PySide signal 报进度** —— 与 Web 无法共用
6. ❌ **`def scan(folder, out_dir=None, formats=None, validate=True, ...)`** —— 入参不是 dataclass
7. ❌ **看到 `inferred=True` 就跳过该图片** —— 破坏调参对比工作流
8. ❌ **`os.environ.get("AUTOLABEL_DATA")`** —— 隐式环境依赖
9. ❌ **写完功能不更新 `CURRENT_STATE.md` 和 `CHANGELOG.md`** —— 维护断层
10. ❌ **加新参数时往 dataclass 末尾塞，不写默认值** —— 破坏向后兼容

---

## 2. 方案描述（Solution）

### 2.1 重构核心三件事

```
1) 模块解耦：每个 core 模块独立可用，不假设其他模块跑过
2) 双调用方支持：同一个 core 模块同时被 PySide6 桌面和 FastAPI HTTP 调用
3) 显式契约：所有输入输出都是 dataclass，所有异常都有错误码
```

### 2.2 调用链总览

```
┌────────────────┐     ┌────────────────┐
│ gui/workers/   │     │ api/routes/    │
│ (PySide6)      │     │ (FastAPI)      │
└───────┬────────┘     └───────┬────────┘
        │                      │
        │ 直接 import          │ 直接 import
        ▼                      ▼
┌─────────────────────────────────────────┐
│ core/                                   │
│ Scanner / Sampler / Trainer / ...       │
│                                         │
│ 入口：核心类.方法名(config: XxxConfig)    │
│       -> XxxResult                      │
└────────────────────┬────────────────────┘
                     │ 依赖
                     ▼
┌─────────────────────────────────────────┐
│ utils/                                  │
│ MappingManager / TaskRegistry /         │
│ PathEncoder / Device / Exceptions / ... │
└─────────────────────────────────────────┘
```

桌面 worker 和 HTTP 路由是 core 的两类客户端，二者通过 `utils/task_registry.py:TaskRegistry` 单例共用任务状态。

### 2.3 典型解耦场景（必须能跑）

下面 4 个场景，**新版本必须每个都有自动化测试**：

| 场景 | 输入 | 调用顺序 |
|------|------|----------|
| **A. 完整流程** | 一个干净的站点目录 | Scan → Sample → 人工标注 → Train → Infer → Restore |
| **B. 跳过扫描** | 用户自己写好 mapping.json + 已抽好的 database | Train → Infer → Restore |
| **C. 跳过训练** | 别处拿到的 best.pt + 任意图片文件夹 | Infer（`image_source="custom"`） → Restore |
| **D. 纯格式转换** | 任意一个包含 YOLO TXT 的文件夹 | Converter.txt_to_xml |

### 2.4 模块入口统一形态

每个 core 模块**必须**遵循：

```python
# core/<module>.py
@dataclass
class XxxConfig:
    ...                                     # 仅 dataclass 字段，禁止方法

@dataclass
class XxxResult:
    ...

class XxxModule:                            # 例如 Scanner、Sampler
    def __init__(self,
                 mapping_manager: MappingManager | None = None,
                 task_handle: TaskHandle | None = None) -> None:
        """依赖注入：mapping 和 task 都可选，便于独立测试。"""

    def <verb>(self, config: XxxConfig) -> XxxResult:
        """单个公开入口方法，名字是动词。"""
```

公开入口方法：`Scanner.scan`、`Sampler.sample`、`Trainer.train`、`Inferencer.infer`、`LabelInspector.list_runs` / `get_run_tree` / `get_product_labels`、`Restorer.restore`、`Converter.txt_to_xml` / `xml_to_txt`、`LabelImgLauncher.validate` / `launch`。

### 2.5 任务模型

所有耗时 > 1 秒 的方法（Scan/Sample/Train/Infer/Restore/批量 Convert）**必须**：

1. 在调用前由调用方从 `TaskRegistry.create_task(task_type)` 拿一个 `TaskHandle`
2. 把 `task_handle` 通过 `Scanner(task_handle=handle)` 注入
3. core 模块在内部周期性更新 `handle.progress_current / total / message`
4. 调用方通过 `TaskRegistry.get(task_id)` 查询状态
5. 用户取消通过 `TaskRegistry.cancel(task_id)`；core 在循环里检查 `handle.is_cancel_requested`，干净退出

`TaskRegistry` 是进程内单例，元数据落 `~/.autolabeler/tasks/{task_id}.json`，进程重启时已运行任务状态置为 `interrupted`。

### 2.6 命名约定（强制）

| 边界 | 风格 | 示例 |
|------|------|------|
| Python 代码（变量、函数、模块文件） | `snake_case` | `mapping_path`、`scan_folder()` |
| Python 类 | `PascalCase` | `Scanner`、`ScanConfig` |
| 常量 | `UPPER_SNAKE` | `DEFAULT_BATCH_SIZE` |
| HTTP API JSON 字段 | `camelCase` | `mappingPath`、`siteFolder` |
| HTTP API URL 路径 | `kebab-case` | `/api/convert/yolo-to-voc` |
| 文件/目录名 | `snake_case` | `train_worker.py` |
| 错误码 | `UPPER_SNAKE` | `SCAN_LABEL_MISMATCH` |
| Git 分支 | `kebab-case` | `feature/decouple-sampler` |

**API 边界自动转换规则**：用 `pydantic v2 BaseModel` 的 `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)` 实现双向自动转换（Python snake_case ↔ JSON camelCase）。**禁止**任何模块手工写 `{"mappingPath": result.mapping_path}` 这种映射。

---

## 3. 技术约束（Tech Constraints）

### 3.1 运行环境

| 项 | 值 |
|----|----|
| Python | 3.11.14（conda 环境 `yolo_new`） |
| GPU 库 | CPU/GPU 双版本，本地开发用 CPU，部署服务器有 GPU |
| 操作系统 | Windows 10+（开发与生产），Linux（生产备选） |
| 路径 | **必须**兼容含中文、空格、长路径（> 260 字符）、UNC 路径 |

### 3.2 强制依赖（必须使用）

| 库 | 用途 | 版本要求 |
|----|------|----------|
| `PySide6` | 桌面 GUI | ≥ 6.5 |
| `PySide6-Fluent-Widgets` | 桌面组件 | ≥ 1.4 |
| `ultralytics` | YOLO 训练/推理 | ≥ 8.3 |
| `torch` | 张量运算 | ≥ 2.0 |
| `opencv-python` | 图像处理 | ≥ 4.7 |
| `Pillow` | 图像 IO | ≥ 9.0 |
| `pydantic` | API 数据模型 + 自动 camelCase 转换 | ≥ 2.0 |
| `fastapi` | HTTP 路由 | ≥ 0.110 |
| `uvicorn` | HTTP 服务器 | ≥ 0.27 |
| `loguru` | 统一日志 | ≥ 0.7 |
| `pytest` | 测试 | ≥ 8.0 |
| `black` | 格式化 | ≥ 24.0 |
| `mypy` | 类型检查 | ≥ 1.8 |
| `ruff` | linter | ≥ 0.4 |

### 3.3 允许引入的库

需要新增依赖时，先在 PR 描述里说明：
- 引入原因（不能被现有库替代）
- 体积影响（pip install 体积）
- License（必须是 MIT/Apache 2.0/BSD）

禁止引入：商业 License、AGPL、研究项目代码（无维护）。

### 3.4 代码规范

| 项 | 工具 | 通过门槛 |
|----|------|----------|
| 格式 | `black` | CI 强制 |
| Import 排序 | `ruff` | CI 强制 |
| Lint | `ruff` | 0 错误 |
| 类型检查 | `mypy --strict` 仅 `core/` 和 `utils/` | 0 错误 |
| 测试 | `pytest` | 全部通过 |
| 覆盖率 | `pytest --cov` | `core/` ≥ 70%，`utils/` ≥ 80% |
| docstring 风格 | Google 风格 | 所有 public 函数/类必有 |

### 3.5 命名与目录边界

- `core/<module>.py` 单文件 ≤ 600 行；超过必须拆分
- `gui/workers/<module>_worker.py` 仅做"接 UI 信号 → 调 core → 回报进度"，禁止业务逻辑
- `api/routes/<module>.py` 仅做"接 HTTP 请求 → 转 dataclass → 调 core → 包响应"，禁止业务逻辑
- `utils/` 内文件不允许 `import` `core/`（反向依赖）
- `core/` 内文件不允许 `import` `gui/` 或 `api/`（反向依赖）

### 3.6 日志规范

- 用 `loguru` 单例 logger（`utils/logging_setup.py` 初始化）
- 日志级别用法：
  - `DEBUG`：开发时排查，生产关闭
  - `INFO`：业务关键节点（"开始扫描"、"扫描完成 N 张"）
  - `WARNING`：可恢复异常（"找不到 classes.txt，使用默认"）
  - `ERROR`：抛异常前必记一次
  - `CRITICAL`：进程级故障
- **禁止** `print()`
- 中文消息用于用户展示，英文用于内部调试

### 3.7 测试规范

- 单元测试文件：`tests/test_<module>.py`，对应 `core/<module>.py`
- 每个模块至少覆盖：构造、典型输入、边界输入、每个异常类、取消
- 集成测试目录：`tests/integration/`，覆盖 2.3 节列出的 4 个场景
- HTTP API 测试：`tests/api/`，用 `fastapi.testclient.TestClient`
- 禁止依赖网络的测试；模型用最小 fixture（如 `yolov8n.pt` 缓存到 `tests/fixtures/`）

### 3.8 性能边界

不卡死性能，但**禁止**做出已知更慢的实现：

- 路径编码/解码不允许 O(N²) 实现
- mapping.json 读写必须有内存缓存（`MappingManager` 内部）
- 批量推理必须使用 ultralytics 的批处理接口，不要 for 循环单图
- 图片复制大批量时（> 1000 张）用 `shutil` 而非读写字节流

---

## 4. 不做清单（Non-Goals）

下面这些**在本期重构中不做**。即使你觉得"顺手做一下"也禁止：

### 4.1 不做的功能

- ❌ 内置 Web 标注器（先用 LabelImg）
- ❌ 用户认证 / 权限 / 多租户
- ❌ 引入数据库（sqlite/postgres/mongodb）
- ❌ 云端部署、对象存储、CDN
- ❌ 多机分布式训练
- ❌ 模型版本管理（多模型存档、A/B 测试）
- ❌ 主动学习 / 不确定度排序
- ❌ 自动超参搜索
- ❌ 多语言 i18n（仅中文）
- ❌ 用户级 settings.json 持久化（本期不做，但要在 LabelImg 模块预留 `~/.autolabeler/`）

### 4.2 不做的架构变更

- ❌ 不引入 DI 容器（如 `dependency-injector`）；用构造函数参数注入足够
- ❌ 不引入消息队列（Kafka/RabbitMQ）；进程内 `TaskRegistry` 够用
- ❌ 不引入微服务；core 是单进程库
- ❌ 不引入 ORM；mapping.json 不是数据库
- ❌ 不引入 GraphQL；REST + 异步任务足够

### 4.3 不做的"顺手优化"

- ❌ 不重写 YOLO 训练逻辑，仅薄包装 `ultralytics`
- ❌ 不优化 ultralytics 内部代码（出问题报上游 issue）
- ❌ 不实现新的目标检测算法
- ❌ 不引入新 GUI 框架（PySide6 保留）
- ❌ 不引入前端代码到本仓库（Next.js 在另一个仓库）

### 4.4 已确认删除的旧功能

| 模块 | 操作 | 原因 |
|------|------|------|
| `utils/site_detector.py` | 删除 | 与解耦目标冲突，未被核心流程使用 |
| `core/conversion_rule.py` | 删除 | 同上 |
| `config/A9950_conversion_rules.yaml` | 删除 | 同上 |
| GUI 设置页"保存"按钮的伪持久化 | 删除 | 本期不做真正持久化，UI 也不再误导用户 |
| 默认删除 TXT 的转换行为 | 改为默认保留 | 防止破坏数据 |

### 4.5 不允许的写代码姿势

- ❌ `from xxx import *`
- ❌ 全局可变状态（包括模块级 dict、单例的属性可变）
- ❌ 默认参数用可变对象（`def f(x=[])`）
- ❌ `try: ... except: pass` 无日志
- ❌ `print()`、`pprint()`
- ❌ Magic number 不带常量名（`epochs = 100` 可以，`if x > 47: ...` 不行）
- ❌ 注释掉的代码（直接删，git 里有历史）
- ❌ TODO 不带 issue 编号（`# TODO(#123): xxx` 可以，纯 `# TODO` 不行）

---

## 5. 成功标准（Success Criteria）

下面 10 条**全部**通过，才算重构完成。每一条都必须**有自动化验证**。

### 5.1 解耦验证（核心）

| # | 验收项 | 验证方式 |
|---|--------|----------|
| 1 | 任一 core 模块脱离其他模块独立可跑 | `tests/integration/test_scenario_*.py` 4 个场景全过 |
| 2 | `core/` 内零 GUI/HTTP 导入 | `tests/test_imports.py` 静态扫描 `import PySide6/PyQt/fastapi/flask` 无结果 |
| 3 | 同一 core 模块被桌面 worker 和 HTTP 路由同时调用 | 提供 `examples/scan_via_desktop.py` + `examples/scan_via_http.py` 跑通 |
| 4 | 跳过扫描可直接训练/推理 | 集成测试 scenario B/C 通过 |

### 5.2 契约验证

| # | 验收项 | 验证方式 |
|---|--------|----------|
| 5 | 所有 core 入口方法只接受单个 dataclass 参数 | `tests/test_contracts.py` 反射检查所有公开方法签名 |
| 6 | 所有异常继承 `AutoLabelerError` 带 `code` | `tests/test_exceptions.py` 反射所有 `raise` 站点 |
| 7 | API 边界 camelCase ↔ snake_case 自动转换 | `tests/api/test_naming.py` 验证请求/响应 JSON 字段格式 |

### 5.3 质量验证

| # | 验收项 | 验证方式 |
|---|--------|----------|
| 8 | `mypy --strict core/ utils/` 0 错误 | CI |
| 9 | `pytest --cov` 通过门槛（core ≥70%，utils ≥80%） | CI |
| 10 | 4 个集成场景全部通过 | CI |

### 5.4 验收清单（PR 合并前自检）

提交合并请求前，逐项打勾：

- [ ] 所有新增/修改的 public 函数有 Google 风格 docstring
- [ ] 所有新增/修改的 dataclass 字段有类型注解
- [ ] 所有新增/修改的异常继承 `AutoLabelerError` 带 `code`
- [ ] 新增的错误码已加到 `utils/exceptions.py` 的枚举
- [ ] 单元测试覆盖新增的成功路径 + 至少 1 个失败路径
- [ ] `black .` 和 `ruff check .` 通过
- [ ] `mypy --strict core/ utils/` 通过
- [ ] `pytest` 全部通过
- [ ] `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/01-requirements.md` 中相关模块描述已同步
- [ ] `CURRENT_STATE.md` 已更新进度
- [ ] `CHANGELOG.md` 已加条目
- [ ] PR 描述包含：变更摘要、影响模块、测试方式

---

## 6. 十条强制纪律（违反即拒绝合并）

> 这十条是上面所有内容的**最浓缩版**。任何 PR review 都会先核对这十条。

| # | 纪律 | 一句话解释 |
|---|------|------------|
| 1 | `core/` 禁止 import PySide6/PyQt/fastapi/flask/uvicorn | 一旦 import 即不可移植 |
| 2 | 模块入口只接受单个 dataclass 参数，禁止 `**kwargs` | 强制契约可见 |
| 3 | 禁止 `os.environ` / `os.getcwd()` / 全局可变 singleton | 杜绝隐式依赖 |
| 4 | 路径一律 `pathlib.Path`，禁止字符串拼路径 | Windows 中文路径必踩坑 |
| 5 | mapping.json 必须经 `MappingManager`，禁止裸 `json.load` | 并发安全 |
| 6 | 异常必须继承 `AutoLabelerError` 带 `code` 字段 | API 错误返回基础 |
| 7 | 公共函数必须 type hint + Google docstring | 接手成本 |
| 8 | API 边界 camelCase ↔ snake_case 必须自动转换 | 减少手抖 |
| 9 | 耗时 > 1 秒任务必须通过 `TaskHandle` | 桌面/Web 共用进度 |
| 10 | 不允许假设前置模块跑过 | 解耦的硬底线 |

---

## 7. 异常与错误码体系

### 7.1 基类设计

```python
# utils/exceptions.py
class AutoLabelerError(Exception):
    """所有业务异常的基类。"""

    code: str = "INTERNAL_ERROR"            # 子类必须覆盖
    retryable: bool = False

    def __init__(self,
                 message: str,
                 details: str | None = None,
                 retryable: bool | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if retryable is not None:
            self.retryable = retryable
```

### 7.2 模块异常组织

每个模块的异常定义在 **该模块同文件内**：

```python
# core/scanner.py
from utils.exceptions import AutoLabelerError

class ScanError(AutoLabelerError):
    """Scanner 模块异常基类。"""

class ScanPathNotFoundError(ScanError):
    code = "SCAN_PATH_NOT_FOUND"

class ScanLabelMismatchError(ScanError):
    code = "SCAN_LABEL_MISMATCH"
```

### 7.3 错误码枚举

`utils/exceptions.py` 维护**全部**错误码枚举，便于 API 层和前端共用：

```python
class ErrorCode(str, Enum):
    # 通用
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PATH_NOT_FOUND = "PATH_NOT_FOUND"
    # Scanner
    SCAN_PATH_NOT_FOUND = "SCAN_PATH_NOT_FOUND"
    SCAN_LABEL_MISMATCH = "SCAN_LABEL_MISMATCH"
    # ...每加一个异常类，同步加这里
```

### 7.4 API 层异常处理

```python
# api/main.py
@app.exception_handler(AutoLabelerError)
async def handle_app_error(request: Request, exc: AutoLabelerError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "retryable": exc.retryable,
            },
        },
    )
```

桌面端在 `gui/workers/<x>_worker.py` 的 slot 里 catch 同一基类，转 UI 提示。

---

## 8. 目录与文件命名底线

### 8.1 必须存在的顶层目录

```
core/        utils/        gui/        api/        tests/        docs/        examples/
```

### 8.2 单文件容量

| 类型 | 上限 |
|------|------|
| `core/<module>.py` | 600 行 |
| `gui/pages/<x>_page.py` | 800 行（含 Qt 布局代码） |
| `gui/workers/<x>_worker.py` | 200 行 |
| `api/routes/<x>.py` | 200 行 |
| `tests/test_*.py` | 不限 |

### 8.3 文件命名

- 模块文件：`snake_case.py`
- 类：`PascalCase`，类名与文件名对应（`scanner.py` 内主类 `Scanner`）
- 测试：`test_<module>.py`
- pydantic schema：`schemas/<module>.py`，类名 `<Verb><Module>Request` / `<Verb><Module>Response`

---

## 9. Git 工作流

### 9.1 分支命名

| 类型 | 格式 | 示例 |
|------|------|------|
| 功能 | `feature/<scope>-<short-desc>` | `feature/decouple-sampler` |
| 修复 | `fix/<scope>-<short-desc>` | `fix/converter-delete-source` |
| 重构 | `refactor/<scope>-<short-desc>` | `refactor/mapping-manager-lock` |
| 文档 | `docs/<scope>` | `docs/update-requirements` |

### 9.2 Commit Message

格式：`<type>(<scope>): <subject>`

| type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修 bug |
| `refactor` | 重构（不改外部行为） |
| `docs` | 文档 |
| `test` | 测试 |
| `chore` | 构建/依赖 |

示例：
- `feat(scanner): support custom output_dir`
- `fix(converter): default delete_source to False`
- `refactor(core): extract MappingManager from sampler`
- `docs(spec): clarify task model in section 2.5`

### 9.3 PR 模板

```markdown
## 变更摘要
（一段话）

## 影响模块
（列出 core/<x>、utils/<y>、gui/<z>）

## 测试方式
（描述如何手工验证 + 自动化测试列表）

## 验收清单
- [ ] 所有 public 函数有 docstring
- [ ] mypy/ruff/pytest 通过
- [ ] 文档已同步
- [ ] CURRENT_STATE.md 已更新
- [ ] CHANGELOG.md 已加条目
```

---

## 10. 启动新模块时的开发顺序

> 当你被分配重写某个模块时，**严格按下面顺序**做，不要跳步：

1. 读 `01-requirements.md` 中该模块的章节
2. 把该模块的 `XxxConfig` 和 `XxxResult` 写到 `core/<module>.py`
3. 把该模块的异常类（`XxxError` 基类 + 子类 + 错误码）写到同文件
4. 把异常的错误码加到 `utils/exceptions.py:ErrorCode` 枚举
5. 写 `tests/test_<module>.py`，至少包含：
   - 成功路径 1 个
   - 每个异常类的触发路径
   - 取消（如果是长任务）
6. 实现 `Xxx` 类的入口方法，让测试通过
7. 写 `examples/<module>_example.py` 演示最小用法
8. 写 `gui/workers/<module>_worker.py`（桌面 worker，调 core 推进度）
9. 写 `api/routes/<module>.py` 和 `api/schemas/<module>.py`
10. 跑 `mypy --strict`、`ruff check`、`pytest`、`pytest --cov`
11. 更新 `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/01-requirements.md`（如有偏差）
12. 更新 `CURRENT_STATE.md` 和 `CHANGELOG.md`
13. 提 PR，套用 9.3 模板

**不要**反过来：不要先写实现再补测试，不要先写 UI 再补 core，不要先写 API 再补 core。

---

## 11. 紧急豁免流程

如果你确实遇到本文档某条约束无法满足，**不要私自破例**。流程：

1. 在 PR 描述里专门列一节"约束豁免请求"
2. 说明：哪一条、为什么必须破例、影响范围、补救计划
3. 等负责人在 PR 上明确写"approve 豁免：xxx 条"
4. 在被豁免的代码处加 `# RULE_EXEMPTION(#PR编号): <一句话原因>` 注释

任何未走流程的破例都会被 reject。

---

## 12. 这份文档本身的维护

- 这份文档**也**在版本管理内，发现错误请提 PR 修
- 修订时在文档头部 `文档版本` 字段加 1（v1.0 → v1.1）
- 重大变更（如新增/删除一条强制纪律）必须经负责人审批
- 不允许通过聊天/邮件口头修改约束
