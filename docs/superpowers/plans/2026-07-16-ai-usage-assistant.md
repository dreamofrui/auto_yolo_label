# AI Usage Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the right-rail AI preview with a chat-only, streaming project usage assistant that talks to Zhipu’s OpenAI-compatible free model by default, without driving forms or editing code.

**Architecture:** Keep business policy in `core/ai_assistant/`, transport in `utils/ai_client.py`, and desktop glue in `gui/` (panel + settings + worker). Config resolves as user settings → env/private file → built-in defaults. Sessions are per-`tool_id` and memory-only. No vendor SDKs and no new third-party dependencies.

**Tech Stack:** Python 3, stdlib `urllib`/`http.client` + JSON/SSE, PySide6 GUI, existing `TaskHandle`/`TaskWorker` patterns, pytest.

**Spec:** `docs/superpowers/specs/2026-07-16-ai-usage-assistant-design.md`

**Python for all commands:** `D:/miniforge3/envs/yolo_new/python.exe`

---

## File map

| Path | Responsibility |
|------|----------------|
| Create: `utils/ai_client.py` | OpenAI-compatible non-stream + SSE stream client |
| Create: `core/ai_assistant/__init__.py` | Public exports |
| Create: `core/ai_assistant/types.py` | Dataclasses: config, messages, stream events |
| Create: `core/ai_assistant/knowledge.py` | Built-in product knowledge + per-tool blurbs |
| Create: `core/ai_assistant/limits.py` | Local hard-limit intent checks |
| Create: `core/ai_assistant/session.py` | Per-tool in-memory sessions |
| Create: `core/ai_assistant/service.py` | Assemble prompts, orchestrate send/test helpers |
| Create: `core/ai_assistant/config.py` | Resolve config from settings/env/file/defaults |
| Create: `gui/ai_assistant_panel.py` | Right-rail chat widget (messages/input/send/clear/stop) |
| Create: `gui/workers/ai_chat_worker.py` | Background streaming chat worker |
| Create: `gui/ai_settings_store.py` | Load/save AI settings JSON beside tool defaults |
| Modify: `utils/exceptions.py` | Add AI error codes + exception classes |
| Modify: `gui/tool_page_chrome.py` | Build real chat panel instead of preview placeholder |
| Modify: `gui/workbench.py` | Settings AI section, wire panel config, tool context |
| Modify: `gui/sample_page.py` (and any page calling `build_ai_assistant_panel`) only if signature changes require it — prefer keeping call site compatible |
| Create: `tests/test_ai_client.py` | HTTP/SSE client unit tests with mocks |
| Create: `tests/test_ai_assistant_core.py` | Knowledge/limits/session/service tests |
| Create: `tests/test_ai_settings_store.py` | Config resolve + persistence tests |
| Create: `tests/test_ai_chat_worker.py` | Worker lifecycle tests |
| Modify: `tests/test_exceptions.py` | Expect new AI error codes |
| Modify: `tests/test_gui_shell.py` | Lightweight GUI assertions for chat panel + settings fields |
| Modify: `docs/dev/PRODUCT_SPEC.md` | Product behavior for assistant |
| Modify: `docs/dev/UI_SPEC.md` | Right-rail chat + settings AI section |
| Modify: `docs/dev/ONBOARDING_SUMMARY.md` | Short module ownership pointer |
| Modify: `CHANGELOG.md` | Notable product/GUI entry |
| Optional ignore: `.gitignore` | Ensure private key file patterns if needed |

Do **not** edit `legacy/`. Do **not** add `openai`/`requests` dependencies.

---

### Task 1: AI error codes and exceptions

**Files:**
- Modify: `utils/exceptions.py`
- Modify: `tests/test_exceptions.py`

- [ ] **Step 1: Write the failing assertion for new codes**

In `tests/test_exceptions.py`, extend `expected` in `test_error_code_enum_covers_core_domains` with:

```python
        "AI_DISABLED",
        "AI_CONFIG_MISSING",
        "AI_UNAUTHORIZED",
        "AI_HTTP_ERROR",
        "AI_NETWORK_ERROR",
        "AI_TIMEOUT",
        "AI_BAD_RESPONSE",
        "AI_CANCELLED",
        "AI_REFUSED",
        "AI_VALIDATION_ERROR",
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_exceptions.py::test_error_code_enum_covers_core_domains -v
```

Expected: FAIL because codes are missing from `ErrorCode`.

- [ ] **Step 3: Add codes and exceptions**

In `utils/exceptions.py` `ErrorCode`, append:

```python
    AI_DISABLED = "AI_DISABLED"
    AI_CONFIG_MISSING = "AI_CONFIG_MISSING"
    AI_UNAUTHORIZED = "AI_UNAUTHORIZED"
    AI_HTTP_ERROR = "AI_HTTP_ERROR"
    AI_NETWORK_ERROR = "AI_NETWORK_ERROR"
    AI_TIMEOUT = "AI_TIMEOUT"
    AI_BAD_RESPONSE = "AI_BAD_RESPONSE"
    AI_CANCELLED = "AI_CANCELLED"
    AI_REFUSED = "AI_REFUSED"
    AI_VALIDATION_ERROR = "AI_VALIDATION_ERROR"
```

Add exception classes near other domain errors:

```python
class AIAssistantError(AutoLabelerError):
    """Base class for AI assistant failures."""

    code = ErrorCode.INTERNAL_ERROR
    retryable = False


class AIDisabledError(AIAssistantError):
    code = ErrorCode.AI_DISABLED


class AIConfigMissingError(AIAssistantError):
    code = ErrorCode.AI_CONFIG_MISSING


class AIUnauthorizedError(AIAssistantError):
    code = ErrorCode.AI_UNAUTHORIZED
    retryable = False


class AIHttpError(AIAssistantError):
    code = ErrorCode.AI_HTTP_ERROR
    retryable = True


class AINetworkError(AIAssistantError):
    code = ErrorCode.AI_NETWORK_ERROR
    retryable = True


class AITimeoutError(AIAssistantError):
    code = ErrorCode.AI_TIMEOUT
    retryable = True


class AIBadResponseError(AIAssistantError):
    code = ErrorCode.AI_BAD_RESPONSE


class AICancelledError(AIAssistantError):
    code = ErrorCode.AI_CANCELLED


class AIRefusedError(AIAssistantError):
    code = ErrorCode.AI_REFUSED


class AIValidationError(AIAssistantError):
    code = ErrorCode.AI_VALIDATION_ERROR
```

