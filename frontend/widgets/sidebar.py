"""Sidebar navigation for Cherry AI."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout


@dataclass(frozen=True)
class NavigationItem:
    """A single sidebar navigation entry."""

    key: str
    label: str


class SidebarNavigation(QFrame):
    """Left navigation rail with checkable section buttons."""

    navigation_requested = pyqtSignal(str)

    ITEMS = (
        NavigationItem("dashboard", "Dashboard"),
        NavigationItem("workspace", "Workspace Center"),
        NavigationItem("tasks", "Tasks"),
        NavigationItem("study", "Study Mode"),
        NavigationItem("memory", "Memory"),
        NavigationItem("knowledge", "Knowledge"),
        NavigationItem("analytics", "Analytics"),
        NavigationItem("settings", "Settings"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(236)
        self._buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(8)

        brand_title = QLabel("Cherry AI")
        brand_title.setObjectName("BrandTitle")

        brand_subtitle = QLabel("Local desktop assistant")
        brand_subtitle.setObjectName("BrandSubtitle")

        layout.addWidget(brand_title)
        layout.addWidget(brand_subtitle)
        layout.addSpacing(18)

        for item in self.ITEMS:
            button = QPushButton(item.label)
            button.setObjectName("SidebarButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda checked=False, key=item.key: self._handle_clicked(key)
            )
            self._buttons[item.key] = button
            layout.addWidget(button)

        layout.addStretch(1)

        local_label = QLabel("Local-first mode")
        local_label.setObjectName("BrandSubtitle")
        layout.addWidget(local_label)

    def select(self, key: str) -> None:
        """Mark a navigation item as selected."""
        for item_key, button in self._buttons.items():
            button.setChecked(item_key == key)

    def _handle_clicked(self, key: str) -> None:
        self.select(key)
        self.navigation_requested.emit(key)
