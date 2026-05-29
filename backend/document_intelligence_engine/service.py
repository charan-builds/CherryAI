"""Document parsing, extraction, and study-note generation."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from config.settings import AppSettings
from backend.content_summarization_engine.service import ContentSummarizationEngine
from backend.context_understanding_engine.service import ContextUnderstandingEngine
from backend.document_intelligence_engine.schemas import DocumentAnalysis

logger = logging.getLogger(__name__)


@dataclass
class DocumentIntelligenceEngine:
    """Understands PDFs and plain-text study materials."""

    settings: AppSettings | None = None
    summarizer: ContentSummarizationEngine | None = None
    context_engine: ContextUnderstandingEngine | None = None

    def __post_init__(self) -> None:
        self.summarizer = self.summarizer or ContentSummarizationEngine()
        self.context_engine = self.context_engine or ContextUnderstandingEngine()

    def analyze_document(self, document_path: str | Path) -> DocumentAnalysis:
        """Parse, summarize, classify, and note a document."""
        path = Path(document_path)
        text = self.extract_text(path)
        max_chars = getattr(self.settings, "knowledge_max_text_chars", 120_000)
        text = text[:max_chars]
        source_type = "pdf" if path.suffix.lower() == ".pdf" else "document"
        summary = self.summarizer.summarize(text)
        context = self.context_engine.classify(text, source_type=source_type)

        return DocumentAnalysis(
            document_path=str(path),
            title=self._title_for(path, text),
            text=text,
            summary=summary,
            context=context,
            notes=summary.notes,
            key_concepts=summary.key_concepts,
            page_count=self._page_count(path) if path.suffix.lower() == ".pdf" else 1,
        )

    def extract_text(self, document_path: str | Path) -> str:
        """Extract text from a PDF or text-like document."""
        path = Path(document_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf_text(path)
        if suffix in {".txt", ".md", ".rst", ".csv", ".json"}:
            return self._read_text(path)
        return self._read_text(path)

    def _extract_pdf_text(self, path: Path) -> str:
        library_text = self._extract_with_pypdf(path)
        if library_text:
            return library_text
        return self._extract_pdf_text_fallback(path)

    def _extract_with_pypdf(self, path: Path) -> str:
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception:
            return ""

        try:
            reader = PdfReader(str(path))
            parts = [page.extract_text() or "" for page in reader.pages]
            return self._normalize_text("\n".join(parts))
        except Exception:
            logger.exception("pypdf failed to extract text from %s", path)
            return ""

    def _extract_pdf_text_fallback(self, path: Path) -> str:
        raw = path.read_bytes().decode("latin-1", errors="ignore")
        literal_strings = re.findall(r"\(((?:\\.|[^\\()]){2,})\)", raw)
        decoded = [self._decode_pdf_literal(item) for item in literal_strings]

        readable_lines = []
        for line in raw.splitlines():
            line = line.strip()
            alpha_count = sum(1 for char in line if char.isalpha())
            if alpha_count >= 12 and not line.startswith(("%PDF", "/", "<<", "end")):
                readable_lines.append(line)

        return self._normalize_text(" ".join([*decoded, *readable_lines]))

    def _decode_pdf_literal(self, value: str) -> str:
        value = value.replace(r"\(", "(").replace(r"\)", ")")
        value = value.replace(r"\n", " ").replace(r"\r", " ").replace(r"\t", " ")
        return value.replace("\\", "")

    def _read_text(self, path: Path) -> str:
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return self._normalize_text(path.read_text(encoding=encoding))
            except UnicodeDecodeError:
                continue
        return self._normalize_text(path.read_bytes().decode("utf-8", errors="ignore"))

    def _page_count(self, path: Path) -> int:
        raw = path.read_bytes().decode("latin-1", errors="ignore")
        count = len(re.findall(r"/Type\s*/Page\b", raw))
        return max(count, 1)

    def _title_for(self, path: Path, text: str) -> str:
        first_sentence = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]
        if 5 <= len(first_sentence) <= 80:
            return first_sentence
        return path.stem.replace("_", " ").replace("-", " ").title()

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()
