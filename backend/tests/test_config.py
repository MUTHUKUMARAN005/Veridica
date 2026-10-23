import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.fixture(autouse=True)
def isolated_settings_environment(monkeypatch):
    for name in (
        "APP_ENV",
        "DATABASE_URL",
        "REDIS_URL",
        "CORS_ORIGINS",
        "JWT_SECRET",
        "AI_PROVIDER",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "OLLAMA_EMBEDDING_DIMENSIONS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_development_defaults_remain_usable():
    settings = Settings(_env_file=None)
    assert settings.app_env == "development"
    assert settings.database_url.scheme == "postgresql+psycopg"
    assert "http://127.0.0.1:5173" in settings.cors_origins
    assert settings.ollama_embedding_dimensions == 768


def test_embedding_dimension_must_match_versioned_pgvector_schema():
    with pytest.raises(ValidationError, match="must be 768"):
        Settings(_env_file=None, ollama_embedding_dimensions=384)


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://*.example.com",
        "https://example.com/path",
        "https://example.com/",
        "https://example.com?query=1",
        "https://example.com#fragment",
        "https://user:password@example.com",
        "file://example.com",
        "https://example.com:invalid",
        "https://example.com:0",
        "https://example.com:65536",
    ],
)
def test_cors_rejects_unsafe_or_non_origin_values(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=[origin])


def test_cors_requires_explicit_origins():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=[])


def test_rejects_async_database_driver():
    with pytest.raises(ValidationError, match="synchronous"):
        Settings(_env_file=None, database_url="postgresql+asyncpg://user:secret@localhost/db")


def test_production_requires_safe_configuration():
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(_env_file=None, app_env="production")
    with pytest.raises(ValidationError, match="non-sample"):
        Settings(_env_file=None, app_env="production", cors_origins=["https://app.example.com"])
    with pytest.raises(ValidationError, match="TLS"):
        Settings(
            _env_file=None,
            app_env="production",
            cors_origins=["https://app.example.com"],
            database_url="postgresql+psycopg://user:test-only-value@db.example.com/veridica",
        )


def test_environment_values_load_and_production_configuration_validates(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://user:test-only-value@db.example.com/veridica"
    )
    monkeypatch.setenv("REDIS_URL", "rediss://cache.example.com:6379/0")
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com"]')
    monkeypatch.setenv("JWT_SECRET", "a" * 32)
    settings = Settings(_env_file=None)
    assert settings.app_env == "production"
    assert settings.cors_origins == ["https://app.example.com"]


def test_validation_error_text_does_not_expose_configuration_secrets():
    secret_url = "postgresql+asyncpg://user:never-print-this@localhost/db"
    with pytest.raises(ValidationError) as failure:
        Settings(_env_file=None, database_url=secret_url)
    assert "never-print-this" not in str(failure.value)


def test_gemini_is_an_opt_in_development_provider_not_production_default():
    settings = Settings(_env_file=None)
    assert settings.ai_provider == "ollama"
    with pytest.raises(ValidationError, match="development-only"):
        Settings(
            _env_file=None,
            app_env="production",
            cors_origins=["https://app.example.com"],
            database_url="postgresql+psycopg://user:strong-pass@db.example.com/veridica",
            redis_url="rediss://cache.example.com:6379/0",
            jwt_secret="a" * 32,
            ai_provider="gemini",
        )