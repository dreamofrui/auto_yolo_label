# AI Usage Assistant Design

Date: 2026-07-16  
Status: Approved for implementation planning  
Product: auto_yolo_label (desktop-first GUI)

## 1. Summary

Replace the existing right-rail **「AI 助手（预览）」** placeholder with a real, chat-only **project usage assistant**.

The assistant helps users understand tool purpose, workflow, limits, and common errors for this product. It must not modify code, call low-level product APIs, drive GUI controls, or fill business form fields/paths for the user.

Default model access uses Zhipu’s OpenAI-compatible free model **`glm-4.7-flash`**, with user-overridable Base URL / API Key / Model. A shared default API key is supported via placeholder injection (real secret is not committed). Streaming replies are required for v1.

## 2. Goals and Non-Goals

### 2.1 Goals (v1)

- Turn the right-rail preview panel into a usable chat assistant.
- Default provider endpoint (OpenAI-compatible):
  - Base URL: `https://open.bigmodel.cn/api/paas/v4/`
  - Model: `glm-4.7-flash`
  - Auth: `Authorization: Bearer <api_key>`
  - Chat path: `POST {base_url}/chat/completions`
- User can override Base URL, API Key, and Model in Settings.
- “Works without manual setup” when a default key is present (placeholder path now; real key supplied later by owner).
- Chat-only product help:
  - Explain tools, workflows, limits, validation rules, common failures.
  - Never edit code, never call product mutation APIs, never drive form widgets, never auto-fill paths/business parameters.
- UX:
  - Right-rail real chat with streaming tokens.
  - Per-tool in-memory sessions.
  - Settings: config fields + Test Connection.
- Architecture boundaries:
  - `utils/`: generic OpenAI-compatible HTTP + SSE client (no vendor SDKs).
  - `core/`: assistant policy, product knowledge, hard limits, session model.
  - `gui/`: panel, settings UI, worker lifecycle, main-thread streaming paint.
- Zero new third-party dependencies unless owner later re-approves.

### 2.2 Non-Goals (v1)

- Local Ollama or multi-provider plugin registry.
- Reading user business data paths or scanning the repo as a live knowledge base.
- Persisting chat history to disk.
- Function calling / tools / automatic file writes / automatic button clicks.
- Web, FastAPI, browser UI, Node integration.
- Reintroducing `cli/` or `runtime/` as active architecture surfaces.
- Claiming permanent free quota beyond vendor wording; UI/docs must say free status/quota is determined by the provider.

### 2.3 Success criteria

With a working key (default or user-provided):

1. On any tool page, open the right-rail assistant and stream answers about “how to use this tool / what are the limits”.
2. Answers are grounded in built-in product knowledge plus current tool context.
3. Failures show readable errors (auth, network, timeout, bad SSE, disabled).
4. The assistant never drives business form controls or writes files.

## 3. Current State

- `gui/tool_page_chrome.py` already builds a right support rail with:
  - **AI 操作** (tool-specific action list; keep)
  - **AI 助手（预览）** placeholder text (replace with real chat)
- `docs/dev/UI_SPEC.md` documents the dual-panel right rail and preview-only assistant.
- No existing OpenAI/Zhipu client, settings schema for AI, or chat worker.
- Product direction remains desktop-first; core must stay framework-free.

## 4. Architecture

### 4.1 Recommended shape: thin client + desktop adapter

```text
gui (settings + right-rail chat + worker)
        |
        v
core/ai_assistant  (policy, knowledge, hard limits, sessions)
        |
        v
utils/ai_client    (OpenAI-compatible HTTP + SSE)
        |
        v
Zhipu / any OpenAI-compatible endpoint
```

### 4.2 Module responsibilities

| Layer | Module (planned) | Responsibility |
|-------|------------------|----------------|
| utils | `utils/ai_client.py` | Stateless OpenAI-compatible chat client: non-stream request, SSE stream parse, timeouts, HTTP errors. No product copy. |
| core | `core/ai_assistant/` | System prompt + built-in knowledge, hard-limit checks, per-`tool_id` memory sessions, request assembly, typed results/errors. |
| gui | right-rail chat panel | Message list, input, send/clear/stop, disabled states, streaming bubble updates. |
| gui | settings AI section | Base URL / API Key / Model / enabled + Test Connection. |
| gui | worker | Background request; emit token/error/finished signals to main thread. |

