from config.settings import AppSettings
from database.init_db import initialize_database


def test_initialize_database_creates_sqlite_file(tmp_path):
    db_path = tmp_path / "cherry_ai.db"
    settings = AppSettings(
        app_name="Cherry AI",
        app_env="test",
        debug=False,
        log_level="INFO",
        sql_echo=False,
        project_root=tmp_path,
        data_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        database_url=f"sqlite:///{db_path.as_posix()}",
        ollama_host="http://localhost:11434",
        ollama_model="test-model",
        ollama_timeout_seconds=1.0,
        ollama_max_retries=0,
        pyautogui_failsafe=True,
        pyautogui_pause_seconds=0.1,
        observer_enabled=True,
        observer_poll_interval_seconds=0.1,
        idle_threshold_seconds=60.0,
        distraction_keywords=("YouTube", "Reddit"),
        automation_enabled=True,
        automation_timeout_seconds=1.0,
        screenshot_dir=tmp_path / "screenshots",
        custom_app_mappings={},
    )

    initialize_database(settings)

    assert db_path.exists()