- [ ] **Step 4: Run test to verify it passes**

```bash
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_exceptions.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add utils/exceptions.py tests/test_exceptions.py
git commit -m "feat(ai): add assistant error codes"
```

---

### Task 2: OpenAI-compatible HTTP client (`utils`)

**Files:**
- Create: `utils/ai_client.py`
- Create: `tests/test_ai_client.py`

- [ ] **Step 1: Write failing client tests**

Create `tests/test_ai_client.py`:

```python
"""Unit tests for OpenAI-compatible AI HTTP client."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest

from utils import ai_client
from utils.exceptions import (
    AIBadResponseError,
    AICancelledError,
    AIHttpError,
    AITimeoutError,
    AIUnauthorizedError,
)


class _FakeResponse:
    def __init__(self, status: int, body: bytes, headers: dict[str, str] | None = None):
        self.status = status
        self._fp = io.BytesIO(body)
        self.headers = headers or {"Content-Type": "application/json"}

    def read(self, amt: int | None = None) -> bytes:
        return self._fp.read() if amt is None else self._fp.read(amt)

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_chat_completion_success(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "choices": [{"message": {"role": "assistant", "content": "hello"}}]
    }
    body = json.dumps(payload).encode("utf-8")

    def fake_urlopen(req: Any, timeout: float | None = None):
        assert req.get_method() == "POST"
        assert "Authorization" in dict(req.header_items()) or req.headers.get("Authorization")
        return _FakeResponse(200, body)

    monkeypatch.setattr(ai_client, "urlopen", fake_urlopen)
    text = ai_client.chat_completion(
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        api_key="k",
        model="glm-4.7-flash",
        messages=[{"role": "user", "content": "hi"}],
        timeout_seconds=5,
    )
    assert text == "hello"


def test_chat_completion_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    from urllib.error import HTTPError

    def fake_urlopen(req: Any, timeout: float | None = None):
        raise HTTPError(
            url="https://example/chat/completions",
            code=401,
            msg="no",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"bad key"}'),
        )

    monkeypatch.setattr(ai_client, "urlopen", fake_urlopen)
    with pytest.raises(AIUnauthorizedError):
        ai_client.chat_completion(
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            api_key="bad",
            model="glm-4.7-flash",
            messages=[{"role": "user", "content": "hi"}],
            timeout_seconds=5,
        )


def test_stream_yields_deltas_and_stops_on_done(monkeypatch: pytest.MonkeyPatch) -> None:
    sse = (
        b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
        b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
        b"data: [DONE]\n\n"
    )

    def fake_urlopen(req: Any, timeout: float | None = None):
        return _FakeResponse(200, sse, {"Content-Type": "text/event-stream"})

    monkeypatch.setattr(ai_client, "urlopen", fake_urlopen)
    chunks = list(
        ai_client.iter_chat_completion_stream(
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            api_key="k",
            model="glm-4.7-flash",
            messages=[{"role": "user", "content": "hi"}],
            timeout_seconds=5,
        )
    )
    assert chunks == ["Hel", "lo"]


def test_stream_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    sse = (
        b'data: {"choices":[{"delta":{"content":"A"}}]}\n\n'
        b'data: {"choices":[{"delta":{"content":"B"}}]}\n\n'
        b"data: [DONE]\n\n"
    )

    def fake_urlopen(req: Any, timeout: float | None = None):
        return _FakeResponse(200, sse, {"Content-Type": "text/event-stream"})

    monkeypatch.setattr(ai_client, "urlopen", fake_urlopen)
    state = {"n": 0}

    def should_cancel() -> bool:
        state["n"] += 1
        return state["n"] > 1

    with pytest.raises(AICancelledError):
        list(
            ai_client.iter_chat_completion_stream(
                base_url="https://open.bigmodel.cn/api/paas/v4/",
                api_key="k",
                model="glm-4.7-flash",
                messages=[{"role": "user", "content": "hi"}],
                timeout_seconds=5,
                should_cancel=should_cancel,
            )
        )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_ai_client.py -v
```

Expected: FAIL with import error for `utils.ai_client`.

- [ ] **Step 3: Implement `utils/ai_client.py`**

```python
"""OpenAI-compatible chat client using stdlib only."""

from __future__ import annotations

import json
import socket
from collections.abc import Callable, Iterator
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from utils.exceptions import (
    AIBadResponseError,
    AICancelledError,
    AIHttpError,
    AINetworkError,
    AITimeoutError,
    AIUnauthorizedError,
)


def _join_chat_url(base_url: str) -> str:
    base = base_url.rstrip("/") + "/"
    if base.endswith("/chat/completions/"):
        return base.rstrip("/")
    return base + "chat/completions"


def _auth_headers(api_key: str, stream: bool) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if stream:
        headers["Accept"] = "text/event-stream"
    return headers


def _raise_http(exc: HTTPError) -> None:
    body = ""
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        body = str(exc)
    if exc.code in (401, 403):
        raise AIUnauthorizedError("AI 鉴权失败，请检查 API Key。", details=body) from exc
    raise AIHttpError(f"AI 服务返回 HTTP {exc.code}。", details=body) from exc


def chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: int = 60,
) -> str:
    """Non-stream chat completion; returns assistant text."""
    url = _join_chat_url(base_url)
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=_auth_headers(api_key, stream=False), method="POST")
    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        _raise_http(exc)
    except TimeoutError as exc:
        raise AITimeoutError("AI 请求超时。", details=str(exc)) from exc
    except socket.timeout as exc:
        raise AITimeoutError("AI 请求超时。", details=str(exc)) from exc
    except URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        if "timed out" in reason.lower():
            raise AITimeoutError("AI 请求超时。", details=reason) from exc
        raise AINetworkError("AI 网络错误。", details=reason) from exc

    try:
        parsed: dict[str, Any] = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
    except Exception as exc:
        raise AIBadResponseError("AI 响应无法解析。", details=raw[:500]) from exc
    if not isinstance(content, str):
        raise AIBadResponseError("AI 响应内容为空或类型错误。", details=raw[:500])
    return content


def iter_chat_completion_stream(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: int = 60,
    should_cancel: Callable[[], bool] | None = None,
) -> Iterator[str]:
    """Yield text deltas from an OpenAI-compatible SSE stream."""
    url = _join_chat_url(base_url)
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=_auth_headers(api_key, stream=True), method="POST")
    try:
        resp = urlopen(req, timeout=timeout_seconds)
    except HTTPError as exc:
        _raise_http(exc)
    except TimeoutError as exc:
        raise AITimeoutError("AI 请求超时。", details=str(exc)) from exc
    except socket.timeout as exc:
        raise AITimeoutError("AI 请求超时。", details=str(exc)) from exc
    except URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        if "timed out" in reason.lower():
            raise AITimeoutError("AI 请求超时。", details=reason) from exc
        raise AINetworkError("AI 网络错误。", details=reason) from exc

    with resp:
        buffer = ""
        while True:
            if should_cancel is not None and should_cancel():
                raise AICancelledError("AI 生成已取消。")
            chunk = resp.read(256)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    return
                try:
                    parsed = json.loads(data_str)
                    delta = parsed["choices"][0].get("delta") or {}
                    content = delta.get("content")
                except Exception as exc:
                    raise AIBadResponseError("AI 流式响应无法解析。", details=data_str[:500]) from exc
                if isinstance(content, str) and content:
                    yield content
```

