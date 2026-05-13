# Utils Logging Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `utils/logging_setup.py` as the shared loguru initialization entry point for core, GUI, and API layers.

**Architecture:** Keep logging setup in `utils/` with no dependency on `core`, `gui`, or `api`. Provide a typed `LoggingConfig` dataclass and an idempotent `setup_logging(config)` function that removes prior managed sinks before adding stderr/file sinks.

**Tech Stack:** Python 3.11 dataclasses, pathlib, loguru, pytest, mypy strict-compatible type hints.

---

### Task 1: Create Logging Setup Tests

**Files:**
- Create: `tests/test_logging_setup.py`
- Create: `utils/logging_setup.py`

- [ ] **Step 1: Write failing tests**

Cover:
- `LoggingConfig` defaults.
- `setup_logging()` returns the loguru logger object.
- A configured file sink writes log messages.
- Repeated setup does not duplicate file output.

- [ ] **Step 2: Run tests to verify RED**

Run: `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_logging_setup.py -v`
Expected: FAIL because `utils.logging_setup` does not exist.

- [ ] **Step 3: Implement minimal logging setup**

Create:
- `LoggingConfig` dataclass with `level`, `log_file`, `enable_stderr`, `rotation`, `retention`, `enqueue`.
- `setup_logging(config: LoggingConfig | None = None) -> Logger`.
- Managed sink tracking so repeated calls remove previous sinks created by this module.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_logging_setup.py -v`
Expected: PASS.

### Task 2: Verification And Docs

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/dev/CURRENT_STATE.md`

- [ ] **Step 1: Run verification**

Run:
- `D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py`
- `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_logging_setup.py tests/test_exceptions.py -v`
- `D:/miniforge3/envs/yolo_new/python.exe -m mypy --strict utils/`

- [ ] **Step 2: Update docs**

Mark `logging_setup.py` complete and set `utils/device.py` as next in progress. Add changelog entry.
