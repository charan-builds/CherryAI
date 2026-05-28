"""Path helpers.

All filesystem access should flow through pathlib-based helpers so the project
works cleanly on Windows today and remains portable for future packaging.
"""

from __future__ import annotations

from pathlib import Path


def get_project_root() -> Path:
    """Return the repository root based on this file's location."""
    return Path(__file__).resolve().parents[1]


def resolve_from_root(*parts: str) -> Path:
    """Build an absolute path inside the project root."""
    return get_project_root().joinpath(*parts).resolve()
