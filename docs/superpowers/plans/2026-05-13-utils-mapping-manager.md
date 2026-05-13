# Utils Mapping Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `utils/mapping_manager.py` as the only supported mapping.json access path.

**Architecture:** `MappingManager` owns a `MappingData` cache, protects mutations with `threading.RLock`, serializes dataclasses to JSON, and saves through a temporary file followed by atomic replace. The module stays in `utils/` and depends only on standard library plus existing shared exceptions.

**Tech Stack:** Python 3.11 dataclasses, pathlib, json, threading, pytest, mypy strict-compatible type hints.

---

### Task 1: Mapping Data And Persistence Tests

**Files:**
- Create: `tests/test_mapping_manager.py`
- Create: `utils/mapping_manager.py`

- [ ] **Step 1: Write failing tests**

Cover:
- `create_new()` creates v1.0 data with project name, paths, timestamps, and empty collections.
- `add_class()` and `add_image()` update cache and statistics.
- `save()` writes JSON and `load()` reconstructs `MappingData` / `ImageInfo`.
- `mark_sampled()`, `mark_labeled()`, `mark_inferred()`, `mark_restored()` mutate state and statistics.
- `get_unsampled_images()` ignores `inferred`; `get_pending_inference_images()` only filters sampled.
- Missing mapping load raises `PathNotFoundError`.

- [ ] **Step 2: Run tests to verify RED**

Run: `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_mapping_manager.py -v`
Expected: FAIL because `utils.mapping_manager` does not exist.

- [ ] **Step 3: Implement minimal manager**

Create:
- `ImageInfo` and `MappingData` dataclasses matching `01-requirements.md`.
- `MappingManager` with create/load/save/add/mark/query methods.
- Atomic JSON save and dataclass reconstruction.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_mapping_manager.py -v`
Expected: PASS.

### Task 2: Verification And Docs

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/dev/CURRENT_STATE.md`

- [ ] **Step 1: Run verification**

Run:
- `D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py`
- `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_exceptions.py tests/test_logging_setup.py tests/test_device.py tests/test_path_encoder.py tests/test_mapping_manager.py -v`
- `D:/miniforge3/envs/yolo_new/python.exe -m mypy --strict utils/`

- [ ] **Step 2: Update docs**

Mark `mapping_manager.py` complete and set `utils/task_registry.py` as next in progress. Add changelog entry.
