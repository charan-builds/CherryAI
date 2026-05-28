"""Intent parsing service."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from backend.intent_parser.schemas import ParsedIntent
from backend.ollama_service.service import OllamaService
from backend.prompt_manager.service import PromptManager
from backend.task_engine.constants import TASK_PRIORITIES, TASK_PRIORITY_NORMAL

logger = logging.getLogger(__name__)

SUPPORTED_INTENTS = {
    "create_task",
    "list_tasks",
    "summarize_tasks",
    "motivational_response",
    "open_app",
    "open_website",
    "play_music",
    "take_screenshot",
    "start_study_workspace",
    "general_chat",
}


@dataclass
class IntentParser:
    """Extracts structured intent from natural language."""

    ollama_service: OllamaService
    prompt_manager: PromptManager

    def parse(self, user_message: str) -> ParsedIntent:
        """Parse a user message into a validated intent."""
        prompt = self.prompt_manager.get_prompt(
            "intent_extraction",
            user_message=user_message,
        )

        try:
            raw_response = self.ollama_service.generate(prompt)
            payload = self._parse_json_object(raw_response)
            parsed = self._validate_payload(payload, user_message)
            logger.info("Detected intent via Ollama: %s", parsed.intent)
            return parsed
        except Exception as exc:
            logger.info("Intent parser using fallback heuristic: %s", exc)
            return self._fallback_parse(user_message)

    def _parse_json_object(self, raw_response: str) -> dict[str, object]:
        stripped = raw_response.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return json.loads(stripped)

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in intent response.")

        return json.loads(stripped[start : end + 1])

    def _validate_payload(
        self,
        payload: dict[str, object],
        user_message: str,
    ) -> ParsedIntent:
        intent = str(payload.get("intent", "general_chat")).strip().lower()
        if intent not in SUPPORTED_INTENTS:
            intent = "general_chat"

        priority = str(payload.get("priority", TASK_PRIORITY_NORMAL)).strip().lower()
        if priority not in TASK_PRIORITIES:
            priority = TASK_PRIORITY_NORMAL

        title = str(payload.get("title", "")).strip()
        if intent == "create_task" and not title:
            title = self._extract_task_title(user_message)

        return ParsedIntent(
            intent=intent,
            title=title,
            description=str(payload.get("description", "")).strip(),
            priority=priority,
            app_name=str(payload.get("app_name", "")).strip(),
            url=str(payload.get("url", "")).strip(),
            query=str(payload.get("query", "")).strip(),
            topic=str(payload.get("topic", "")).strip(),
            raw=payload,
        )

    def _fallback_parse(self, user_message: str) -> ParsedIntent:
        normalized = user_message.strip().lower()

        if self._looks_like_task_creation(normalized):
            return ParsedIntent(
                intent="create_task",
                title=self._extract_task_title(user_message),
                priority=self._extract_priority(normalized),
                raw={"source": "fallback"},
            )

        if any(phrase in normalized for phrase in ("list tasks", "show tasks", "my tasks")):
            return ParsedIntent(intent="list_tasks", raw={"source": "fallback"})

        if "summarize" in normalized and "task" in normalized:
            return ParsedIntent(intent="summarize_tasks", raw={"source": "fallback"})

        if any(word in normalized for word in ("motivate", "motivation", "encourage")):
            return ParsedIntent(
                intent="motivational_response",
                raw={"source": "fallback"},
            )

        if "screenshot" in normalized:
            return ParsedIntent(intent="take_screenshot", raw={"source": "fallback"})

        if "study workspace" in normalized or "study setup" in normalized:
            return ParsedIntent(
                intent="start_study_workspace",
                topic=self._extract_after_keywords(
                    user_message,
                    ("study workspace", "study setup"),
                ),
                raw={"source": "fallback"},
            )

        if normalized.startswith(("open app ", "launch app ")):
            return ParsedIntent(
                intent="open_app",
                app_name=self._extract_after_keywords(
                    user_message,
                    ("open app", "launch app"),
                ),
                raw={"source": "fallback"},
            )

        if normalized.startswith(("open ", "launch ")):
            target = self._extract_after_keywords(user_message, ("open", "launch"))
            if "." in target or "http" in target.lower() or "youtube" in target.lower():
                return ParsedIntent(
                    intent="open_website",
                    url=target,
                    raw={"source": "fallback"},
                )
            return ParsedIntent(
                intent="open_app",
                app_name=target,
                raw={"source": "fallback"},
            )

        if "play music" in normalized or "focus music" in normalized:
            return ParsedIntent(
                intent="play_music",
                query=self._extract_after_keywords(
                    user_message,
                    ("play music", "play", "focus music"),
                )
                or "focus music",
                raw={"source": "fallback"},
            )

        return ParsedIntent(intent="general_chat", raw={"source": "fallback"})

    def _looks_like_task_creation(self, normalized: str) -> bool:
        return any(
            phrase in normalized
            for phrase in (
                "add task",
                "create task",
                "new task",
                "todo",
                "remind me to",
            )
        )

    def _extract_task_title(self, user_message: str) -> str:
        cleaned = re.sub(
            r"^\s*(add|create|new)\s+task\s*[:\-]?\s*",
            "",
            user_message,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"^\s*(todo|remind me to)\s*[:\-]?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        return cleaned.strip() or user_message.strip()

    def _extract_priority(self, normalized: str) -> str:
        if "high priority" in normalized or "urgent" in normalized:
            return "high"
        if "low priority" in normalized:
            return "low"
        return TASK_PRIORITY_NORMAL

    def _extract_after_keywords(self, user_message: str, keywords: tuple[str, ...]) -> str:
        for keyword in keywords:
            pattern = rf"^\s*{re.escape(keyword)}\s*[:\-]?\s*"
            cleaned = re.sub(pattern, "", user_message, flags=re.IGNORECASE).strip()
            if cleaned != user_message.strip():
                return cleaned
        return ""
