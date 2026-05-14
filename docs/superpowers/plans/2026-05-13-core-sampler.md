# Core Sampler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `core/sampler.py` so existing `mapping.json` data can produce a YOLO `database/` dataset without forcing Scanner to run in the same workflow.

**Architecture:** `Sampler` consumes `MappingManager` as the source of truth, groups unsampled `ImageInfo` records by Code/Product, copies selected images and pre-existing labels into YOLO train/val folders, and marks mapping state only after each file succeeds. XML label conversion is implemented as a private helper for this module until the public `Converter.xml_to_txt()` module lands.

**Tech Stack:** Python 3.11 dataclasses, pathlib, shutil, xml.etree.ElementTree, standard-library file IO, `MappingManager`, `TaskHandle`, pytest, mypy strict-compatible type hints.

---

### Task 1: Sampler Tests

**Files:**
- Create: `tests/test_sampler.py`
- Create: `core/sampler.py`

- [ ] **Step 1: Write failing tests**

Cover:
- count mode creates `database/images/train`, `database/images/val`, `labels/train`, `labels/val`, `data.yaml`, and mapping sampled state.
- ratio/mixed/count target calculations.
- pre-existing TXT copy and XML conversion.
- `val`, not legacy `vals`.
- missing mapping raises `SampleMappingNotFoundError`.
- invalid config raises `SampleInvalidConfigError`.
- malformed/unknown-class XML raises `SampleXmlConvertError`.
- cancellation raises `TaskCancelledError`.

- [ ] **Step 2: Run RED**

Run:

```powershell
New-Item -ItemType Directory -Force -Path pytest_tmp_codex | Out-Null
$env:PYTHONPATH=(Get-Location).Path
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_sampler.py -q --basetemp pytest_tmp_codex/sampler-red
```

Expected: FAIL because `core.sampler` does not exist.

### Task 2: Sampler Implementation

**Files:**
- Create: `core/sampler.py`

- [ ] **Step 1: Implement public dataclasses and exceptions**

Implement `SampleConfig`, `SamplePaths`, `SampleStatistics`, `SampleResult`, `SampleError`, `SampleMappingNotFoundError`, `SampleInvalidConfigError`, `SampleXmlConvertError`, and `SampleIOError`.

- [ ] **Step 2: Implement config validation and mapping load**

Validate mode/count/ratio/min/max/full_threshold/train_ratio/site_folder. Load `site_folder/.autolabeler/mapping.json` through `MappingManager`, translating missing mapping into `SampleMappingNotFoundError`.

- [ ] **Step 3: Implement deterministic sampling plan**

Group `manager.get_unsampled_images()` by `(code, product)`. Use stable ordering, with pre-labeled items first when `pre_labeled_priority=True`. Do not add `seed` in this pass.

- [ ] **Step 4: Implement copy/convert outputs**

Copy images to encoded filenames. Copy pre-existing TXT labels. Convert pre-existing XML labels with a private helper matching YOLO output. Do not create empty labels and do not delete source labels.

- [ ] **Step 5: Implement mapping/data.yaml/task updates**

Write `data.yaml`, mark sampled items, update mapping config/statistics, save mapping, and update injected `TaskHandle`. On cancellation, raise `TaskCancelledError`; do not roll back copied files.

- [ ] **Step 6: Run GREEN and verification**

Run:

```powershell
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_sampler.py -q --basetemp pytest_tmp_codex/sampler-green
D:/miniforge3/envs/yolo_new/python.exe -m mypy --strict core/ utils/
D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py
```

Expected: all pass.

### Task 3: Docs And Commit

**Files:**
- Modify: `docs/dev/CURRENT_STATE.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update status**

Mark `sampler.py` complete, add completion note, and set the next core module to `converter.py` unless it has already landed from the parallel branch.

- [ ] **Step 2: Run full tests**

Run:

```powershell
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests -q --basetemp pytest_tmp_codex/sampler-all
D:/miniforge3/envs/yolo_new/python.exe -m mypy --strict core/ utils/
D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py
```

- [ ] **Step 3: Commit**

Commit implementation and docs with:

```powershell
git add core/sampler.py tests/test_sampler.py docs/dev/CURRENT_STATE.md CHANGELOG.md docs/superpowers/plans/2026-05-13-core-sampler.md
git commit -m "feat(core): implement sampler module"
```
