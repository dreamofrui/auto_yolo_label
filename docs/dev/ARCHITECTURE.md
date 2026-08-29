# AutoLabeler Architecture

> Status: current architecture description.
> Last updated: 2026-08-14

This document describes the desktop-first AutoLabeler system architecture: layer
structure, module responsibilities, dependency direction, key data flows,
persistence locations, long-running task ownership, and external integrations.

It is a companion to `docs/dev/PRODUCT_SPEC.md` (product behavior contract) and
`docs/dev/UI_SPEC.md` (GUI behavior and layout baseline). It is not a per-file
maintenance map, risk log, reading order, or future-plan document.

## 1. System Context

AutoLabeler is a desktop-first YOLO semi-automatic image labeling workbench.

```text
scan -> sample -> label with LabelImg -> train -> infer
-> review with LabelImg -> restore XML labels
```

The formal product surface is the PySide6 desktop GUI. Framework-free business
logic lives in `core/`, and thin desktop adapters call `core/` from
`gui/workers/` while recording task state through `TaskRegistry`.

Active layers:
- **Desktop GUI** (`gui/`): PySide6 shell, pages, shared widgets, and UI state.
- **Business logic** (`core/`): framework-free modules with typed dataclass
  inputs and typed result outputs.
- **Worker adapters** (`gui/workers/`): thin desktop-API glue that calls
  `core/` directly and manages task lifecycle.
- **Infrastructure** (`utils/`): shared utilities such as mapping, task
  registry, path encoding, device helpers, and business exceptions.
- **Standalone server scripts** (`server_scripts/`): independent Linux/Docker
  training and prediction scripts. The desktop GUI must not depend on them.

Deleted, inactive, or non-goal layers:
- `cli/` is deleted and must not be reintroduced as an active architecture
  surface.
- `runtime/services` is deleted; desktop workers now call `core/` directly.
- `legacy/` is read-only reference. Do not edit it or copy implementation
  bodies from it.
- Web, FastAPI, browser UI, and Node subprocess integration are not current
  goals.

## 2. Dependency Direction

```text
gui/ (pages, shell, shared widgets)
  |
  +---> gui/workers/ (desktop task adapters)
  |        |
  |        +---> core/ (business logic)
  |        |
  |        +---> utils/ (task registry, exceptions)
  |
  +---> utils/ (mapping manager, path encoder, etc.)
  |
  +---> core/ (direct calls for non-worker paths)

core/ (business logic)
  +---> utils/ (exceptions, mapping manager, path encoder, device)

utils/ (standalone infrastructure --- no dependencies on core/ or gui/)

server_scripts/ (standalone --- no dependencies from GUI)
```

Rules:
- `core/` must not import GUI or HTTP frameworks.
- `utils/` must not depend on `core/`.
- `gui/workers/` stays thin; it calls `core/` directly and owns desktop task
  lifecycle glue.
- `server_scripts/` must not be imported by the desktop GUI.

## 3. Module Responsibilities

### core/scanner.py
Flow mode metadata creation. Accepts a strict `site/Code/Product/image` tree
and produces `mapping.json` and `classes.txt`. Does not move, rename, or
organize user files.

### core/sampler.py
Builds a YOLO training dataset by sampling from a scanned site (Flow mode) or
from explicit user-selected paths (Independent mode). Supports count, ratio,
and mixed strategies. Copies images and labels; does not move source data.

### core/trainer.py
Launches a YOLO training job through Ultralytics. Reports progress, metrics,
and final model path. Runs in a separate process to avoid blocking the GUI.

### core/inferencer.py
Runs YOLO prediction on a set of images. Supports Flow mode (via mapping) and
Independent mode (via explicit paths). Produces YOLO TXT labels in a
timestamped run directory.

### core/restorer.py
Writes reviewed YOLO TXT labels back as Pascal VOC XML beside original images.
Uses mapping for Flow mode restores or explicit paths for Independent mode.
Runs full preflight before writing; refuses to overwrite existing XML without
confirmation.

### core/converter.py
Converts between YOLO and VOC annotation formats. Main feature: image + XML
directory to standard YOLO dataset. Auxiliary helpers: YOLO TXT -> VOC XML and
VOC XML -> YOLO TXT. No mapping dependency.

### core/labelimg_launcher.py
Launches the external LabelImg application with the correct mode, paths, and
class file. Validates the environment before launch. Does not embed LabelImg.

