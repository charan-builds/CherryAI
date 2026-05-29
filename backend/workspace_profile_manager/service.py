"""Workspace profile manager for personal operating workspaces."""

from __future__ import annotations

import re
from dataclasses import dataclass

from config.settings import AppSettings
from backend.operating_context_manager.repository import OperatingContextRepository
from backend.operating_context_manager.schemas import (
    OPERATING_MODE_CODING,
    OPERATING_MODE_ML,
    OPERATING_MODE_REVISION,
    WORKSPACE_TYPE_BUILTIN,
    WORKSPACE_TYPE_CUSTOM,
    WorkspaceProfileRecord,
)


@dataclass
class WorkspaceProfileManager:
    """Creates and manages reusable workspace profiles."""

    settings: AppSettings
    repository: OperatingContextRepository | None = None

    def __post_init__(self) -> None:
        self.repository = self.repository or OperatingContextRepository.from_settings(
            self.settings
        )
        self.ensure_default_profiles()

    def ensure_default_profiles(self) -> list[WorkspaceProfileRecord]:
        """Ensure ML, coding, and revision profiles exist."""
        defaults = [
            WorkspaceProfileRecord(
                key="ml_workspace",
                name="ML Workspace",
                description="Model learning, datasets, notebooks, and study focus.",
                profile_type=WORKSPACE_TYPE_BUILTIN,
                operating_mode=OPERATING_MODE_ML,
                focus_area="Machine learning study and experimentation",
                default_goals=(
                    "Continue ML learning plan",
                    "Review active dataset or notebook",
                ),
                default_documents=("ML notes", "Dataset notebook"),
                apps=("vscode",),
                urls=("https://www.kaggle.com/datasets", "https://docs.python.org/3/"),
                metadata={"kind": "study", "recommended_focus_minutes": 50},
                is_builtin=True,
            ),
            WorkspaceProfileRecord(
                key="coding_workspace",
                name="Coding Workspace",
                description="Editor, docs, active implementation goals, and code context.",
                profile_type=WORKSPACE_TYPE_BUILTIN,
                operating_mode=OPERATING_MODE_CODING,
                focus_area="Software implementation",
                default_goals=("Resume active implementation", "Run focused tests"),
                default_documents=("Active source files", "Project notes"),
                apps=("vscode",),
                urls=("https://docs.python.org/3/",),
                metadata={"kind": "engineering", "recommended_focus_minutes": 45},
                is_builtin=True,
            ),
            WorkspaceProfileRecord(
                key="revision_workspace",
                name="Revision Workspace",
                description="Review notes, practice material, and spaced repetition focus.",
                profile_type=WORKSPACE_TYPE_BUILTIN,
                operating_mode=OPERATING_MODE_REVISION,
                focus_area="Revision and recall",
                default_goals=("Review pending notes", "Complete a short recall block"),
                default_documents=("Revision notes",),
                apps=(),
                urls=("https://docs.google.com/",),
                metadata={"kind": "revision", "recommended_focus_minutes": 30},
                is_builtin=True,
            ),
        ]
        return [self.repository.upsert_workspace(profile) for profile in defaults]

    def list_profiles(
        self,
        include_custom: bool = True,
    ) -> list[WorkspaceProfileRecord]:
        """Return available workspace profiles."""
        return self.repository.list_workspaces(include_custom=include_custom)

    def get_profile(self, key: str) -> WorkspaceProfileRecord:
        """Return a workspace profile by key."""
        return self.repository.get_workspace(key.strip())

    def activate_profile(self, key: str) -> WorkspaceProfileRecord:
        """Mark a profile as active."""
        return self.repository.activate_workspace(key.strip())

    def create_custom_workspace(
        self,
        name: str,
        description: str = "",
        operating_mode: str = "custom",
        focus_area: str = "",
        project_path: str = "",
        default_goals: tuple[str, ...] | list[str] = (),
        default_documents: tuple[str, ...] | list[str] = (),
        apps: tuple[str, ...] | list[str] = (),
        urls: tuple[str, ...] | list[str] = (),
        metadata: dict[str, object] | None = None,
    ) -> WorkspaceProfileRecord:
        """Create or update a custom workspace profile."""
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Workspace name is required.")
        key = self._unique_key(_slug(cleaned_name) or "custom_workspace")
        profile = WorkspaceProfileRecord(
            key=key,
            name=cleaned_name,
            description=description.strip(),
            profile_type=WORKSPACE_TYPE_CUSTOM,
            operating_mode=operating_mode.strip().lower() or "custom",
            focus_area=focus_area.strip() or cleaned_name,
            project_path=project_path.strip(),
            default_goals=_clean_tuple(default_goals),
            default_documents=_clean_tuple(default_documents),
            apps=_clean_tuple(apps),
            urls=_clean_tuple(urls),
            metadata=metadata or {},
            is_builtin=False,
        )
        return self.repository.upsert_workspace(profile)

    def _unique_key(self, base_key: str) -> str:
        existing = {profile.key for profile in self.repository.list_workspaces()}
        if base_key not in existing:
            return base_key
        index = 2
        while f"{base_key}_{index}" in existing:
            index += 1
        return f"{base_key}_{index}"


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return cleaned.strip("_")


def _clean_tuple(value: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(item.strip() for item in value if item and item.strip())
