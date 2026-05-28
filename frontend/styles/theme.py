"""Stylesheet loading for Cherry AI.

Keeping QSS outside widget classes makes it easier to add light/dark themes,
user preferences, and packaged assets later.
"""

from __future__ import annotations

from pathlib import Path


STYLES_DIR = Path(__file__).resolve().parent


def load_stylesheet(theme_name: str = "dark_theme") -> str:
    """Load a QSS theme by file stem."""
    stylesheet_path = STYLES_DIR / f"{theme_name}.qss"
    return stylesheet_path.read_text(encoding="utf-8")
