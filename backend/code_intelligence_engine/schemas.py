"""Schemas for code understanding."""

from __future__ import annotations

from dataclasses import dataclass

from backend.context_understanding_engine.schemas import ContextAnalysis


@dataclass(frozen=True)
class CodeFileAnalysis:
    """Static analysis for a single source file."""

    file_path: str
    language: str
    line_count: int
    functions: tuple[str, ...]
    classes: tuple[str, ...]
    imports: tuple[str, ...]
    summary: str
    context: ContextAnalysis


@dataclass(frozen=True)
class ProjectSummary:
    """High-level explanation of a project directory."""

    root_path: str
    file_count: int
    languages: tuple[str, ...]
    important_files: tuple[str, ...]
    architecture_summary: str


@dataclass(frozen=True)
class CodeWalkthrough:
    """Beginner-readable walkthrough for one source file."""

    file_path: str
    overview: str
    steps: tuple[str, ...]
