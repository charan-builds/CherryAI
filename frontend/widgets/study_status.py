"""Study Mode status widgets."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout


class StudyMetricGrid(QFrame):
    """Small reusable metric grid for Study Mode."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("StudyMetricGrid")

        layout = QGridLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        self.focus_label = self._add_metric(layout, "Focus", "00:00", 0, 0)
        self.idle_label = self._add_metric(layout, "Idle", "0s", 0, 1)
        self.switches_label = self._add_metric(layout, "Switches", "0", 1, 0)
        self.distractions_label = self._add_metric(layout, "Distractions", "0", 1, 1)

    def update_metrics(
        self,
        focus_seconds: float,
        idle_seconds: float,
        app_switch_count: int,
        distraction_count: int,
    ) -> None:
        """Update rendered metric values."""
        self.focus_label.setText(_format_duration(focus_seconds))
        self.idle_label.setText(f"{int(idle_seconds)}s")
        self.switches_label.setText(str(app_switch_count))
        self.distractions_label.setText(str(distraction_count))

    def _add_metric(self, layout: QGridLayout, title: str, value: str, row: int, col: int) -> QLabel:
        panel = QFrame()
        panel.setObjectName("StudyMetricCard")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 10, 12, 10)
        panel_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("PanelSubtitle")

        value_label = QLabel(value)
        value_label.setObjectName("StudyMetricValue")

        panel_layout.addWidget(title_label)
        panel_layout.addWidget(value_label)
        layout.addWidget(panel, row, col)
        return value_label


def _format_duration(seconds: float) -> str:
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
