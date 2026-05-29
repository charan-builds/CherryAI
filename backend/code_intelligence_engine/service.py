"""Static code intelligence for project summaries and walkthroughs."""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from config.settings import AppSettings
from backend.code_intelligence_engine.schemas import (
    CodeFileAnalysis,
    CodeWalkthrough,
    ProjectSummary,
)
from backend.context_understanding_engine.service import ContextUnderstandingEngine


_LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".jsx": "JavaScript React",
    ".sql": "SQL",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".css": "CSS",
    ".html": "HTML",
}

_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}


@dataclass
class CodeIntelligenceEngine:
    """Explains source files and project architecture using static analysis."""

    settings: AppSettings | None = None
    context_engine: ContextUnderstandingEngine | None = None

    def __post_init__(self) -> None:
        self.context_engine = self.context_engine or ContextUnderstandingEngine()

    def analyze_file(self, file_path: str | Path) -> CodeFileAnalysis:
        """Analyze one code file."""
        path = Path(file_path)
        text = path.read_text(encoding="utf-8", errors="ignore")
        language = self._language_for(path)
        functions: tuple[str, ...] = ()
        classes: tuple[str, ...] = ()
        imports: tuple[str, ...] = ()

        if path.suffix == ".py":
            functions, classes, imports = self._analyze_python(text)

        line_count = len(text.splitlines())
        summary = self._file_summary(path, language, line_count, functions, classes)
        context = self.context_engine.classify(text, source_type="code")
        return CodeFileAnalysis(
            file_path=str(path),
            language=language,
            line_count=line_count,
            functions=functions,
            classes=classes,
            imports=imports,
            summary=summary,
            context=context,
        )

    def summarize_project(self, root_path: str | Path) -> ProjectSummary:
        """Summarize a project directory without walking unbounded folders."""
        root = Path(root_path)
        limit = getattr(self.settings, "knowledge_project_file_limit", 80)
        files = list(self._iter_project_files(root, limit=limit))
        languages = Counter(self._language_for(path) for path in files)
        important_files = self._important_files(root, files)
        modules = sorted({path.parent.relative_to(root).parts[0] for path in files if path.parent != root})
        module_text = ", ".join(modules[:8]) if modules else "root-level files"
        architecture = (
            f"This project contains {len(files)} analyzed file(s) across "
            f"{', '.join(languages.keys()) or 'unknown languages'}. "
            f"Primary modules: {module_text}. "
            f"Important entry points: {', '.join(important_files) or 'none detected'}."
        )
        return ProjectSummary(
            root_path=str(root),
            file_count=len(files),
            languages=tuple(languages.keys()),
            important_files=tuple(important_files),
            architecture_summary=architecture,
        )

    def explain_architecture(self, root_path: str | Path) -> str:
        """Return a beginner-readable architecture explanation."""
        return self.summarize_project(root_path).architecture_summary

    def walkthrough_file(self, file_path: str | Path) -> CodeWalkthrough:
        """Produce a step-by-step code walkthrough."""
        analysis = self.analyze_file(file_path)
        steps: list[str] = []
        if analysis.imports:
            steps.append("Imports dependencies: " + ", ".join(analysis.imports[:8]))
        if analysis.classes:
            steps.append("Defines classes: " + ", ".join(analysis.classes))
        if analysis.functions:
            steps.append("Defines functions: " + ", ".join(analysis.functions))
        if not steps:
            steps.append("Contains declarations or content without top-level Python symbols.")
        return CodeWalkthrough(
            file_path=analysis.file_path,
            overview=analysis.summary,
            steps=tuple(steps),
        )

    def _analyze_python(
        self,
        text: str,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return (), (), ()

        functions = []
        classes = []
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        return tuple(functions), tuple(classes), tuple(dict.fromkeys(imports))

    def _file_summary(
        self,
        path: Path,
        language: str,
        line_count: int,
        functions: tuple[str, ...],
        classes: tuple[str, ...],
    ) -> str:
        parts = [f"{path.name} is a {language} file with {line_count} line(s)."]
        if classes:
            parts.append(f"It defines {len(classes)} class(es): {', '.join(classes)}.")
        if functions:
            parts.append(f"It defines {len(functions)} function(s): {', '.join(functions[:6])}.")
        if not classes and not functions:
            parts.append("No top-level Python classes or functions were detected.")
        return " ".join(parts)

    def _iter_project_files(self, root: Path, limit: int):
        count = 0
        for path in root.rglob("*"):
            if count >= limit:
                break
            if path.is_dir() or any(part in _SKIP_DIRS for part in path.parts):
                continue
            if self._language_for(path) == "Unknown":
                continue
            count += 1
            yield path

    def _important_files(self, root: Path, files: list[Path]) -> list[str]:
        important_names = {
            "app.py",
            "main.py",
            "__init__.py",
            "pyproject.toml",
            "requirements.txt",
            "package.json",
            "README.md",
        }
        important = []
        for path in files:
            if path.name in important_names:
                important.append(path.relative_to(root).as_posix())
        return important[:10]

    def _language_for(self, path: Path) -> str:
        return _LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "Unknown")
