from config.settings import AppSettings


def make_test_settings(tmp_path) -> AppSettings:
    db_path = tmp_path / "cherry_ai.db"
    return AppSettings(
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
        pyautogui_failsafe=True,
        pyautogui_pause_seconds=0.1,
    )
