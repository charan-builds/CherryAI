"""Task summary widget."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from backend.task_engine.schemas import DailyTaskSummary, TaskStatistics


class TaskSummaryWidget(QFrame):
    """Displays task statistics and daily summary text."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TaskSummary")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QLabel("Daily Summary")
        header.setObjectName("PanelTitle")

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)

        self.open_label = self._build_stat_label("Open: 0")
        self.completed_label = self._build_stat_label("Done: 0")
        self.rate_label = self._build_stat_label("Rate: 0%")

        stats_layout.addWidget(self.open_label)
        stats_layout.addWidget(self.completed_label)
        stats_layout.addWidget(self.rate_label)
        stats_layout.addStretch(1)

        self.summary_label = QLabel("No task activity yet today.")
        self.summary_label.setObjectName("PanelSubtitle")
        self.summary_label.setWordWrap(True)

        layout.addWidget(header)
        layout.addLayout(stats_layout)
        layout.addWidget(self.summary_label)

    def update_summary(
        self,
        statistics: TaskStatistics,
        daily_summary: DailyTaskSummary,
    ) -> None:
        """Render the latest task summary."""
        self.open_label.setText(f"Open: {statistics.open_count}")
        self.completed_label.setText(f"Done: {statistics.completed_count}")
        self.rate_label.setText(f"Rate: {statistics.completion_rate}%")
        self.summary_label.setText(daily_summary.summary_text)

    def _build_stat_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("TaskStatLabel")
        return label
