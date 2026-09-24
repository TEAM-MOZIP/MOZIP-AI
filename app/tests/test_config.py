from app.core.config import Settings, get_settings


def test_settings_default_values(monkeypatch):
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("ONTOLOGY_FILE_PATH", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("GEMINI_CHAT_TIMEOUT_SECONDS", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_name == "MOZIP-AI"
    assert settings.environment == "local"
    assert settings.ontology_file_path == "app/ontology/mozip.owl"
    assert settings.gemini_api_key is None
    # alias("gemini-flash-lite-latest")가 아니라 확인된 구체 stable 모델 ID여야 한다.
    assert settings.gemini_model == "gemini-3.5-flash-lite"
    assert settings.gemini_timeout_seconds == 2.5
    assert settings.gemini_chat_timeout_seconds == 15.0


def test_settings_reads_from_environment(monkeypatch):
    monkeypatch.setenv("APP_NAME", "custom-name")
    monkeypatch.setenv("ENVIRONMENT", "production")

    settings = Settings(_env_file=None)

    assert settings.app_name == "custom-name"
    assert settings.environment == "production"


def test_get_settings_returns_cached_instance():
    get_settings.cache_clear()

    first = get_settings()
    second = get_settings()

    assert first is second
