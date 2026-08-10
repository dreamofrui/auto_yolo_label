# Shared Infrastructure

## MappingManager

`utils/mapping_manager.py` is the sole owner of `.autolabeler/mapping.json`.
Use `create_new`, `load`, `save`, `add_class`, `add_image`, and the explicit
state markers (`mark_sampled`, `mark_labeled`, `mark_inferred`,
`mark_restored`). Query helpers such as `get_unsampled_images`,
`get_pending_inference_images`, and `get_sampled_images` encode product
semantics; do not rebuild those filters from raw JSON.

`MappingData` stores classes, image metadata, products, statistics, and Flow
state. `MappingManager.save` writes a temporary file and replaces the target;
keep that atomic write shape. Verify mapping behavior with
`tests/test_mapping_manager.py` and the workflow tests that assert state after
scan, sample, infer, and restore.

## TaskRegistry And TaskHandle

`utils/task_registry.py` persists `TaskHandle` JSON with camelCase keys. Active
statuses are `queued` and `running`; terminal statuses are `succeeded`,
`failed`, `cancelled`, and `interrupted`. Only one active task of a given type
is allowed. On registry reload, unfinished tasks become `interrupted`; active
tasks cannot be deleted, while terminal records can be removed or retained by
the cleanup policy. Use `tests/test_task_registry.py` as the lifecycle source
of truth.

## Errors

`ErrorCode`, `ErrorInfo`, and `AutoLabelerError` define the shared failure
contract. Preserve the stable code, human message, optional details, and
retryable flag. New business exceptions inherit `AutoLabelerError` and set a
specific code; workers call `to_error_info()` rather than serializing
exceptions ad hoc. See `tests/test_exceptions.py`.

## Paths, Devices, And Logs

- `PathEncoder` owns the `Code__Product__filename` flattening format and rejects
  separator collisions; use it only where the output contract is flat.
- `utils/device.py` lazily probes Torch and resolves `auto`, `cpu`, `gpu`,
  `mps`, and CUDA id lists; keep device validation out of GUI pages.
- `utils/logging_setup.py` configures managed loguru stderr/file sinks with
  rotation and retention. Use structured context and avoid exposing wrapper
  commands or secrets in user-facing logs.
