# GUI Task Feedback

## Running Work

`gui/task_runner.py` separates execution from page state:

- `ImmediateTaskRunner` is synchronous and deterministic for tests and small
  controlled calls.
- `AsyncTaskRunner` runs a callable on Qt's global thread pool and emits one
  success or error callback without freezing the UI.

Pages should keep the runnable callable small: build a typed config first, then
call the worker. Update visible state before starting and handle both the
worker's typed outcome and unexpected runner exceptions.

## Outcome Rendering

Workers return frozen outcome dataclasses with `success`, a `TaskHandle`, and
either a typed result or `ErrorInfo`. Render concise summaries by default and
keep full paths, error codes, and diagnostics in logs or tooltips. Follow the
long-path handling in `gui/tool_page_chrome.py` and the review path compaction
in `gui/labelimg_page.py`.

## High-Risk Actions

Use the sequence `inputs -> preflight -> inline confirmation -> execute` for
sampling moves, output clearing, restore writes, and overwrite. `SamplePage`
requires a move confirmation in Independent mode; `RestorePage` invalidates
preflight after changing overwrite or mode and requires a fresh explicit
confirmation. Do not replace this with an unconditional modal or a page-only
boolean that bypasses core preflight.

## Task Center

The workbench reads `TaskRegistry` state and preserves running tasks while the
user switches pages. Task rows show module, status, time, output, and failure
reason; terminal records may be deleted, active tasks may not. Keep task-center
filters reversible so a filtered view has a clear return to the full list.
