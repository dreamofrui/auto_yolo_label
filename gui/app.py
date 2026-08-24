"""AutoLabeler desktop application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from gui.workbench import AutoLabelerWindow
from gui.theme_manager import get_theme_manager


def run(argv: list[str] | None = None) -> int:
    """Run the desktop GUI application."""
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv if argv is None else argv)

    # Initialize theme manager and apply persisted theme
    theme_manager = get_theme_manager()
    app.setStyleSheet(theme_manager.get_stylesheet())

    window = AutoLabelerWindow()
    window.show()

    if owns_app:
        return app.exec()
    return 0


def main() -> int:
    """Console script compatible entry point."""
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