- [ ] **Step 4: Run client tests**

```bash
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_ai_client.py -v
```

Expected: PASS  
If `Request.header_items` assertion is awkward on this Python/urllib version, simplify the auth assertion to only check URL/method and keep unauthorized/stream tests as the main coverage.

- [ ] **Step 5: Commit**

```bash
git add utils/ai_client.py tests/test_ai_client.py
git commit -m "feat(ai): add stdlib OpenAI-compatible client"
```

---

### Task 3: Core types, knowledge, limits, sessions, config, service

**Files:**
- Create: `core/ai_assistant/__init__.py`
- Create: `core/ai_assistant/types.py`
- Create: `core/ai_assistant/knowledge.py`
- Create: `core/ai_assistant/limits.py`
- Create: `core/ai_assistant/session.py`
- Create: `core/ai_assistant/config.py`
- Create: `core/ai_assistant/service.py`
- Create: `tests/test_ai_assistant_core.py`
- Create: `tests/test_ai_settings_store.py` (config resolve parts can live here or in core tests; keep resolve tests with config module)

- [ ] **Step 1: Write failing core tests**

Create `tests/test_ai_assistant_core.py`:

```python
"""Core AI assistant policy and session tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.ai_assistant.config import resolve_assistant_config
from core.ai_assistant.limits import check_user_message_allowed
from core.ai_assistant.service import AIAssistantService
from core.ai_assistant.session import SessionStore
from core.ai_assistant.types import AssistantConfig, ChatMessage
from utils.exceptions import AIRefusedError, AIValidationError


def test_sessions_are_isolated_by_tool() -> None:
    store = SessionStore()
    store.append("sample", ChatMessage(role="user", content="u1"))
    store.append("train", ChatMessage(role="user", content="u2"))
    assert [m.content for m in store.get("sample")] == ["u1"]
    assert [m.content for m in store.get("train")] == ["u2"]
    store.clear("sample")
    assert store.get("sample") == []
    assert [m.content for m in store.get("train")] == ["u2"]


def test_hard_limit_refuses_fill_form_requests() -> None:
    with pytest.raises(AIRefusedError):
        check_user_message_allowed("请直接帮我填写站点路径和类别名")


def test_validation_rejects_empty_and_too_long() -> None:
    svc = AIAssistantService()
    cfg = AssistantConfig(
        enabled=True,
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        api_key="k",
        model="glm-4.7-flash",
    )
    with pytest.raises(AIValidationError):
        svc.build_model_messages(cfg, tool_id="sample", tool_title="抽样", user_text="  ")
    with pytest.raises(AIValidationError):
        svc.build_model_messages(cfg, tool_id="sample", tool_title="抽样", user_text="x" * 2001)


def test_system_prompt_includes_tool_and_boundaries() -> None:
    svc = AIAssistantService()
    cfg = AssistantConfig(
        enabled=True,
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        api_key="k",
        model="glm-4.7-flash",
    )
    messages = svc.build_model_messages(
        cfg,
        tool_id="sample",
        tool_title="抽样",
        user_text="这个工具怎么用？",
    )
    assert messages[0]["role"] == "system"
    system = messages[0]["content"]
    assert "抽样" in system
    assert "不能" in system or "禁止" in system
    assert messages[-1] == {"role": "user", "content": "这个工具怎么用？"}


def test_resolve_config_priority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTO_YOLO_AI_API_KEY", raising=False)
    monkeypatch.delenv("AUTO_YOLO_AI_BASE_URL", raising=False)
    monkeypatch.delenv("AUTO_YOLO_AI_MODEL", raising=False)
    key_file = tmp_path / "ai_api_key.txt"
    key_file.write_text("file-key\n", encoding="utf-8")
    cfg = resolve_assistant_config(
        user_settings={"enabled": True, "base_url": "", "api_key": "", "model": ""},
        env=os.environ,
        key_file_path=key_file,
    )
    assert cfg.api_key == "file-key"
    assert cfg.model == "glm-4.7-flash"
    assert "bigmodel.cn" in cfg.base_url

    monkeypatch.setenv("AUTO_YOLO_AI_API_KEY", "env-key")
    cfg2 = resolve_assistant_config(
        user_settings={"enabled": True, "base_url": "", "api_key": "", "model": ""},
        env=os.environ,
        key_file_path=key_file,
    )
    assert cfg2.api_key == "env-key"

    cfg3 = resolve_assistant_config(
        user_settings={
            "enabled": True,
            "base_url": "https://example.com/v1/",
            "api_key": "user-key",
            "model": "custom-model",
        },
        env=os.environ,
        key_file_path=key_file,
    )
    assert cfg3.api_key == "user-key"
    assert cfg3.model == "custom-model"
    assert cfg3.base_url == "https://example.com/v1/"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_ai_assistant_core.py -v
```

Expected: FAIL on missing module.

- [ ] **Step 3: Implement core package**

`core/ai_assistant/types.py`:

