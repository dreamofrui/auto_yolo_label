# Design: AutoLabeler Trellis Spec Refresh

## Spec Topology

The repository is a single Python desktop application. The spec tree follows
runtime ownership rather than the generated full-stack `backend/frontend`
split:

- `core/`: framework-free business workflows and annotation contracts.
- `gui/`: PySide6 shell, pages, shared controls, and user-facing state.
- `workers/`: the `gui/workers/` desktop adapter boundary.
- `utils/`: mapping, task persistence, errors, paths, devices, and logging.
- `server_scripts/`: standalone Linux/Docker training and prediction tools.
- `guides/`: cross-layer data-flow and reuse checks.

Each layer gets an `index.md` with a pre-development checklist and a quality
check section. Topic files stay small enough to load independently and link to
the source and tests that establish each rule.

## Evidence Map

- Public core contracts: `tests/test_contracts.py`, `core/scanner.py`,
  `core/sampler.py`, `core/trainer.py`, `core/inferencer.py`,
  `core/restorer.py`, and `core/converter.py`.
- Annotation semantics: `core/annotation_formats.py`,
  `tests/test_annotation_formats.py`, and `CONTEXT.md`.
- Filesystem safety: sampler and restorer preflight methods plus
  `tests/test_sampler.py` and `tests/test_restorer.py`.
- GUI composition: `gui/workbench.py`, `gui/tool_page_chrome.py`,
  `gui/path_picker.py`, `gui/task_runner.py`, and `tests/test_gui_shell.py`.
- Worker lifecycle: `gui/workers/_task_lifecycle.py`, worker adapters, and
  `tests/test_*_worker.py` / `tests/test_service_cancellation.py`.
- Shared infrastructure: `utils/mapping_manager.py`, `utils/task_registry.py`,
  `utils/exceptions.py`, `utils/device.py`, `utils/logging_setup.py`, and
  their focused tests.
- Standalone operations: `server_scripts/README.md`,
  `server_scripts/train_yolo.py`, `server_scripts/predict_yolo.py`, and
  `tests/test_server_scripts.py`.

## Boundary Decisions

Core may depend on `utils` contracts but never on PySide6, HTTP frameworks, or
the GUI. Workers import core directly and own only task lifecycle translation.
Pages construct typed configs and render outcomes; they do not implement file
selection, annotation conversion, mapping mutation, or model operations.
`server_scripts` is documented as an operational surface and remains separate
from the desktop import graph.

## Compatibility

This refresh changes documentation and Trellis task artifacts only. It does not
change product behavior, public Python contracts, test data, dependencies, or
the generated runtime templates under `.trellis/scripts/`.
