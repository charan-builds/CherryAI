"""Local Ollama service wrapper."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from config.settings import AppSettings

logger = logging.getLogger(__name__)

SUPPORTED_MODEL_PREFIXES = ("llama3", "mistral")


class OllamaGenerationError(RuntimeError):
    """Raised when Ollama generation fails after retries."""


def is_supported_ollama_model(model_name: str) -> bool:
    """Return whether the configured model family is officially supported."""
    normalized = model_name.strip().lower()
    return normalized.startswith(SUPPORTED_MODEL_PREFIXES)


@dataclass
class OllamaService:
    """Safe wrapper around the local Ollama runtime.

    The service is synchronous at its core because the Ollama Python client is
    synchronous. UI callers should run it in a worker thread; async callers can
    use generate_async.
    """

    settings: AppSettings
    client_factory: Callable[[], object] | None = None

    def check_connectivity(self) -> bool:
        """Check whether the local Ollama runtime responds."""
        try:
            client = self._create_client()
            client.list()
            logger.info("Ollama connectivity check succeeded")
            return True
        except Exception as exc:
            logger.warning("Ollama connectivity check failed: %s", exc)
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str | None = None,
    ) -> str:
        """Generate text with retry and graceful logging."""
        model_name = model or self.settings.ollama_model
        if not is_supported_ollama_model(model_name):
            logger.warning("Unsupported Ollama model configured: %s", model_name)

        last_error: Exception | None = None
        attempts = max(self.settings.ollama_max_retries, 0) + 1

        for attempt in range(1, attempts + 1):
            started = time.perf_counter()
            try:
                client = self._create_client()
                request = {"model": model_name, "prompt": prompt}
                if system_prompt:
                    request["system"] = system_prompt

                response = client.generate(**request)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                text = str(response.get("response", "")).strip()
                if not text:
                    raise OllamaGenerationError("Ollama returned an empty response.")

                logger.info(
                    "Ollama generation succeeded in %sms using %s",
                    elapsed_ms,
                    model_name,
                )
                return text
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Ollama generation attempt %s/%s failed: %s",
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    time.sleep(0.25)

        raise OllamaGenerationError(
            f"Ollama generation failed after {attempts} attempt(s): {last_error}"
        )

    async def generate_async(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str | None = None,
    ) -> str:
        """Async-ready wrapper for non-Qt runtimes."""
        return await asyncio.to_thread(self.generate, prompt, system_prompt, model)

    def _create_client(self) -> object:
        if self.client_factory is not None:
            return self.client_factory()

        import ollama

        return ollama.Client(
            host=self.settings.ollama_host,
            timeout=self.settings.ollama_timeout_seconds,
        )
