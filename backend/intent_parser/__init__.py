"""Intent parsing for AI messages."""

from backend.intent_parser.schemas import ParsedIntent
from backend.intent_parser.service import IntentParser

__all__ = ["IntentParser", "ParsedIntent"]
