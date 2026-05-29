"""Daily companion dashboard panels."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from backend.companion_interaction_manager.schemas import CompanionMessage
from backend.contextual_recommendation_engine.schemas import ContextualRecommendation
from backend.daily_reflection_engine.schemas import DailyReflection
from backend.daily_timeline_manager.schemas import DailyTimeline
from backend.startup_briefing_engine.schemas import StartupBriefing
from backend.workspace_preparation_engine.schemas import WorkspaceDefinition


class DailyBriefingPanel(QFrame):
    """Shows Cherry's startup briefing."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("CompanionPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title = QLabel("Daily Briefing")
        title.setObjectName("PanelTitle")
        self.greeting_label = QLabel("Cherry is gathering today's context.")
        self.greeting_label.setObjectName("PanelSubtitle")
        self.greeting_label.setWordWrap(True)
        self.detail_label = QLabel("")
        self.detail_label.setObjectName("CompanionText")
        self.detail_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.greeting_label)
        layout.addWidget(self.detail_label)

    def update_briefing(self, briefing: StartupBriefing) -> None:
        """Render a startup briefing."""
        pending = ", ".join(briefing.pending_tasks[:3]) or "No pending tasks"
        goals = ", ".join(briefing.active_goals[:2]) or "No active workflows"
        self.greeting_label.setText(briefing.greeting)
        self.detail_label.setText(
            f"{briefing.yesterday_summary}\n"
            f"Pending: {pending}\n"
            f"Goals: {goals}\n"
            f"{briefing.focus_score_trend}\n"
            f"Suggested: {briefing.suggested_first_action}"
        )


class ReflectionPanel(QFrame):
    """Shows the daily reflection card."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("CompanionPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title = QLabel("Reflection")
        title.setObjectName("PanelTitle")
        self.summary_label = QLabel("Reflection will appear after today's activity.")
        self.summary_label.setObjectName("CompanionText")
        self.summary_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.summary_label)

    def update_reflection(self, reflection: DailyReflection) -> None:
        """Render reflection metrics."""
        cards = " | ".join(reflection.card_items)
        self.summary_label.setText(
            f"{reflection.summary_text}\n"
            f"{cards}\n"
            f"Recommendation effectiveness: {reflection.recommendation_effectiveness}%"
        )


class TimelinePanel(QFrame):
    """Shows daily timeline items."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("CompanionPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title = QLabel("Timeline")
        title.setObjectName("PanelTitle")
        self.timeline_label = QLabel("No timeline entries yet today.")
        self.timeline_label.setObjectName("CompanionText")
        self.timeline_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.timeline_label)

    def update_timeline(self, timeline: DailyTimeline) -> None:
        """Render daily timeline records."""
        if not timeline.items:
            self.timeline_label.setText("No timeline entries yet today.")
            return
        lines = []
        for item in timeline.items[:5]:
            time_text = item.started_at.strftime("%H:%M")
            lines.append(f"{time_text} | {item.title} - {item.description}")
        self.timeline_label.setText("\n".join(lines))


class WorkspaceLauncherPanel(QFrame):
    """Launches predefined workspace workflows."""

    workspace_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("CompanionPanel")
        self.workspace_buttons: list[QPushButton] = []
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 14, 16, 14)
        self.layout.setSpacing(8)

        title = QLabel("Workspaces")
        title.setObjectName("PanelTitle")
        self.layout.addWidget(title)

        self.button_row = QHBoxLayout()
        self.button_row.setSpacing(10)
        self.layout.addLayout(self.button_row)

    def update_workspaces(self, workspaces: list[WorkspaceDefinition]) -> None:
        """Render workspace launch buttons."""
        for button in self.workspace_buttons:
            self.button_row.removeWidget(button)
            button.deleteLater()
        self.workspace_buttons.clear()

        for workspace in workspaces:
            button = QPushButton(workspace.name.replace(" Workspace", ""))
            button.setObjectName("TaskSecondaryButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _, key=workspace.key: self.workspace_requested.emit(key)
            )
            self.button_row.addWidget(button)
            self.workspace_buttons.append(button)


class CompanionFeedPanel(QFrame):
    """Shows Cherry's companion feed and contextual recommendations."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("CompanionPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title = QLabel("Companion Feed")
        title.setObjectName("PanelTitle")
        self.feed_label = QLabel("Cherry will surface useful nudges here.")
        self.feed_label.setObjectName("CompanionText")
        self.feed_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.feed_label)

    def update_feed(
        self,
        messages: list[CompanionMessage],
        recommendations: list[ContextualRecommendation],
    ) -> None:
        """Render recent companion messages and recommendations."""
        lines = []
        for message in messages[:3]:
            lines.append(f"{message.title}: {message.message}")
        for recommendation in recommendations[:3]:
            lines.append(f"{recommendation.title}: {recommendation.message}")
        self.feed_label.setText("\n".join(lines) if lines else "Cherry will surface useful nudges here.")
