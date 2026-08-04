from app.core.config import Settings, get_settings


def test_settings_default_values(monkeypatch):
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("ONTOLOGY_FILE_PATH", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_name == "MOZIP-AI"
    assert settings.environment == "local"
    assert settings.ontology_file_path == "app/ontology/mozip.owl"


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