```python
"""Typed models for the AI usage assistant."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str


@dataclass(frozen=True)
class AssistantConfig:
    enabled: bool
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 60
    max_input_chars: int = 2000
    max_history_messages: int = 20
    max_output_chars: int = 8000


@dataclass
class ChatStreamEvent:
    kind: str  # delta | error | finished | cancelled
    text: str = ""
    code: str | None = None
```

`core/ai_assistant/knowledge.py`:

```python
"""Built-in condensed product knowledge for the usage assistant."""

from __future__ import annotations

PRODUCT_OVERVIEW = """
你是桌面应用「YOLO 自动打标工具」的使用助手。
产品定位：桌面优先 GUI；帮助用户完成站点扫描、抽样、LabelImg、训练、推理、检查、还原、转换等流程。
你只能聊天解释用法与限制，不能改代码、不能调用底层接口、不能替用户填写表单或路径。
""".strip()

TOOL_BLURBS: dict[str, str] = {
    "home": "首页：查看模块入口与整体工作流。",
    "scan": "扫描：校验站点目录结构并生成 mapping.json。",
    "sample": "抽样：按策略从站点抽样，生成 YOLO 数据集目录。",
    "labelimg": "LabelImg：校验/启动标注环境（受安全开关约束）。",
    "train": "训练：基于 data.yaml 与基础模型启动训练任务。",
    "infer": "推理：加载模型对图片目录推理并写出结果。",
    "inspect": "检查：浏览推理 run 与标签质量。",
    "restore": "还原：把标注结果还原回站点结构。",
    "convert": "转换：XML/YOLO 等格式转换。",
    "history": "历史：查看任务历史与状态。",
    "settings": "设置：工具默认参数与 AI 助手配置。",
}

HARD_RULES = """
硬性规则：
1. 不要声称可以修改用户代码、项目文件或底层 API。
2. 不要替用户给出“可直接粘贴进表单的最终业务参数”作为代填；可解释参数含义与合法范围。
3. 不要引导用户执行危险系统命令。
4. 若问题超出内置产品知识，要明确不确定，不要编造不存在的功能。
5. 回答使用简洁中文，面向桌面操作者。
""".strip()


def tool_blurb(tool_id: str, tool_title: str) -> str:
    base = TOOL_BLURBS.get(tool_id, f"当前工具：{tool_title or tool_id}。")
    return f"当前页面 tool_id={tool_id}，标题={tool_title}。{base}"


def build_system_prompt(tool_id: str, tool_title: str) -> str:
    return "\n\n".join(
        [
            PRODUCT_OVERVIEW,
            HARD_RULES,
            tool_blurb(tool_id, tool_title),
            "平台默认模型为智谱 glm-4.7-flash（OpenAI 兼容）。免费额度以服务商为准。",
        ]
    )
```

`core/ai_assistant/limits.py`:

```python
"""Local hard-limit checks for the usage assistant."""

from __future__ import annotations

import re

from utils.exceptions import AIRefusedError

_REFUSAL_PATTERNS = (
    r"帮我填",
    r"直接填[写入]?",
    r"代填",
    r"自动填",
    r"改(代码|源码|底层|接口)",
    r"修改(代码|源码|接口)",
    r"调用(底层|内部)接口",
    r"执行(命令|cmd|powershell|shell)",
    r"运行命令",
    r"write file|edit code|call internal api",
)


def check_user_message_allowed(text: str) -> None:
    """Raise AIRefusedError when the user asks for disallowed automation."""
    normalized = text.strip().lower()
    for pattern in _REFUSAL_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            raise AIRefusedError(
                "我只能解答本工具的用法与限制，不能代填表单、改代码或执行命令。"
                "请说明你想了解哪个参数的含义或流程步骤。"
            )
```

`core/ai_assistant/session.py`:

```python
"""In-memory per-tool chat sessions."""

from __future__ import annotations

from core.ai_assistant.types import ChatMessage


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, list[ChatMessage]] = {}

    def get(self, tool_id: str) -> list[ChatMessage]:
        return list(self._sessions.get(tool_id, []))

    def append(self, tool_id: str, message: ChatMessage) -> None:
        self._sessions.setdefault(tool_id, []).append(message)

    def clear(self, tool_id: str) -> None:
        self._sessions[tool_id] = []

    def replace(self, tool_id: str, messages: list[ChatMessage]) -> None:
        self._sessions[tool_id] = list(messages)
```

`core/ai_assistant/config.py`:

```python
"""Resolve AI assistant configuration from settings/env/file/defaults."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from core.ai_assistant.types import AssistantConfig

DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
DEFAULT_MODEL = "glm-4.7-flash"
DEFAULT_KEY_PLACEHOLDER = ""  # real key via env/file/user settings only


def default_key_file_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "auto_yolo_label" / "ai_api_key.txt"
    return Path.home() / ".auto_yolo_label" / "ai_api_key.txt"


def _read_key_file(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    except OSError:
        return ""


def resolve_assistant_config(
    *,
    user_settings: Mapping[str, object] | None = None,
    env: Mapping[str, str] | None = None,
    key_file_path: Path | None = None,
) -> AssistantConfig:
    user_settings = dict(user_settings or {})
    env = env or os.environ
    if key_file_path is None:
        key_file_path = default_key_file_path()

    enabled_raw = user_settings.get("enabled", True)
    enabled = bool(enabled_raw) if not isinstance(enabled_raw, str) else enabled_raw.lower() in {"1", "true", "yes"}

    user_base = str(user_settings.get("base_url") or "").strip()
    user_key = str(user_settings.get("api_key") or "").strip()
    user_model = str(user_settings.get("model") or "").strip()

    env_base = str(env.get("AUTO_YOLO_AI_BASE_URL") or "").strip()
    env_key = str(env.get("AUTO_YOLO_AI_API_KEY") or "").strip()
    env_model = str(env.get("AUTO_YOLO_AI_MODEL") or "").strip()
    file_key = _read_key_file(key_file_path)

    base_url = user_base or env_base or DEFAULT_BASE_URL
    api_key = user_key or env_key or file_key or DEFAULT_KEY_PLACEHOLDER
    model = user_model or env_model or DEFAULT_MODEL

    return AssistantConfig(
        enabled=enabled,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
```

`core/ai_assistant/service.py`:

