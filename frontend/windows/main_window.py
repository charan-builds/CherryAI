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
from frontend.diagnostics.diagnostics_page import DiagnosticsPage
from frontend.knowledge.knowledge_center_page import KnowledgeCenterPage
from frontend.notifications.notification_center import NotificationCenter
from frontend.study.study_page import StudyModePage
from frontend.tasks.tasks_page import TasksPage
from frontend.workspace.workspace_center import (
    SessionRecoveryDialog,
    WorkspaceCenterPage,
)
from frontend.workflows.workflow_worker import WorkflowExecutionWorker
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
        key="workspace",
        title="Workspace Center",
        subtitle="Restore sessions, switch contexts, and resume active work",
        placeholder="Workspace Center",
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
        key="knowledge",
        title="Knowledge",
        subtitle="Documents, code, screenshots, summaries, and notes",
        placeholder="Knowledge Center",
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
        self.workflow_workers: list[WorkflowExecutionWorker] = []
        self._last_proactive_refresh = 0.0
        self._last_companion_refresh = 0.0
        self._last_activity_snapshot = 0.0

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
        self.workspace_center_page = WorkspaceCenterPage()
        self.tasks_page = TasksPage(task_engine=services.tasks)
        self.diagnostics_page = DiagnosticsPage(services=services)
        self.knowledge_page = KnowledgeCenterPage(services=services)
        self.study_page = StudyModePage(
            observer_engine=services.observer,
            automation_engine=services.automation,
        )
        self.observer_timer = QTimer(self)
        self.observer_timer.setInterval(
            max(int(settings.observer_poll_interval_seconds * 1000), 250)
        )
        self.workflow_timer = QTimer(self)
        self.workflow_timer.setInterval(1000)
        self.platform_timer = QTimer(self)
        self.platform_timer.setInterval(
            max(int(settings.performance_monitor_interval_seconds * 1000), 1000)
        )

        self._build_pages()
        self._build_layout()
        self._connect_signals()
        self._switch_section("dashboard")

        QTimer.singleShot(300, self._complete_startup)
        if settings.observer_enabled:
            self.observer_timer.start()
        self.workflow_timer.start()
        self.platform_timer.start()
        logger.info("Main window initialized")

    def _build_pages(self) -> None:
        """Create stack pages for each navigation section."""
        for section in SECTIONS:
            if section.key == "dashboard":
                page = self.dashboard_page
            elif section.key == "workspace":
                page = self.workspace_center_page
            elif section.key == "tasks":
                page = self.tasks_page
            elif section.key == "study":
                page = self.study_page
            elif section.key == "knowledge":
                page = self.knowledge_page
            elif section.key == "analytics":
                page = self.diagnostics_page
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
        self.study_page.workflow_requested.connect(self._start_workflow)
        self.dashboard_page.workflow_start_requested.connect(self._start_workflow)
        self.dashboard_page.workflow_pause_requested.connect(self._pause_workflow)
        self.dashboard_page.workflow_resume_requested.connect(self._resume_workflow)
        self.dashboard_page.workflow_cancel_requested.connect(self._cancel_workflow)
        self.dashboard_page.workspace_requested.connect(self._launch_workspace)
        self.workspace_center_page.workspace_selected.connect(
            self._switch_operating_workspace
        )
        self.workspace_center_page.context_save_requested.connect(
            self._save_operating_context
        )
        self.workspace_center_page.context_switch_requested.connect(
            self._switch_saved_context
        )
        self.workspace_center_page.recovery_requested.connect(
            self._show_session_recovery_dialog
        )
        self.workspace_center_page.custom_workspace_requested.connect(
            self._create_custom_workspace
        )
        self.observer_timer.timeout.connect(self._poll_observer)
        self.workflow_timer.timeout.connect(self._refresh_workflow_panel)
        self.platform_timer.timeout.connect(self._refresh_platform_runtime)
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
            self._refresh_companion_experience()
        elif key == "tasks":
            self.tasks_page.refresh_tasks()
            self.footer.set_message("Task workspace ready")
        elif key == "workspace":
            self._refresh_workspace_center()
            self.footer.set_message("Workspace Center ready")
        elif key == "study":
            self.study_page.update_status(self.services.observer.get_status())
            self.footer.set_message("Study Mode ready")
        elif key == "analytics":
            self.diagnostics_page.refresh()
            self.footer.set_message("Diagnostics ready")
        elif key == "knowledge":
            self.knowledge_page.refresh()
            self.footer.set_message("Knowledge Center ready")
        else:
            self.footer.set_message(f"{section.title} shell ready")

        self.services.analytics.record("frontend_section_opened", section=key)

    def _complete_startup(self) -> None:
        """Mark startup complete after the first event-loop tick."""
        self.top_bar.set_status("Ready", "ready")
        self._poll_observer(force_proactive=True)
        self.dashboard_page.add_startup_message()
        self.notifications.notify("ready", "Cherry AI interface ready")
        self._refresh_workflow_panel()
        self._refresh_platform_runtime()
        self._refresh_companion_experience(force=True)
        self._refresh_workspace_center()

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
        if result.detected_intent == "start_workflow":
            self._refresh_workflow_panel()
        if result.detected_intent == "resume_status":
            self._refresh_workspace_center()

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

    def _start_workflow(self, goal: str) -> None:
        """Plan and run an agentic workflow in the background."""
        worker = WorkflowExecutionWorker(
            goal_planner=self.services.goal_planner,
            workflow_execution=self.services.workflow_execution,
            goal=goal,
        )
        worker.started_workflow.connect(self._handle_workflow_started)
        worker.completed.connect(self._handle_workflow_completed)
        worker.failed.connect(self._handle_workflow_error)
        worker.finished.connect(lambda: self._cleanup_workflow_worker(worker))
        self.workflow_workers.append(worker)
        self.footer.set_message(f"Starting workflow: {goal}")
        self.notifications.notify("workflow", f"Starting workflow: {goal}")
        worker.start()

    def _launch_workspace(self, workspace_key: str) -> None:
        """Run a predefined companion workspace workflow."""
        workspace = self.services.workspace_preparation.get_workspace(workspace_key)
        worker = WorkflowExecutionWorker(
            goal_planner=self.services.goal_planner,
            workflow_execution=self.services.workflow_execution,
            goal=workspace.workflow_plan.goal,
            plan=workspace.workflow_plan,
        )
        worker.started_workflow.connect(self._handle_workflow_started)
        worker.completed.connect(self._handle_workflow_completed)
        worker.failed.connect(self._handle_workflow_error)
        worker.finished.connect(lambda: self._cleanup_workflow_worker(worker))
        self.workflow_workers.append(worker)
        self.footer.set_message(f"Launching workspace: {workspace.name}")
        self.services.daily_timeline.record_item(
            "workspace_launch",
            workspace.name,
            "Workspace launch requested.",
            source_id=workspace.key,
        )
        worker.start()

    def _switch_operating_workspace(self, workspace_key: str) -> None:
        """Switch the active personal operating workspace."""
        try:
            result = self.services.context_switching.switch_workspace(workspace_key)
            self.footer.set_message(result.message)
            self.notifications.notify("workspace", result.message)
            self.services.daily_timeline.record_item(
                "context_switch",
                result.message,
                "Operating workspace switched.",
                source_id=workspace_key,
            )
        except Exception as exc:
            logger.exception("Workspace switch failed")
            self.footer.set_message(f"Workspace switch failed: {exc}")
        self._refresh_workspace_center()

    def _create_custom_workspace(self, name: str, focus_area: str) -> None:
        """Create a custom workspace profile and activate it."""
        try:
            profile = self.services.workspace_profiles.create_custom_workspace(
                name=name,
                focus_area=focus_area or name,
                operating_mode="custom",
            )
            self.services.context_switching.switch_workspace(profile.key)
            self.footer.set_message(f"Created workspace: {profile.name}")
        except Exception as exc:
            logger.exception("Custom workspace creation failed")
            self.footer.set_message(f"Could not create workspace: {exc}")
        self._refresh_workspace_center()

    def _save_operating_context(self) -> None:
        """Persist the current context for later switching."""
        try:
            saved = self.services.context_switching.save_current_context()
            self.footer.set_message(f"Context saved: {saved.name}")
        except Exception as exc:
            logger.exception("Context save failed")
            self.footer.set_message(f"Could not save context: {exc}")
        self._refresh_workspace_center()

    def _switch_saved_context(self, context_key: str) -> None:
        """Restore a previously saved context."""
        try:
            result = self.services.context_switching.switch_context(context_key)
            self.footer.set_message(result.message)
            self.notifications.notify("context", result.message)
        except Exception as exc:
            logger.exception("Saved context switch failed")
            self.footer.set_message(f"Could not switch context: {exc}")
        self._refresh_workspace_center()

    def _show_session_recovery_dialog(self) -> None:
        """Open the session recovery dialog."""
        plan = self.services.session_recovery.recovery_plan()
        dialog = SessionRecoveryDialog(plan, self)
        dialog.restore_requested.connect(self._restore_session)
        dialog.exec()

    def _restore_session(self, resume_workflows: bool) -> None:
        """Restore persisted session state."""
        try:
            plan = self.services.session_recovery.restore_session(
                resume_workflows=resume_workflows
            )
            self.footer.set_message(plan.summary)
            self.notifications.notify("recovery", "Session context restored")
        except Exception as exc:
            logger.exception("Session recovery failed")
            self.footer.set_message(f"Session recovery failed: {exc}")
        self._refresh_workspace_center()

    def _pause_workflow(self, workflow_id: str) -> None:
        if not workflow_id:
            return
        self.services.workflow_execution.pause_workflow(workflow_id)
        self.services.activity_snapshots.take_snapshot(
            metadata={"workflow_paused": workflow_id}
        )
        self.footer.set_message("Workflow paused")
        self._refresh_workflow_panel()
        self._refresh_workspace_center()

    def _resume_workflow(self, workflow_id: str) -> None:
        if not workflow_id:
            return
        self.services.workflow_execution.resume_workflow(workflow_id)
        self.services.operating_context.set_active_workflow(workflow_id)
        self.services.activity_snapshots.take_snapshot(
            metadata={"workflow_resumed": workflow_id}
        )
        self.footer.set_message("Workflow resumed")
        self._refresh_workflow_panel()
        self._refresh_workspace_center()

    def _cancel_workflow(self, workflow_id: str) -> None:
        if not workflow_id:
            return
        self.services.workflow_execution.cancel_workflow(workflow_id)
        self.services.operating_context.update_context(active_workflow_id="")
        self.services.activity_snapshots.take_snapshot(
            metadata={"workflow_cancelled": workflow_id}
        )
        self.footer.set_message("Workflow cancellation requested")
        self.notifications.notify("workflow", "Workflow cancellation requested")
        self._refresh_workflow_panel()
        self._refresh_workspace_center()

    def _handle_workflow_started(self, workflow_id: str, name: str) -> None:
        self.dashboard_page.workflow_panel.mark_starting(workflow_id, name)
        self.services.operating_context.set_active_workflow(workflow_id)
        self.services.activity_snapshots.take_snapshot(
            metadata={"workflow_started": name}
        )
        self.footer.set_message(f"Workflow running: {name}")

    def _handle_workflow_completed(self, result) -> None:
        message = result.reflection_summary or result.message
        self.footer.set_message(message)
        self.notifications.notify(result.status, message)
        try:
            snapshot = self.services.workflow_state.snapshot(result.workflow_id)
            self.services.daily_timeline.record_workflow_event(
                snapshot.workflow.name,
                result.status,
                result.workflow_id,
            )
        except Exception:
            logger.exception("Failed to record workflow timeline item")
        self.services.operating_context.update_context(active_workflow_id="")
        self.services.activity_snapshots.take_snapshot(
            metadata={"workflow_completed": result.status}
        )
        self._refresh_workflow_panel()
        self._refresh_workspace_center()
        self._refresh_companion_experience(force=True)

    def _handle_workflow_error(self, message: str) -> None:
        self.footer.set_message(f"Workflow failed: {message}")
        self.notifications.notify("workflow_failed", message)
        self._refresh_workflow_panel()

    def _cleanup_workflow_worker(self, worker: WorkflowExecutionWorker) -> None:
        if worker in self.workflow_workers:
            self.workflow_workers.remove(worker)
        worker.deleteLater()

    def _refresh_workflow_panel(self) -> None:
        """Refresh workflow UI from persisted state."""
        try:
            self.dashboard_page.workflow_panel.update_active_workflows(
                self.services.workflow_state.list_active_workflows(limit=5)
            )
            self.dashboard_page.workflow_panel.update_history(
                self.services.workflow_state.list_history(limit=8)
            )
        except Exception:
            logger.exception("Workflow panel refresh failed")

    def _refresh_workspace_center(self) -> None:
        """Refresh Personal OS UI from persisted operating state."""
        try:
            self.workspace_center_page.update_state(
                profiles=self.services.workspace_profiles.list_profiles(),
                context=self.services.operating_context.current_context(),
                resume_summary=self.services.resume_engine.generate_summary(),
                saved_contexts=self.services.context_switching.list_saved_contexts(),
                recovery_plan=self.services.session_recovery.recovery_plan(),
                snapshots=self.services.activity_snapshots.list_snapshots(limit=8),
            )
        except Exception:
            logger.exception("Workspace Center refresh failed")

    def _refresh_platform_runtime(self) -> None:
        """Refresh platform health and performance samples."""
        try:
            sample = self.services.performance_monitor.sample(self.services.event_bus)
            health = self.services.observability.health_report()
            self.services.app_state.update_domain(
                "health",
                {
                    "status": health.status,
                    "degraded": health.degraded,
                    "memory_mb": sample.memory_mb,
                    "worker_count": sample.worker_count,
                    "alerts": sample.alerts,
                },
            )
            self.diagnostics_page.refresh()
            self._refresh_companion_experience()
            self._maybe_take_activity_snapshot()
        except Exception:
            logger.exception("Platform runtime refresh failed")

    def _maybe_take_activity_snapshot(self) -> None:
        """Take periodic Personal OS snapshots on a gentle cadence."""
        now = time.monotonic()
        interval = max(self.settings.personal_os_snapshot_interval_seconds, 15.0)
        if now - self._last_activity_snapshot < interval:
            return
        self._last_activity_snapshot = now
        self.services.activity_snapshots.take_snapshot()
        if self.current_section == "workspace":
            self._refresh_workspace_center()

    def _refresh_companion_experience(self, force: bool = False) -> None:
        """Refresh daily companion panels on a gentle cadence."""
        if not self.settings.companion_enabled:
            return

        now = time.monotonic()
        interval = max(self.settings.companion_briefing_refresh_minutes * 60, 60)
        if not force and now - self._last_companion_refresh < interval:
            return

        self._last_companion_refresh = now
        try:
            greeting = self.services.companion_interactions.greeting()
            self.services.companion_interactions.maybe_emit(
                greeting,
                cooldown_seconds=20 * 3600,
            )
            briefing = self.services.startup_briefings.generate()
            reflection = self.services.daily_reflections.generate()
            timeline = self.services.daily_timeline.generate_for_day()
            workspaces = self.services.workspace_preparation.list_workspaces()
            contextual = self.services.contextual_recommendations.generate()
            messages = self.services.companion_interactions.recent_feed(limit=5)
            self.dashboard_page.update_companion_experience(
                briefing,
                reflection,
                timeline,
                workspaces,
                messages,
                contextual,
            )
        except Exception:
            logger.exception("Companion experience refresh failed")

    def _poll_observer(self, force_proactive: bool = False) -> None:
        """Poll observer state and update lightweight UI indicators."""
        status = self.services.observer.sample_once()
        self.services.memory.update_observer_status(status)
        if status.active_study_session is not None:
            self.services.operating_context.set_active_study_session(
                status.active_study_session.id
            )
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
