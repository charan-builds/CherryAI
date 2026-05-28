"""Chat session schemas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from database.ai_models import AIInteraction


@dataclass(frozen=True)
class AIInteractionRecord:
    """Immutable chat interaction record."""

    id: str
    session_id: str
    user_prompt: str
    ai_response: str
    detected_intent: str
    created_at: datetime

    @classmethod
    def from_model(cls, interaction: AIInteraction) -> "AIInteractionRecord":
        """Convert an ORM interaction into a DTO."""
        return cls(
            id=interaction.id,
            session_id=interaction.session_id,
            user_prompt=interaction.user_prompt,
            ai_response=interaction.ai_response,
            detected_intent=interaction.detected_intent,
            created_at=interaction.created_at,
        )
