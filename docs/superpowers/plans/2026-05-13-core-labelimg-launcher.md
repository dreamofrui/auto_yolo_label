# Core LabelImg Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `core/labelimg_launcher.py` as a testable integration boundary for validating an external Python interpreter and launching LabelImg.

**Architecture:** `LabelImgLauncher` exposes `validate` and `launch` with dataclass-only inputs. It uses an injectable subprocess runner for deterministic tests, validates filesystem inputs with `Path`, starts LabelImg through list argv, maps failures to business exceptions, and returns immediately with process metadata.

**Tech Stack:** Python 3.11 dataclasses, pathlib, subprocess, shlex display formatting, `AutoLabelerError` / `ErrorCode`, pytest fakes, mypy strict-compatible protocols.

---

### Task 1: LabelImg Launcher Tests

**Files:**
- Create: `tests/test_labelimg_launcher.py`
- Create: `core/labelimg_launcher.py`

- [ ] **Step 1: Write failing tests**

Cover:
- construction and dataclass defaults.
- `validate` success with Python and LabelImg version probes.
- `validate` missing Python and missing LabelImg as non-throwing invalid results.
- `launch` missing Python, missing image directory, missing classes file, missing LabelImg, and process start failures.
- `launch` default and explicit `label_dir` / `classes_file` command construction.
- subprocess execution uses list argv and returns process id plus display command.

- [ ] **Step 2: Run RED**

Run:

```powershell
New-Item -ItemType Directory -Force -Path pytest_tmp_codex | Out-Null
$env:PYTHONPATH=(Get-Location).Path
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_labelimg_launcher.py -q --basetemp pytest_tmp_codex/labelimg-red
```

Expected: FAIL because `core.labelimg_launcher` does not exist.

### Task 2: LabelImg Launcher Implementation

**Files:**
- Create: `core/labelimg_launcher.py`

- [ ] **Step 1: Implement contracts and exceptions**

Define `LabelImgConfig`, `LabelImgValidateConfig`, `LabelImgValidateResult`, `LabelImgLaunchResult`, and `LabelImg*Error` classes with existing `ErrorCode` members.

- [ ] **Step 2: Implement runner abstraction**

Add a private protocol and default subprocess runner. Use `subprocess.run(..., capture_output=True, text=True, check=False)` for probes and `subprocess.Popen(list_args)` for launch. Never use `shell=True`.

- [ ] **Step 3: Implement validate and launch**

Keep `validate` non-throwing and return invalid result on probe failures. Keep `launch` exception-driven for invalid launch inputs. Default `label_dir` to `image_dir`; default `classes_file` to `image_dir / "classes.txt"` and fail fast if missing.

- [ ] **Step 4: Run GREEN and strict checks**

Run:

```powershell
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_labelimg_launcher.py -q --basetemp pytest_tmp_codex/labelimg-green
D:/miniforge3/envs/yolo_new/python.exe -m mypy --strict core/ utils/
D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py
```

### Task 3: Docs And Commit

**Files:**
- Modify: `docs/dev/CURRENT_STATE.md`
- Modify: `CHANGELOG.md`

- [ ] Mark `labelimg_launcher.py` complete and move current work to M1 integration scenarios / M1.3 entry layers.
- [ ] Run full target verification and commit with `feat(core): implement labelimg launcher module`.
