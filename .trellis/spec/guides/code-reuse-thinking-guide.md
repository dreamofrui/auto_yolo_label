# Code Reuse Guide

Search for an existing owner before creating a helper. This repository already
has shared contracts for the patterns most likely to be duplicated.

## Search Targets

- `MappingManager` for all mapping reads, writes, state markers, and Flow
  filters.
- `annotation_formats.py` for YOLO/VOC parsing, geometry validation, and
  serialization.
- `TaskHandle`, `TaskRegistry`, and `gui/workers/_task_lifecycle.py` for task
  state, progress, cancellation, and JSON payload conversion.
- `PathEncoder` for flattened Flow names and `PathPicker` for GUI path input.
- `resolve_device` for CPU/GPU/MPS validation and batch defaults.
- `build_log_box`, `constrain_feedback_label`, and the page chrome helpers for
  repeated GUI surfaces.

Use `rg -n "MappingManager|TaskRegistry|parse_yolo_label_text|PathEncoder|PathPicker"`
before adding a new implementation. Check the module matrix in
`docs/dev/ONBOARDING_SUMMARY.md` to find the owning layer.

## When To Extract

Extract a helper when the same non-trivial rule appears in at least two
workflow modules, when a parser or safety check would otherwise diverge, or
when a shared result/error contract needs one owner. Keep one-use, obvious
expressions local when extraction would make the call path harder to follow.

## Local Anti-Patterns

- Reading `mapping.json` with `json.load` outside `MappingManager`.
- Reimplementing YOLO geometry checks in Restore, Convert, or a worker.
- Copying task status/error serialization into each worker.
- Adding a page-local path picker or a second device parser.
- Copying implementation from `legacy/` or reviving removed web/CLI/runtime
  surfaces.

After a batch change, search again for the old pattern and run
`scripts/check_disciplines.py` plus the focused tests.
