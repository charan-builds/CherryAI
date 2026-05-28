from pathlib import Path

from config.settings import load_settings


def test_load_settings_uses_environment_paths(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"

    monkeypatch.setenv("CHERRY_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CHERRY_DATA_DIR", str(data_dir))
    monkeypatch.setenv("CHERRY_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("CHERRY_OLLAMA_MODEL", "test-model")

    settings = load_settings()

    assert settings.project_root == Path(tmp_path).resolve()
    assert settings.data_dir == data_dir.resolve()
    assert settings.log_level == "DEBUG"
    assert settings.ollama_model == "test-model"
