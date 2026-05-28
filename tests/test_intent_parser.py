from backend.intent_parser.service import IntentParser
from backend.prompt_manager.service import PromptManager
from tests.helpers import make_test_settings


class FakeIntentOllama:
    def __init__(self, response):
        self.response = response

    def generate(self, prompt, system_prompt="", model=None):
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_intent_parser_valid_create_task_json(tmp_path):
    settings = make_test_settings(tmp_path)
    parser = IntentParser(
        ollama_service=FakeIntentOllama(
            '{"intent":"create_task","title":"study numpy","priority":"high"}'
        ),
        prompt_manager=PromptManager(),
    )

    parsed = parser.parse("Add task study numpy")

    assert parsed.intent == "create_task"
    assert parsed.title == "study numpy"
    assert parsed.priority == "high"


def test_intent_parser_handles_wrapped_json(tmp_path):
    parser = IntentParser(
        ollama_service=FakeIntentOllama(
            'Sure: {"intent":"summarize_tasks","priority":"normal"}'
        ),
        prompt_manager=PromptManager(),
    )

    parsed = parser.parse("summarize my tasks")

    assert parsed.intent == "summarize_tasks"


def test_intent_parser_fallback_for_malformed_response(tmp_path):
    parser = IntentParser(
        ollama_service=FakeIntentOllama("not json"),
        prompt_manager=PromptManager(),
    )

    parsed = parser.parse("Add task study numpy")

    assert parsed.intent == "create_task"
    assert parsed.title == "study numpy"


def test_intent_parser_fallback_for_general_chat(tmp_path):
    parser = IntentParser(
        ollama_service=FakeIntentOllama(RuntimeError("offline")),
        prompt_manager=PromptManager(),
    )

    parsed = parser.parse("How are you?")

    assert parsed.intent == "general_chat"
