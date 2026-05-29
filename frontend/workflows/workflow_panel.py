"""Workflow control panel widgets."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from backend.workflow_state_manager.schemas import (
    WORKFLOW_STATUS_PAUSED,
    WORKFLOW_STATUS_RUNNING,
    WorkflowRecord,
)


class WorkflowPanel(QFrame):
    """Displays active workflow progress, controls, and history."""

    start_requested = pyqtSignal(str)
    pause_requested = pyqtSignal(str)
    resume_requested = pyqtSignal(str)
    cancel_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("WorkflowPanel")
        self.current_workflow_id = ""
        self.current_status = ""

        self.goal_input = QLineEdit()
        self.goal_input.setObjectName("WorkflowGoalInput")
        self.goal_input.setPlaceholderText("Workflow goal")

        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("TaskPrimaryButton")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.pause_button = QPushButton("Pause")
        self.pause_button.setObjectName("TaskSecondaryButton")
        self.pause_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.resume_button = QPushButton("Resume")
        self.resume_button.setObjectName("TaskSecondaryButton")
        self.resume_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("TaskDangerButton")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.status_label = QLabel("No active workflow")
        self.status_label.setObjectName("PanelSubtitle")
        self.status_label.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("WorkflowProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.history_label = QLabel("Workflow history will appear here.")
        self.history_label.setObjectName("WorkflowHistoryLabel")
        self.history_label.setWordWrap(True)

        self._build_layout()
        self._connect_signals()
        self._update_controls()

    def mark_starting(self, workflow_id: str, name: str) -> None:
        """Render an optimistic starting state."""
        self.current_workflow_id = workflow_id
        self.current_status = WORKFLOW_STATUS_RUNNING
        self.status_label.setText(f"Running: {name}")
        self.progress_bar.setValue(0)
        self._update_controls()

    def update_active_workflows(self, workflows: list[WorkflowRecord]) -> None:
        """Render the latest active workflow list."""
        active = workflows[0] if workflows else None
        if active is None:
            self.current_workflow_id = ""
            self.current_status = ""
            self.status_label.setText("No active workflow")
            self.progress_bar.setValue(0)
            self._update_controls()
            return

        self.current_workflow_id = active.id
        self.current_status = active.status
        self.status_label.setText(
            f"{active.status.title()}: {active.name} | {active.current_step_key or 'waiting'}"
        )
        self.progress_bar.setValue(int(active.progress_percent))
        self._update_controls()

    def update_history(self, history: list[dict[str, object]]) -> None:
        """Render compact workflow history."""
        if not history:
            self.history_label.setText("Workflow history will appear here.")
            return

        lines = []
        for row in history[:4]:
            message = str(row.get("message", ""))
            event_type = str(row.get("event_type", "workflow"))
            lines.append(f"{event_type}: {message}")
        self.history_label.setText("\n".join(lines))

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("Agentic Workflows")
        title.setObjectName("PanelTitle")

        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        input_row.addWidget(self.goal_input, stretch=1)
        input_row.addWidget(self.start_button)

        control_row = QHBoxLayout()
        control_row.setSpacing(10)
        control_row.addWidget(self.pause_button)
        control_row.addWidget(self.resume_button)
        control_row.addWidget(self.cancel_button)
        control_row.addStretch(1)

        layout.addWidget(title)
        layout.addLayout(input_row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addLayout(control_row)
        layout.addWidget(self.history_label)

    def _connect_signals(self) -> None:
        self.start_button.clicked.connect(self._emit_start)
        self.goal_input.returnPressed.connect(self._emit_start)
        self.pause_button.clicked.connect(
            lambda: self.pause_requested.emit(self.current_workflow_id)
        )
        self.resume_button.clicked.connect(
            lambda: self.resume_requested.emit(self.current_workflow_id)
        )
        self.cancel_button.clicked.connect(
            lambda: self.cancel_requested.emit(self.current_workflow_id)
        )

    def _emit_start(self) -> None:
        goal = self.goal_input.text().strip()
        if goal:
            self.start_requested.emit(goal)

    def _update_controls(self) -> None:
        has_workflow = bool(self.current_workflow_id)
        is_running = self.current_status == WORKFLOW_STATUS_RUNNING
        is_paused = self.current_status == WORKFLOW_STATUS_PAUSED
        self.pause_button.setEnabled(has_workflow and is_running)
        self.resume_button.setEnabled(has_workflow and is_paused)
        self.cancel_button.setEnabled(has_workflow and (is_running or is_paused))
