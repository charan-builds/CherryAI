"""Developer diagnostics page for platform health."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from backend.service_registry import ServiceRegistry


class RuntimeHealthWidget(QFrame):
    """Shows current system health."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("DiagnosticsPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title = QLabel("Runtime Health")
        title.setObjectName("PanelTitle")
        self.status_label = QLabel("Status: starting")
        self.status_label.setObjectName("PanelSubtitle")
        self.status_label.setWordWrap(True)
        self.detail_label = QLabel("")
        self.detail_label.setObjectName("PanelSubtitle")
        self.detail_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.detail_label)

    def update_health(self, services: ServiceRegistry) -> None:
        """Render latest health report."""
        report = services.observability.health_report()
        sandbox = services.execution_sandbox.state()
        self.status_label.setText(
            f"Status: {report.status} | Safe mode: {sandbox.safe_mode} | "
            f"Emergency stop: {sandbox.emergency_stop}"
        )
        self.detail_label.setText(
            f"Diagnostics: {report.checks.get('diagnostics', 0)} | "
            f"Recent errors: {report.checks.get('recent_errors', 0)}"
        )


class PerformanceSummaryCards(QFrame):
    """Compact performance cards."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ProductivityCards")
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        self.memory_label = self._add_card(layout, "Memory", "0 MB", 0, 0)
        self.worker_label = self._add_card(layout, "Workers", "0", 0, 1)
        self.events_label = self._add_card(layout, "Events/min", "0", 0, 2)
        self.workflow_label = self._add_card(layout, "Workflows", "0", 0, 3)

    def update_performance(self, services: ServiceRegistry) -> None:
        """Render latest performance sample."""
        sample = services.performance_monitor.latest_sample()
        if sample is None:
            sample = services.performance_monitor.sample(services.event_bus)
        self.memory_label.setText(f"{sample.memory_mb:.0f} MB")
        self.worker_label.setText(str(sample.worker_count))
        self.events_label.setText(f"{sample.event_throughput_per_minute:.0f}")
        self.workflow_label.setText(str(sample.workflow_concurrency))

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


class EventMonitorPanel(QGroupBox):
    """Collapsible recent event monitor."""

    def __init__(self) -> None:
        super().__init__("Event Monitor")
        self.setObjectName("DiagnosticsGroup")
        self.setCheckable(True)
        self.setChecked(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)
        self.events_label = QLabel("No platform events yet.")
        self.events_label.setObjectName("DiagnosticsText")
        self.events_label.setWordWrap(True)
        layout.addWidget(self.events_label)

    def update_events(self, services: ServiceRegistry) -> None:
        """Render recent events."""
        events = services.event_bus.recent_events(limit=6)
        if not events:
            self.events_label.setText("No platform events yet.")
            return
        lines = [
            f"{event.category}/{event.event_type} | {event.source}"
            for event in events
        ]
        self.events_label.setText("\n".join(lines))


class AdvancedDiagnosticsPanel(QGroupBox):
    """Collapsible advanced diagnostics."""

    def __init__(self) -> None:
        super().__init__("Advanced Diagnostics")
        self.setObjectName("DiagnosticsGroup")
        self.setCheckable(True)
        self.setChecked(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)
        self.detail_label = QLabel("Diagnostics will appear after runtime activity.")
        self.detail_label.setObjectName("DiagnosticsText")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

    def update_details(self, services: ServiceRegistry) -> None:
        """Render sandbox, lifecycle, and diagnostic details."""
        sandbox = services.execution_sandbox.state()
        lifecycle = services.lifecycle.state()
        diagnostics = services.observability.recent_diagnostics(limit=4)
        lines = [
            f"Blocked actions: {', '.join(sandbox.blocked_actions) or 'none'}",
            f"Active locks: {', '.join(sandbox.active_locks) or 'none'}",
            f"Lifecycle started: {', '.join(lifecycle.started_steps) or 'none'}",
        ]
        for record in diagnostics:
            lines.append(f"{record.level}: {record.category} - {record.message}")
        self.detail_label.setText("\n".join(lines))


class DiagnosticsPage(QFrame):
    """Developer-friendly platform diagnostics surface."""

    def __init__(self, services: ServiceRegistry) -> None:
        super().__init__()
        self.services = services
        self.setObjectName("DiagnosticsPage")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        self.health = RuntimeHealthWidget()
        self.performance = PerformanceSummaryCards()
        self.events = EventMonitorPanel()
        self.advanced = AdvancedDiagnosticsPanel()

        scroll = QScrollArea()
        scroll.setObjectName("TaskScrollArea")
        scroll.setWidgetResizable(True)
        viewport = QWidget()
        viewport.setObjectName("TaskScrollViewport")
        layout = QVBoxLayout(viewport)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.health)
        layout.addWidget(self.performance)
        layout.addWidget(self.events)
        layout.addWidget(self.advanced)
        layout.addStretch(1)
        scroll.setWidget(viewport)
        root_layout.addWidget(scroll)

        self.refresh()

    def refresh(self) -> None:
        """Refresh all diagnostics widgets."""
        self.health.update_health(self.services)
        self.performance.update_performance(self.services)
        self.events.update_events(self.services)
        self.advanced.update_details(self.services)
