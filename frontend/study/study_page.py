"""Study Mode page with live observer status."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from backend.observer_engine.schemas import ObserverStatus
from backend.observer_engine.service import ObserverEngine
from frontend.widgets.study_status import StudyMetricGrid


class StudyModePage(QFrame):
    """Study session controls and live behavioral status."""

    status_message = pyqtSignal(str)

    def __init__(self, observer_engine: ObserverEngine) -> None:
        super().__init__()
        self.observer_engine = observer_engine
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
        live_layout.addStretch(1)

        root_layout.addWidget(controls)
        root_layout.addWidget(live_panel, stretch=1)

    def _connect_signals(self) -> None:
        self.start_button.clicked.connect(self._start_session)
        self.stop_button.clicked.connect(self._stop_session)
        self.topic_input.returnPressed.connect(self._start_session)

    def _start_session(self) -> None:
        topic = self.topic_input.text().strip() or "Focused study"
        session = self.observer_engine.start_study_session(topic)
        self.status_message.emit(f"Study started: {session.topic}")
        self.update_status(self.observer_engine.get_status())

    def _stop_session(self) -> None:
        session = self.observer_engine.stop_study_session()
        if session is None:
            self.status_message.emit("No active study session")
        else:
            self.status_message.emit(
                f"Study completed: {int(session.duration_seconds)}s"
            )
        self.update_status(self.observer_engine.get_status())
