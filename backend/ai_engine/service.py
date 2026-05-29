"""AI engine orchestration.

AIEngine is the backend composition point for conversational workflows. It does
not directly manipulate UI widgets or database tables; it delegates intent
execution to the action router and persistence to the chat session manager.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from config.settings import AppSettings
from backend.action_router.service import ActionRouter
from backend.automation_engine.service import AutomationEngine
from backend.ai_response_handler.schemas import AIWorkflowResult
from backend.ai_response_handler.service import AIResponseHandler
from backend.centralized_event_bus.schemas import (
    EVENT_CATEGORY_AI,
    PRIORITY_NORMAL,
    PlatformEvent,
)
from backend.centralized_event_bus.service import CentralizedEventBus
from backend.chat_session_manager.service import ChatSessionManager
from backend.error_recovery_engine.service import ErrorRecoveryEngine
from backend.intent_parser.service import IntentParser
from backend.memory_engine.service import MemoryEngine
from backend.observability_engine.service import ObservabilityEngine
from backend.ollama_service.service import OllamaGenerationError, OllamaService
from backend.prompt_manager.service import PromptManager
from backend.task_engine.service import TaskEngine

logger = logging.getLogger(__name__)


@dataclass
class AIEngine:
    """Coordinates local AI chat, intent routing, and response persistence."""

    settings: AppSettings
    task_engine: TaskEngine | None = None
    automation_engine: AutomationEngine | None = None
    memory_engine: MemoryEngine | None = None
    ollama_service: OllamaService | None = None
    prompt_manager: PromptManager | None = None
    intent_parser: IntentParser | None = None
    action_router: ActionRouter | None = None
    response_handler: AIResponseHandler | None = None
    chat_sessions: ChatSessionManager | None = None
    event_bus: CentralizedEventBus | None = None
    observability: ObservabilityEngine | None = None
    error_recovery: ErrorRecoveryEngine | None = None

    def __post_init__(self) -> None:
        self.prompt_manager = self.prompt_manager or PromptManager()
        self.ollama_service = self.ollama_service or OllamaService(self.settings)

        if self.task_engine is None:
            self.task_engine = TaskEngine(settings=self.settings)
        if self.automation_engine is None:
            self.automation_engine = AutomationEngine(settings=self.settings)
        if self.memory_engine is None:
            self.memory_engine = MemoryEngine(settings=self.settings)

        self.intent_parser = self.intent_parser or IntentParser(
            ollama_service=self.ollama_service,
            prompt_manager=self.prompt_manager,
        )
        self.action_router = self.action_router or ActionRouter(
            task_engine=self.task_engine,
            automation_engine=self.automation_engine,
        )
        self.response_handler = self.response_handler or AIResponseHandler(
            ollama_service=self.ollama_service,
            prompt_manager=self.prompt_manager,
        )
        self.chat_sessions = self.chat_sessions or ChatSessionManager(self.settings)

    def start_session(self) -> str:
        """Create a new chat session id."""
        return self.chat_sessions.create_session()

    def check_connectivity(self) -> bool:
        """Return whether Ollama is reachable."""
        return self.ollama_service.check_connectivity()

    def generate(self, prompt: str) -> str:
        """Compatibility wrapper for direct text generation."""
        try:
            return self.ollama_service.generate(prompt)
        except OllamaGenerationError as exc:
            logger.warning("Direct generation failed: %s", exc)
            return (
                "I could not reach Ollama. Please make sure the local Ollama "
                "runtime is running and the configured model is available."
            )

    def handle_message(
        self,
        user_message: str,
        session_id: str | None = None,
    ) -> AIWorkflowResult:
        """Process one user message through the full AI runtime workflow."""
        active_session_id = session_id or self.start_session()
        started = time.perf_counter()
        self._publish_event(
            "ai_request_started",
            active_session_id,
            {"session_id": active_session_id},
        )

        try:
            history_text = self.chat_sessions.format_history(active_session_id)
            self.memory_engine.update_conversation(active_session_id, user_message)
            memory_context = self.memory_engine.build_prompt_context(
                user_message=user_message,
                session_id=active_session_id,
            )
            parsed_intent = self.intent_parser.parse(user_message)
            action_result = self.action_router.route(parsed_intent)
            response_text = self.response_handler.build_response(
                user_message=user_message,
                parsed_intent=parsed_intent,
                action_result=action_result,
                history_text=history_text,
                memory_context=memory_context,
            )

            self.chat_sessions.record_interaction(
                session_id=active_session_id,
                user_prompt=user_message,
                ai_response=response_text,
                detected_intent=parsed_intent.intent,
            )

            logger.info("AI workflow completed with intent: %s", parsed_intent.intent)
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            self._publish_event(
                "ai_request_completed",
                active_session_id,
                {
                    "session_id": active_session_id,
                    "intent": parsed_intent.intent,
                    "success": action_result.success,
                    "duration_ms": duration_ms,
                },
            )
            if self.observability is not None:
                self.observability.record_timing(
                    "ai_handle_message",
                    duration_ms,
                    EVENT_CATEGORY_AI,
                )
            return AIWorkflowResult(
                session_id=active_session_id,
                user_message=user_message,
                response_text=response_text,
                detected_intent=parsed_intent.intent,
                success=action_result.success,
            )
        except Exception as exc:
            logger.exception("AI workflow failed")
            if self.error_recovery is not None:
                self.error_recovery.recover(exc, context="ai_handle_message")
            fallback_response = (
                "I hit a local runtime problem while handling that. "
                "Your desktop app is still running, and you can try again."
            )

            try:
                self.chat_sessions.record_interaction(
                    session_id=active_session_id,
                    user_prompt=user_message,
                    ai_response=fallback_response,
                    detected_intent="general_chat",
                )
            except Exception:
                logger.exception("Failed to persist fallback AI interaction")

            return AIWorkflowResult(
                session_id=active_session_id,
                user_message=user_message,
                response_text=f"{fallback_response}\n\nDetails: {exc}",
                detected_intent="general_chat",
                success=False,
            )

    def _publish_event(
        self,
        event_type: str,
        session_id: str,
        payload: dict[str, object],
    ) -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish(
            PlatformEvent(
                event_type=event_type,
                source="ai_engine",
                category=EVENT_CATEGORY_AI,
                priority=PRIORITY_NORMAL,
                correlation_id=session_id,
                payload=payload,
            )
        )
