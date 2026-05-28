from backend.ollama_service.service import (
    OllamaGenerationError,
    OllamaService,
    is_supported_ollama_model,
)
from tests.helpers import make_test_settings


class FakeOllamaClient:
    def __init__(self, fail_generate_times=0, fail_list=False):
        self.fail_generate_times = fail_generate_times
        self.fail_list = fail_list
        self.generate_calls = 0

    def list(self):
        if self.fail_list:
            raise RuntimeError("offline")
        return {"models": []}

    def generate(self, **kwargs):
        self.generate_calls += 1
        if self.generate_calls <= self.fail_generate_times:
            raise TimeoutError("timeout")
        return {"response": "Hello from local Ollama"}


def test_ollama_connectivity_success_and_failure(tmp_path):
    settings = make_test_settings(tmp_path)
    online = OllamaService(settings, client_factory=lambda: FakeOllamaClient())
    offline = OllamaService(
        settings,
        client_factory=lambda: FakeOllamaClient(fail_list=True),
    )

    assert online.check_connectivity() is True
    assert offline.check_connectivity() is False


def test_ollama_generation_retries(tmp_path):
    settings = make_test_settings(tmp_path)
    client = FakeOllamaClient(fail_generate_times=1)
    settings = settings.__class__(**{**settings.__dict__, "ollama_max_retries": 1})
    service = OllamaService(settings, client_factory=lambda: client)

    assert service.generate("Hello") == "Hello from local Ollama"
    assert client.generate_calls == 2


def test_ollama_generation_raises_after_retries(tmp_path):
    settings = make_test_settings(tmp_path)
    client = FakeOllamaClient(fail_generate_times=2)
    service = OllamaService(settings, client_factory=lambda: client)

    try:
        service.generate("Hello")
    except OllamaGenerationError as exc:
        assert "failed after" in str(exc)
    else:
        raise AssertionError("Expected OllamaGenerationError")


def test_supported_model_families():
    assert is_supported_ollama_model("llama3")
    assert is_supported_ollama_model("llama3.1")
    assert is_supported_ollama_model("mistral")
    assert not is_supported_ollama_model("unknown-model")
