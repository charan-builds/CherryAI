"""Resume engine for answering where the user left off."""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings
from database.models import utc_now
from backend.activity_snapshot_manager.service import ActivitySnapshotManager
from backend.operating_context_manager.schemas import ResumeSummary
from backend.operating_context_manager.service import OperatingContextManager


@dataclass
class ResumeEngine:
    """Builds human-facing resume answers from snapshots and active state."""

    settings: AppSettings
    operating_context: OperatingContextManager
    snapshots: ActivitySnapshotManager
    workflow_state: object | None = None
    task_engine: object | None = None
    observer_engine: object | None = None

    def generate_summary(self) -> ResumeSummary:
        """Answer what was happening, what is pending, and where work stopped."""
        context = self.operating_context.current_context()
        snapshot = self.snapshots.latest_snapshot()
        active_workflows = self._active_workflows()
        active_workflow = active_workflows[0] if active_workflows else None
        active_study = self._active_study_session()
        pending = self._pending_items(active_workflows)
        what = self._what_was_i_doing(context, active_workflow, active_study, snapshot)
        where = self._where_did_i_stop(context, active_workflow, snapshot)
        next_action = self._suggest_next_action(context, active_workflow, pending)

        return ResumeSummary(
            what_was_i_doing=what,
            what_is_pending=tuple(pending),
            where_did_i_stop=where,
            active_project=context.current_project,
            active_workspace=context.current_workspace,
            active_mode=context.operating_mode,
            suggested_next_action=next_action,
            generated_at=utc_now(),
        )

    def answer(self, question: str) -> str:
        """Answer a resume-oriented natural language question."""
        normalized = question.strip().lower()
        summary = self.generate_summary()
        if "what was i doing" in normalized or "doing" in normalized:
            return summary.what_was_i_doing
        if "pending" in normalized or "left" in normalized:
            if not summary.what_is_pending:
                return "Nothing urgent is pending from the last saved context."
            return "\n".join(f"- {item}" for item in summary.what_is_pending)
        if "where did i stop" in normalized or "where" in normalized:
            return summary.where_did_i_stop
        return summary.as_text()

    def _what_was_i_doing(
        self,
        context,
        active_workflow,
        active_study,
        snapshot,
    ) -> str:
        if active_workflow is not None:
            return (
                f"You were running {active_workflow.name} in "
                f"{context.current_workspace or context.operating_mode}."
            )
        if active_study is not None:
            return f"You were studying {active_study.topic}."
        if context.focus_area:
            return (
                f"You were in {context.operating_mode} mode focused on "
                f"{context.focus_area}."
            )
        if snapshot is not None and snapshot.context.focus_area:
            return (
                f"You were last focused on {snapshot.context.focus_area} in "
                f"{snapshot.context.current_workspace or snapshot.context.operating_mode}."
            )
        return "There is no active work context yet. Start or switch to a workspace."

    def _where_did_i_stop(self, context, active_workflow, snapshot) -> str:
        if active_workflow is not None:
            step = active_workflow.current_step_key or "waiting for the next step"
            return f"{active_workflow.name} stopped at {step}."
        if context.active_document:
            return f"You stopped around {context.active_document}."
        if snapshot is not None:
            timestamp = snapshot.created_at.strftime("%Y-%m-%d %H:%M") if snapshot.created_at else "the last snapshot"
            if snapshot.active_workflow_name:
                return f"Last snapshot: {snapshot.active_workflow_name} at {timestamp}."
            if snapshot.context.active_document:
                return f"Last snapshot: {snapshot.context.active_document} at {timestamp}."
            return f"Last snapshot was saved at {timestamp}."
        return "No snapshot has been saved yet."

    def _suggest_next_action(self, context, active_workflow, pending: list[str]) -> str:
        if active_workflow is not None:
            return f"Resume or inspect {active_workflow.name}."
        if pending:
            return f"Start with {pending[0]}."
        if context.active_goals:
            return f"Continue: {context.active_goals[0]}."
        return "Choose a workspace and capture the first concrete goal."

    def _pending_items(self, active_workflows: list[object]) -> list[str]:
        items: list[str] = []
        for workflow in active_workflows[:5]:
            status = getattr(workflow, "status", "active")
            items.append(f"Workflow: {workflow.name} ({status})")
        if self.task_engine is not None and hasattr(self.task_engine, "list_tasks"):
            for task in self.task_engine.list_tasks(status_filter="open")[:5]:
                items.append(f"Task: {task.title}")
        return items

    def _active_workflows(self) -> list[object]:
        if self.workflow_state is None or not hasattr(
            self.workflow_state,
            "list_active_workflows",
        ):
            return []
        return list(self.workflow_state.list_active_workflows(limit=5))

    def _active_study_session(self) -> object | None:
        if self.observer_engine is None or not hasattr(self.observer_engine, "get_status"):
            return None
        return self.observer_engine.get_status().active_study_session
