# Core LabelInspector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `core/label_inspector.py` so desktop and HTTP callers can browse inference runs and label files without depending on `mapping.json`.

**Architecture:** `LabelInspector` is a pure read-only filesystem query module. It scans `site_folder/.autolabeler/inference_results`, parses optional run config snapshots defensively, summarizes Code/Product label trees, and resolves original image paths by checking common image suffixes under `site_folder/<code>/<product>/`.

**Tech Stack:** Python 3.11 dataclasses, pathlib, json, datetime fallback formatting, `AutoLabelerError` / `ErrorCode`, pytest tmp_path fixtures, mypy strict-compatible types.

---

### Task 1: LabelInspector Tests

**Files:**
- Create: `tests/test_label_inspector.py`
- Create: `core/label_inspector.py`

- [ ] **Step 1: Write failing tests**

Cover:
- construction and dataclass defaults.
- `list_runs` returns sorted run directories, parses valid `inference_config.json`, and does not require `mapping.json`.
- invalid `inference_config.json` returns `config_exists=False` and `config=None`.
- `get_run_tree` raises `InspectorRunNotFoundError` for missing run.
- `get_run_tree` filters control files and counts empty TXT labels per product.
- `get_product_labels` raises `InspectorProductNotFoundError` for missing Code/Product.
- `get_product_labels` filters control files, counts non-empty annotation rows, and resolves original image paths or `None`.

- [ ] **Step 2: Run RED**

Run:

```powershell
New-Item -ItemType Directory -Force -Path pytest_tmp_codex | Out-Null
$env:PYTHONPATH=(Get-Location).Path
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_label_inspector.py -q --basetemp pytest_tmp_codex/label-inspector-red
```

Expected: FAIL because `core.label_inspector` does not exist.

### Task 2: LabelInspector Implementation

**Files:**
- Create: `core/label_inspector.py`

- [ ] **Step 1: Implement public contracts**

Define `ListRunsConfig`, `GetRunTreeConfig`, `GetProductLabelsConfig`, `InferenceRun`, `RunTreeNode`, and `ProductLabel` as dataclasses matching `01-requirements.md`.

- [ ] **Step 2: Implement exceptions**

Define `InspectorError`, `InspectorRunNotFoundError`, and `InspectorProductNotFoundError` using `ErrorCode.INSPECTOR_*`.

- [ ] **Step 3: Implement read-only filesystem queries**

Use only `pathlib.Path`. Do not instantiate `MappingManager` and do not read `mapping.json`. Filter `classes.txt`, `data.yaml`, and `README.txt`.

- [ ] **Step 4: Run GREEN and strict checks**

Run:

```powershell
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_label_inspector.py -q --basetemp pytest_tmp_codex/label-inspector-green
D:/miniforge3/envs/yolo_new/python.exe -m mypy --strict core/ utils/
D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py
```

### Task 3: Docs And Commit

**Files:**
- Modify: `docs/dev/CURRENT_STATE.md`
- Modify: `CHANGELOG.md`

- [ ] Mark `label_inspector.py` complete and move current work to `restorer.py`.
- [ ] Run full target verification and commit with `feat(core): implement label inspector module`.
