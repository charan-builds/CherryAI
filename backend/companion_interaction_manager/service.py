"""Companion interaction manager."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from config.settings import AppSettings
from database.models import utc_now
from backend.companion_interaction_manager.repository import (
    CompanionInteractionRepository,
)
from backend.companion_interaction_manager.schemas import (
    CompanionDecision,
    CompanionMessage,
)


@dataclass
class CompanionInteractionManager:
    """Generates non-annoying companion messages with cooldowns."""

    settings: AppSettings
    repository: CompanionInteractionRepository | None = None

    def __post_init__(self) -> None:
        self.repository = self.repository or CompanionInteractionRepository.from_settings(
            self.settings
        )

    def greeting(self, now: datetime | None = None) -> CompanionMessage:
        """Create a friendly time-aware greeting."""
        current = now or utc_now()
        hour = current.hour
        if hour < 12:
            prefix = "Good morning"
        elif hour < 17:
            prefix = "Good afternoon"
        else:
            prefix = "Good evening"
        return CompanionMessage(
            interaction_type="greeting",
            title="Daily hello",
            message=f"{prefix} {self.settings.user_display_name}.",
            priority="low",
            cooldown_key=f"greeting_{current.date().isoformat()}",
            created_at=current,
        )

    def maybe_emit(
        self,
        message: CompanionMessage,
        cooldown_seconds: float | None = None,
        now: datetime | None = None,
    ) -> CompanionDecision:
        """Persist a message only when its cooldown permits it."""
        if not self.settings.companion_enabled:
            return CompanionDecision(False, "Companion layer disabled.")

        current = now or utc_now()
        cooldown = (
            self.settings.companion_message_cooldown_seconds
            if cooldown_seconds is None
            else cooldown_seconds
        )
        cooldown_key = message.cooldown_key or message.interaction_type
        if self.repository.has_recent(cooldown_key, current, cooldown):
            return CompanionDecision(False, "Companion cooldown active.")

        stored = self.repository.create(
            CompanionMessage(
                interaction_type=message.interaction_type,
                title=message.title,
                message=message.message,
                priority=message.priority,
                cooldown_key=cooldown_key,
                context=message.context,
                created_at=current,
            )
        )
        return CompanionDecision(True, "Message emitted.", stored)

    def coaching_nudge(
        self,
        title: str,
        message: str,
        cooldown_key: str,
        priority: str = "normal",
        context: dict[str, object] | None = None,
    ) -> CompanionDecision:
        """Emit a coaching nudge if it is not too soon."""
        return self.maybe_emit(
            CompanionMessage(
                interaction_type="coaching",
                title=title,
                message=message,
                priority=priority,
                cooldown_key=cooldown_key,
                context=context or {},
            )
        )

    def recent_feed(self, limit: int = 8) -> list[CompanionMessage]:
        """Return recent companion messages."""
        return self.repository.recent(limit=limit)
