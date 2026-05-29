"""Context switching engine for pausing, saving, and restoring work."""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings
from database.models import utc_now
from backend.activity_snapshot_manager.service import ActivitySnapshotManager
from backend.operating_context_manager.repository import OperatingContextRepository
from backend.operating_context_manager.schemas import (
    SNAPSHOT_TYPE_CONTEXT_SAVE,
    SNAPSHOT_TYPE_CONTEXT_SWITCH,
    ContextSwitchResult,
    OperatingContext,
    SavedContextRecord,
)
from backend.operating_context_manager.service import OperatingContextManager
from backend.workspace_profile_manager.service import WorkspaceProfileManager


@dataclass
class ContextSwitchingEngine:
    """Coordinates context saves, workspace switches, and workflow pause/resume."""

    settings: AppSettings
    operating_context: OperatingContextManager
    workspace_profiles: WorkspaceProfileManager
    snapshots: ActivitySnapshotManager
    repository: OperatingContextRepository | None = None
    workflow_state: object | None = None
    workflow_execution: object | None = None
    task_engine: object | None = None

    def __post_init__(self) -> None:
        self.repository = self.repository or OperatingContextRepository.from_settings(
            self.settings
        )

    def save_current_context(
        self,
        context_key: str = "",
        name: str = "",
        status: str = "saved",
    ) -> SavedContextRecord:
        """Save the current context, active workflows, and pending task titles."""
        context = self.operating_context.current_context()
        key = context_key.strip() or self._generated_context_key(context)
        title = name.strip() or self._context_name(context)
        workflow_ids = self._active_workflow_ids()
        pending_tasks = self._pending_task_titles()
        saved = self.repository.save_named_context(
            context_key=key,
            name=title,
            context=context,
            workflow_ids=workflow_ids,
            pending_tasks=pending_tasks,
            status=status,
            metadata={
                **context.metadata,
                "saved_at": utc_now().isoformat(),
                "pending_count": len(pending_tasks),
            },
        )
        self.snapshots.take_snapshot(
            SNAPSHOT_TYPE_CONTEXT_SAVE,
            metadata={"saved_context_key": saved.context_key, "status": status},
        )
        return saved

    def switch_workspace(
        self,
        workspace_key: str,
        pause_current_workflows: bool = True,
        save_current: bool = True,
        project_override: str = "",
    ) -> ContextSwitchResult:
        """Save the current context and switch to a workspace profile."""
        saved = None
        paused_ids: tuple[str, ...] = ()
        if save_current:
            saved = self.save_current_context(status="paused")
        if pause_current_workflows:
            paused_ids = self.pause_active_workflows()

        profile = self.workspace_profiles.activate_profile(workspace_key)
        active_context = self.operating_context.apply_workspace(
            profile,
            project_override=project_override,
        )
        self.snapshots.take_snapshot(
            SNAPSHOT_TYPE_CONTEXT_SWITCH,
            metadata={"workspace_key": profile.key, "previous_context": getattr(saved, "context_key", "")},
        )
        return ContextSwitchResult(
            success=True,
            message=f"Switched to {profile.name}.",
            active_context=active_context,
            saved_context=saved,
            paused_workflow_ids=paused_ids,
        )

    def switch_context(
        self,
        context_key: str,
        pause_current_workflows: bool = True,
        resume_saved_workflows: bool = True,
    ) -> ContextSwitchResult:
        """Restore a saved context by key."""
        saved = self.repository.get_named_context(context_key.strip())
        paused_ids: tuple[str, ...] = ()
        if pause_current_workflows:
            paused_ids = self.pause_active_workflows()
            self.save_current_context(status="paused")

        active_context = self.operating_context.restore_context(saved.context)
        resumed_ids: tuple[str, ...] = ()
        if resume_saved_workflows:
            resumed_ids = self.resume_workflows(saved.workflow_ids)
        self.repository.set_named_context_status(saved.context_key, "active")
        self.snapshots.take_snapshot(
            SNAPSHOT_TYPE_CONTEXT_SWITCH,
            metadata={"restored_context_key": saved.context_key},
        )
        return ContextSwitchResult(
            success=True,
            message=f"Restored {saved.name}.",
            active_context=active_context,
            saved_context=saved,
            paused_workflow_ids=paused_ids,
            resumed_workflow_ids=resumed_ids,
        )

    def pause_active_workflows(self) -> tuple[str, ...]:
        """Pause active workflows and return their ids."""
        paused: list[str] = []
        for workflow_id in self._active_workflow_ids():
            if self._pause_workflow(workflow_id):
                paused.append(workflow_id)
        return tuple(paused)

    def resume_workflows(self, workflow_ids: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        """Resume saved workflow ids."""
        resumed: list[str] = []
        for workflow_id in workflow_ids:
            if workflow_id and self._resume_workflow(workflow_id):
                resumed.append(workflow_id)
        return tuple(resumed)

    def list_saved_contexts(self, limit: int = 20) -> list[SavedContextRecord]:
        """Return saved contexts for UI context switching."""
        return self.repository.list_named_contexts(limit=limit)

    def _active_workflow_ids(self) -> tuple[str, ...]:
        if self.workflow_state is None or not hasattr(
            self.workflow_state,
            "list_active_workflows",
        ):
            return ()
        return tuple(
            workflow.id
            for workflow in self.workflow_state.list_active_workflows(limit=10)
            if getattr(workflow, "id", "")
        )

    def _pending_task_titles(self) -> tuple[str, ...]:
        if self.task_engine is None or not hasattr(self.task_engine, "list_tasks"):
            return ()
        return tuple(
            getattr(task, "title", str(task))
            for task in self.task_engine.list_tasks(status_filter="open")[:10]
        )

    def _pause_workflow(self, workflow_id: str) -> bool:
        target = self.workflow_execution or self.workflow_state
        if target is None or not hasattr(target, "pause_workflow"):
            return False
        target.pause_workflow(workflow_id)
        return True

    def _resume_workflow(self, workflow_id: str) -> bool:
        target = self.workflow_execution or self.workflow_state
        if target is None or not hasattr(target, "resume_workflow"):
            return False
        target.resume_workflow(workflow_id)
        return True

    def _generated_context_key(self, context: OperatingContext) -> str:
        base = context.current_workspace or context.operating_mode or "context"
        stamp = utc_now().strftime("%Y%m%d%H%M%S")
        return f"{base}_{stamp}"

    def _context_name(self, context: OperatingContext) -> str:
        workspace = context.metadata.get("workspace_name") or context.current_workspace
        if workspace:
            return f"{workspace} context"
        if context.current_project:
            return f"{context.current_project} context"
        return "Saved context"