```python
"""Assistant orchestration: validation, refusal, prompt assembly, history."""

from __future__ import annotations

from core.ai_assistant.knowledge import build_system_prompt
from core.ai_assistant.limits import check_user_message_allowed
from core.ai_assistant.session import SessionStore
from core.ai_assistant.types import AssistantConfig, ChatMessage
from utils.exceptions import (
    AIConfigMissingError,
    AIDisabledError,
    AIValidationError,
)


class AIAssistantService:
    def __init__(self, sessions: SessionStore | None = None) -> None:
        self.sessions = sessions or SessionStore()

    def ensure_ready(self, config: AssistantConfig) -> None:
        if not config.enabled:
            raise AIDisabledError("AI 助手已关闭。请在设置中启用。")
        if not config.api_key.strip():
            raise AIConfigMissingError("未配置 API Key。请在设置中填写，或配置环境变量 AUTO_YOLO_AI_API_KEY。")
        if not config.base_url.strip() or not config.model.strip():
            raise AIConfigMissingError("AI Base URL 或模型名为空。")

    def build_model_messages(
        self,
        config: AssistantConfig,
        *,
        tool_id: str,
        tool_title: str,
        user_text: str,
    ) -> list[dict[str, str]]:
        text = user_text.strip()
        if not text:
            raise AIValidationError("请输入要咨询的问题。")
        if len(text) > config.max_input_chars:
            raise AIValidationError(f"输入过长（>{config.max_input_chars} 字符）。")
        check_user_message_allowed(text)
        self.ensure_ready(config)

        history = self.sessions.get(tool_id)[-config.max_history_messages :]
        messages: list[dict[str, str]] = [
            {"role": "system", "content": build_system_prompt(tool_id, tool_title)}
        ]
        for item in history:
            messages.append({"role": item.role, "content": item.content})
        messages.append({"role": "user", "content": text})
        return messages

    def commit_turn(self, tool_id: str, user_text: str, assistant_text: str) -> None:
        self.sessions.append(tool_id, ChatMessage(role="user", content=user_text.strip()))
        self.sessions.append(tool_id, ChatMessage(role="assistant", content=assistant_text))

    def clear(self, tool_id: str) -> None:
        self.sessions.clear(tool_id)
```

`core/ai_assistant/__init__.py`:

```python
"""AI usage assistant core package."""

from core.ai_assistant.config import default_key_file_path, resolve_assistant_config
from core.ai_assistant.service import AIAssistantService
from core.ai_assistant.session import SessionStore
from core.ai_assistant.types import AssistantConfig, ChatMessage, ChatStreamEvent

__all__ = [
    "AIAssistantService",
    "AssistantConfig",
    "ChatMessage",
    "ChatStreamEvent",
    "SessionStore",
    "default_key_file_path",
    "resolve_assistant_config",
]
```

- [ ] **Step 4: Run core tests**

```bash
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_ai_assistant_core.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/ai_assistant tests/test_ai_assistant_core.py
git commit -m "feat(ai): add assistant core policy and sessions"
```

---

### Task 4: AI settings store (GUI-adjacent persistence)

**Files:**
- Create: `gui/ai_settings_store.py`
- Create: `tests/test_ai_settings_store.py`

- [ ] **Step 1: Write failing store tests**

```python
"""Tests for AI settings persistence."""

from __future__ import annotations

from pathlib import Path

from gui.ai_settings_store import AISettings, load_ai_settings, save_ai_settings


def test_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "ai_settings.json"
    saved = save_ai_settings(
        AISettings(
            enabled=True,
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            api_key="secret",
            model="glm-4.7-flash",
        ),
        path,
    )
    assert saved == path
    loaded = load_ai_settings(path)
    assert loaded.api_key == "secret"
    assert loaded.model == "glm-4.7-flash"


def test_missing_file_returns_defaults(tmp_path: Path) -> None:
    loaded = load_ai_settings(tmp_path / "missing.json")
    assert loaded.enabled is True
    assert loaded.api_key == ""
    assert "bigmodel.cn" in loaded.base_url
```

- [ ] **Step 2: Run to verify fail**

```bash
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_ai_settings_store.py -v
```

- [ ] **Step 3: Implement store**

`gui/ai_settings_store.py`:

```python
"""Load/save AI assistant settings for the desktop GUI."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from core.ai_assistant.config import DEFAULT_BASE_URL, DEFAULT_MODEL


@dataclass
class AISettings:
    enabled: bool = True
    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    model: str = DEFAULT_MODEL


def default_ai_settings_path(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[1]
    return root / "ai_settings.json"


def load_ai_settings(path: Path) -> AISettings:
    if not path.is_file():
        return AISettings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AISettings()
    if not isinstance(raw, dict):
        return AISettings()
    return AISettings(
        enabled=bool(raw.get("enabled", True)),
        base_url=str(raw.get("base_url") or DEFAULT_BASE_URL),
        api_key=str(raw.get("api_key") or ""),
        model=str(raw.get("model") or DEFAULT_MODEL),
    )


def save_ai_settings(settings: AISettings, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
```

Also export `DEFAULT_BASE_URL` / `DEFAULT_MODEL` from `core/ai_assistant/config.py` if not already importable (they are module constants in Task 3).

- [ ] **Step 4: Decide git policy for `ai_settings.json`**

If the file may contain secrets, add to `.gitignore`:

```gitignore
ai_settings.json
```

Do not commit real keys.

- [ ] **Step 5: Run tests + commit**

```bash
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_ai_settings_store.py -v
git add gui/ai_settings_store.py tests/test_ai_settings_store.py .gitignore
git commit -m "feat(ai): persist assistant settings locally"
```

---

### Task 5: Streaming chat worker

**Files:**
- Create: `gui/workers/ai_chat_worker.py`
- Create: `tests/test_ai_chat_worker.py`

- [ ] **Step 1: Write failing worker test**