### 4.3 Boundary rules

- `core/` must not import GUI or HTTP frameworks.
- `utils/` must not depend on `core/`.
- `gui/workers/` stays thin: lifecycle glue only; calls `core` + `utils` as designed.
- No function-calling bridge into product tools.
- No writes into business form fields from assistant code paths.

### 4.4 Alternatives considered

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| A. Thin client + core policy + gui adapter | Clean testability; matches repo boundaries | Slightly more files | **Chosen** |
| B. All logic in GUI | Smaller diff | Hard to test; boundary rot | Rejected |
| C. Multi-provider plugin registry | Future flexibility | Overkill for chat-only v1 | Rejected (YAGNI) |

## 5. Configuration

### 5.1 Fields

- `enabled: bool`
- `base_url: str` (default `https://open.bigmodel.cn/api/paas/v4/`)
- `api_key: str` (secret)
- `model: str` (default `glm-4.7-flash`)

Required operational limits (defaults for v1; overridable later only if needed):

- request timeout: 60 seconds
- max user input: 2000 chars
- max history messages sent to model: 20 (excluding system)
- max assistant output retained/displayed per reply: 8000 chars

### 5.2 Resolution priority

Highest wins:

1. User settings (GUI-saved)
2. Environment variable and/or local private file (for default key injection)
3. Built-in placeholder defaults (base_url + model + key placeholder)

### 5.3 Default key handling (security)

- Design and code use a **placeholder** for the shared default key.
- Owner later places the real key in the agreed local mechanism (env and/or private file). Real key must not be committed to git.
- UI may mask key display (e.g. password echo).
- Docs must state: embedded/shared keys can be extracted and abused; users may override with their own key.
- Provider free-model wording: “平台标注免费，额度与是否持续免费以服务商为准”.

### 5.4 Env / file conventions (fixed for v1)

- Env (highest among non-GUI defaults):
  - `AUTO_YOLO_AI_API_KEY` (required for default-key injection)
  - `AUTO_YOLO_AI_BASE_URL` (optional override)
  - `AUTO_YOLO_AI_MODEL` (optional override)
- Private file fallback for key only (if env absent):
  - Windows: `%APPDATA%/auto_yolo_label/ai_api_key.txt`
  - File contains a single line API key; must not be committed
- Built-in code defaults supply base_url + model; built-in key default is empty placeholder string unless replaced by env/file/user settings

### 5.5 Settings UX

- Fields: Base URL, API Key, Model, Enabled
- Actions: Save, Test Connection
- Test Connection: non-stream small `chat/completions` request; show success/failure clearly
- Unconfigured/disabled assistant: right-rail input disabled with guidance to Settings

## 6. Data Flow

### 6.1 Happy path (streaming chat)

1. User types message in right rail; GUI validates non-empty and length limits.
2. GUI asks core to build a chat request for current `tool_id`:
   - system: product knowledge + hard-limit policy + current tool context
   - history: that tool’s in-memory turns
   - user: new message
3. Core runs local hard-limit intent checks. If blocked, return a local refusal message without network I/O.
4. If allowed, GUI worker calls `utils` streaming client with resolved config.
5. SSE deltas are emitted to the main thread and appended to the assistant bubble.
6. On success, core appends the final user+assistant turn to that tool’s memory session.
7. On failure, show readable error; do not append a partial/failed assistant turn as successful history.

### 6.2 Test connection

1. Settings tests the **values currently shown in the form**, even if not yet saved.
2. Non-stream request with a tiny prompt (e.g. user content `ping`).
3. Map HTTP/auth/network errors to readable Chinese status text.
4. Successful test does not write chat history.

### 6.3 Cancellation

- Right-rail **Stop** control is required while a reply is streaming.
- Stop cancels the in-flight worker/HTTP read where practical.
- Cancelled generation must not be stored as a completed successful answer.

## 7. Session Model

- Scope: **per tool page (`tool_id`)**, in-memory only.
- Switching tools switches visible transcript to that tool’s session.
- Restarting the app clears all sessions.
- Provide **Clear conversation** for the current tool session.
- No disk persistence in v1.

