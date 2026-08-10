# Server Scripts Layer

`server_scripts/` contains standalone offline training and prediction commands
for Linux/Docker GPU environments. These scripts are operational tools, not a
second application service layer and not a dependency of the PySide6 GUI.

## Read Before Editing

- [Standalone operations](./standalone-operations.md)
- `server_scripts/README.md` for supported commands and output layout
- `tests/test_server_scripts.py` for CLI and serialization coverage

## Quality Check

- Keep argument parsing and process output in the script; do not import GUI,
  workbench, or worker modules.
- Preserve the documented train/predict flags, separate timestamped run
  directories, `inference_config.json`, log files, and relative label paths.
- Test argument validation and filesystem behavior without requiring a live
  CUDA device or a full training run.
