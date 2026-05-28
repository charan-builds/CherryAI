"""Prompt loading and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class PromptNotFoundError(FileNotFoundError):
    """Raised when a prompt template does not exist."""


@dataclass(frozen=True)
class PromptManager:
    """Loads prompt templates from disk and renders variables."""

    template_dir: Path | None = None

    def __post_init__(self) -> None:
        if self.template_dir is None:
            object.__setattr__(
                self,
                "template_dir",
                Path(__file__).resolve().parent / "templates",
            )

    def get_prompt(self, name: str, **variables: str) -> str:
        """Render a prompt template by name."""
        template_path = self.template_dir / f"{name}.txt"
        if not template_path.exists():
            raise PromptNotFoundError(f"Prompt template not found: {name}")

        template = template_path.read_text(encoding="utf-8")
        return template.format_map(_SafeVariables(variables))


class _SafeVariables(dict[str, str]):
    """Format mapping that leaves unknown variables empty."""

    def __missing__(self, key: str) -> str:
        return ""