Canonical structures for v1:

```text
ChatMessage(role: "user"|"assistant", content: str)
ChatSession(tool_id: str, messages: list[ChatMessage])
AssistantConfig(enabled: bool, base_url: str, api_key: str, model: str,
                timeout_seconds: int = 60,
                max_input_chars: int = 2000,
                max_history_messages: int = 20,
                max_output_chars: int = 8000)
ChatStreamEvent(kind: "delta"|"error"|"finished"|"cancelled", text: str = "", code: str | None = None)
```

Rules:

- System prompt is assembled at send-time and is not stored in `ChatSession`.
- History sent to the model is truncated to `max_history_messages` (excluding system).
- User input longer than `max_input_chars` is rejected in GUI/core before network I/O.
- Assistant output longer than `max_output_chars` is truncated for display/storage with a visible notice.

## 8. Product Knowledge and Prompt Policy

### 8.1 Knowledge source

- Built-in condensed product knowledge distilled from:
  - `README.md`
  - `docs/dev/PRODUCT_SPEC.md`
  - `docs/dev/UI_SPEC.md`
  - tool purpose/limit notes already implied by the product surface
- Knowledge is shipped as code/data constants in `core/ai_assistant/`, not by reading arbitrary user files at runtime.
- Current tool context (tool name, short capability/limit blurb, maybe non-sensitive UI mode labels) is injected into system prompt at send time.

### 8.2 Assistant behavioral rules (system prompt must state)

- You are a usage assistant for this desktop auto-labeling product.
- Explain how to use tools, workflows, constraints, and common errors.
- Do not claim you can modify the user’s project code or click the GUI.
- Do not invent product features that are not in the built-in knowledge.
- If asked to fill paths, class names, thresholds, or other business parameters, refuse to supply final filled values for direct paste-as-automation; instead explain what kind of value is needed and where the user should enter it.
- If asked to change underlying APIs/code, refuse and explain the product boundary.
- Prefer concise, stepwise desktop-user language (Chinese UI copy).

### 8.3 Local hard limits (beyond prompt)

Minimum hard-limit package:

1. No tool/function calling channel from model to product.
2. No file writes, no subprocess launches, no GUI widget driving APIs in assistant paths.
3. Local intent refusal for clear “fill the form for me / change the code / run this command / call internal API” requests before network when pattern/heuristic matches; always enforce again via system policy.
4. Input/output length truncation.
5. Assistant can be disabled in settings.

Hard limits must fail closed: if assistant is disabled or key missing, chat send is blocked in UI.

## 9. HTTP Client Design (`utils`)

### 9.1 API surface

- `chat_completion(*, base_url: str, api_key: str, model: str, messages: list[dict], timeout_seconds: int) -> str`
  - Non-stream helper used by Test Connection and any non-stream callers.
- `iter_chat_completion_stream(*, base_url: str, api_key: str, model: str, messages: list[dict], timeout_seconds: int, should_cancel: Callable[[], bool] | None = None) -> Iterator[str]`
  - Yields text deltas; raises typed/transport errors; stops when `should_cancel()` is true.

### 9.2 Protocol details

- OpenAI-compatible JSON body:

```json
{
  "model": "glm-4.7-flash",
  "messages": [{"role": "user", "content": "..."}],
  "stream": true
}
```

- Headers:
  - `Authorization: Bearer <api_key>`
  - `Content-Type: application/json`
  - `Accept: text/event-stream` when streaming
- Parse SSE lines `data: {...}`; stop on `[DONE]`.
- Use stdlib only (`urllib` / `http.client` + JSON). No `openai` package, no vendor SDK, no new dependency.

### 9.3 Errors

Map to stable error codes under project exception style where appropriate (inherit `AutoLabelerError` for core-facing errors). At minimum distinguish:

- missing/disabled config
- unauthorized / bad key
- HTTP 4xx/5xx
- network failure
- timeout
- invalid/malformed SSE or JSON
- cancelled

GUI shows short Chinese explanations; logs may keep technical detail.

## 10. GUI Design

### 10.1 Right rail chat (replaces preview-only block)

Keep the existing dual-panel rail structure:

