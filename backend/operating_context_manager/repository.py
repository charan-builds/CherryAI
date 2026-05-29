"""Repository for operating contexts, workspaces, and snapshots."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.models import utc_now
from database.operating_context_models import (
    ActivitySnapshot,
    OperatingContextState,
    SavedOperatingContext,
    WorkspaceProfile,
)
from database.session import create_database_engine, create_session_factory
from backend.operating_context_manager.schemas import (
    ActivitySnapshotRecord,
    OperatingContext,
    SavedContextRecord,
    WorkspaceProfileRecord,
)


class OperatingContextNotFoundError(ValueError):
    """Raised when a workspace or saved context does not exist."""


class OperatingContextRepository:
    """Database access for Cherry's personal operating environment."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "OperatingContextRepository":
        engine = create_database_engine(settings)
        return cls(create_session_factory(engine))

    @contextmanager
    def _session_scope(self) -> Iterator[Session]:
        with self.session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def upsert_workspace(self, profile: WorkspaceProfileRecord) -> WorkspaceProfileRecord:
        """Create or update a workspace profile."""
        with self._session_scope() as session:
            row = session.scalars(
                select(WorkspaceProfile).where(
                    WorkspaceProfile.workspace_key == profile.key
                )
            ).first()
            if row is None:
                row = WorkspaceProfile(workspace_key=profile.key)
                session.add(row)

            row.name = profile.name
            row.description = profile.description
            row.profile_type = profile.profile_type
            row.operating_mode = profile.operating_mode
            row.focus_area = profile.focus_area
            row.project_path = profile.project_path
            row.goals_json = _dump_json(list(profile.default_goals))
            row.documents_json = _dump_json(list(profile.default_documents))
            row.apps_json = _dump_json(list(profile.apps))
            row.urls_json = _dump_json(list(profile.urls))
            row.metadata_json = _dump_json(profile.metadata)
            row.is_builtin = 1 if profile.is_builtin else 0
            if profile.is_active:
                self._clear_active_workspaces(session)
                row.is_active = 1
                row.last_used_at = utc_now()
            session.flush()
            return self._workspace_record(row)

    def get_workspace(self, key: str) -> WorkspaceProfileRecord:
        """Return one workspace profile by key."""
        with self.session_factory() as session:
            row = self._workspace_model(session, key)
            return self._workspace_record(row)

    def list_workspaces(
        self,
        include_custom: bool = True,
    ) -> list[WorkspaceProfileRecord]:
        """List workspace profiles with active and built-in entries first."""
        statement = select(WorkspaceProfile).order_by(
            WorkspaceProfile.is_active.desc(),
            WorkspaceProfile.is_builtin.desc(),
            WorkspaceProfile.name.asc(),
        )
        if not include_custom:
            statement = statement.where(WorkspaceProfile.is_builtin == 1)
        with self.session_factory() as session:
            return [self._workspace_record(row) for row in session.scalars(statement)]

    def activate_workspace(self, key: str) -> WorkspaceProfileRecord:
        """Mark a workspace as the active workspace."""
        with self._session_scope() as session:
            row = self._workspace_model(session, key)
            self._clear_active_workspaces(session)
            row.is_active = 1
            row.last_used_at = utc_now()
            session.flush()
            return self._workspace_record(row)

    def get_current_context(self) -> OperatingContext:
        """Return the singleton current operating context."""
        with self.session_factory() as session:
            row = session.get(OperatingContextState, "current")
            if row is None:
                return OperatingContext()
            return self._context_record(row)

    def save_current_context(self, context: OperatingContext) -> OperatingContext:
        """Persist the singleton current operating context."""
        with self._session_scope() as session:
            row = session.get(OperatingContextState, "current")
            if row is None:
                row = OperatingContextState(id="current")
                session.add(row)
            self._apply_context(row, context)
            session.flush()
            return self._context_record(row)

    def save_named_context(
        self,
        context_key: str,
        name: str,
        context: OperatingContext,
        workflow_ids: tuple[str, ...] = (),
        pending_tasks: tuple[str, ...] = (),
        status: str = "saved",
        metadata: dict[str, object] | None = None,
    ) -> SavedContextRecord:
        """Create or update a named context restore point."""
        with self._session_scope() as session:
            row = session.scalars(
                select(SavedOperatingContext).where(
                    SavedOperatingContext.context_key == context_key
                )
            ).first()
            if row is None:
                row = SavedOperatingContext(context_key=context_key, name=name)
                session.add(row)

            row.name = name
            row.status = status
            row.operating_mode = context.operating_mode
            row.current_project = context.current_project
            row.current_workspace = context.current_workspace
            row.focus_area = context.focus_area
            row.active_workflow_id = context.active_workflow_id
            row.active_study_session_id = context.active_study_session_id
            row.active_document = context.active_document
            row.goals_json = _dump_json(list(context.active_goals))
            row.documents_json = _dump_json(list(context.active_documents))
            row.workflow_ids_json = _dump_json(list(workflow_ids))
            row.pending_tasks_json = _dump_json(list(pending_tasks))
            row.metadata_json = _dump_json(metadata or context.metadata)
            session.flush()
            return self._saved_context_record(row)

    def get_named_context(self, context_key: str) -> SavedContextRecord:
        """Return one saved context."""
        with self.session_factory() as session:
            row = session.scalars(
                select(SavedOperatingContext).where(
                    SavedOperatingContext.context_key == context_key
                )
            ).first()
            if row is None:
                raise OperatingContextNotFoundError(
                    f"Saved context not found: {context_key}"
                )
            return self._saved_context_record(row)

    def list_named_contexts(self, limit: int = 20) -> list[SavedContextRecord]:
        """List recently updated saved contexts."""
        statement = (
            select(SavedOperatingContext)
            .order_by(SavedOperatingContext.updated_at.desc())
            .limit(limit)
        )
        with self.session_factory() as session:
            return [self._saved_context_record(row) for row in session.scalars(statement)]

    def set_named_context_status(self, context_key: str, status: str) -> SavedContextRecord:
        """Update a saved context's lifecycle status."""
        with self._session_scope() as session:
            row = session.scalars(
                select(SavedOperatingContext).where(
                    SavedOperatingContext.context_key == context_key
                )
            ).first()
            if row is None:
                raise OperatingContextNotFoundError(
                    f"Saved context not found: {context_key}"
                )
            row.status = status
            session.flush()
            return self._saved_context_record(row)

    def create_snapshot(
        self,
        snapshot_type: str,
        context: OperatingContext,
        active_workflow_name: str = "",
        active_study_topic: str = "",
        pending_tasks: tuple[str, ...] = (),
        workflow_ids: tuple[str, ...] = (),
        metadata: dict[str, object] | None = None,
    ) -> ActivitySnapshotRecord:
        """Persist one activity snapshot."""
        with self._session_scope() as session:
            row = ActivitySnapshot(
                snapshot_type=snapshot_type,
                operating_mode=context.operating_mode,
                current_project=context.current_project,
                current_workspace=context.current_workspace,
                focus_area=context.focus_area,
                active_workflow_id=context.active_workflow_id,
                active_workflow_name=active_workflow_name,
                active_study_session_id=context.active_study_session_id,
                active_study_topic=active_study_topic,
                active_document=context.active_document,
                goals_json=_dump_json(list(context.active_goals)),
                documents_json=_dump_json(list(context.active_documents)),
                pending_tasks_json=_dump_json(list(pending_tasks)),
                workflow_ids_json=_dump_json(list(workflow_ids)),
                metadata_json=_dump_json(metadata or context.metadata),
            )
            session.add(row)
            session.flush()
            return self._snapshot_record(row)

    def latest_snapshot(self) -> ActivitySnapshotRecord | None:
        """Return the most recent activity snapshot."""
        statement = (
            select(ActivitySnapshot)
            .order_by(ActivitySnapshot.created_at.desc())
            .limit(1)
        )
        with self.session_factory() as session:
            row = session.scalars(statement).first()
            if row is None:
                return None
            return self._snapshot_record(row)

    def list_snapshots(self, limit: int = 20) -> list[ActivitySnapshotRecord]:
        """List recent activity snapshots."""
        statement = (
            select(ActivitySnapshot)
            .order_by(ActivitySnapshot.created_at.desc())
            .limit(limit)
        )
        with self.session_factory() as session:
            return [self._snapshot_record(row) for row in session.scalars(statement)]

    def _workspace_model(self, session: Session, key: str) -> WorkspaceProfile:
        row = session.scalars(
            select(WorkspaceProfile).where(WorkspaceProfile.workspace_key == key)
        ).first()
        if row is None:
            raise OperatingContextNotFoundError(f"Workspace profile not found: {key}")
        return row

    def _clear_active_workspaces(self, session: Session) -> None:
        for row in session.scalars(select(WorkspaceProfile).where(WorkspaceProfile.is_active == 1)):
            row.is_active = 0

    def _apply_context(
        self,
        row: OperatingContextState,
        context: OperatingContext,
    ) -> None:
        row.operating_mode = context.operating_mode
        row.current_project = context.current_project
        row.current_workspace = context.current_workspace
        row.focus_area = context.focus_area
        row.active_workflow_id = context.active_workflow_id
        row.active_study_session_id = context.active_study_session_id
        row.active_document = context.active_document
        row.goals_json = _dump_json(list(context.active_goals))
        row.documents_json = _dump_json(list(context.active_documents))
        row.metadata_json = _dump_json(context.metadata)

    def _workspace_record(self, row: WorkspaceProfile) -> WorkspaceProfileRecord:
        return WorkspaceProfileRecord(
            id=row.id,
            key=row.workspace_key,
            name=row.name,
            description=row.description,
            profile_type=row.profile_type,
            operating_mode=row.operating_mode,
            focus_area=row.focus_area,
            project_path=row.project_path,
            default_goals=tuple(_load_json(row.goals_json, [])),
            default_documents=tuple(_load_json(row.documents_json, [])),
            apps=tuple(_load_json(row.apps_json, [])),
            urls=tuple(_load_json(row.urls_json, [])),
            metadata=_load_json(row.metadata_json, {}),
            is_builtin=bool(row.is_builtin),
            is_active=bool(row.is_active),
            created_at=row.created_at,
            updated_at=row.updated_at,
            last_used_at=row.last_used_at,
        )

    def _context_record(self, row: OperatingContextState) -> OperatingContext:
        return OperatingContext(
            operating_mode=row.operating_mode,
            current_project=row.current_project,
            current_workspace=row.current_workspace,
            focus_area=row.focus_area,
            active_workflow_id=row.active_workflow_id,
            active_study_session_id=row.active_study_session_id,
            active_document=row.active_document,
            active_goals=tuple(_load_json(row.goals_json, [])),
            active_documents=tuple(_load_json(row.documents_json, [])),
            metadata=_load_json(row.metadata_json, {}),
            updated_at=row.updated_at,
        )

    def _saved_context_record(self, row: SavedOperatingContext) -> SavedContextRecord:
        context = OperatingContext(
            operating_mode=row.operating_mode,
            current_project=row.current_project,
            current_workspace=row.current_workspace,
            focus_area=row.focus_area,
            active_workflow_id=row.active_workflow_id,
            active_study_session_id=row.active_study_session_id,
            active_document=row.active_document,
            active_goals=tuple(_load_json(row.goals_json, [])),
            active_documents=tuple(_load_json(row.documents_json, [])),
            metadata=_load_json(row.metadata_json, {}),
            updated_at=row.updated_at,
        )
        return SavedContextRecord(
            id=row.id,
            context_key=row.context_key,
            name=row.name,
            status=row.status,
            context=context,
            workflow_ids=tuple(_load_json(row.workflow_ids_json, [])),
            pending_tasks=tuple(_load_json(row.pending_tasks_json, [])),
            metadata=_load_json(row.metadata_json, {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _snapshot_record(self, row: ActivitySnapshot) -> ActivitySnapshotRecord:
        context = OperatingContext(
            operating_mode=row.operating_mode,
            current_project=row.current_project,
            current_workspace=row.current_workspace,
            focus_area=row.focus_area,
            active_workflow_id=row.active_workflow_id,
            active_study_session_id=row.active_study_session_id,
            active_document=row.active_document,
            active_goals=tuple(_load_json(row.goals_json, [])),
            active_documents=tuple(_load_json(row.documents_json, [])),
            metadata=_load_json(row.metadata_json, {}),
            updated_at=row.created_at,
        )
        return ActivitySnapshotRecord(
            id=row.id,
            snapshot_type=row.snapshot_type,
            context=context,
            active_workflow_name=row.active_workflow_name,
            active_study_topic=row.active_study_topic,
            pending_tasks=tuple(_load_json(row.pending_tasks_json, [])),
            workflow_ids=tuple(_load_json(row.workflow_ids_json, [])),
            metadata=_load_json(row.metadata_json, {}),
            created_at=row.created_at,
        )


def _dump_json(payload: object) -> str:
    return json.dumps(payload, default=str)


def _load_json(raw_value: str, fallback):
    try:
        return json.loads(raw_value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback
