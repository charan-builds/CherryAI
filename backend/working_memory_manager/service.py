"""Working memory manager."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from config.settings import AppSettings
from database.models import utc_now
from backend.observer_engine.schemas import ObserverStatus
from backend.working_memory_manager.repository import WorkingMemoryRepository
from backend.working_memory_manager.schemas import WorkingMemoryRecord


@dataclass
class WorkingMemoryManager:
    """Tracks active conversation, study, goals, and temporary focus state."""

    settings: AppSettings
    repository: WorkingMemoryRepository | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = WorkingMemoryRepository.from_settings(self.settings)

    def update_state(
        self,
        state_key: str,
        state_type: str,
        content: str,
        metadata: dict[str, object] | None = None,
        ttl_minutes: int | None = None,
    ) -> WorkingMemoryRecord:
        """Store temporary context with an optional TTL."""
        ttl = ttl_minutes if ttl_minutes is not None else self.settings.working_memory_ttl_minutes
        expires_at = utc_now() + timedelta(minutes=max(ttl, 1))
        return self.repository.upsert(
            state_key=state_key,
            state_type=state_type,
            content=content.strip(),
            metadata=metadata or {},
            expires_at=expires_at,
        )

    def update_conversation(self, session_id: str, user_message: str) -> WorkingMemoryRecord:
        """Track the active conversation thread."""
        return self.update_state(
            state_key=f"conversation:{session_id}",
            state_type="conversation",
            content=user_message,
            metadata={"session_id": session_id},
        )

    def update_observer_status(self, status: ObserverStatus) -> list[WorkingMemoryRecord]:
        """Track current study and focus state from observer status."""
        records: list[WorkingMemoryRecord] = []
        focus_content = (
            f"Active app {status.active_app}; idle={status.is_idle}; "
            f"focus_seconds={int(status.focus_seconds)}; "
            f"distractions={status.distraction_count}."
        )
        records.append(
            self.update_state(
                "focus_state",
                "focus_state",
                focus_content,
                metadata={
                    "active_app": status.active_app,
                    "is_idle": status.is_idle,
                    "focus_seconds": status.focus_seconds,
                    "distraction_count": status.distraction_count,
                },
                ttl_minutes=30,
            )
        )

        if status.active_study_session is not None:
            session = status.active_study_session
            records.append(
                self.update_state(
                    "active_study_session",
                    "study_session",
                    f"Currently studying {session.topic}.",
                    metadata={"session_id": session.id, "topic": session.topic},
                    ttl_minutes=60,
                )
            )
        return records

    def list_active(self, state_type: str | None = None) -> list[WorkingMemoryRecord]:
        """Return active working memory states."""
        self.repository.clear_expired()
        return self.repository.list_active(state_type=state_type)
