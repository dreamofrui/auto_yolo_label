# Core Inferencer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `core/inferencer.py` so trained YOLO models can run batch inference and write reviewable YOLO TXT outputs into timestamped run folders.

**Architecture:** `Inferencer` validates model/device/image inputs, resolves images either from `MappingManager` or explicit custom paths, loads YOLO lazily through an internal factory, writes one TXT per image under `inference_results/run_*`, records a JSON config snapshot, and updates mapping inferred statistics when mapping is involved.

**Tech Stack:** Python 3.11 dataclasses, pathlib, json, datetime, lazy `ultralytics` import, `utils.device`, `MappingManager`, `TaskHandle`, pytest monkeypatching, mypy strict-compatible type hints.

---

### Task 1: Inferencer Tests

**Files:**
- Create: `tests/test_inferencer.py`
- Create: `core/inferencer.py`

- [ ] Write failing tests for constructor, missing model, custom inference success, mapping unsampled filtering, all-image filtering, missing image, missing mapping for non-custom, model load failure, device validation, empty prediction file output, and TaskHandle progress/cancellation.
- [ ] Run RED with `pytest tests/test_inferencer.py -q`; expected failure is missing `core.inferencer`.

### Task 2: Inferencer Implementation

**Files:**
- Create: `core/inferencer.py`

- [ ] Implement public dataclasses and module exceptions.
- [ ] Implement mapping/custom image selection without assuming Scanner ran in this process.
- [ ] Implement lazy YOLO load and fake-friendly prediction parsing.
- [ ] Write output TXT files, including empty files for empty predictions.
- [ ] Write `inference_config.json` and mark mapping images inferred when applicable.
- [ ] Run target tests, mypy, and discipline checks.

### Task 3: Docs And Commit

**Files:**
- Modify: `docs/dev/CURRENT_STATE.md`
- Modify: `CHANGELOG.md`

- [ ] Mark inferencer complete and move current work to `label_inspector.py`.
- [ ] Run full verification and commit with `feat(core): implement inferencer module`.
