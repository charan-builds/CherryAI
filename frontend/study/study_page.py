"""Study Mode page with live observer status."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from backend.automation_engine.schemas import AutomationResult
from backend.automation_engine.service import AutomationEngine
from backend.daily_summary_engine.schemas import DailyProductivitySummary
from backend.memory_consolidation_engine.schemas import ConsolidatedPatternRecord
from backend.observer_engine.schemas import ObserverStatus
from backend.observer_engine.service import ObserverEngine
from backend.productivity_analyzer.schemas import ProductivityAnalysis
from backend.recommendation_engine.schemas import Recommendation
from backend.semantic_memory_manager.schemas import SemanticMemoryRecord
from frontend.study.automation_worker import AutomationWorker
from frontend.widgets.proactive_intelligence import (
    DailySummaryPanel,
    MemoryInsightsPanel,
    RecommendationListWidget,
)
from frontend.widgets.study_status import StudyMetricGrid
from backend.working_memory_manager.schemas import WorkingMemoryRecord


class StudyModePage(QFrame):
    """Study session controls and live behavioral status."""

    status_message = pyqtSignal(str)
    workflow_requested = pyqtSignal(str)

    def __init__(
        self,
        observer_engine: ObserverEngine,
        automation_engine: AutomationEngine,
    ) -> None:
        super().__init__()
        self.observer_engine = observer_engine
        self.automation_engine = automation_engine
        self.automation_workers: list[AutomationWorker] = []
        self.setObjectName("StudyModePage")

        self.topic_input = QLineEdit()
        self.topic_input.setObjectName("StudyTopicInput")
        self.topic_input.setPlaceholderText("Study topic")

        self.start_button = QPushButton("Start Study")
        self.start_button.setObjectName("TaskPrimaryButton")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("TaskSecondaryButton")
        self.stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_button.setDisabled(True)

        self.session_status_label = QLabel("No active study session")
        self.session_status_label.setObjectName("StudySessionStatus")
        self.session_status_label.setWordWrap(True)

        self.active_app_label = QLabel("Unknown")
        self.active_app_label.setObjectName("StudyLiveValue")
        self.window_title_label = QLabel("")
        self.window_title_label.setObjectName("StudyLiveValue")
        self.window_title_label.setWordWrap(True)

        self.metric_grid = StudyMetricGrid()
        self.focus_score_label = QLabel("Focus score: 0/100")
        self.focus_score_label.setObjectName("StudyLiveValue")
        self.focus_score_label.setWordWrap(True)
        self.daily_summary_panel = DailySummaryPanel()
        self.recommendation_panel = RecommendationListWidget()
        self.memory_insights_panel = MemoryInsightsPanel()
        self.open_workspace_button = QPushButton("Open Workspace")
        self.open_workspace_button.setObjectName("TaskPrimaryButton")
        self.open_workspace_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.study_workflow_button = QPushButton("Study Workflow")
        self.study_workflow_button.setObjectName("TaskPrimaryButton")
        self.study_workflow_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.music_button = QPushButton("Focus Music")
        self.music_button.setObjectName("TaskSecondaryButton")
        self.music_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.screenshot_button = QPushButton("Screenshot")
        self.screenshot_button.setObjectName("TaskSecondaryButton")
        self.screenshot_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.history_label = QLabel("No automation actions yet.")
        self.history_label.setObjectName("StudyAutomationHistory")
        self.history_label.setWordWrap(True)

        self._build_layout()
        self._connect_signals()
        self.update_status(self.observer_engine.get_status())

    def update_status(self, status: ObserverStatus) -> None:
        """Render current observer status."""
        self.active_app_label.setText(status.active_app)
        self.window_title_label.setText(status.window_title or "No active window title")
        self.metric_grid.update_metrics(
            focus_seconds=status.focus_seconds,
            idle_seconds=status.idle_seconds,
            app_switch_count=status.app_switch_count,
            distraction_count=status.distraction_count,
        )

        if status.active_study_session is None:
            self.session_status_label.setText("No active study session")
            self.start_button.setDisabled(False)
            self.stop_button.setDisabled(True)
        else:
            self.session_status_label.setText(
                f"Studying: {status.active_study_session.topic}"
            )
            self.start_button.setDisabled(True)
            self.stop_button.setDisabled(False)

    def _build_layout(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        controls = QFrame()
        controls.setObjectName("StudyPanel")
        controls.setFixedWidth(340)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(16, 16, 16, 16)
        controls_layout.setSpacing(12)

        title = QLabel("Study Session")
        title.setObjectName("PanelTitle")

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)

        controls_layout.addWidget(title)
        controls_layout.addWidget(self.topic_input)
        controls_layout.addLayout(buttons_layout)
        controls_layout.addWidget(self.session_status_label)
        controls_layout.addSpacing(8)
        controls_layout.addWidget(self.study_workflow_button)
        controls_layout.addWidget(self.open_workspace_button)
        controls_layout.addWidget(self.music_button)
        controls_layout.addWidget(self.screenshot_button)
        controls_layout.addWidget(self.history_label)
        controls_layout.addStretch(1)

        live_panel = QFrame()
        live_panel.setObjectName("StudyPanel")
        live_layout = QVBoxLayout(live_panel)
        live_layout.setContentsMargins(16, 16, 16, 16)
        live_layout.setSpacing(12)

        live_title = QLabel("Live Focus Status")
        live_title.setObjectName("PanelTitle")

        active_app_title = QLabel("Current active app")
        active_app_title.setObjectName("PanelSubtitle")
        window_title = QLabel("Current window")
        window_title.setObjectName("PanelSubtitle")

        live_layout.addWidget(live_title)
        live_layout.addWidget(active_app_title)
        live_layout.addWidget(self.active_app_label)
        live_layout.addWidget(window_title)
        live_layout.addWidget(self.window_title_label)
        live_layout.addWidget(self.metric_grid)
        live_layout.addWidget(self.focus_score_label)
        live_layout.addStretch(1)

        root_layout.addWidget(controls)
        right_panel = QFrame()
        right_panel.setObjectName("TaskSidePanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        right_layout.addWidget(live_panel, stretch=1)
        right_layout.addWidget(self.daily_summary_panel)
        right_layout.addWidget(self.recommendation_panel)
        right_layout.addWidget(self.memory_insights_panel)

        root_layout.addWidget(right_panel, stretch=1)

    def _connect_signals(self) -> None:
        self.start_button.clicked.connect(self._start_session)
        self.stop_button.clicked.connect(self._stop_session)
        self.topic_input.returnPressed.connect(self._start_session)
        self.open_workspace_button.clicked.connect(self._open_study_workspace)
        self.study_workflow_button.clicked.connect(self._start_study_workflow)
        self.music_button.clicked.connect(self._play_focus_music)
        self.screenshot_button.clicked.connect(self._take_screenshot)

    def update_proactive_intelligence(
        self,
        analysis: ProductivityAnalysis,
        summary: DailyProductivitySummary,
        recommendations: list[Recommendation],
        semantic_memories: list[SemanticMemoryRecord] | None = None,
        consolidated_patterns: list[ConsolidatedPatternRecord] | None = None,
        working_memory: list[WorkingMemoryRecord] | None = None,
    ) -> None:
        """Update Study Mode proactive coaching widgets."""
        self.focus_score_label.setText(
            f"Focus score: {analysis.focus_score}/100 | "
            f"Quality {analysis.focus_metrics.session_quality if analysis.focus_metrics else 0}/100"
        )
        self.daily_summary_panel.update_summary(summary)
        self.recommendation_panel.update_recommendations(recommendations)
        self.memory_insights_panel.update_memory(
            semantic_memories or [],
            consolidated_patterns or [],
            working_memory or [],
        )

    def _start_session(self) -> None:
        topic = self.topic_input.text().strip() or "Focused study"
        session = self.observer_engine.start_study_session(topic)
        self.status_message.emit(f"Study started: {session.topic}")
        self.update_status(self.observer_engine.get_status())

    def _open_study_workspace(self) -> None:
        topic = self.topic_input.text().strip() or "study"
        self._run_automation(
            "open_study_workspace",
            {"topic": topic, "app_name": "vscode"},
        )

    def _start_study_workflow(self) -> None:
        topic = self.topic_input.text().strip() or "Focused"
        self.workflow_requested.emit(f"Prepare {topic} study session")

    def _play_focus_music(self) -> None:
        self._run_automation("play_music", {"query": "focus music"})

    def _take_screenshot(self) -> None:
        self._run_automation("take_screenshot", {})

    def _run_automation(
        self,
        tool_name: str,
        parameters: dict[str, object],
        confirmed: bool = False,
    ) -> None:
        worker = AutomationWorker(
            automation_engine=self.automation_engine,
            tool_name=tool_name,
            parameters=parameters,
            confirmed=confirmed,
        )
        worker.completed.connect(
            lambda result, name=tool_name, params=parameters: self._handle_automation_result(
                result,
                name,
                params,
            )
        )
        worker.failed.connect(self._handle_automation_error)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self.automation_workers.append(worker)
        self.status_message.emit(f"Running automation: {tool_name}")
        worker.start()

    def _handle_automation_result(
        self,
        result: AutomationResult,
        tool_name: str,
        parameters: dict[str, object],
    ) -> None:
        if result.confirmation_required:
            response = QMessageBox.question(
                self,
                "Confirm Automation",
                result.message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if response == QMessageBox.StandardButton.Yes:
                self._run_automation(tool_name, parameters, confirmed=True)
            else:
                self.status_message.emit("Automation cancelled")
            return

        self.status_message.emit(result.message)
        self._refresh_action_history()

    def _handle_automation_error(self, message: str) -> None:
        self.status_message.emit(f"Automation failed: {message}")

    def _cleanup_worker(self, worker: AutomationWorker) -> None:
        if worker in self.automation_workers:
            self.automation_workers.remove(worker)
        worker.deleteLater()

    def _refresh_action_history(self) -> None:
        actions = self.automation_engine.recent_actions(limit=3)
        if not actions:
            self.history_label.setText("No automation actions yet.")
            return

        lines = []
        for action in actions:
            status = "ok" if action.success else "failed"
            lines.append(f"{action.tool_name}: {status}")
        self.history_label.setText("\n".join(lines))

    def _stop_session(self) -> None:
        session = self.observer_engine.stop_study_session()
        if session is None:
            self.status_message.emit("No active study session")
        else:
            self.status_message.emit(
                f"Study completed: {int(session.duration_seconds)}s"
            )
        self.update_status(self.observer_engine.get_status())
