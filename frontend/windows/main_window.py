"""Main Cherry AI application window.

The window is the frontend composition root. It owns layout wiring, view
switching, and placeholder interactions, while reusable UI pieces live in
frontend/widgets and feature pages live in frontend/dashboard.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from backend.service_registry import ServiceRegistry
from config.settings import AppSettings
from backend.ai_response_handler.schemas import AIWorkflowResult
from frontend.dashboard.chat_worker import ChatWorker
from frontend.dashboard.dashboard_page import DashboardPage
from frontend.dashboard.proactive_worker import (
    ProactiveIntelligenceResult,
    ProactiveIntelligenceWorker,
)
from frontend.notifications.notification_center import NotificationCenter
from frontend.study.study_page import StudyModePage
from frontend.tasks.tasks_page import TasksPage
from frontend.widgets.page_placeholder import PlaceholderPage
from frontend.widgets.sidebar import SidebarNavigation
from frontend.widgets.status_footer import StatusFooter
from frontend.widgets.top_bar import TopBar

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SectionDefinition:
    """Metadata for a navigable UI section."""

    key: str
    title: str
    subtitle: str
    placeholder: str


SECTIONS: tuple[SectionDefinition, ...] = (
    SectionDefinition(
        key="dashboard",
        title="Dashboard",
        subtitle="Chat workspace and local system overview",
        placeholder="Assistant console, local readiness, and future system cards.",
    ),
    SectionDefinition(
        key="tasks",
        title="Tasks",
        subtitle="Plan and monitor agent work",
        placeholder="Task queues, approvals, retries, and execution timelines will live here.",
    ),
    SectionDefinition(
        key="study",
        title="Study Mode",
        subtitle="Focused learning workspace",
        placeholder="Study sessions, notes, flashcards, and guided explanations will live here.",
    ),
    SectionDefinition(
        key="memory",
        title="Memory",
        subtitle="Manage local assistant memory",
        placeholder="Saved memories, preferences, and retrieval controls will live here.",
    ),
    SectionDefinition(
        key="analytics",
        title="Analytics",
        subtitle="Local usage and health insights",
        placeholder="Local event trends, task outcomes, and model performance views will live here.",
    ),
    SectionDefinition(
        key="settings",
        title="Settings",
        subtitle="Configure Cherry AI",
        placeholder="Theme, Ollama, automation safety, storage, and privacy controls will live here.",
    ),
)


class MainWindow(QMainWindow):
    """Primary desktop shell."""

    def __init__(self, settings: AppSettings, services: ServiceRegistry) -> None:
        super().__init__()
        self.settings = settings
        self.services = services
        self.current_section = "dashboard"
        self.chat_session_id = services.ai.start_session()
        self.chat_workers: list[ChatWorker] = []
        self.proactive_workers: list[ProactiveIntelligenceWorker] = []
        self._last_proactive_refresh = 0.0

        self.section_lookup = {section.key: section for section in SECTIONS}
        self.pages: dict[str, QWidget] = {}

        self.setWindowTitle(settings.app_name)
        self.setMinimumSize(1120, 700)
        self.resize(1240, 780)

        self.sidebar = SidebarNavigation()
        self.top_bar = TopBar(settings.app_name)
        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentStack")
        self.footer = StatusFooter()
        self.notifications = NotificationCenter()

        self.dashboard_page = DashboardPage()
        self.tasks_page = TasksPage(task_engine=services.tasks)
        self.study_page = StudyModePage(
            observer_engine=services.observer,
            automation_engine=services.automation,
        )
        self.observer_timer = QTimer(self)
        self.observer_timer.setInterval(
            max(int(settings.observer_poll_interval_seconds * 1000), 250)
        )

        self._build_pages()
        self._build_layout()
        self._connect_signals()
        self._switch_section("dashboard")

        QTimer.singleShot(300, self._complete_startup)
        if settings.observer_enabled:
            self.observer_timer.start()
        logger.info("Main window initialized")

    def _build_pages(self) -> None:
        """Create stack pages for each navigation section."""
        for section in SECTIONS:
            if section.key == "dashboard":
                page = self.dashboard_page
            elif section.key == "tasks":
                page = self.tasks_page
            elif section.key == "study":
                page = self.study_page
            else:
                page = PlaceholderPage(section.title, section.placeholder)

            self.pages[section.key] = page
            self.stack.addWidget(page)

    def _build_layout(self) -> None:
        """Build the high-level application layout."""
        root = QFrame(self)
        root.setObjectName("AppRoot")

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        main_content = QFrame()
        main_content.setObjectName("MainContent")

        main_layout = QVBoxLayout(main_content)
        main_layout.setContentsMargins(18, 18, 18, 14)
        main_layout.setSpacing(12)

        main_layout.addWidget(self.top_bar)
        main_layout.addWidget(self.stack, stretch=1)
        main_layout.addWidget(self.footer)

        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(main_content, stretch=1)

        self.setCentralWidget(root)

    def _connect_signals(self) -> None:
        """Connect widget signals to shell behavior."""
        self.sidebar.navigation_requested.connect(self._switch_section)
        self.dashboard_page.command_submitted.connect(self._handle_prompt)
        self.tasks_page.status_message.connect(self.footer.set_message)
        self.study_page.status_message.connect(self.footer.set_message)
        self.observer_timer.timeout.connect(self._poll_observer)
        self.notifications.notification_emitted.connect(self._handle_notification)

    def _switch_section(self, key: str) -> None:
        """Switch the central stacked widget to a section."""
        section = self.section_lookup.get(key)
        page = self.pages.get(key)
        if section is None or page is None:
            logger.warning("Unknown frontend section requested: %s", key)
            return

        self.current_section = key
        self.stack.setCurrentWidget(page)
        self.sidebar.select(key)
        self.top_bar.set_section(section.title, section.subtitle)
        self.footer.set_context(
            f"{self.settings.app_env} | {self.settings.ollama_model} | SQLite"
        )

        if key == "dashboard":
            self.footer.set_message("Assistant console ready")
        elif key == "tasks":
            self.tasks_page.refresh_tasks()
            self.footer.set_message("Task workspace ready")
        elif key == "study":
            self.study_page.update_status(self.services.observer.get_status())
            self.footer.set_message("Study Mode ready")
        else:
            self.footer.set_message(f"{section.title} shell ready")

        self.services.analytics.record("frontend_section_opened", section=key)

    def _complete_startup(self) -> None:
        """Mark startup complete after the first event-loop tick."""
        self.top_bar.set_status("Ready", "ready")
        self._poll_observer(force_proactive=True)
        self.dashboard_page.add_startup_message()
        self.notifications.notify("ready", "Cherry AI interface ready")

    def _handle_notification(self, level: str, message: str) -> None:
        """Handle local UI notifications."""
        logger.info("UI notification [%s]: %s", level, message)
        self.footer.set_message(message)

    def _handle_prompt(self, prompt: str) -> None:
        """Handle dashboard command submission."""
        if self.current_section != "dashboard":
            self._switch_section("dashboard")

        self.dashboard_page.add_user_message(prompt)
        self.dashboard_page.show_loading("Cherry AI is typing...")
        self.top_bar.set_status("Thinking", "loading")
        self.footer.set_message("Routing intent through local AI runtime")
        self.services.analytics.record("chat_prompt_submitted", section="dashboard")

        worker = ChatWorker(
            ai_engine=self.services.ai,
            user_message=prompt,
            session_id=self.chat_session_id,
        )
        worker.completed.connect(self._handle_ai_response)
        worker.failed.connect(self._handle_ai_error)
        worker.finished.connect(lambda: self._cleanup_chat_worker(worker))
        self.chat_workers.append(worker)
        worker.start()

    def _handle_ai_response(self, result: AIWorkflowResult) -> None:
        """Render an AI workflow result."""
        self.chat_session_id = result.session_id
        self.dashboard_page.hide_loading()
        self.dashboard_page.add_assistant_message(result.response_text)
        self.top_bar.set_status("Ready", "ready")
        self.footer.set_message(f"Intent: {result.detected_intent}")

        if result.detected_intent in {"create_task", "list_tasks", "summarize_tasks"}:
            self.tasks_page.refresh_tasks()

    def _handle_ai_error(self, message: str) -> None:
        """Render a worker-level error."""
        self.dashboard_page.hide_loading()
        self.dashboard_page.add_assistant_message(
            "I could not complete that local AI request. "
            f"Details: {message}"
        )
        self.top_bar.set_status("Ready", "ready")
        self.footer.set_message("AI request failed")

    def _cleanup_chat_worker(self, worker: ChatWorker) -> None:
        """Drop completed workers so QThread objects can be collected."""
        if worker in self.chat_workers:
            self.chat_workers.remove(worker)
        worker.deleteLater()

    def _poll_observer(self, force_proactive: bool = False) -> None:
        """Poll observer state and update lightweight UI indicators."""
        status = self.services.observer.sample_once()
        self.services.memory.update_observer_status(status)
        self.study_page.update_status(status)
        self.dashboard_page.update_observer_summary(status)
        self.footer.set_context(
            f"{self.settings.app_env} | {self.settings.ollama_model} | "
            f"App: {status.active_app}"
        )
        self._refresh_proactive_intelligence(status, force=force_proactive)

    def _refresh_proactive_intelligence(self, status, force: bool = False) -> None:
        """Refresh proactive metrics on a slower, non-AI UI cadence."""
        if not self.settings.proactive_enabled:
            return

        now = time.monotonic()
        refresh_interval = max(self.settings.proactive_refresh_interval_seconds, 1.0)
        if not force and now - self._last_proactive_refresh < refresh_interval:
            return

        self._last_proactive_refresh = now
        if self.proactive_workers:
            return

        worker = ProactiveIntelligenceWorker(
            services=self.services,
            status=status,
        )
        worker.completed.connect(self._handle_proactive_result)
        worker.failed.connect(self._handle_proactive_error)
        worker.finished.connect(lambda: self._cleanup_proactive_worker(worker))
        self.proactive_workers.append(worker)
        worker.start()

    def _handle_proactive_result(self, result: ProactiveIntelligenceResult) -> None:
        """Render a completed proactive intelligence refresh."""
        self.dashboard_page.update_proactive_intelligence(
            result.analysis,
            result.summary,
            result.recommendations,
            result.semantic_memories,
            result.consolidated_patterns,
            result.working_memory,
        )
        self.study_page.update_proactive_intelligence(
            result.analysis,
            result.summary,
            result.recommendations,
            result.semantic_memories,
            result.consolidated_patterns,
            result.working_memory,
        )
        self._emit_adaptive_notification(result.notification_candidates)

    def _handle_proactive_error(self, message: str) -> None:
        """Log proactive refresh errors without interrupting the user."""
        logger.warning("Proactive intelligence refresh failed: %s", message)

    def _cleanup_proactive_worker(self, worker: ProactiveIntelligenceWorker) -> None:
        """Drop completed proactive worker references."""
        if worker in self.proactive_workers:
            self.proactive_workers.remove(worker)
        worker.deleteLater()

    def _emit_adaptive_notification(self, recommendations) -> None:
        """Emit at most one decision-approved proactive notification."""
        for recommendation in recommendations:
            decision = self.services.notification_decisions.evaluate(recommendation)
            if decision.should_notify:
                self.notifications.notify(decision.priority, recommendation.message)
                return
