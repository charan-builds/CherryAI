"""Schemas for Cherry's personal operating context layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


OPERATING_MODE_GENERAL = "general"
OPERATING_MODE_ML = "ml"
OPERATING_MODE_CODING = "coding"
OPERATING_MODE_REVISION = "revision"
OPERATING_MODE_STUDY = "study"

WORKSPACE_TYPE_BUILTIN = "builtin"
WORKSPACE_TYPE_CUSTOM = "custom"

SNAPSHOT_TYPE_PERIODIC = "periodic"
SNAPSHOT_TYPE_CONTEXT_SAVE = "context_save"
SNAPSHOT_TYPE_CONTEXT_SWITCH = "context_switch"
SNAPSHOT_TYPE_SESSION_RECOVERY = "session_recovery"


@dataclass(frozen=True)
class WorkspaceProfileRecord:
    """A persisted workspace profile."""

    key: str
    name: str
    description: str
    profile_type: str
    operating_mode: str
    focus_area: str
    project_path: str = ""
    default_goals: tuple[str, ...] = field(default_factory=tuple)
    default_documents: tuple[str, ...] = field(default_factory=tuple)
    apps: tuple[str, ...] = field(default_factory=tuple)
    urls: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, object] = field(default_factory=dict)
    is_builtin: bool = False
    is_active: bool = False
    id: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_used_at: datetime | None = None


@dataclass(frozen=True)
class OperatingContext:
    """The current operating mode, workspace, project, and focus state."""

    operating_mode: str = OPERATING_MODE_GENERAL
    current_project: str = ""
    current_workspace: str = ""
    focus_area: str = ""
    active_workflow_id: str = ""
    active_study_session_id: str = ""
    active_document: str = ""
    active_goals: tuple[str, ...] = field(default_factory=tuple)
    active_documents: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, object] = field(default_factory=dict)
    updated_at: datetime | None = None


@dataclass(frozen=True)
class SavedContextRecord:
    """A named context saved for later restore or switching."""

    context_key: str
    name: str
    context: OperatingContext
    status: str = "saved"
    workflow_ids: tuple[str, ...] = field(default_factory=tuple)
    pending_tasks: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class ActivitySnapshotRecord:
    """A persisted point-in-time operating snapshot."""

    id: str
    snapshot_type: str
    context: OperatingContext
    active_workflow_name: str = ""
    active_study_topic: str = ""
    pending_tasks: tuple[str, ...] = field(default_factory=tuple)
    workflow_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass(frozen=True)
class ContextSwitchResult:
    """Result returned after saving or switching operating context."""

    success: bool
    message: str
    active_context: OperatingContext
    saved_context: SavedContextRecord | None = None
    paused_workflow_ids: tuple[str, ...] = field(default_factory=tuple)
    resumed_workflow_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SessionRecoveryPlan:
    """Recoverable state collected from workflows, study, tasks, and snapshots."""

    active_workflows: tuple[object, ...]
    active_study_session: object | None
    workspace_state: OperatingContext
    pending_tasks: tuple[object, ...]
    last_snapshot: ActivitySnapshotRecord | None
    summary: str
    generated_at: datetime


@dataclass(frozen=True)
class ResumeSummary:
    """Human-facing answer for resuming work."""

    what_was_i_doing: str
    what_is_pending: tuple[str, ...]
    where_did_i_stop: str
    active_project: str
    active_workspace: str
    active_mode: str
    suggested_next_action: str
    generated_at: datetime

    def as_text(self) -> str:
        """Return a compact natural-language resume summary."""
        pending = "\n".join(f"- {item}" for item in self.what_is_pending)
        if not pending:
            pending = "- Nothing urgent is pending."
        return (
            f"What you were doing: {self.what_was_i_doing}\n"
            f"Pending:\n{pending}\n"
            f"Where you stopped: {self.where_did_i_stop}\n"
            f"Next: {self.suggested_next_action}"
        )
