"""AI engine for local model interaction.

The initial implementation is intentionally thin. It centralizes Ollama access
so future agent code can depend on Cherry AI's own interface instead of calling
the Ollama SDK directly throughout the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings


@dataclass
class AIEngine:
    """Wrapper around local Ollama model calls."""

    settings: AppSettings

    def generate(self, prompt: str) -> str:
        """Generate a response from the configured local model."""
        import ollama

        client = ollama.Client(host=self.settings.ollama_host)
        response = client.generate(
            model=self.settings.ollama_model,
            prompt=prompt,
        )
        return str(response.get("response", "")).strip()
