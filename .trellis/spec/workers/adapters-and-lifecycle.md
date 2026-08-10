# Worker Adapters And Lifecycle

## Standard Adapter Shape

`gui/workers/scan_worker.py`, `sample_worker.py`, `train_worker.py`,
`infer_worker.py`, `restore_worker.py`, `labelimg_worker.py`,
`label_inspector_worker.py`, and `convert_worker.py` follow this sequence:

1. Create and start a task with `start_worker_task`.
2. Construct the core service with the task handle (and a progress callback
   where the service supports one).
3. Call the typed core entrypoint directly.
4. Catch `AutoLabelerError`, call `finish_worker_error`, and return an outcome
   containing `ErrorInfo`.
5. On success, call `finish_worker_success` and return the typed result.

Keep this glue in `gui/workers/_task_lifecycle.py`; do not copy status mapping,
dataclass serialization, or cancellation code into each worker.

## Preflight Adapters

Sampling and restore workers expose preflight methods that do not create a
`TaskHandle` because preflight is non-writing analysis. They return a typed
preflight result and an `ErrorInfo` on known business failures. Preserve the
same core preflight semantics and do not make a worker preflight mutate files.

## Cancellation And Progress

`finish_worker_error` maps `TASK_CANCELLED` and `TRAIN_INTERRUPTED` to a
cancelled task terminal state; all other `AutoLabelerError` values become
failed tasks. `registry_progress_callback` persists current/total/message for
core services that report incremental progress. Do not mark a cancelled task
successful after the core acknowledges cancellation.

## Anti-Patterns And Tests

Do not reimplement sampling, restore matching, annotation parsing, or model
validation in a worker. Do not import GUI pages into workers. Use
`tests/test_scan_worker.py`, `tests/test_sample_worker.py`,
`tests/test_restore_worker.py`, `tests/test_infer_worker.py`,
`tests/test_train_worker.py`, `tests/test_convert_worker.py`, and
`tests/test_labelimg_worker.py` as the adapter contract examples.
