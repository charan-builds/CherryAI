"""AI engine orchestration.

AIEngine is the backend composition point for conversational workflows. It does
not directly manipulate UI widgets or database tables; it delegates intent
execution to the action router and persistence to the chat session manager.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.action_router.service import ActionRouter
from backend.ai_response_handler.schemas import AIWorkflowResult
from backend.ai_response_handler.service import AIResponseHandler
from backend.chat_session_manager.service import ChatSessionManager
from backend.intent_parser.service import IntentParser
from backend.ollama_service.service import OllamaGenerationError, OllamaService
from backend.prompt_manager.service import PromptManager
from backend.task_engine.service import TaskEngine

logger = logging.getLogger(__name__)


@dataclass
class AIEngine:
    """Coordinates local AI chat, intent routing, and response persistence."""

    settings: AppSettings
    task_engine: TaskEngine | None = None
    ollama_service: OllamaService | None = None
    prompt_manager: PromptManager | None = None
    intent_parser: IntentParser | None = None
    action_router: ActionRouter | None = None
    response_handler: AIResponseHandler | None = None
    chat_sessions: ChatSessionManager | None = None

    def __post_init__(self) -> None:
        self.prompt_manager = self.prompt_manager or PromptManager()
        self.ollama_service = self.ollama_service or OllamaService(self.settings)

        if self.task_engine is None:
            self.task_engine = TaskEngine(settings=self.settings)

        self.intent_parser = self.intent_parser or IntentParser(
            ollama_service=self.ollama_service,
            prompt_manager=self.prompt_manager,
        )
        self.action_router = self.action_router or ActionRouter(
            task_engine=self.task_engine,
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

        try:
            history_text = self.chat_sessions.format_history(active_session_id)
            parsed_intent = self.intent_parser.parse(user_message)
            action_result = self.action_router.route(parsed_intent)
            response_text = self.response_handler.build_response(
                user_message=user_message,
                parsed_intent=parsed_intent,
                action_result=action_result,
                history_text=history_text,
            )

            self.chat_sessions.record_interaction(
                session_id=active_session_id,
                user_prompt=user_message,
                ai_response=response_text,
                detected_intent=parsed_intent.intent,
            )

            logger.info("AI workflow completed with intent: %s", parsed_intent.intent)
            return AIWorkflowResult(
                session_id=active_session_id,
                user_message=user_message,
                response_text=response_text,
                detected_intent=parsed_intent.intent,
                success=action_result.success,
            )
        except Exception as exc:
            logger.exception("AI workflow failed")
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
