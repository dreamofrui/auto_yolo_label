# M1.3 Remaining Entry Adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the remaining thin desktop and HTTP adapters for train, infer, restore, convert, label inspection, and LabelImg launch while keeping core modules framework-free.

**Architecture:** Each adapter slice follows the existing scan/sample pattern: pydantic request schema -> core dataclass config -> shared service with `TaskRegistry` lifecycle -> HTTP route or desktop worker response. Routes and workers contain no business logic; `api/main.py`, `CHANGELOG.md`, and `docs/dev/CURRENT_STATE.md` are integrated once after all module slices are ready.

**Tech Stack:** Python 3.11, FastAPI, pydantic v2 camelCase schemas, pytest, `utils.task_registry.TaskRegistry`, core dataclass contracts.

---

## File Boundaries

- Shared registration/docs owned by controller only:
  - Modify: `api/main.py`
  - Modify: `CHANGELOG.md`
  - Modify: `docs/dev/CURRENT_STATE.md`
- Train slice:
  - Create: `api/schemas/train.py`
  - Create: `api/services/train_service.py`
  - Create: `api/routes/train.py`
  - Create: `gui/workers/train_worker.py`
  - Test: `tests/api/test_train_route.py`
  - Test: `tests/test_train_worker.py`
- Infer slice:
  - Create: `api/schemas/infer.py`
  - Create: `api/services/infer_service.py`
  - Create: `api/routes/infer.py`
  - Create: `gui/workers/infer_worker.py`
  - Test: `tests/api/test_infer_route.py`
  - Test: `tests/test_infer_worker.py`
- Restore slice:
  - Create: `api/schemas/restore.py`
  - Create: `api/services/restore_service.py`
  - Create: `api/routes/restore.py`
  - Create: `gui/workers/restore_worker.py`
  - Test: `tests/api/test_restore_route.py`
  - Test: `tests/test_restore_worker.py`
- Convert slice:
  - Create: `api/schemas/convert.py`
  - Create: `api/services/convert_service.py`
  - Create: `api/routes/convert.py`
  - Create: `gui/workers/convert_worker.py`
  - Test: `tests/api/test_convert_route.py`
  - Test: `tests/test_convert_worker.py`
- Label inspector slice:
  - Create: `api/schemas/label_inspector.py`
  - Create: `api/services/label_inspector_service.py`
  - Create: `api/routes/label_inspector.py`
  - Create: `gui/workers/label_inspector_worker.py`
  - Test: `tests/api/test_label_inspector_route.py`
  - Test: `tests/test_label_inspector_worker.py`
- LabelImg slice:
  - Create: `api/schemas/labelimg.py`
  - Create: `api/services/labelimg_service.py`
  - Create: `api/routes/labelimg.py`
  - Create: `gui/workers/labelimg_worker.py`
  - Test: `tests/api/test_labelimg_route.py`
  - Test: `tests/test_labelimg_worker.py`

## Shared Adapter Contract

- Services create one task with the module type, start it, call the core module with the task handle where the core supports one, then call `succeed_task` or `fail_task`.
- Services return frozen outcome dataclasses with `success`, `task`, `result`, and `error`.
- Workers accept the core config dataclass and return frozen worker outcome dataclasses with `ErrorInfo | None`.
- Route tests may create `app = create_app(task_registry=registry)` and include the module router manually. The final controller commit will add permanent router registration in `api/main.py`.
- Tests must monkeypatch YOLO loaders for train and infer. Do not invoke Ultralytics.
- No adapter may import or modify `legacy/`.

## Task 1: Train Adapter

- [ ] Write failing route and worker tests for `POST /api/train` using camelCase request fields.
- [ ] Monkeypatch `core.trainer._load_yolo_model` with a fake model that writes `weights/best.pt` and `results.csv`.
- [ ] Implement train schema, service, route, and worker.
- [ ] Verify `pytest tests/api/test_train_route.py tests/test_train_worker.py -q` fails before implementation and passes after implementation.
- [ ] Commit only train adapter files on branch `agent-entry-train`.

## Task 2: Infer Adapter

- [ ] Write failing route and worker tests for `POST /api/infer` using camelCase request fields.
- [ ] Monkeypatch `core.inferencer._load_yolo_model` with a fake predictor that returns deterministic empty or one-box results.
- [ ] Implement infer schema, service, route, and worker.
- [ ] Verify `pytest tests/api/test_infer_route.py tests/test_infer_worker.py -q` fails before implementation and passes after implementation.
- [ ] Commit only infer adapter files on branch `agent-entry-infer`.

## Task 3: Restore Adapter

- [ ] Write failing route and worker tests for `POST /api/restore` using camelCase request fields.
- [ ] Use real `Scanner` fixtures to create `mapping.json` and source label files.
- [ ] Implement restore schema, service, route, and worker.
- [ ] Verify `pytest tests/api/test_restore_route.py tests/test_restore_worker.py -q` fails before implementation and passes after implementation.
- [ ] Commit only restore adapter files on branch `agent-entry-restore`.

## Task 4: Convert Adapter

- [ ] Write failing route and worker tests for `POST /api/convert/yolo-to-voc` and `POST /api/convert/voc-to-yolo`.
- [ ] Use tiny PIL image fixtures and simple YOLO/VOC annotations.
- [ ] Implement convert schema, service, route, and worker.
- [ ] Verify `pytest tests/api/test_convert_route.py tests/test_convert_worker.py -q` fails before implementation and passes after implementation.
- [ ] Commit only convert adapter files on branch `agent-entry-convert`.

## Task 5: Label Inspector Adapter

- [ ] Write failing route and worker tests for run listing, run tree, and product labels.
- [ ] Implement label inspector schema, service, route, and worker.
- [ ] Verify `pytest tests/api/test_label_inspector_route.py tests/test_label_inspector_worker.py -q` fails before implementation and passes after implementation.
- [ ] Commit with controller-owned files only.

## Task 6: LabelImg Adapter

- [ ] Write failing route and worker tests for validate and launch using a fake subprocess runner or monkeypatched launcher.
- [ ] Implement LabelImg schema, service, route, and worker.
- [ ] Verify `pytest tests/api/test_labelimg_route.py tests/test_labelimg_worker.py -q` fails before implementation and passes after implementation.
- [ ] Commit with controller-owned files only.

## Task 7: Integration Registration

- [ ] Add all routers to `api/main.py`.
- [ ] Run all API and worker tests.
- [ ] Update `CHANGELOG.md` and `docs/dev/CURRENT_STATE.md`.
- [ ] Run `pytest tests -q`, `mypy --strict core/ utils/`, and `python scripts/check_disciplines.py`.
- [ ] Commit the final integration state without staging `AGENTS.md`, `notes/`, or `yolov8n.pt`.
