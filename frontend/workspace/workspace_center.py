"""Workspace Center UI for Cherry's personal operating layer."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from backend.operating_context_manager.schemas import (
    ActivitySnapshotRecord,
    OperatingContext,
    ResumeSummary,
    SavedContextRecord,
    SessionRecoveryPlan,
    WorkspaceProfileRecord,
)


class ResumePanel(QFrame):
    """Displays the current resume summary."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("OperatingPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title = QLabel("Resume")
        title.setObjectName("PanelTitle")
        self.doing_label = QLabel("No active resume summary yet.")
        self.doing_label.setObjectName("CompanionText")
        self.doing_label.setWordWrap(True)
        self.pending_label = QLabel("")
        self.pending_label.setObjectName("CompanionText")
        self.pending_label.setWordWrap(True)
        self.stop_label = QLabel("")
        self.stop_label.setObjectName("PanelSubtitle")
        self.stop_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.doing_label)
        layout.addWidget(self.pending_label)
        layout.addWidget(self.stop_label)

    def update_summary(self, summary: ResumeSummary) -> None:
        """Render a resume summary."""
        pending = "\n".join(f"- {item}" for item in summary.what_is_pending[:5])
        self.doing_label.setText(summary.what_was_i_doing)
        self.pending_label.setText(pending or "No pending work in this context.")
        self.stop_label.setText(
            f"{summary.where_did_i_stop}\nNext: {summary.suggested_next_action}"
        )


class ContextSwitcher(QFrame):
    """Saved-context picker and controls."""

    save_requested = pyqtSignal()
    switch_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("OperatingPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("Context Switcher")
        title.setObjectName("PanelTitle")
        self.context_combo = QComboBox()
        self.context_combo.setObjectName("OperatingContextCombo")

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("TaskSecondaryButton")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.switch_button = QPushButton("Switch")
        self.switch_button.setObjectName("TaskPrimaryButton")
        self.switch_button.setCursor(Qt.CursorShape.PointingHandCursor)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.switch_button)
        button_row.addStretch(1)

        self.status_label = QLabel("No saved contexts yet.")
        self.status_label.setObjectName("PanelSubtitle")
        self.status_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.context_combo)
        layout.addLayout(button_row)
        layout.addWidget(self.status_label)

        self.save_button.clicked.connect(self.save_requested.emit)
        self.switch_button.clicked.connect(self._emit_switch)

    def update_contexts(self, contexts: list[SavedContextRecord]) -> None:
        """Render saved contexts."""
        self.context_combo.clear()
        for context in contexts:
            self.context_combo.addItem(
                f"{context.name} ({context.status})",
                context.context_key,
            )
        self.switch_button.setEnabled(bool(contexts))
        if contexts:
            self.status_label.setText(f"{len(contexts)} saved context(s).")
        else:
            self.status_label.setText("No saved contexts yet.")

    def _emit_switch(self) -> None:
        key = self.context_combo.currentData()
        if key:
            self.switch_requested.emit(str(key))