```python
"""Tests for AI chat worker streaming lifecycle."""

from __future__ import annotations

from utils.exceptions import AICancelledError
from gui.workers.ai_chat_worker import run_ai_chat_stream
from core.ai_assistant.types import AssistantConfig


def test_worker_emits_deltas_and_commits(monkeypatch):
    events: list[tuple] = []

    def fake_iter(**kwargs):
        yield "你"
        yield "好"

    monkeypatch.setattr("gui.workers.ai_chat_worker.iter_chat_completion_stream", fake_iter)

    cfg = AssistantConfig(
        enabled=True,
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        api_key="k",
        model="glm-4.7-flash",
    )
    result = run_ai_chat_stream(
        config=cfg,
        messages=[{"role": "user", "content": "hi"}],
        should_cancel=lambda: False,
        on_delta=lambda t: events.append(("delta", t)),
    )
    assert result == "你好"
    assert events == [("delta", "你"), ("delta", "好")]


def test_worker_cancel(monkeypatch):
    def fake_iter(**kwargs):
        yield "A"
        raise AICancelledError("AI 生成已取消。")

    monkeypatch.setattr("gui.workers.ai_chat_worker.iter_chat_completion_stream", fake_iter)
    cfg = AssistantConfig(
        enabled=True,
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        api_key="k",
        model="glm-4.7-flash",
    )
    try:
        run_ai_chat_stream(
            config=cfg,
            messages=[{"role": "user", "content": "hi"}],
            should_cancel=lambda: True,
            on_delta=lambda t: None,
        )
        assert False, "expected cancel"
    except AICancelledError:
        pass
```

- [ ] **Step 2: Implement worker helper**

`gui/workers/ai_chat_worker.py`:

```python
"""Desktop worker helpers for AI chat streaming."""

from __future__ import annotations

from collections.abc import Callable

from core.ai_assistant.types import AssistantConfig
from utils.ai_client import chat_completion, iter_chat_completion_stream


def run_ai_chat_stream(
    *,
    config: AssistantConfig,
    messages: list[dict[str, str]],
    should_cancel: Callable[[], bool],
    on_delta: Callable[[str], None],
) -> str:
    """Stream assistant text; return full assembled content."""
    parts: list[str] = []
    for delta in iter_chat_completion_stream(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
        messages=messages,
        timeout_seconds=config.timeout_seconds,
        should_cancel=should_cancel,
    ):
        parts.append(delta)
        on_delta(delta)
    text = "".join(parts)
    if len(text) > config.max_output_chars:
        text = text[: config.max_output_chars] + "\n…(输出已截断)"
    return text


def run_ai_connection_test(*, config: AssistantConfig) -> str:
    """Non-stream tiny request for Settings → Test Connection."""
    return chat_completion(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
        messages=[{"role": "user", "content": "ping"}],
        timeout_seconds=min(config.timeout_seconds, 30),
    )
```

Wire into existing `TaskWorker` from GUI when sending:

- GUI creates a small callable / or uses `TaskWorker` with a function that calls `run_ai_chat_stream`.
- Because streaming needs mid-task UI updates, prefer a dedicated `QThread` subclass **or** extend the callable to emit via a Qt signal object passed in. Keep the worker thin.

Recommended concrete GUI integration pattern (implement in Task 6):

```python
class AIChatThread(QThread):
    delta = Signal(str)
    failed = Signal(str, str)  # message, code
    finished_ok = Signal(str)
    cancelled = Signal()

    def __init__(self, config, messages, parent=None):
        super().__init__(parent)
        self._config = config
        self._messages = messages
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            text = run_ai_chat_stream(
                config=self._config,
                messages=self._messages,
                should_cancel=lambda: self._cancel,
                on_delta=lambda t: self.delta.emit(t),
            )
            if self._cancel:
                self.cancelled.emit()
                return
            self.finished_ok.emit(text)
        except AICancelledError:
            self.cancelled.emit()
        except AutoLabelerError as exc:
            self.failed.emit(str(exc), exc.code.value)
        except Exception as exc:
            self.failed.emit(str(exc), "INTERNAL_ERROR")
```

Put `AIChatThread` in `gui/workers/ai_chat_worker.py` as well if that keeps imports simpler.

- [ ] **Step 3: Run worker tests**

```bash
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_ai_chat_worker.py -v
```

- [ ] **Step 4: Commit**

```bash
git add gui/workers/ai_chat_worker.py tests/test_ai_chat_worker.py
git commit -m "feat(ai): add streaming chat worker helpers"
```

---

### Task 6: Right-rail chat panel widget

**Files:**
- Create: `gui/ai_assistant_panel.py`
- Modify: `gui/tool_page_chrome.py`
- Modify pages only if needed for new return type / hooks

- [ ] **Step 1: Implement `AIAssistantPanel`**

Create `gui/ai_assistant_panel.py` with a `QWidget` that exposes:

```python
class AIAssistantPanel(QFrame):
    send_requested = Signal(str)  # user text
    stop_requested = Signal()
    clear_requested = Signal()

    def set_tool_context(self, tool_id: str, tool_title: str) -> None: ...
    def set_enabled_state(self, *, ready: bool, hint: str) -> None: ...
    def reset_transcript(self) -> None: ...
    def load_history(self, pairs: list[tuple[str, str]]) -> None: ...  # role, content
    def append_user(self, text: str) -> None: ...
    def begin_assistant(self) -> None: ...
    def append_assistant_delta(self, text: str) -> None: ...
    def finish_assistant(self, text: str | None = None) -> None: ...
    def show_notice(self, text: str, *, role: str = "error") -> None: ...
    def set_streaming(self, streaming: bool) -> None: ...
```

UI structure (object names stable for tests):

- `aiAssistantPanel` (root)
- `aiAssistantTitle` label = `AI 助手`
- `aiAssistantContext` label = current tool title
- `aiAssistantTranscript` `QTextEdit` or list of labels inside `QScrollArea` (read-only transcript is fine with `QTextEdit.setReadOnly(True)`)
- `aiAssistantInput` `QPlainTextEdit`
- `aiAssistantSendButton`
- `aiAssistantClearButton`
- `aiAssistantStopButton`
- `aiAssistantHint` muted hint label

Behavior:

- Empty input → ignore send
- Streaming true → disable send/clear input editing if desired; enable Stop
- Streaming false → enable send; disable Stop
- `set_enabled_state(ready=False)` disables input/send and shows hint (missing key / disabled)

Use existing objectName styles (`panelTitle`, `mutedText`, `primaryButton`, `secondaryButton`, `rightSupportPanel` parent already styled).

- [ ] **Step 2: Replace preview builder**

In `gui/tool_page_chrome.py`, change `build_ai_assistant_panel` to create `AIAssistantPanel` instead of static preview labels.

