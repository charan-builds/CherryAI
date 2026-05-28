"""Reusable placeholder page for future modules."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout


class PlaceholderPage(QFrame):
    """Clean placeholder for sections that will gain full dashboards later."""

    def __init__(self, title: str, description: str) -> None:
        super().__init__()
        self.setObjectName("PlaceholderPage")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        surface = QFrame()
        surface.setObjectName("PlaceholderSurface")

        surface_layout = QVBoxLayout(surface)
        surface_layout.setContentsMargins(28, 26, 28, 26)
        surface_layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("TopBarTitle")

        body_label = QLabel(description)
        body_label.setObjectName("PlaceholderBody")
        body_label.setWordWrap(True)

        status_label = QLabel("Module shell ready for future integration.")
        status_label.setObjectName("PanelSubtitle")

        surface_layout.addWidget(title_label)
        surface_layout.addWidget(body_label)
        surface_layout.addSpacing(12)
        surface_layout.addWidget(status_label)
        surface_layout.addStretch(1)

        root_layout.addWidget(surface, stretch=1)
