# Utils Path Encoder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `utils/path_encoder.py` for deterministic `Code/Product/Filename` flattening and decoding.

**Architecture:** Keep the module pure and dependency-light. `PathEncoder` validates separator conflicts, encodes three explicit path parts, decodes encoded names, and exposes `to_relative_path()` for consumers that need a `Path`.

**Tech Stack:** Python 3.11 dataclasses, pathlib, pytest, mypy strict-compatible type hints.

---

### Task 1: Path Encoder Tests

**Files:**
- Create: `tests/test_path_encoder.py`
- Create: `utils/path_encoder.py`

- [ ] **Step 1: Write failing tests**

Cover:
- Default encode result: `AS_CV_PI_P__H4A238FDF04__IMG_001.jpg`.
- Decode returns `DecodedPath`.
- `to_relative_path()` returns `Path("Code") / "Product" / "Filename"`.
- Invalid encoded names return `None`.
- Separator conflicts raise `ValidationError`.
- Custom separator works.

- [ ] **Step 2: Run tests to verify RED**

Run: `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_path_encoder.py -v`
Expected: FAIL because `utils.path_encoder` does not exist.

- [ ] **Step 3: Implement minimal path encoder**

Create:
- `DecodedPath` frozen dataclass.
- `PathEncoder` with `encode()`, `decode()`, `to_relative_path()`.
- Separator validation through `ValidationError`.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_path_encoder.py -v`
Expected: PASS.

### Task 2: Verification And Docs

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/dev/CURRENT_STATE.md`

- [ ] **Step 1: Run verification**

Run:
- `D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py`
- `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_exceptions.py tests/test_logging_setup.py tests/test_device.py tests/test_path_encoder.py -v`
- `D:/miniforge3/envs/yolo_new/python.exe -m mypy --strict utils/`

- [ ] **Step 2: Update docs**

Mark `path_encoder.py` complete and set `utils/mapping_manager.py` as next in progress. Add changelog entry.
