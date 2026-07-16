"""Shared path picker widget for desktop forms."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLineEdit, QToolButton

PathPickerMode = Literal["directory", "file"]


def normalize_path_text(text: str) -> str:
    """Normalize pasted path text by trimming whitespace and wrapper quotes."""
    normalized = text.strip()
    if len(normalized) >= 2:
        if normalized[0] == normalized[-1] and normalized[0] in {'"', "'"}:
            normalized = normalized[1:-1].strip()
    return normalized


class PathPicker(QFrame):
    """A compact path field with paste support and a browse button."""

    textChanged = Signal(str)

    def __init__(
        self,
        *,
        mode: PathPickerMode = "directory",
        value: str = "",
        placeholder: str = "",
        dialog_title: str | None = None,
        file_filter: str = "All Files (*)",
    ) -> None:
        super().__init__()
        self.setObjectName("pathPicker")
        self._mode = mode
        self._dialog_title = dialog_title or (
            "选择目录" if mode == "directory" else "选择文件"
        )
        self._file_filter = file_filter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.line_edit = QLineEdit()
        self.line_edit.setObjectName("formInput")
        if placeholder:
            self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.textChanged.connect(self.textChanged.emit)

        self.browse_button = QToolButton()
        self.browse_button.setObjectName("pathBrowseButton")
        self.browse_button.setText("浏览")
        self.browse_button.clicked.connect(self._browse)

        layout.addWidget(self.line_edit, 1)
        layout.addWidget(self.browse_button, 0)

        if value:
            self.setText(value)

    def text(self) -> str:
        """Return the normalized text shown in the picker."""
        return normalize_path_text(self.line_edit.text())

    def setText(self, value: str) -> None:
        """Set the picker text and keep wrapper quotes out of the field."""
        self.line_edit.setText(normalize_path_text(value))

    def clear(self) -> None:
        """Clear the picker text."""
        self.line_edit.clear()

    def path(self) -> Path:
        """Return the current text as a Path, if present."""
        text = self.text()
        if not text:
            raise ValueError("Path is empty")
        return Path(text)

    def _browse(self) -> None:
        """Open the appropriate dialog and write the selected path back."""
        if self._mode == "directory":
            selected = QFileDialog.getExistingDirectory(
                self,
                self._dialog_title,
                self._start_path(),
            )
            if selected:
                self.setText(selected)
            return

        selected, _ = QFileDialog.getOpenFileName(
            self,
            self._dialog_title,
            self._start_path(),
            self._file_filter,
        )
        if selected:
            self.setText(selected)

    def _start_path(self) -> str:
        """Pick a reasonable initial directory for the browse dialog."""
        current = normalize_path_text(self.line_edit.text())
        if not current:
            return ""
        current_path = Path(current)
        if current_path.exists():
            return str(current_path if current_path.is_dir() else current_path.parent)
        if current_path.parent.exists():
            return str(current_path.parent)
        return ""
