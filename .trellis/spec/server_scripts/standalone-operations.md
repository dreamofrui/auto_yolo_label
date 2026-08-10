# Standalone Operations

## Training

`server_scripts/train_yolo.py` accepts `--data-yaml`, `--base-model`,
`--output-dir`, `--device`, epochs, image size, batch, run name, overwrite,
cache, and log-file options. It prints the run directory and model paths and
can be run under `nohup` with an explicit log file. Keep the script's device
semantics aligned with `utils.device.resolve_device` without importing that
module into the standalone surface.

## Prediction

`server_scripts/predict_yolo.py` recursively scans supported image suffixes,
does not require mapping or copy images, and writes a separate
`run_YYYYMMDD_HHMMSS` directory with `inference_config.json`, `classes.txt`,
progress/log artifacts, and `labels/` preserving source-relative paths. Batch
failures are retried per image and individual failures receive `.error.txt`
files. Keep `--label-y-offset-px` behavior explicit and default it to zero.

## Boundary

The desktop GUI has its own `core.trainer` and `core.inferencer` paths. Do not
make a GUI worker shell out to these scripts or make the scripts depend on
`.autolabeler/mapping.json`. Update `server_scripts/README.md` and
`tests/test_server_scripts.py` together when a command or output contract
changes.
