# M1 Integration Scenarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the four mandatory decoupling integration scenarios from `02-constraints.md` section 2.3.

**Architecture:** The tests exercise real core module boundaries with filesystem fixtures while monkeypatching only external YOLO model loading. They verify that modules can be composed without GUI/API code and that non-standard paths such as skipping scan or training remain supported.

**Tech Stack:** pytest, pathlib, Pillow for tiny image fixtures, existing core modules, `MappingManager`, monkeypatching lazy YOLO factories.

---

### Task 1: Integration Test Helpers

**Files:**
- Create: `tests/integration/test_scenario_a.py`
- Create: `tests/integration/test_scenario_b.py`
- Create: `tests/integration/test_scenario_c.py`
- Create: `tests/integration/test_scenario_d.py`

- [ ] Create small helper functions in each file rather than a shared fixture module for now.
- [ ] Use tiny generated JPEG/PNG files so converter paths can read image dimensions.
- [ ] Use fake YOLO trainers/predictors and monkeypatch `_load_yolo_model` in trainer/inferencer tests.

### Task 2: Scenario Tests

**Files:**
- Test: `tests/integration/test_scenario_a.py`
- Test: `tests/integration/test_scenario_b.py`
- Test: `tests/integration/test_scenario_c.py`
- Test: `tests/integration/test_scenario_d.py`

- [ ] Scenario A: clean site `Scan -> Sample -> manual label -> Train -> Infer -> Restore`.
- [ ] Scenario B: hand-written mapping + database `Train -> Infer -> Restore`.
- [ ] Scenario C: external best model + custom image `Infer(custom) -> Restore`.
- [ ] Scenario D: standalone `Converter.txt_to_xml`.
- [ ] Run RED before implementation if any helper production code is needed. Expected: these are test-only additions, so tests should pass once written against existing core.

### Task 3: Verification And Docs

**Files:**
- Modify: `docs/dev/CURRENT_STATE.md`
- Modify: `CHANGELOG.md`

- [ ] Run `pytest tests/integration -q`.
- [ ] Run full `pytest tests -q`, `mypy --strict core/ utils/`, and `scripts/check_disciplines.py`.
- [ ] Mark integration scenarios complete and commit with `test(integration): add mandatory m1 scenarios`.
