"""Operating context manager for Cherry's personal OS layer."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace

from config.settings import AppSettings
from backend.operating_context_manager.repository import OperatingContextRepository
from backend.operating_context_manager.schemas import (
    OPERATING_MODE_GENERAL,
    OperatingContext,
    WorkspaceProfileRecord,
)

logger = logging.getLogger(__name__)


@dataclass
class OperatingContextManager:
    """Maintains Cherry's current operating mode, project, workspace, and focus."""

    settings: AppSettings
    repository: OperatingContextRepository | None = None
    memory_engine: object | None = None

    def __post_init__(self) -> None:
        self.repository = self.repository or OperatingContextRepository.from_settings(
            self.settings
        )
        current = self.repository.get_current_context()
        if not current.updated_at:
            self.repository.save_current_context(current)

    def current_context(self) -> OperatingContext:
        """Return the current operating context."""
        return self.repository.get_current_context()

    def update_context(
        self,
        operating_mode: str | None = None,
        current_project: str | None = None,
        current_workspace: str | None = None,
        focus_area: str | None = None,
        active_workflow_id: str | None = None,
        active_study_session_id: str | None = None,
        active_document: str | None = None,
        active_goals: tuple[str, ...] | list[str] | None = None,
        active_documents: tuple[str, ...] | list[str] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> OperatingContext:
        """Merge updates into the current operating context."""
        current = self.current_context()
        merged_metadata = dict(current.metadata)
        if metadata:
            merged_metadata.update(metadata)

        updated = replace(
            current,
            operating_mode=_clean(operating_mode, current.operating_mode),
            current_project=_clean(current_project, current.current_project),
            current_workspace=_clean(current_workspace, current.current_workspace),
            focus_area=_clean(focus_area, current.focus_area),
            active_workflow_id=_clean(active_workflow_id, current.active_workflow_id),
            active_study_session_id=_clean(
                active_study_session_id,
                current.active_study_session_id,
            ),
            active_document=_clean(active_document, current.active_document),
            active_goals=_clean_tuple(active_goals, current.active_goals),
            active_documents=_clean_tuple(active_documents, current.active_documents),
            metadata=merged_metadata,
        )
        saved = self.repository.save_current_context(updated)
        self._update_working_memory(saved)
        logger.info(
            "Operating context updated: mode=%s workspace=%s project=%s",
            saved.operating_mode,
            saved.current_workspace,
            saved.current_project,
        )
        return saved

    def apply_workspace(
        self,
        profile: WorkspaceProfileRecord,
        project_override: str = "",
    ) -> OperatingContext:
        """Switch the current operating context to a workspace profile."""
        project = project_override.strip() or profile.project_path
        return self.update_context(
            operating_mode=profile.operating_mode,
            current_project=project,
            current_workspace=profile.key,
            focus_area=profile.focus_area,
            active_goals=profile.default_goals,
            active_documents=profile.default_documents,
            metadata={
                "workspace_name": profile.name,
                "workspace_description": profile.description,
                "workspace_apps": list(profile.apps),
                "workspace_urls": list(profile.urls),
            },
        )

    def set_general_mode(self) -> OperatingContext:
        """Return Cherry to a neutral general operating context."""
        return self.update_context(
            operating_mode=OPERATING_MODE_GENERAL,
            current_workspace="",
            focus_area="",
        )

    def set_active_workflow(self, workflow_id: str) -> OperatingContext:
        """Track the currently active workflow id."""
        return self.update_context(active_workflow_id=workflow_id)

    def set_active_study_session(self, session_id: str) -> OperatingContext:
        """Track the currently active study session id."""
        return self.update_context(active_study_session_id=session_id)

    def set_active_document(self, document: str) -> OperatingContext:
        """Track the active document and keep it in the document list."""
        current = self.current_context()
        cleaned = document.strip()
        documents = list(current.active_documents)
        if cleaned and cleaned not in documents:
            documents.insert(0, cleaned)
        return self.update_context(
            active_document=cleaned,
            active_documents=tuple(documents[:10]),
        )

    def add_goal(self, goal: str) -> OperatingContext:
        """Add a visible operating goal to current context."""
        cleaned = goal.strip()
        current = self.current_context()
        goals = list(current.active_goals)
        if cleaned and cleaned not in goals:
            goals.insert(0, cleaned)
        return self.update_context(active_goals=tuple(goals[:10]))

    def restore_context(self, context: OperatingContext) -> OperatingContext:
        """Replace current operating context with a saved context."""
        restored = self.repository.save_current_context(context)
        self._update_working_memory(restored)
        return restored

    def _update_working_memory(self, context: OperatingContext) -> None:
        if self.memory_engine is None or not hasattr(self.memory_engine, "working_memory"):
            return
        working_memory = getattr(self.memory_engine, "working_memory")
        content = (
            f"Mode {context.operating_mode}; workspace {context.current_workspace or 'none'}; "
            f"project {context.current_project or 'none'}; focus {context.focus_area or 'none'}."
        )
        try:
            working_memory.update_state(
                state_key="operating_context",
                state_type="operating_context",
                content=content,
                metadata={
                    "operating_mode": context.operating_mode,
                    "current_project": context.current_project,
                    "current_workspace": context.current_workspace,
                    "focus_area": context.focus_area,
                    "active_workflow_id": context.active_workflow_id,
                    "active_study_session_id": context.active_study_session_id,
                    "active_goals": list(context.active_goals),
                    "active_documents": list(context.active_documents),
                },
            )
        except Exception:
            logger.exception("Failed to update working memory for operating context")


def _clean(value: str | None, fallback: str) -> str:
    if value is None:
        return fallback
    return value.strip()


def _clean_tuple(
    value: tuple[str, ...] | list[str] | None,
    fallback: tuple[str, ...],
) -> tuple[str, ...]:
    if value is None:
        return fallback
    return tuple(item.strip() for item in value if item and item.strip())
