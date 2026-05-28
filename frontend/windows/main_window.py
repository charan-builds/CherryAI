"""Main Cherry AI application window.

The window is the frontend composition root. It owns layout wiring, view
switching, and placeholder interactions, while reusable UI pieces live in
frontend/widgets and feature pages live in frontend/dashboard.
"""

from __future__ import annotations

import logging
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
from frontend.dashboard.dashboard_page import DashboardPage
from frontend.notifications.notification_center import NotificationCenter
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

        self._build_pages()
        self._build_layout()
        self._connect_signals()
        self._switch_section("dashboard")

        QTimer.singleShot(300, self._complete_startup)
        logger.info("Main window initialized")

    def _build_pages(self) -> None:
        """Create stack pages for each navigation section."""
        for section in SECTIONS:
            if section.key == "dashboard":
                page = self.dashboard_page
            elif section.key == "tasks":
                page = self.tasks_page
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
        else:
            self.footer.set_message(f"{section.title} shell ready")

        self.services.analytics.record("frontend_section_opened", section=key)

    def _complete_startup(self) -> None:
        """Mark startup complete after the first event-loop tick."""
        self.top_bar.set_status("Ready", "ready")
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
        self.dashboard_page.show_loading("Preparing a local placeholder response...")
        self.top_bar.set_status("Thinking", "loading")
        self.footer.set_message("Planning placeholder response")
        self.services.analytics.record("chat_prompt_submitted", section="dashboard")

        QTimer.singleShot(450, lambda: self._finish_placeholder_response(prompt))

    def _finish_placeholder_response(self, prompt: str) -> None:
        """Render a placeholder response using the existing planner stub."""
        plan = self.services.planner.create_plan(prompt)
        plan_preview = "\n".join(f"- {step}" for step in plan)
        response = (
            "Placeholder response generated by the desktop UI layer.\n\n"
            "When Ollama streaming is connected, model output can be routed "
            "through this same response panel.\n\n"
            f"Planning preview:\n{plan_preview}"
        )

        self.dashboard_page.hide_loading()
        self.dashboard_page.add_assistant_message(response)
        self.top_bar.set_status("Ready", "ready")
        self.footer.set_message("Placeholder response generated")
