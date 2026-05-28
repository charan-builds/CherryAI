from dataclasses import replace

from backend.context_injection_engine.service import ContextInjectionEngine
from backend.context_retriever.schemas import ContextItem, RetrievedContext, ScoredContextItem
from database.models import utc_now
from tests.helpers import make_test_settings


class FakeRetriever:
    def retrieve(self, query, session_id=None):
        return RetrievedContext(query=query, items=[])


def test_context_injection_trims_to_configured_budget(tmp_path):
    settings = replace(make_test_settings(tmp_path), memory_context_max_chars=220)
    engine = ContextInjectionEngine(
        settings=settings,
        context_retriever=FakeRetriever(),
    )
    now = utc_now()
    retrieved = RetrievedContext(
        query="focus",
        items=[
            ScoredContextItem(
                item=ContextItem(
                    source="semantic_memory",
                    title="Night ML study",
                    content="The user prefers studying machine learning at night.",
                    category="semantic",
                    created_at=now,
                ),
                score=92,
            ),
            ScoredContextItem(
                item=ContextItem(
                    source="behavioral_pattern",
                    title="Long focus note",
                    content="Distractions appear after long sessions. " * 20,
                    category="behavioral",
                    created_at=now,
                ),
                score=88,
            ),
        ],
    )

    prompt_context = engine.from_retrieved_context(retrieved)

    assert len(prompt_context.text) <= settings.memory_context_max_chars
    assert prompt_context.included_items
    assert prompt_context.trimmed is True
    assert "Night ML study" in prompt_context.text
