# Utils Task Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `utils/task_registry.py` for shared long-running task state across desktop workers and HTTP routes.

**Architecture:** `TaskRegistry` manages in-process `TaskHandle` dataclasses, persists each task as JSON under a configurable task directory, and exposes explicit lifecycle methods. Running or queued persisted tasks are marked `interrupted` on registry startup.

**Tech Stack:** Python 3.11 dataclasses, pathlib, uuid, json, threading, pytest, mypy strict-compatible type hints.

---

### Task 1: Task Registry Tests

**Files:**
- Create: `tests/test_task_registry.py`
- Create: `utils/task_registry.py`

- [ ] **Step 1: Write failing tests**

Cover:
- `create_task()` creates queued handle with stable `task_id`, timestamps, progress defaults, and persisted JSON.
- `start_task()`, `succeed_task()`, `fail_task()`, and `cancel()` update status and timestamps.
- `cancel()` sets `is_cancel_requested` for core loops.
- `get()` raises `TaskNotFoundError` for missing tasks.
- duplicate running task type raises `TaskAlreadyRunningError`.
- new registry loading persisted queued/running tasks marks them `interrupted`.

- [ ] **Step 2: Run tests to verify RED**

Run: `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_task_registry.py -v`
Expected: FAIL because `utils.task_registry` does not exist.

- [ ] **Step 3: Implement minimal registry**

Create:
- `TaskHandle` dataclass.
- `TaskRegistry` with create/get/list/start/succeed/fail/cancel.
- JSON persistence and startup loading.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_task_registry.py -v`
Expected: PASS.

### Task 2: Verification And Docs

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/dev/CURRENT_STATE.md`

- [ ] **Step 1: Run verification**

Run:
- `D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py`
- `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_*.py -v`
- `D:/miniforge3/envs/yolo_new/python.exe -m mypy --strict utils/`

- [ ] **Step 2: Update docs**

Mark `task_registry.py` complete. M1.1 utils is complete; set next in-progress module to `core/scanner.py`.
