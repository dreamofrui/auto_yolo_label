"""Static import boundary tests."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_CORE_IMPORTS = {
    "PySide6",
    "PyQt5",
    "PyQt6",
    "fastapi",
    "flask",
    "uvicorn",
    "starlette",
}


def test_core_has_no_gui_or_http_imports() -> None:
    """Core modules must not import GUI or HTTP frameworks."""
    root = Path(__file__).resolve().parent.parent
    violations: list[str] = []
    for path in sorted((root / "core").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in FORBIDDEN_CORE_IMPORTS:
                        violations.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                module = node.module.split(".")[0]
                if module in FORBIDDEN_CORE_IMPORTS:
                    violations.append(f"{path.name}: from {node.module} import ...")

    assert violations == []
