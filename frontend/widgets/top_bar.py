"""Header bar for the main window."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from frontend.widgets.style_helpers import refresh_style


class TopBar(QFrame):
    """Displays the active section and startup/model status."""

    def __init__(self, app_name: str) -> None:
        super().__init__()
        self.setObjectName("TopBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(3)

        self.title_label = QLabel(app_name)
        self.title_label.setObjectName("TopBarTitle")

        self.subtitle_label = QLabel("Initializing local workspace")
        self.subtitle_label.setObjectName("TopBarSubtitle")

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        self.status_label = QLabel("Starting")
        self.status_label.setObjectName("StatusIndicator")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setProperty("state", "starting")

        layout.addLayout(title_layout, stretch=1)
        layout.addWidget(self.status_label)

    def set_section(self, title: str, subtitle: str) -> None:
        """Update the visible section title."""
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)

    def set_status(self, text: str, state: str) -> None:
        """Update the top-right status indicator."""
        self.status_label.setText(text)
        self.status_label.setProperty("state", state)
        refresh_style(self.status_label)
