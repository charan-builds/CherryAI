"""Footer/status bar widget."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel


class StatusFooter(QFrame):
    """Compact footer for environment and interaction status."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("StatusFooter")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 9, 14, 9)
        layout.setSpacing(12)

        self.primary_label = QLabel("Ready")
        self.primary_label.setObjectName("FooterPrimary")

        self.secondary_label = QLabel("")
        self.secondary_label.setObjectName("FooterSecondary")

        layout.addWidget(self.primary_label)
        layout.addStretch(1)
        layout.addWidget(self.secondary_label)

    def set_message(self, message: str) -> None:
        """Set the primary footer message."""
        self.primary_label.setText(message)

    def set_context(self, context: str) -> None:
        """Set secondary footer context."""
        self.secondary_label.setText(context)
