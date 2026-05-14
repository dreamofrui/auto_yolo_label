# Core Trainer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `core/trainer.py` as a thin, testable Ultralytics YOLO training wrapper that is independent of Scanner/Sampler and driven only by `data.yaml`.

**Architecture:** `Trainer` validates input files and data.yaml shape, resolves device/batch through `utils.device`, loads YOLO lazily through a small internal factory, registers an epoch callback for `TaskHandle`, maps common training failures to business exceptions, and parses run outputs (`weights/`, `results.csv`) into `TrainResult`.

**Tech Stack:** Python 3.11 dataclasses, pathlib, csv, yaml-lite parsing via simple text checks, lazy `ultralytics` import, `utils.device`, `TaskHandle`, pytest monkeypatching, mypy strict-compatible type hints.

---

### Task 1: Trainer Tests

**Files:**
- Create: `tests/test_trainer.py`
- Create: `core/trainer.py`

- [ ] **Step 1: Write failing tests**

Cover:
- construction and public dataclass defaults.
- missing/invalid `data.yaml` raises `TrainDataYamlInvalidError`.
- missing base model raises `TrainBaseModelNotFoundError`.
- successful training calls YOLO with resolved config and returns weights/metrics.
- `batch_size=-1` on CPU resolves to at least `1`.
- injected `TaskHandle` callback updates epoch progress.
- cancellation raises `TrainInterruptedError`.
- OOM-like runtime errors raise `TrainOOMError`.

- [ ] **Step 2: Run RED**

Run:

```powershell
New-Item -ItemType Directory -Force -Path pytest_tmp_codex | Out-Null
$env:PYTHONPATH=(Get-Location).Path
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_trainer.py -q --basetemp pytest_tmp_codex/trainer-red
```

Expected: FAIL because `core.trainer` does not exist.

### Task 2: Trainer Implementation

**Files:**
- Create: `core/trainer.py`

- [ ] **Step 1: Implement dataclasses and exceptions**

Implement `TrainConfig`, `TrainMetrics`, `TrainResult`, `TrainerError`, and module-specific exceptions using existing `ErrorCode` enum values.

- [ ] **Step 2: Implement validation**

Validate `data_yaml` exists, has required keys (`path`, `train`, `val`, `nc`, `names`), and `base_model` exists. Do not require data_yaml to come from Sampler.

- [ ] **Step 3: Implement YOLO boundary**

Use `_load_yolo_model(base_model)` so tests can monkeypatch it. Do not import ultralytics at module import time.

- [ ] **Step 4: Implement training call and result parsing**

Call `model.train(...)` with project/name so output is `output_dir/train`. Parse `results.csv` if present; default missing metrics to `0.0`.

- [ ] **Step 5: Implement cancellation and error mapping**

Register an epoch-end callback if the fake/real model supports `add_callback`. Callback checks `task_handle.is_cancel_requested`, updates progress, and raises `TrainInterruptedError` on cancellation. Map CUDA/OOM RuntimeError messages to `TrainOOMError`.

- [ ] **Step 6: Run GREEN and verification**

Run:

```powershell
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_trainer.py -q --basetemp pytest_tmp_codex/trainer-green
D:/miniforge3/envs/yolo_new/python.exe -m mypy --strict core/ utils/
D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py
```

### Task 3: Docs And Commit

**Files:**
- Modify: `docs/dev/CURRENT_STATE.md`
- Modify: `CHANGELOG.md`

- [ ] Update status from `trainer.py` to complete and move current task to `inferencer.py`.
- [ ] Run full tests and commit with `feat(core): implement trainer module`.
