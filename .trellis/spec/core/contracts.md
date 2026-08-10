# Core Contracts

## One Typed Configuration In

Public workflow methods accept one dataclass configuration and return a typed
result. This is enforced by `tests/test_contracts.py`.

Examples:

- `Scanner.scan(ScanConfig) -> ScanResult` in `core/scanner.py`.
- `Sampler.sample(SampleConfig) -> SampleResult` and its explicit
  `preflight` method in `core/sampler.py`.
- `Trainer.train(TrainConfig) -> TrainResult` in `core/trainer.py`.
- `Inferencer.infer(InferConfig) -> InferResult` in `core/inferencer.py`.
- `Restorer.restore(RestoreConfig) -> RestoreResult` in `core/restorer.py`.
- `Converter.convert_xml_dataset(XmlDatasetConvertConfig)` plus the smaller
  `TxtToXmlConfig` and `XmlToTxtConfig` operations in `core/converter.py`.

Keep configs frozen when they describe caller input. Keep result dataclasses
focused on paths, counts, warnings, diagnostics, and other data the GUI or
tests need. Do not add untyped `**kwargs` or make a page pass a raw dictionary
into core.

## Dependency Direction

Core modules may import `utils` contracts such as `MappingManager`,
`TaskHandle`, `ErrorCode`, and `resolve_device`. They must not import GUI
widgets, Qt event loops, HTTP frameworks, or desktop page modules. The static
boundary is covered by `tests/test_imports.py` and `scripts/check_disciplines.py`.

## Progress And Cancellation

Long-running loops accept an optional `TaskHandle` and update its progress
fields through the owning core service. `Scanner`, `Sampler`, `Restorer`, and
`Converter` check cancellation during file loops; `Trainer` and `Inferencer`
also use progress callbacks where model work is involved. Raise
`utils.exceptions.TaskCancelledError` (or a domain error with the cancellation
code) so the worker can preserve a cancelled terminal state.

## Errors

Business failures inherit `AutoLabelerError` and define an `ErrorCode`, as in
`core/scanner.py`, `core/sampler.py`, and `core/trainer.py`. Include a concise
user message and useful path/row diagnostics in `details`; let the worker
convert the exception to `ErrorInfo` instead of inventing a second error shape.

## Test Shape

Use `tmp_path` fixtures and small synthetic files. The tests in
`tests/test_scanner.py`, `tests/test_sampler.py`, `tests/test_restorer.py`, and
`tests/test_converter.py` assert both returned dataclasses and filesystem
effects. When behavior is destructive, assert that preflight failure leaves
the source and output unchanged.
