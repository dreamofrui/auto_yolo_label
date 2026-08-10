# Cross-Layer Data Flow Guide

Trace a feature through the real AutoLabeler path before editing more than one
layer:

```text
GUI form -> typed worker config -> core operation -> MappingManager/files
        <- outcome/ErrorInfo <- TaskRegistry progress and terminal state
```

## Boundary Questions

| Boundary | Contract owner | Verify |
| --- | --- | --- |
| Page -> worker | Page-specific config builder and worker protocol | `tests/test_gui_shell.py` and the matching worker test |
| Worker -> core | Core dataclass entrypoint and typed outcome | `tests/test_contracts.py`, worker tests |
| Core -> mapping | `MappingManager` and `ImageInfo` state markers | `tests/test_mapping_manager.py` plus scan/sample/infer/restore tests |
| Core -> annotations | `core.annotation_formats` and `CONTEXT.md` | `tests/test_annotation_formats.py` and row-level restore diagnostics |
| Core -> task | `TaskHandle` progress/cancellation contract | `tests/test_task_registry.py`, `tests/test_service_cancellation.py` |
| Core -> filesystem | Preflight plan and explicit overwrite/move confirmation | `tests/test_sampler.py`, `tests/test_restorer.py`, `tests/test_converter.py` |

## Flow And Independent

Make mode a typed/configured choice, not an implicit dependency. Flow sampling
and restore use mapping to preserve source relationships; Independent sampling,
inference, and restore operate from explicit roots and must not create or read
mapping. If a path or output structure changes, update the core config/result,
worker adapter, page state, focused tests, and `PRODUCT_SPEC.md`/`UI_SPEC.md`
only when the documented behavior actually changes.

## Errors And Safety

Validate once at the core boundary, return structured preflight issues, and
surface `ErrorInfo` through the worker. A page may format a message, but it
must not reinterpret class ids, path identities, or task statuses. For any
move, delete, overwrite, or restore path, prove that preflight completes before
the first write and that a blocker leaves source and output unchanged.

## Verification

Use GitNexus query/context to locate the execution flow, then read the source
and tests before documenting or changing it. Run the focused tests at each
boundary and the import/discipline checks before declaring a cross-layer task
complete.
