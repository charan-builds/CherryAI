"""Session recovery engine for restoring Cherry's operating environment."""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings
from database.models import utc_now
from backend.activity_snapshot_manager.service import ActivitySnapshotManager
from backend.operating_context_manager.schemas import (
    SNAPSHOT_TYPE_SESSION_RECOVERY,
    SessionRecoveryPlan,
)
from backend.operating_context_manager.service import OperatingContextManager


@dataclass
class SessionRecoveryEngine:
    """Collects and restores recoverable workflows, study state, workspaces, and tasks."""

    settings: AppSettings
    operating_context: OperatingContextManager
    snapshots: ActivitySnapshotManager
    workflow_state: object | None = None
    workflow_execution: object | None = None
    task_engine: object | None = None
    observer_engine: object | None = None

    def recovery_plan(self) -> SessionRecoveryPlan:
        """Build a deterministic recovery plan from local persisted state."""
        active_workflows = tuple(self.restore_active_workflows())
        active_study = self.restore_study_session()
        workspace_state = self.restore_workspace_state()
        pending_tasks = tuple(self.restore_pending_tasks())
        last_snapshot = self.snapshots.latest_snapshot()
        summary = self._summary(
            workflow_count=len(active_workflows),
            has_study=active_study is not None,
            pending_count=len(pending_tasks),
            workspace=workspace_state.current_workspace,
        )
        return SessionRecoveryPlan(
            active_workflows=active_workflows,
            active_study_session=active_study,
            workspace_state=workspace_state,
            pending_tasks=pending_tasks,
            last_snapshot=last_snapshot,
            summary=summary,
            generated_at=utc_now(),
        )

    def restore_session(
        self,
        resume_workflows: bool = False,
    ) -> SessionRecoveryPlan:
        """Restore current context from the latest snapshot and optionally resume workflows."""
        last_snapshot = self.snapshots.latest_snapshot()
        if last_snapshot is not None:
            self.operating_context.restore_context(last_snapshot.context)

        plan = self.recovery_plan()
        if resume_workflows:
            for workflow in plan.active_workflows:
                workflow_id = getattr(workflow, "id", "")
                status = getattr(workflow, "status", "")
                if workflow_id and status == "paused":
                    self._resume_workflow(workflow_id)

        self.snapshots.take_snapshot(
            SNAPSHOT_TYPE_SESSION_RECOVERY,
            metadata={"resume_workflows": resume_workflows},
        )
        return self.recovery_plan()

    def restore_active_workflows(self) -> list[object]:
        """Return active or paused workflows that can be resumed."""
        if self.workflow_state is None or not hasattr(
            self.workflow_state,
            "list_active_workflows",
        ):
            return []
        return list(self.workflow_state.list_active_workflows(limit=10))

    def restore_study_session(self) -> object | None:
        """Return the active study session if one exists."""
        if self.observer_engine is None or not hasattr(self.observer_engine, "get_status"):
            return None
        return self.observer_engine.get_status().active_study_session

    def restore_workspace_state(self):
        """Return the current persisted workspace state."""
        return self.operating_context.current_context()

    def restore_pending_tasks(self) -> list[object]:
        """Return pending or open tasks for recovery."""
        if self.task_engine is None or not hasattr(self.task_engine, "list_tasks"):
            return []
        return list(self.task_engine.list_tasks(status_filter="open")[:10])

    def _resume_workflow(self, workflow_id: str) -> None:
        target = self.workflow_execution or self.workflow_state
        if target is not None and hasattr(target, "resume_workflow"):
            target.resume_workflow(workflow_id)

    def _summary(
        self,
        workflow_count: int,
        has_study: bool,
        pending_count: int,
        workspace: str,
    ) -> str:
        parts = []
        if workspace:
            parts.append(f"Workspace: {workspace}")
        parts.append(f"{workflow_count} active workflow(s)")
        if has_study:
            parts.append("study session ready")
        parts.append(f"{pending_count} pending task(s)")
        return "; ".join(parts)