Keep function signature compatible if possible:

```python
def build_ai_assistant_panel(page: QWidget, tool_title: str) -> AIAssistantPanel:
    panel = AIAssistantPanel(tool_title=tool_title, parent=page)
    page.ai_assistant_panel = panel
    # retain page.ai_assistant_title for tests if they look for it
    page.ai_assistant_title = panel.title_label
    page.ai_assistant_preview = panel.hint_label  # or transcript empty-state
    return panel
```

Update title text from `AI 助手（预览）` to `AI 助手`.

- [ ] **Step 3: Manual smoke in mind / optional tiny unit check**

If pure widget construction is easy without full window:

```python
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from gui.ai_assistant_panel import AIAssistantPanel
app = QApplication.instance() or QApplication([])
p = AIAssistantPanel(tool_title="抽样")
assert p.objectName() == "aiAssistantPanel"
```

Add this as `tests/test_ai_assistant_panel.py` if desired (recommended short test).

- [ ] **Step 4: Commit**

```bash
git add gui/ai_assistant_panel.py gui/tool_page_chrome.py tests/test_ai_assistant_panel.py
git commit -m "feat(ai): replace preview rail with chat panel widget"
```

---

### Task 7: Workbench wiring — settings + chat controller

**Files:**
- Modify: `gui/workbench.py`
- Modify: `tests/test_gui_shell.py`

This is the integration task.

- [ ] **Step 1: Load AI settings in `AutoLabelerWindow.__init__`**

```python
from gui.ai_settings_store import AISettings, default_ai_settings_path, load_ai_settings, save_ai_settings
from core.ai_assistant import AIAssistantService, resolve_assistant_config
from gui.workers.ai_chat_worker import AIChatThread, run_ai_connection_test
```

Fields:

```python
self._ai_settings_path = default_ai_settings_path(Path(__file__).resolve().parents[1])
self._ai_settings = load_ai_settings(self._ai_settings_path)
self._ai_service = AIAssistantService()
self._ai_thread: AIChatThread | None = None
self._ai_current_tool_id = "home"
self._ai_current_tool_title = "首页"
self._ai_pending_user_text = ""
```

- [ ] **Step 2: Add Settings UI section**

In `_build_settings_page`, add section `06 AI 助手` with:

- `settings_ai_enabled_input` QCheckBox
- `settings_ai_base_url_input` QLineEdit
- `settings_ai_api_key_input` QLineEdit (echo mode Password)
- `settings_ai_model_input` QLineEdit
- `settings_ai_test_button` QPushButton("测试连接")
- `settings_ai_test_status` QLabel
- Include in quick nav list
- Populate from `self._ai_settings` on build
- Extend save flow:
  - Either separate `settings_ai_save` or include AI fields into `save_tool_default_settings` **and** a dedicated save path. Prefer **dedicated** `save_ai_settings_from_page` called by a `保存 AI 设置` button next to test, so tool-default validation does not block AI saves.
  - Buttons: `settings_ai_save_button`, `settings_ai_test_button`

Save handler:

```python
def save_ai_settings_from_page(self) -> None:
    settings = AISettings(
        enabled=self.settings_ai_enabled_input.isChecked(),
        base_url=self.settings_ai_base_url_input.text().strip(),
        api_key=self.settings_ai_api_key_input.text().strip(),
        model=self.settings_ai_model_input.text().strip() or "glm-4.7-flash",
    )
    save_ai_settings(settings, self._ai_settings_path)
    self._ai_settings = settings
    self._refresh_all_ai_panels_ready_state()
    self.settings_ai_test_status.setText("AI 设置已保存。")
```

Test handler (background thread or ImmediateTaskRunner):

```python
def test_ai_connection_from_settings(self) -> None:
    form_cfg = resolve_assistant_config(
        user_settings={
            "enabled": True,
            "base_url": self.settings_ai_base_url_input.text().strip(),
            "api_key": self.settings_ai_api_key_input.text().strip(),
            "model": self.settings_ai_model_input.text().strip(),
        }
    )
    self.settings_ai_test_status.setText("正在测试连接…")
    # run in thread; on success set status to 连接成功；on error show message
```

- [ ] **Step 3: Connect each page's AI panel**

After pages are built (or inside a helper called when showing a module):

```python
def _iter_ai_panels(self):
    for key, page in self.pages.items():
        panel = getattr(page, "ai_assistant_panel", None)
        if panel is not None:
            yield key, page, panel
```

For each panel:

- `panel.send_requested.connect(self._on_ai_send)`
- `panel.stop_requested.connect(self._on_ai_stop)`
- `panel.clear_requested.connect(self._on_ai_clear)`

When `show_module(key)` runs, call:

```python
self._ai_current_tool_id = key
self._ai_current_tool_title = page title from MODULES
panel = page.ai_assistant_panel
panel.set_tool_context(key, title)
panel.reset_transcript()
for msg in self._ai_service.sessions.get(key):
    if msg.role == "user":
        panel.append_user(msg.content)
    else:
        panel.begin_assistant(); panel.finish_assistant(msg.content)
self._refresh_ai_panel_ready_state(panel)
```

If a stream is running for another tool, cancel it before switch (spec: prevent cross-tool corruption).

- [ ] **Step 4: Send / stop / clear handlers**

```python
def _resolved_ai_config(self) -> AssistantConfig:
    return resolve_assistant_config(user_settings=asdict(self._ai_settings))

def _on_ai_send(self, text: str) -> None:
    panel = self._current_ai_panel()
    if panel is None:
        return
    cfg = self._resolved_ai_config()
    try:
        messages = self._ai_service.build_model_messages(
            cfg,
            tool_id=self._ai_current_tool_id,
            tool_title=self._ai_current_tool_title,
            user_text=text,
        )
    except AutoLabelerError as exc:
        panel.show_notice(str(exc), role="error")
        return
    self._ai_pending_user_text = text.strip()
    panel.append_user(text.strip())
    panel.begin_assistant()
    panel.set_streaming(True)
    self._start_ai_thread(cfg, messages)

def _on_ai_stop(self) -> None:
    if self._ai_thread is not None:
        self._ai_thread.cancel()

def _on_ai_clear(self) -> None:
    self._ai_service.clear(self._ai_current_tool_id)
    panel = self._current_ai_panel()
    if panel:
        panel.reset_transcript()
```

