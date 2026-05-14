# Core Restorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `core/restorer.py` so reviewed database labels or inference run labels can be copied back beside original source images through `mapping.json`.

**Architecture:** `Restorer` loads mapping through `MappingManager`, resolves either database label folders or inference run folders, filters non-label control files, copies each valid label to `site_folder/Code/Product/Image.txt`, records per-file failures without aborting the batch, and marks successfully restored mapping entries.

**Tech Stack:** Python 3.11 dataclasses, pathlib, shutil, loguru, `MappingManager`, `TaskHandle`, `AutoLabelerError`, pytest tmp_path fixtures, mypy strict-compatible types.

---

### Task 1: Restorer Tests

**Files:**
- Create: `tests/test_restorer.py`
- Create: `core/restorer.py`

- [ ] **Step 1: Write failing tests**

Cover:
- construction and public dataclass defaults.
- database source restores labels from `labels/train` and `labels/val`.
- inference source restores labels by `run_id` and by explicit `inference_run_dir`.
- target exists and already-restored mapping entries skip when `overwrite=False`.
- `overwrite=True` replaces existing target labels.
- control files are filtered.
- unknown database mapping key and unknown inference label path become per-file failures.
- copy failures become per-file failures and continue.
- missing mapping, invalid source type, missing source inputs, and missing source directories raise module exceptions.
- `TaskHandle` progress and cancellation.

- [ ] **Step 2: Run RED**

Run:

```powershell
New-Item -ItemType Directory -Force -Path pytest_tmp_codex | Out-Null
$env:PYTHONPATH=(Get-Location).Path
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_restorer.py -q --basetemp pytest_tmp_codex/restorer-red
```

Expected: FAIL because `core.restorer` does not exist.

### Task 2: Restorer Implementation

**Files:**
- Create: `core/restorer.py`

- [ ] **Step 1: Implement public contracts**

Define `RestoreConfig`, `RestoreResult`, `RestoreFileError`, and `RestoreError` type alias matching `01-requirements.md`.

- [ ] **Step 2: Implement exceptions**

Define `RestorerError`, `RestoreSourceNotFoundError`, `RestoreMappingNotFoundError`, and `RestoreInvalidSourceTypeError`.

- [ ] **Step 3: Implement restore behavior**

Use `MappingManager` for all mapping access. Use `PathEncoder` only to validate database encoded stems when useful. Filter `classes.txt`, `data.yaml`, and `README.txt`. Save mapping after successful restores. Do not call `mark_inferred()`.

- [ ] **Step 4: Run GREEN and strict checks**

Run:

```powershell
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_restorer.py -q --basetemp pytest_tmp_codex/restorer-green
D:/miniforge3/envs/yolo_new/python.exe -m mypy --strict core/ utils/
D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py
```

### Task 3: Docs And Commit

**Files:**
- Modify: `docs/dev/CURRENT_STATE.md`
- Modify: `CHANGELOG.md`

- [ ] Mark `restorer.py` complete and move current work to `labelimg_launcher.py`.
- [ ] Run full target verification and commit with `feat(core): implement restorer module`.
