"""Browser automation helpers."""

from __future__ import annotations

import logging
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import quote_plus, urlparse

from backend.automation_engine.schemas import ToolExecutionResult

logger = logging.getLogger(__name__)


BrowserOpenFn = Callable[[str], bool]


@dataclass
class BrowserAutomation:
    """Opens URLs and study/music resources in the default browser."""

    opener: BrowserOpenFn | None = None

    def open_url(self, url: str) -> ToolExecutionResult:
        """Open a URL in the default browser."""
        normalized_url = self._normalize_url(url)
        try:
            self._open(normalized_url)
            return ToolExecutionResult(
                success=True,
                message=f"Opened {normalized_url}.",
                data={"url": normalized_url},
            )
        except Exception as exc:
            logger.exception("Failed to open URL: %s", normalized_url)
            return ToolExecutionResult(
                success=False,
                message="I could not open that website.",
                error_message=str(exc),
            )

    def open_youtube_search(self, query: str) -> ToolExecutionResult:
        """Open a YouTube search."""
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        return self.open_url(url)

    def open_playlist(self, playlist_url: str) -> ToolExecutionResult:
        """Open a playlist URL."""
        return self.open_url(playlist_url)

    def open_study_resources(self, topic: str) -> ToolExecutionResult:
        """Open a focused study search page for a topic."""
        query = quote_plus(topic.strip() or "study resources")
        return self.open_url(f"https://www.google.com/search?q={query}+study+resources")

    def _open(self, url: str) -> None:
        if self.opener is not None:
            self.opener(url)
        else:
            webbrowser.open_new_tab(url)

    def _normalize_url(self, url: str) -> str:
        cleaned = url.strip()
        parsed = urlparse(cleaned)
        if not parsed.scheme:
            cleaned = f"https://{cleaned}"
        return cleaned
