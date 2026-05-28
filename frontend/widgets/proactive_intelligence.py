"""Widgets for proactive productivity intelligence."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout

from backend.daily_summary_engine.schemas import DailyProductivitySummary
from backend.memory_consolidation_engine.schemas import ConsolidatedPatternRecord
from backend.productivity_analyzer.schemas import ProductivityAnalysis
from backend.recommendation_engine.schemas import Recommendation
from backend.semantic_memory_manager.schemas import SemanticMemoryRecord
from backend.working_memory_manager.schemas import WorkingMemoryRecord


class ProductivityCardsWidget(QFrame):
    """Live productivity score cards."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ProductivityCards")

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        self.productivity_label = self._add_card(layout, "Productivity", "0/100", 0, 0)
        self.focus_label = self._add_card(layout, "Focus", "0/100", 0, 1)
        self.study_label = self._add_card(layout, "Study", "0m", 0, 2)
        self.distraction_label = self._add_card(layout, "Distractions", "0", 0, 3)

    def update_analysis(self, analysis: ProductivityAnalysis) -> None:
        """Render the latest productivity analysis."""
        self.productivity_label.setText(f"{analysis.productivity_score}/100")
        self.focus_label.setText(f"{analysis.focus_score}/100")
        self.study_label.setText(_format_minutes(analysis.study_duration_seconds))
        self.distraction_label.setText(str(analysis.distraction_count))

    def _add_card(
        self,
        layout: QGridLayout,
        title: str,
        value: str,
        row: int,
        col: int,
    ) -> QLabel:
        panel = QFrame()
        panel.setObjectName("ProductivityMetricCard")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 10, 12, 10)
        panel_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("PanelSubtitle")
        value_label = QLabel(value)
        value_label.setObjectName("ProductivityMetricValue")

        panel_layout.addWidget(title_label)
        panel_layout.addWidget(value_label)
        layout.addWidget(panel, row, col)
        return value_label


class RecommendationListWidget(QFrame):
    """Displays gentle proactive recommendations."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("RecommendationPanel")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 14, 16, 14)
        self.layout.setSpacing(8)

        title = QLabel("Coaching")
        title.setObjectName("PanelTitle")
        self.empty_label = QLabel("No coaching nudges right now.")
        self.empty_label.setObjectName("PanelSubtitle")
        self.empty_label.setWordWrap(True)

        self.layout.addWidget(title)
        self.layout.addWidget(self.empty_label)
        self.items: list[QLabel] = []

    def update_recommendations(self, recommendations: list[Recommendation]) -> None:
        """Render recommendation messages."""
        for item in self.items:
            self.layout.removeWidget(item)
            item.deleteLater()
        self.items.clear()

        self.empty_label.setVisible(not recommendations)
        for recommendation in recommendations:
            label = QLabel(f"{recommendation.title}: {recommendation.message}")
            label.setObjectName("RecommendationItem")
            label.setWordWrap(True)
            self.layout.addWidget(label)
            self.items.append(label)


class DailySummaryPanel(QFrame):
    """Daily productivity summary panel."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("DailySummaryPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title = QLabel("Daily Summary")
        title.setObjectName("PanelTitle")
        self.summary_label = QLabel("Daily summary will appear after activity is observed.")
        self.summary_label.setObjectName("PanelSubtitle")
        self.summary_label.setWordWrap(True)
        self.focus_label = QLabel("")
        self.focus_label.setObjectName("PanelSubtitle")
        self.focus_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.focus_label)

    def update_summary(self, summary: DailyProductivitySummary) -> None:
        """Render the latest daily summary."""
        self.summary_label.setText(summary.summary_text)
        self.focus_label.setText(summary.focus_report)


class MemoryInsightsPanel(QFrame):
    """Displays active context and learned behavior memory."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("MemoryInsightsPanel")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 14, 16, 14)
        self.layout.setSpacing(8)

        title = QLabel("Memory")
        title.setObjectName("PanelTitle")
        self.active_context_label = QLabel("No active context stored yet.")
        self.active_context_label.setObjectName("PanelSubtitle")
        self.active_context_label.setWordWrap(True)

        self.layout.addWidget(title)
        self.layout.addWidget(self.active_context_label)
        self.items: list[QLabel] = []

    def update_memory(
        self,
        semantic_memories: list[SemanticMemoryRecord],
        consolidated_patterns: list[ConsolidatedPatternRecord],
        working_memory: list[WorkingMemoryRecord],
    ) -> None:
        """Render active context indicators and learned behavior cards."""
        for item in self.items:
            self.layout.removeWidget(item)
            item.deleteLater()
        self.items.clear()

        if working_memory:
            active_bits = [
                f"{state.state_type.replace('_', ' ')}: {state.content}"
                for state in working_memory[:2]
            ]
            self.active_context_label.setText(" | ".join(active_bits))
        else:
            self.active_context_label.setText("No active context stored yet.")

        cards = []
        for pattern in consolidated_patterns[:3]:
            cards.append(("Learned behavior", pattern.title, pattern.insight))
        for memory in semantic_memories[:2]:
            cards.append(("Memory", memory.title, memory.content))

        for label_text, title, body in cards[:4]:
            label = QLabel(f"{label_text}: {title} - {body}")
            label.setObjectName("MemoryInsightItem")
            label.setWordWrap(True)
            self.layout.addWidget(label)
            self.items.append(label)


def _format_minutes(seconds: float) -> str:
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    hours, remaining_minutes = divmod(minutes, 60)
    return f"{hours}h {remaining_minutes}m"
