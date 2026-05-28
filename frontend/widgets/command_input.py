"""Command input widget."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QPushButton


class CommandInputArea(QFrame):
    """Input row for user commands."""

    submitted = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("CommandInputArea")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.input = QLineEdit()
        self.input.setObjectName("CommandInput")
        self.input.setPlaceholderText("Ask Cherry AI or describe a task")
        self.input.returnPressed.connect(self._submit)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("SendButton")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self._submit)

        layout.addWidget(self.input, stretch=1)
        layout.addWidget(self.send_button)

    def set_loading(self, loading: bool) -> None:
        """Enable or disable input during work."""
        self.input.setDisabled(loading)
        self.send_button.setDisabled(loading)
        if loading:
            self.send_button.setText("Wait")
        else:
            self.send_button.setText("Send")
            self.input.setFocus()

    def _submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return

        self.input.clear()
        self.submitted.emit(text)
