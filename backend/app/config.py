from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: PostgresDsn = "postgresql+psycopg://veridica:local-only@localhost:5432/veridica"
    redis_url: RedisDsn = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    jwt_secret: str = "development-only-change-me"
    access_token_minutes: int = 30
    ai_provider: Literal["ollama", "gemini"] = "ollama"
    ai_provider_timeout_seconds: int = 60
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_embedding_dimensions: int = 768
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    idea_asset_storage_dir: Path = ROOT / "backend" / ".private-assets"
    prototype_source_storage_dir: Path = ROOT / "backend" / ".private-prototypes"

    @model_validator(mode="after")
    def validate_runtime_configuration(self) -> "Settings":
        if self.database_url.scheme != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use the synchronous postgresql+psycopg driver.")
        if not self.cors_origins:
            raise ValueError("Configure at least one explicit CORS origin.")
        if self.ai_provider_timeout_seconds < 1 or self.ai_provider_timeout_seconds > 300:
            raise ValueError("AI provider timeout must be between 1 and 300 seconds.")
        if self.ollama_embedding_dimensions != 768:
            raise ValueError(
                "OLLAMA_EMBEDDING_DIMENSIONS must be 768 for the configured pgvector schema."
            )
        if self.app_env == "production" and self.ai_provider == "gemini":
            raise ValueError(
                "Gemini Developer API is a development-only provider; production must use "
                "the approved provider boundary."
            )
        if self.ai_provider == "gemini" and self.gemini_model is not None:
            if not self.gemini_model.strip() or any(
                character in self.gemini_model for character in "/:?&#"
            ):
                raise ValueError("GEMINI_MODEL must be a model identifier.")
        for origin in self.cors_origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or "*" in origin
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths.")
            try:
                if parsed.port == 0:
                    raise ValueError("Port zero is not a valid browser origin port.")
            except ValueError as error:
                raise ValueError("CORS origin has an invalid port.") from error
            if self.app_env == "production" and parsed.scheme != "https":
                raise ValueError("Production CORS origins must use HTTPS.")
        if self.app_env == "production":
            hosts = self.database_url.hosts()
            if any(host.get("password") in {None, "", "local-only"} for host in hosts):
                raise ValueError("Production requires explicit, non-sample database credentials.")
            if self.redis_url.scheme != "rediss":
                raise ValueError("Production Redis connections must use TLS (rediss).")
            if self.jwt_secret == "development-only-change-me" or len(self.jwt_secret) < 32:
                raise ValueError("Production requires a strong JWT secret.")
        return self