1. **AI 操作** — unchanged tool action list
2. **AI 助手** — real chat (rename from preview)

Chat panel contents:

- Title: `AI 助手`
- Context line: current tool display name
- Scrollable message list (user / assistant / system-notice or error styles)
- Multiline input
- Buttons: **Send**, **Clear**, and **Stop** (Stop visible/enabled only while streaming)
- Empty state copy explaining usage-help only (no form filling)

States:

- Disabled/missing key: input+send disabled; hint to Settings
- Streaming: Send disabled; Stop enabled; append deltas to one assistant bubble
- Error: show inline error bubble/notice; keep prior successful history
- Cancelled: show cancelled notice; do not save partial reply as successful history

### 10.2 Settings page

Add an AI assistant section (or subsection):

- Enabled checkbox
- Base URL
- API Key (masked)
- Model
- Save
- Test Connection status line

Do not add a new primary nav page for chat in v1.

### 10.3 Visual constraints

Follow existing UI direction:

- light main workspace, dark side navigation, restrained accent
- no decorative AI-looking gradients or card spam
- reuse project path picker only where path-like inputs exist; AI settings fields are plain inputs

## 11. Worker / Threading

- Network I/O runs off the GUI thread via existing worker patterns (`gui/workers` + `TaskHandle` style where it fits).
- Signals/callbacks:
  - `delta(text)`
  - `failed(message, code?)`
  - `finished()`
- Main thread only updates widgets.
- Switching tool pages mid-stream: cancel or ignore stale worker events for the previous tool (implementation must prevent cross-tool transcript corruption).

## 12. Testing Strategy

### 12.1 `utils` client

- Mock HTTP layer / fake responses for:
  - non-stream success
  - stream success with multiple SSE chunks + `[DONE]`
  - 401/403
  - 5xx
  - timeout
  - malformed SSE

### 12.2 `core` assistant

- Hard-limit refusals do not call client
- Per-`tool_id` session isolation
- System prompt includes current tool context
- History truncation behavior
- Failed generations do not become successful history

### 12.3 GUI

- Optional smoke with real key in local env (not CI-secret dependent)
- Widget state transitions: disabled, streaming, error, clear

### 12.4 Docs / changelog

When implementing, update:

- `docs/dev/PRODUCT_SPEC.md` — assistant behavior and boundaries
- `docs/dev/UI_SPEC.md` — right-rail chat + settings controls (no longer preview-only)
- `CHANGELOG.md` — product/GUI note
- `docs/dev/ONBOARDING_SUMMARY.md` if ownership/module map needs a short pointer

## 13. Documentation and Copy Rules

- Do not promise “permanently free forever”; use provider-qualified wording.
- Explicitly document:
  - chat-only scope
  - no auto-fill
  - no code edits
  - config fields and defaults
  - how to override key
- Keep README entry short; detailed behavior lives in PRODUCT_SPEC / UI_SPEC.

## 14. Implementation Phases (for planning skill)

1. Config model + resolution (defaults/env/settings) with key placeholder
2. `utils` OpenAI-compatible client (non-stream + SSE)
3. `core` knowledge, hard limits, sessions, request assembly
4. GUI worker + right-rail chat panel replacement
5. Settings AI section + test connection
6. Tests
7. PRODUCT_SPEC / UI_SPEC / CHANGELOG updates

## 15. Open Items Owned by Human (not blockers for planning)

- Provide real default API key via `AUTO_YOLO_AI_API_KEY` or `%APPDATA%/auto_yolo_label/ai_api_key.txt` when ready.
- Accept residual risk if a shared key is later redistributed outside private env/file injection.

## 16. Approval Record

Brainstorm decisions locked with product owner:

- Provider style: free cloud OpenAI-compatible API
- Default: Zhipu `glm-4.7-flash` + configurable URL/Key/Model
- Knowledge: built-in condensed product knowledge
- Placement: replace right preview; Settings config + test connection
- Sessions: per-tool in-memory
- Dependencies: no vendor SDK; stdlib HTTP client
- Streaming: required in v1
- Safety: hard-limit package, not prompt-only
- Default key: shared default via placeholder; real secret supplied later out of band
- Architecture option A approved end-to-end
