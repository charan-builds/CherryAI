"""Dashboard page for the assistant workspace."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

from backend.daily_summary_engine.schemas import DailyProductivitySummary
from backend.companion_interaction_manager.schemas import CompanionMessage
from backend.contextual_recommendation_engine.schemas import ContextualRecommendation
from backend.daily_reflection_engine.schemas import DailyReflection
from backend.daily_timeline_manager.schemas import DailyTimeline
from backend.memory_consolidation_engine.schemas import ConsolidatedPatternRecord
from backend.observer_engine.schemas import ObserverStatus
from backend.productivity_analyzer.schemas import ProductivityAnalysis
from backend.recommendation_engine.schemas import Recommendation
from backend.semantic_memory_manager.schemas import SemanticMemoryRecord
from backend.startup_briefing_engine.schemas import StartupBriefing
from backend.working_memory_manager.schemas import WorkingMemoryRecord
from backend.workspace_preparation_engine.schemas import WorkspaceDefinition
from frontend.companion.companion_panels import (
    CompanionFeedPanel,
    DailyBriefingPanel,
    ReflectionPanel,
    TimelinePanel,
    WorkspaceLauncherPanel,
)
from frontend.widgets.chat_display import ChatDisplayArea
from frontend.widgets.command_input import CommandInputArea
from frontend.workflows.workflow_panel import WorkflowPanel
from frontend.widgets.proactive_intelligence import (
    DailySummaryPanel,
    MemoryInsightsPanel,
    ProductivityCardsWidget,
    RecommendationListWidget,
)


class DashboardPage(QFrame):
    """Primary assistant workspace with chat and command input."""

    command_submitted = pyqtSignal(str)
    workflow_start_requested = pyqtSignal(str)
    workflow_pause_requested = pyqtSignal(str)
    workflow_resume_requested = pyqtSignal(str)
    workflow_cancel_requested = pyqtSignal(str)
    workspace_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("DashboardPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.chat_display = ChatDisplayArea()
        self.command_input = CommandInputArea()
        self.command_input.submitted.connect(self.command_submitted.emit)
        self.briefing_panel = DailyBriefingPanel()
        self.reflection_panel = ReflectionPanel()
        self.timeline_panel = TimelinePanel()
        self.workspace_launcher = WorkspaceLauncherPanel()
        self.workspace_launcher.workspace_requested.connect(self.workspace_requested.emit)
        self.companion_feed = CompanionFeedPanel()
        self.productivity_cards = ProductivityCardsWidget()
        self.workflow_panel = WorkflowPanel()
        self.workflow_panel.start_requested.connect(self.workflow_start_requested.emit)
        self.workflow_panel.pause_requested.connect(self.workflow_pause_requested.emit)
        self.workflow_panel.resume_requested.connect(self.workflow_resume_requested.emit)
        self.workflow_panel.cancel_requested.connect(self.workflow_cancel_requested.emit)
        self.daily_summary = DailySummaryPanel()
        self.recommendations = RecommendationListWidget()
        self.memory_insights = MemoryInsightsPanel()
        self.observer_summary = QLabel("Activity: waiting for observer")
        self.observer_summary.setObjectName("DashboardObserverSummary")

        layout.addWidget(self.briefing_panel)
        layout.addWidget(self.workspace_launcher)
        layout.addWidget(self.companion_feed)
        layout.addWidget(self.reflection_panel)
        layout.addWidget(self.timeline_panel)
        layout.addWidget(self.productivity_cards)
        layout.addWidget(self.workflow_panel)
        layout.addWidget(self.daily_summary)
        layout.addWidget(self.recommendations)
        layout.addWidget(self.memory_insights)
        layout.addWidget(self.observer_summary)
        layout.addWidget(self.chat_display, stretch=1)
        layout.addWidget(self.command_input)

    def add_startup_message(self) -> None:
        """Add the initial system message."""
        self.chat_display.add_system_message(
            "Cherry AI interface is online. Local database and logging are ready."
        )

    def add_user_message(self, message: str) -> None:
        """Append a user message to the chat."""
        self.chat_display.add_user_message(message)

    def add_assistant_message(self, message: str) -> None:
        """Append an assistant message to the chat."""
        self.chat_display.add_assistant_message(message)

    def show_loading(self, message: str) -> None:
        """Show loading state in the chat and input."""
        self.chat_display.show_loading(message)
        self.command_input.set_loading(True)

    def hide_loading(self) -> None:
        """Hide loading state in the chat and input."""
        self.chat_display.hide_loading()
        self.command_input.set_loading(False)

    def update_observer_summary(self, status: ObserverStatus) -> None:
        """Update dashboard activity summary."""
        state = "idle" if status.is_idle else "active"
        self.observer_summary.setText(
            f"Activity: {status.active_app} | {state} | "
            f"Focus {int(status.focus_seconds)}s"
        )

    def update_proactive_intelligence(
        self,
        analysis: ProductivityAnalysis,
        summary: DailyProductivitySummary,
        recommendations: list[Recommendation],
        semantic_memories: list[SemanticMemoryRecord] | None = None,
        consolidated_patterns: list[ConsolidatedPatternRecord] | None = None,
        working_memory: list[WorkingMemoryRecord] | None = None,
    ) -> None:
        """Update proactive productivity widgets."""
        self.productivity_cards.update_analysis(analysis)
        self.daily_summary.update_summary(summary)
        self.recommendations.update_recommendations(recommendations)
        self.memory_insights.update_memory(
            semantic_memories or [],
            consolidated_patterns or [],
            working_memory or [],
        )

    def update_companion_experience(
        self,
        briefing: StartupBriefing,
        reflection: DailyReflection,
        timeline: DailyTimeline,
        workspaces: list[WorkspaceDefinition],
        messages: list[CompanionMessage],
        contextual_recommendations: list[ContextualRecommendation],
    ) -> None:
        """Update companion panels."""
        self.briefing_panel.update_briefing(briefing)
        self.reflection_panel.update_reflection(reflection)
        self.timeline_panel.update_timeline(timeline)
        self.workspace_launcher.update_workspaces(workspaces)
        self.companion_feed.update_feed(messages, contextual_recommendations)