On thread `finished_ok`:

- truncate already handled in worker
- `self._ai_service.commit_turn(tool_id, user_text, assistant_text)` only if tool_id still matches
- `panel.finish_assistant(assistant_text)`; `set_streaming(False)`

On `failed`:

- `panel.show_notice(message)`; `set_streaming(False)`; do not commit turn

On `cancelled`:

- `panel.show_notice("已停止生成。", role="muted")`; `set_streaming(False)`; do not commit

- [ ] **Step 5: GUI tests**

Extend `tests/test_gui_shell.py` with focused checks:

```python
def test_ai_assistant_panel_not_preview_only():
    window = make_window()
    page = window.pages["sample"]
    panel = page.ai_assistant_panel
    assert panel is not None
    assert "预览" not in panel.title_label.text()
    assert panel.findChild(QPushButton, "aiAssistantSendButton") is not None


def test_settings_has_ai_fields():
    window = make_window()
    window.show_settings()
    assert window.settings_ai_base_url_input is not None
    assert window.settings_ai_api_key_input is not None
    assert window.settings_ai_model_input is not None
```

Use whatever actual attribute names you create; keep them stable.

Run:

```bash
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_gui_shell.py -k ai -v
```

- [ ] **Step 6: Commit**

```bash
git add gui/workbench.py tests/test_gui_shell.py
git commit -m "feat(ai): wire settings and right-rail chat controller"
```

---

### Task 8: Docs + changelog

**Files:**
- Modify: `docs/dev/PRODUCT_SPEC.md`
- Modify: `docs/dev/UI_SPEC.md`
- Modify: `docs/dev/ONBOARDING_SUMMARY.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: PRODUCT_SPEC**

Add a section before Related docs, e.g. `## AI usage assistant`:

- Chat-only desktop helper
- Default Zhipu OpenAI-compatible `glm-4.7-flash`
- Configurable base_url/api_key/model
- Cannot fill forms, edit code, call internal APIs
- Per-tool memory sessions; no disk chat history
- Free-model wording: 额度以服务商为准
- Config priority: user settings > env/file > defaults
- Env: `AUTO_YOLO_AI_API_KEY` / optional URL/model; key file `%APPDATA%/auto_yolo_label/ai_api_key.txt`

- [ ] **Step 2: UI_SPEC**

Replace preview-only assistant bullets with:

- Right rail second panel is real chat: transcript, input, Send/Clear/Stop
- Title `AI 助手` (no 预览)
- Settings page section for AI config + 测试连接 + 保存 AI 设置
- Disabled/missing key states
- Streaming state rules

- [ ] **Step 3: ONBOARDING_SUMMARY**

Add ownership lines:

- `core/ai_assistant/`: policy/knowledge/sessions
- `utils/ai_client.py`: transport
- `gui/ai_assistant_panel.py` + workbench wiring + `gui/workers/ai_chat_worker.py`

- [ ] **Step 4: CHANGELOG**

Under Unreleased / date section:

```markdown
### Product / GUI
- Right-rail AI usage assistant: streaming chat against OpenAI-compatible APIs (default Zhipu glm-4.7-flash), settings + test connection, chat-only safety limits.
```

- [ ] **Step 5: Commit**

```bash
git add docs/dev/PRODUCT_SPEC.md docs/dev/UI_SPEC.md docs/dev/ONBOARDING_SUMMARY.md CHANGELOG.md
git commit -m "docs: document AI usage assistant behavior"
```

---

### Task 9: End-to-end verification

**Files:** none required (verification only)

- [ ] **Step 1: Run unit/integration tests**

```bash
D:/miniforge3/envs/yolo_new/python.exe -m pytest \
  tests/test_exceptions.py \
  tests/test_ai_client.py \
  tests/test_ai_assistant_core.py \
  tests/test_ai_settings_store.py \
  tests/test_ai_chat_worker.py \
  tests/test_gui_shell.py -k ai \
  -v
```

Expected: all PASS

- [ ] **Step 2: Optional live smoke (owner key required)**

```bash
export AUTO_YOLO_AI_API_KEY='***'
D:/miniforge3/envs/yolo_new/python.exe -m gui.main
```

Manual checklist:

1. Open 抽样 page → right rail shows `AI 助手` with input
2. Ask「这个工具有什么限制？」→ streaming tokens appear
3. Ask「帮我填写站点路径」→ local refusal, no network needed
4. Settings → change model/key → 测试连接 success/fail readable
5. Switch to 训练 page → transcript isolated
6. Stop mid-stream → cancelled notice, history not polluted

- [ ] **Step 3: Final commit only if verification fixes were needed**

If fixes landed, commit them with focused messages. Do not claim full product coverage beyond tests actually run.

---

## Spec coverage self-check

| Spec requirement | Task |
|------------------|------|
| Replace right-rail preview with real chat | 6, 7 |
| Default Zhipu URL + glm-4.7-flash | 3, 4, 7 |
| User override base_url/key/model | 4, 7 |
| Default key via env/file placeholder | 3, 7, 9 |
| Streaming required | 2, 5, 7 |
| Per-tool memory sessions | 3, 7 |
| Built-in product knowledge | 3 |
| Hard limits (no tools/form fill/code) | 3, 7 |
| Settings + test connection | 7 |
| Stdlib client, no vendor SDK | 2 |
| Error codes | 1 |
| Docs PRODUCT/UI/ONBOARDING/CHANGELOG | 8 |
| Stop control | 5, 6, 7 |
| Limits 60s / 2000 / 20 / 8000 | 3, 5 |

## Placeholder / consistency scan

- Function names aligned: `chat_completion`, `iter_chat_completion_stream`, `resolve_assistant_config`, `AIAssistantService.build_model_messages`, `run_ai_chat_stream`, `AIChatThread`
- Config fields aligned: `enabled`, `base_url`, `api_key`, `model`
- Error codes aligned across exceptions, client, service, GUI notices

## Execution notes

- Prefer subagent-driven development: one task per subagent, run tests before commit.
- Keep diffs surgical; do not reintroduce `cli/` or `runtime/`.
- Never commit real API keys.
- Before editing existing symbols during execution, run GitNexus `impact` on those symbols per project rules.
