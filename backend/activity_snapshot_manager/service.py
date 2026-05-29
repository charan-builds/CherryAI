"""Activity snapshot manager for persistent operating context history."""

from __future__ import annotations

from dataclasses import dataclass, replace

from config.settings import AppSettings
from database.models import utc_now
from backend.operating_context_manager.repository import OperatingContextRepository
from backend.operating_context_manager.schemas import (
    SNAPSHOT_TYPE_PERIODIC,
    ActivitySnapshotRecord,
    OperatingContext,
)
from backend.operating_context_manager.service import OperatingContextManager


@dataclass
class ActivitySnapshotManager:
    """Creates and retrieves periodic snapshots of Cherry's active work."""

    settings: AppSettings
    operating_context: OperatingContextManager
    repository: OperatingContextRepository | None = None
    workflow_state: object | None = None
    task_engine: object | None = None
    observer_engine: object | None = None

    def __post_init__(self) -> None:
        self.repository = self.repository or OperatingContextRepository.from_settings(
            self.settings
        )

    def take_snapshot(
        self,
        snapshot_type: str = SNAPSHOT_TYPE_PERIODIC,
        context: OperatingContext | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ActivitySnapshotRecord:
        """Capture active project, workflow, goals, documents, and pending tasks."""
        base_context = context or self.operating_context.current_context()
        active_workflows = self._active_workflows()
        active_workflow = active_workflows[0] if active_workflows else None
        active_study = self._active_study_session()
        pending_tasks = self._pending_task_titles()

        active_workflow_id = getattr(active_workflow, "id", "") if active_workflow else ""
        active_workflow_name = (
            getattr(active_workflow, "name", "") if active_workflow else ""
        )
        active_study_id = getattr(active_study, "id", "") if active_study else ""
        active_study_topic = getattr(active_study, "topic", "") if active_study else ""

        effective_context = replace(
            base_context,
            active_workflow_id=active_workflow_id or base_context.active_workflow_id,
            active_study_session_id=active_study_id
            or base_context.active_study_session_id,
            metadata={
                **base_context.metadata,
                "snapshot_at": utc_now().isoformat(),
                **(metadata or {}),
            },
        )
        workflow_ids = tuple(
            getattr(workflow, "id", "")
            for workflow in active_workflows
            if getattr(workflow, "id", "")
        )
        return self.repository.create_snapshot(
            snapshot_type=snapshot_type,
            context=effective_context,
            active_workflow_name=active_workflow_name,
            active_study_topic=active_study_topic,
            pending_tasks=tuple(pending_tasks),
            workflow_ids=workflow_ids,
            metadata=effective_context.metadata,
        )

    def latest_snapshot(self) -> ActivitySnapshotRecord | None:
        """Return the most recent snapshot."""
        return self.repository.latest_snapshot()

    def list_snapshots(self, limit: int = 20) -> list[ActivitySnapshotRecord]:
        """Return recent snapshots."""
        return self.repository.list_snapshots(limit=limit)

    def _active_workflows(self) -> list[object]:
        if self.workflow_state is None or not hasattr(
            self.workflow_state,
            "list_active_workflows",
        ):
            return []
        return list(self.workflow_state.list_active_workflows(limit=5))

    def _pending_task_titles(self) -> list[str]:
        if self.task_engine is None or not hasattr(self.task_engine, "list_tasks"):
            return []
        return [
            getattr(task, "title", str(task))
            for task in self.task_engine.list_tasks(status_filter="open")[:10]
        ]

    def _active_study_session(self) -> object | None:
        if self.observer_engine is None or not hasattr(self.observer_engine, "get_status"):
            return None
        return self.observer_engine.get_status().active_study_session
