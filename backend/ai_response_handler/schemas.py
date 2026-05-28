"""AI response schemas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AIWorkflowResult:
    """Final result returned to the desktop chat UI."""

    session_id: str
    user_message: str
    response_text: str
    detected_intent: str
    success: bool = True
