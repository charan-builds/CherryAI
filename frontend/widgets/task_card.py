"""Task card widget."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from backend.task_engine.constants import TASK_STATUS_COMPLETED
from backend.task_engine.schemas import TaskRecord


class TaskCard(QFrame):
    """Reusable task list item."""

    completion_changed = pyqtSignal(str, bool)
    delete_requested = pyqtSignal(str)

    def __init__(self, task: TaskRecord) -> None:
        super().__init__()
        self.task = task
        self.setObjectName("TaskCard")
        self.setProperty("priority", task.priority)
        self.setProperty("status", task.status)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(12)

        self.complete_checkbox = QCheckBox()
        self.complete_checkbox.setObjectName("TaskCompleteCheck")
        self.complete_checkbox.setChecked(task.status == TASK_STATUS_COMPLETED)
        self.complete_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.complete_checkbox.toggled.connect(self._emit_completion_changed)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)

        title_label = QLabel(task.title)
        title_label.setObjectName("TaskCardTitle")
        title_label.setWordWrap(True)

        description = task.description or "No description"
        description_label = QLabel(description)
        description_label.setObjectName("TaskCardDescription")
        description_label.setWordWrap(True)

        meta_label = QLabel(self._build_meta_text(task))
        meta_label.setObjectName("TaskCardMeta")

        text_layout.addWidget(title_label)
        text_layout.addWidget(description_label)
        text_layout.addWidget(meta_label)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("TaskDangerButton")
        self.delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_button.clicked.connect(
            lambda: self.delete_requested.emit(self.task.id)
        )

        root_layout.addWidget(self.complete_checkbox)
        root_layout.addLayout(text_layout, stretch=1)
        root_layout.addWidget(self.delete_button)

    def _emit_completion_changed(self, checked: bool) -> None:
        self.completion_changed.emit(self.task.id, checked)

    def _build_meta_text(self, task: TaskRecord) -> str:
        created = self._format_datetime(task.created_at)
        completed = (
            f" | completed {self._format_datetime(task.completed_at)}"
            if task.completed_at is not None
            else ""
        )
        return f"{task.priority.title()} priority | {task.status.title()} | created {created}{completed}"

    def _format_datetime(self, value: datetime | None) -> str:
        if value is None:
            return ""
        return value.strftime("%Y-%m-%d %H:%M")
