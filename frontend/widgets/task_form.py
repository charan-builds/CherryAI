"""Task creation form widget."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class TaskFormWidget(QFrame):
    """Form for creating new tasks."""

    task_created = pyqtSignal(str, str, str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TaskForm")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Create Task")
        title.setObjectName("PanelTitle")

        self.title_input = QLineEdit()
        self.title_input.setObjectName("TaskTitleInput")
        self.title_input.setPlaceholderText("Task title")
        self.title_input.returnPressed.connect(self._submit)

        self.description_input = QTextEdit()
        self.description_input.setObjectName("TaskDescriptionInput")
        self.description_input.setPlaceholderText("Optional description")
        self.description_input.setFixedHeight(96)

        self.priority_combo = QComboBox()
        self.priority_combo.setObjectName("TaskPriorityCombo")
        self.priority_combo.addItem("Low", "low")
        self.priority_combo.addItem("Normal", "normal")
        self.priority_combo.addItem("High", "high")
        self.priority_combo.setCurrentIndex(1)

        self.create_button = QPushButton("Add Task")
        self.create_button.setObjectName("TaskPrimaryButton")
        self.create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_button.clicked.connect(self._submit)

        layout.addWidget(title)
        layout.addWidget(self.title_input)
        layout.addWidget(self.description_input)
        layout.addWidget(self.priority_combo)
        layout.addWidget(self.create_button)
        layout.addStretch(1)

    def focus_title(self) -> None:
        """Focus the task title field."""
        self.title_input.setFocus()

    def _submit(self) -> None:
        title = self.title_input.text().strip()
        if not title:
            self.title_input.setFocus()
            return

        description = self.description_input.toPlainText().strip()
        priority = str(self.priority_combo.currentData())

        self.title_input.clear()
        self.description_input.clear()
        self.priority_combo.setCurrentIndex(1)
        self.task_created.emit(title, description, priority)
