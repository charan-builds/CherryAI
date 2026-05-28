"""Task filtering controls."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton


class TaskFilterBar(QFrame):
    """Reusable task filter controls."""

    filter_changed = pyqtSignal(str, str)
    refresh_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TaskFilterBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        label = QLabel("Filters")
        label.setObjectName("PanelSubtitle")

        self.status_filter = QComboBox()
        self.status_filter.setObjectName("TaskFilterCombo")
        self.status_filter.addItem("Open", "open")
        self.status_filter.addItem("Completed", "completed")
        self.status_filter.addItem("All", "all")

        self.priority_filter = QComboBox()
        self.priority_filter.setObjectName("TaskFilterCombo")
        self.priority_filter.addItem("Any priority", "all")
        self.priority_filter.addItem("High", "high")
        self.priority_filter.addItem("Normal", "normal")
        self.priority_filter.addItem("Low", "low")

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("TaskSecondaryButton")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.status_filter.currentIndexChanged.connect(self._emit_filters)
        self.priority_filter.currentIndexChanged.connect(self._emit_filters)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)

        layout.addWidget(label)
        layout.addWidget(self.status_filter)
        layout.addWidget(self.priority_filter)
        layout.addStretch(1)
        layout.addWidget(self.refresh_button)

    def current_filters(self) -> tuple[str, str]:
        """Return selected status and priority filter keys."""
        return (
            str(self.status_filter.currentData()),
            str(self.priority_filter.currentData()),
        )

    def _emit_filters(self) -> None:
        status, priority = self.current_filters()
        self.filter_changed.emit(status, priority)