class SessionRecoveryDialog(QDialog):
    """Dialog for restoring the latest recoverable session."""

    restore_requested = pyqtSignal(bool)

    def __init__(self, plan: SessionRecoveryPlan, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SessionRecoveryDialog")
        self.setWindowTitle("Session Recovery")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Session Recovery")
        title.setObjectName("PanelTitle")
        details = QLabel(self._plan_text(plan))
        details.setObjectName("CompanionText")
        details.setWordWrap(True)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        self.restore_button = QPushButton("Restore")
        self.restore_button.setObjectName("TaskPrimaryButton")
        self.resume_button = QPushButton("Restore + Resume")
        self.resume_button.setObjectName("TaskSecondaryButton")
        self.close_button = QPushButton("Close")
        self.close_button.setObjectName("TaskSecondaryButton")
        button_row.addWidget(self.restore_button)
        button_row.addWidget(self.resume_button)
        button_row.addStretch(1)
        button_row.addWidget(self.close_button)

        layout.addWidget(title)
        layout.addWidget(details)
        layout.addLayout(button_row)

        self.restore_button.clicked.connect(lambda: self._restore(False))
        self.resume_button.clicked.connect(lambda: self._restore(True))
        self.close_button.clicked.connect(self.reject)

    def _restore(self, resume: bool) -> None:
        self.restore_requested.emit(resume)
        self.accept()

    def _plan_text(self, plan: SessionRecoveryPlan) -> str:
        workflows = ", ".join(getattr(item, "name", "") for item in plan.active_workflows)
        tasks = ", ".join(getattr(item, "title", "") for item in plan.pending_tasks[:5])
        study = getattr(plan.active_study_session, "topic", "") if plan.active_study_session else "None"
        return (
            f"{plan.summary}\n"
            f"Workflows: {workflows or 'None'}\n"
            f"Study: {study}\n"
            f"Pending: {tasks or 'None'}"
        )


class WorkspaceCenterPage(QFrame):
    """Personal operating environment page."""

    workspace_selected = pyqtSignal(str)
    context_save_requested = pyqtSignal()
    context_switch_requested = pyqtSignal(str)
    recovery_requested = pyqtSignal()
    custom_workspace_requested = pyqtSignal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("WorkspaceCenterPage")
        self.workspace_buttons: list[QPushButton] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("WorkspaceScrollArea")
        scroll.setWidgetResizable(True)
        viewport = QWidget()
        viewport.setObjectName("WorkspaceScrollViewport")
        layout = QVBoxLayout(viewport)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.context_panel = QFrame()
        self.context_panel.setObjectName("OperatingPanel")
        context_layout = QVBoxLayout(self.context_panel)
        context_layout.setContentsMargins(16, 14, 16, 14)
        context_layout.setSpacing(8)
        title = QLabel("Operating Context")
        title.setObjectName("PanelTitle")
        self.context_label = QLabel("No operating context selected.")
        self.context_label.setObjectName("CompanionText")
        self.context_label.setWordWrap(True)
        context_layout.addWidget(title)
        context_layout.addWidget(self.context_label)

        self.profiles_panel = QFrame()
        self.profiles_panel.setObjectName("OperatingPanel")
        profiles_layout = QVBoxLayout(self.profiles_panel)
        profiles_layout.setContentsMargins(16, 14, 16, 14)
        profiles_layout.setSpacing(10)
        profiles_title = QLabel("Workspaces")
        profiles_title.setObjectName("PanelTitle")
        self.profile_button_row = QHBoxLayout()
        self.profile_button_row.setSpacing(10)
        profiles_layout.addWidget(profiles_title)
        profiles_layout.addLayout(self.profile_button_row)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(10)
        self.custom_name_input = QLineEdit()
        self.custom_name_input.setObjectName("OperatingTextInput")
        self.custom_name_input.setPlaceholderText("Custom workspace")
        self.custom_focus_input = QLineEdit()
        self.custom_focus_input.setObjectName("OperatingTextInput")
        self.custom_focus_input.setPlaceholderText("Focus area")
        self.custom_button = QPushButton("Create")
        self.custom_button.setObjectName("TaskSecondaryButton")
        self.custom_button.setCursor(Qt.CursorShape.PointingHandCursor)
        custom_row.addWidget(self.custom_name_input, stretch=1)
        custom_row.addWidget(self.custom_focus_input, stretch=1)
        custom_row.addWidget(self.custom_button)
        profiles_layout.addLayout(custom_row)

        self.resume_panel = ResumePanel()
        self.context_switcher = ContextSwitcher()
        self.context_switcher.save_requested.connect(self.context_save_requested.emit)
        self.context_switcher.switch_requested.connect(self.context_switch_requested.emit)

        self.recovery_panel = QFrame()
        self.recovery_panel.setObjectName("OperatingPanel")
        recovery_layout = QVBoxLayout(self.recovery_panel)
        recovery_layout.setContentsMargins(16, 14, 16, 14)
        recovery_layout.setSpacing(8)
        recovery_title = QLabel("Session Recovery")
        recovery_title.setObjectName("PanelTitle")
        self.recovery_label = QLabel("No recovery plan generated yet.")
        self.recovery_label.setObjectName("CompanionText")
        self.recovery_label.setWordWrap(True)
        self.recovery_button = QPushButton("Open Recovery")
        self.recovery_button.setObjectName("TaskPrimaryButton")
        self.recovery_button.setCursor(Qt.CursorShape.PointingHandCursor)
        recovery_layout.addWidget(recovery_title)
        recovery_layout.addWidget(self.recovery_label)
        recovery_layout.addWidget(self.recovery_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.snapshot_label = QLabel("Snapshots will appear after activity is saved.")
        self.snapshot_label.setObjectName("DashboardObserverSummary")
        self.snapshot_label.setWordWrap(True)

        layout.addWidget(self.context_panel)
        layout.addWidget(self.profiles_panel)
        layout.addWidget(self.resume_panel)
        layout.addWidget(self.context_switcher)
        layout.addWidget(self.recovery_panel)
        layout.addWidget(self.snapshot_label)
        layout.addStretch(1)

        scroll.setWidget(viewport)
        outer.addWidget(scroll)

        self.recovery_button.clicked.connect(self.recovery_requested.emit)
        self.custom_button.clicked.connect(self._emit_custom_workspace)

    def update_state(
        self,
        profiles: list[WorkspaceProfileRecord],
        context: OperatingContext,
        resume_summary: ResumeSummary,
        saved_contexts: list[SavedContextRecord],
        recovery_plan: SessionRecoveryPlan,
        snapshots: list[ActivitySnapshotRecord],
    ) -> None:
        """Render the latest Personal OS state."""
        self._update_profiles(profiles)
        self.context_label.setText(
            f"Mode: {context.operating_mode}\n"
            f"Workspace: {context.current_workspace or 'None'}\n"
            f"Project: {context.current_project or 'None'}\n"
            f"Focus: {context.focus_area or 'None'}"
        )
        self.resume_panel.update_summary(resume_summary)
        self.context_switcher.update_contexts(saved_contexts)
        self.recovery_label.setText(recovery_plan.summary)
        self.snapshot_label.setText(self._snapshot_text(snapshots))

    def _update_profiles(self, profiles: list[WorkspaceProfileRecord]) -> None:
        while self.profile_button_row.count():
            item = self.profile_button_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.workspace_buttons.clear()

        for profile in profiles:
            label = profile.name.replace(" Workspace", "")
            if profile.is_active:
                label = f"{label} Active"
            button = QPushButton(label)
            button.setObjectName("TaskPrimaryButton" if profile.is_active else "TaskSecondaryButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _, key=profile.key: self.workspace_selected.emit(key)
            )
            self.profile_button_row.addWidget(button)
            self.workspace_buttons.append(button)
        self.profile_button_row.addStretch(1)

    def _snapshot_text(self, snapshots: list[ActivitySnapshotRecord]) -> str:
        if not snapshots:
            return "Snapshots will appear after activity is saved."
        lines = []
        for snapshot in snapshots[:4]:
            created = snapshot.created_at.strftime("%H:%M") if snapshot.created_at else ""
            workspace = snapshot.context.current_workspace or snapshot.context.operating_mode
            lines.append(f"{created} | {snapshot.snapshot_type} | {workspace}")
        return "\n".join(lines)

    def _emit_custom_workspace(self) -> None:
        name = self.custom_name_input.text().strip()
        focus = self.custom_focus_input.text().strip()
        if not name:
            return
        self.custom_workspace_requested.emit(name, focus)
        self.custom_name_input.clear()
        self.custom_focus_input.clear()