### core/label_inspector.py
Resolves original images, prediction label paths, and classes for LabelImg
review in Flow mode. Used by the Review workflow to prepare paths before
launching LabelImg.

### core/annotation_formats.py
Shared YOLO TXT and Pascal VOC XML format helpers. Used by restore, conversion,
and sample flows.

## 4. Key Data Flows

### Flow Mode
```text
Scan (site/Code/Product/image tree)
  -> mapping.json, classes.txt
  -> Sample (via mapping)
  -> YOLO dataset (images + labels + data.yaml)
  -> Train (via Ultralytics)
  -> Model weights
  -> Infer (via mapping, using model)
  -> run_YYYYMMDD_HHMMSS/labels/
  -> Review with LabelImg (via mapping to resolve originals)
  -> Restore (via mapping, writes VOC XML beside original images)
```

### Independent Mode
Each module can run without `mapping.json` when explicit paths are sufficient.
Independent mode must not secretly create or require mapping.

- **Independent Sample**: explicit image root + label root -> YOLO dataset or
  XML labeling folder.
- **Independent Infer**: explicit image root + model -> run directory.
- **Independent Restore**: explicit image root + label root -> VOC XML beside
  matching images.
- **Convert**: image + XML directory -> YOLO dataset (no mapping).

## 5. Persistence Locations

| Data | Location | Owner |
|------|----------|-------|
| Flow mode metadata | `site/.autolabeler/mapping.json` | Scanner/Sampler |
| Class list | `site/.autolabeler/classes.txt` | Scanner |
| YOLO training dataset | User-selected output path | Sampler |
| Model weights | User-selected output path | Trainer |
| Inference results | `site/.autolabeler/inference_results/run_*/` (Flow) or user-selected root (Independent) | Inferencer |
| Tool defaults | `site/.autolabeler/tool_defaults.json` | GUI pages |
| Labels (VOC XML) | Beside original images | Restorer/Converter |
| Labels (YOLO TXT) | Dataset `labels/train|val` or inference run `labels/` | Sampler/Inferencer |
| Task logs | `.autolabeler/` (runtime, not product source) | TaskRegistry |
| Model weights cache | Ultralytics default cache | Trainer |

## 6. Long-Running Task Ownership

Long-running GUI work (scan, sample, train, infer, restore, convert) is
tracked through `TaskRegistry` (`utils/task_registry.py`). Each worker in
`gui/workers/`:

1. Registers a task handle with `TaskRegistry` before starting work.
2. Reports progress, intermediate results, and final status through the handle.
3. Supports cancellation via the handle's stop-requested flag.
4. Cleans up the task record on completion or failure.

Workers call `core/` modules directly in a background thread or process. The
GUI remains responsive while the task runs.

## 7. External Integrations

| Integration | Mechanism | Owner |
|-------------|-----------|-------|
| LabelImg | External process launch via `core/labelimg_launcher.py` | GUI Label/Review pages |
| YOLO (Ultralytics) | Python library, called from `core/trainer.py` and `core/inferencer.py` | Core |
| PyTorch/CUDA | Runtime dependency of Ultralytics | Core (device helpers in `utils/`) |
| Server training scripts | Standalone `server_scripts/train_yolo.py`, `predict_yolo.py` | Server operators (not GUI) |

## 8. Architecture Constraints

- `core/` is business logic only and must not import GUI or HTTP frameworks.
- `utils/` is infrastructure only and must not depend on `core/`.
- `gui/workers/` stays thin and desktop-adapter only; it calls `core/`
  directly and owns desktop task lifecycle glue.
- Use `pathlib.Path` for paths.
- Keep module boundaries explicit with dataclasses and typed results.
- Use `MappingManager` for `mapping.json`.
- Long-running work uses `TaskHandle`.
- New business exceptions inherit `AutoLabelerError` and carry an error code.
- Do not introduce new HTTP routes, schemas, CLI JSON contracts, or Node-facing
  behavior by default.

## 9. Non-Goals (Architecture)

The following are not part of the current or planned architecture:

- Web UI, FastAPI, browser UI, or Node subprocess integration.
- Active `cli/` or `runtime/service` layers.
- Multi-user login, permissions, server job queues, or cloud storage.
- Editing `legacy/` or copying legacy implementation bodies.
- Workflows that depend on AI execution.
