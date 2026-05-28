"""Chat session manager."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from config.settings import AppSettings
from backend.chat_session_manager.repository import AIInteractionRepository
from backend.chat_session_manager.schemas import AIInteractionRecord

logger = logging.getLogger(__name__)


@dataclass
class ChatSessionManager:
    """Creates sessions and stores interaction history."""

    settings: AppSettings
    repository: AIInteractionRepository | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = AIInteractionRepository.from_settings(self.settings)

    def create_session(self) -> str:
        """Create a new in-memory session id."""
        return str(uuid4())

    def record_interaction(
        self,
        session_id: str,
        user_prompt: str,
        ai_response: str,
        detected_intent: str,
    ) -> AIInteractionRecord:
        """Persist one interaction."""
        record = self.repository.create(
            session_id=session_id,
            user_prompt=user_prompt,
            ai_response=ai_response,
            detected_intent=detected_intent,
        )
        logger.info("Persisted AI interaction: %s", record.id)
        return record

    def get_recent_history(self, session_id: str, limit: int = 8) -> list[AIInteractionRecord]:
        """Return recent chat history for prompt context."""
        return self.repository.list_recent(session_id=session_id, limit=limit)

    def format_history(self, session_id: str, limit: int = 8) -> str:
        """Return recent history as prompt-friendly text."""
        records = self.get_recent_history(session_id=session_id, limit=limit)
        if not records:
            return "No previous messages."

        lines: list[str] = []
        for record in records:
            lines.append(f"User: {record.user_prompt}")
            lines.append(f"Cherry AI: {record.ai_response}")
        return "\n".join(lines)
