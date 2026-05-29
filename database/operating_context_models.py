"""Persistence models for Cherry's personal operating layer."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.models import utc_now


class WorkspaceProfile(Base):
    """A reusable workspace profile such as coding, revision, or ML study."""

    __tablename__ = "workspace_profiles"
    __table_args__ = (
        UniqueConstraint("workspace_key", name="uq_workspace_profile_key"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    workspace_key: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    profile_type: Mapped[str] = mapped_column(String(60), default="custom", index=True)
    operating_mode: Mapped[str] = mapped_column(String(60), default="general")
    focus_area: Mapped[str] = mapped_column(String(180), default="", nullable=False)
    project_path: Mapped[str] = mapped_column(Text, default="", nullable=False)
    goals_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    documents_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    apps_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    urls_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    is_builtin: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[int] = mapped_column(Integer, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OperatingContextState(Base):
    """Singleton state for Cherry's current operating context."""

    __tablename__ = "operating_context_state"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="current")
    operating_mode: Mapped[str] = mapped_column(String(60), default="general")
    current_project: Mapped[str] = mapped_column(Text, default="", nullable=False)
    current_workspace: Mapped[str] = mapped_column(String(120), default="", index=True)
    focus_area: Mapped[str] = mapped_column(String(180), default="", nullable=False)
    active_workflow_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    active_study_session_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    active_document: Mapped[str] = mapped_column(Text, default="", nullable=False)
    goals_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    documents_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SavedOperatingContext(Base):
    """A named context that can be restored during context switches."""

    __tablename__ = "saved_operating_contexts"
    __table_args__ = (
        UniqueConstraint("context_key", name="uq_saved_operating_context_key"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    context_key: Mapped[str] = mapped_column(String(140), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="saved", index=True)
    operating_mode: Mapped[str] = mapped_column(String(60), default="general")
    current_project: Mapped[str] = mapped_column(Text, default="", nullable=False)
    current_workspace: Mapped[str] = mapped_column(String(120), default="", index=True)
    focus_area: Mapped[str] = mapped_column(String(180), default="", nullable=False)
    active_workflow_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    active_study_session_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    active_document: Mapped[str] = mapped_column(Text, default="", nullable=False)
    goals_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    documents_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    workflow_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    pending_tasks_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class ActivitySnapshot(Base):
    """Point-in-time snapshot of the personal operating environment."""

    __tablename__ = "activity_snapshots"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    snapshot_type: Mapped[str] = mapped_column(String(60), default="periodic", index=True)
    operating_mode: Mapped[str] = mapped_column(String(60), default="general")
    current_project: Mapped[str] = mapped_column(Text, default="", nullable=False)
    current_workspace: Mapped[str] = mapped_column(String(120), default="", index=True)
    focus_area: Mapped[str] = mapped_column(String(180), default="", nullable=False)
    active_workflow_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    active_workflow_name: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    active_study_session_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    active_study_topic: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    active_document: Mapped[str] = mapped_column(Text, default="", nullable=False)
    goals_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    documents_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    pending_tasks_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    workflow_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )
