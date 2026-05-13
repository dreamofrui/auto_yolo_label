# Utils Device Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `utils/device.py` for deterministic CPU/CUDA/MPS detection and conservative automatic batch-size selection.

**Architecture:** Keep the public API small: `DeviceInfo`, `get_device_info()`, `resolve_device()`, and `get_optimal_batch_size()`. Use an internal probe protocol so tests can simulate torch hardware without requiring real GPUs.

**Tech Stack:** Python 3.11 dataclasses, Protocol, pytest, mypy strict-compatible type hints, optional runtime torch import.

---

### Task 1: Device Detection Tests

**Files:**
- Create: `tests/test_device.py`
- Create: `utils/device.py`

- [ ] **Step 1: Write failing tests**

Cover:
- CPU fallback returns `DeviceInfo(device="cpu", device_id="", memory_mb=0)`.
- CUDA single GPU returns id `0`, CUDA multi GPU returns ids like `0,1`.
- MPS is used when CUDA is unavailable and MPS is available.
- `resolve_device("auto")` maps to the optimal YOLO device string.
- Explicit `cpu`, `mps`, and GPU ids pass through.
- Invalid explicit device raises `ValidationError`.
- Batch-size selection is conservative and CPU returns at least `1`.

- [ ] **Step 2: Run tests to verify RED**

Run: `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_device.py -v`
Expected: FAIL because `utils.device` does not exist.

- [ ] **Step 3: Implement minimal device helpers**

Create:
- `DeviceInfo` dataclass matching `01-requirements.md`.
- Internal `DeviceProbe` protocol and default torch-backed probe.
- `get_device_info(probe: DeviceProbe | None = None) -> DeviceInfo`.
- `resolve_device(requested: str = "auto", probe: DeviceProbe | None = None) -> str`.
- `get_optimal_batch_size(device: str = "auto", image_size: int = 640, probe: DeviceProbe | None = None) -> int`.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_device.py -v`
Expected: PASS.

### Task 2: Verification And Docs

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/dev/CURRENT_STATE.md`

- [ ] **Step 1: Run verification**

Run:
- `D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py`
- `D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_exceptions.py tests/test_logging_setup.py tests/test_device.py -v`
- `D:/miniforge3/envs/yolo_new/python.exe -m mypy --strict utils/`

- [ ] **Step 2: Update docs**

Mark `device.py` complete and set `utils/path_encoder.py` as next in progress. Add changelog entry.
