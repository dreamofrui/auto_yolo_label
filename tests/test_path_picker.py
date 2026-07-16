from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from gui.path_picker import PathPicker


def app() -> QApplication:
    """Return a QApplication for widget tests."""
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication(sys.argv[:1])
    return instance


def test_path_picker_normalizes_pasted_quotes() -> None:
    """The picker should accept pasted paths with wrapping quotes."""
    app()
    picker = PathPicker(mode="directory")

    picker.setText(' "D:/tmp/site" ')

    assert picker.text() == "D:/tmp/site"
    assert picker.path() == Path("D:/tmp/site")


def test_directory_picker_browse_updates_text(monkeypatch: object) -> None:
    """Directory browsing should write the chosen folder back into the field."""
    qt_app = app()
    picker = PathPicker(mode="directory", dialog_title="选择目录")
    picker.show()
    qt_app.processEvents()

    chosen = "D:/data/site"
    monkeypatch.setattr(
        "gui.path_picker.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: chosen,
    )

    QTest.mouseClick(picker.browse_button, Qt.MouseButton.LeftButton)

    assert picker.text() == chosen


def test_file_picker_browse_updates_text(monkeypatch: object) -> None:
    """File browsing should write the chosen file back into the field."""
    qt_app = app()
    picker = PathPicker(mode="file", dialog_title="选择文件")
    picker.show()
    qt_app.processEvents()

    chosen = "D:/models/best.pt"
    monkeypatch.setattr(
        "gui.path_picker.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (chosen, ""),
    )

    QTest.mouseClick(picker.browse_button, Qt.MouseButton.LeftButton)

    assert picker.text() == chosen
