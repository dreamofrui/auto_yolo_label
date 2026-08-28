"""Persisted default parameters for GUI tool pages."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ToolDefaults:
    """Default parameters for tool pages.

    Includes both non-path parameters (numeric/enum) and tool configuration paths
    (Python interpreter, external tool paths). Work data paths (input/output dirs)
    are not persisted here.
    """

    sample: dict[str, object] = field(default_factory=dict)
    train: dict[str, object] = field(default_factory=dict)
    infer: dict[str, object] = field(default_factory=dict)
    convert: dict[str, object] = field(default_factory=dict)
    restore: dict[str, object] = field(default_factory=dict)
    labelimg: dict[str, object] = field(default_factory=dict)


def _get_app_root() -> Path:
    """Return application root directory for user configuration.

    Always returns the user's home directory to ensure configs are writable
    in both development and packaged modes. This avoids permission issues
    when installed to system directories like Program Files.

    Returns:
        User home directory (e.g., C:/Users/username on Windows)
    """
    return Path.home()


DEFAULT_TOOL_DEFAULTS_PATH = _get_app_root() / ".autolabeler" / "tool_defaults.json"


def load_tool_defaults(path: Path | None = None) -> ToolDefaults:
    """Load persisted GUI tool defaults, falling back to empty overrides."""
    config_path = path or DEFAULT_TOOL_DEFAULTS_PATH
    if not config_path.exists() or not config_path.is_file():
        return ToolDefaults()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ToolDefaults()
    if not isinstance(raw, dict):
        return ToolDefaults()
    return ToolDefaults(
        sample=_dict_value(raw, "sample"),
        train=_dict_value(raw, "train"),
        infer=_dict_value(raw, "infer"),
        convert=_dict_value(raw, "convert"),
        restore=_dict_value(raw, "restore"),
        labelimg=_dict_value(raw, "labelimg"),
    )


def save_tool_defaults(defaults: ToolDefaults, path: Path | None = None) -> Path:
    """Persist GUI tool defaults as UTF-8 JSON."""
    config_path = path or DEFAULT_TOOL_DEFAULTS_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        key: value for key, value in asdict(defaults).items() if value
    }
    config_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return config_path


def default_text(defaults: ToolDefaults, section: str, key: str, fallback: str) -> str:
    """Read one default value as display text."""
    value = _section(defaults, section).get(key)
    if value is None:
        return fallback
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def default_bool(defaults: ToolDefaults, section: str, key: str, fallback: bool) -> bool:
    """Read one default value as bool."""
    value = _section(defaults, section).get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    if isinstance(value, int):
        return bool(value)
    return fallback


def default_path(defaults: ToolDefaults, section: str, key: str, fallback: str) -> str:
    """Read one default value as path string.

    Returns the configured path if present, otherwise returns fallback.
    Does not validate path existence - validation happens at usage time.
    However, validates that the value can be converted to a valid Path object.

    Args:
        defaults: Tool defaults configuration
        section: Configuration section name
        key: Configuration key name
        fallback: Default value if not configured or invalid

    Returns:
        Configured path string or fallback
    """
    value = _section(defaults, section).get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        return fallback
    try:
        # Validate it's a valid path string (not that it exists)
        Path(str(value))
        return str(value)
    except (ValueError, TypeError, OSError):
        # Invalid path string (e.g., null bytes, invalid characters)
        return fallback


def _section(defaults: ToolDefaults, section: str) -> dict[str, object]:
    value = getattr(defaults, section, {})
    return value if isinstance(value, dict) else {}


def _dict_value(source: dict[str, Any], key: str) -> dict[str, object]:
    value = source.get(key)
    return value if isinstance(value, dict) else {}
