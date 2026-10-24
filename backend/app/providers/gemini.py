"""Gemini Developer API provider backed by httpx REST calls.

This provider is backend-only. Credentials and model identifiers are read from
application settings (environment / .env) and are never leaked to the frontend.
A configured Gemini call that fails persists an honest failed state; it never
falls back to Ollama, fixtures, or a mocked success.
"""

from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import Settings
from app.providers.base import (
    ProviderConfigurationError,
    ProviderResponseError,
    classify_http_error,
    classify_transport_error,
)

_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_DEFAULT_TEMPERATURE = 0.1
_DEFAULT_MAX_OUTPUT_TOKENS = 4096


@dataclass
class GeminiProvider:
    settings: Settings
    last_token_usage: dict[str, int] | None = field(
        init=False, repr=False, default=None
    )

    def __post_init__(self) -> None:
        if not self.settings.gemini_api_key:
            raise ProviderConfigurationError(
                "GEMINI_API_KEY is required when AI_PROVIDER=gemini."
            )
        if not self.settings.gemini_model:
            raise ProviderConfigurationError(
                "GEMINI_MODEL is required when AI_PROVIDER=gemini."
            )

    @property
    def model_id(self) -> str:
        return self.settings.gemini_model or ""

    @property
    def embedding_model_id(self) -> str:
        return self.settings.gemini_embedding_model or "text-embedding-004"

    def chat(self, prompt: str, system: str) -> str:
        """Return a raw JSON text response for the given prompt/system pair."""
        url = f"{_GEMINI_API_BASE}/{self.model_id}:generateContent"
        try:
            response = httpx.post(
                url,
                headers={
                    "x-goog-api-key": self.settings.gemini_api_key or "",
                    "content-type": "application/json",
                },
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": _DEFAULT_TEMPERATURE,
                        "maxOutputTokens": _DEFAULT_MAX_OUTPUT_TOKENS,
                    },
                },
                timeout=self.settings.ai_provider_timeout_seconds,
            )
        except httpx.TransportError as error:
            raise classify_transport_error(error, "Gemini Developer API") from error
        classify_http_error(response, "Gemini Developer API")
        try:
            payload: Any = response.json()
        except ValueError as error:
            raise ProviderResponseError(
                "Gemini Developer API returned an invalid JSON response."
            ) from error
        if not isinstance(payload, dict):
            raise ProviderResponseError(
                "Gemini Developer API returned an unexpected payload shape."
            )
        usage = payload.get("usageMetadata")
        if isinstance(usage, dict):
            self.last_token_usage = {
                "prompt_tokens": int(usage.get("promptTokenCount", 0) or 0),
                "candidates_tokens": int(usage.get("candidatesTokenCount", 0) or 0),
                "total_tokens": int(usage.get("totalTokenCount", 0) or 0),
            }
        else:
            self.last_token_usage = None
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ProviderResponseError(
                "Gemini Developer API returned no usable model response."
            )
        content = (
            candidates[0].get("content")
            if isinstance(candidates[0], dict)
            else None
        )
        parts = content.get("parts") if isinstance(content, dict) else None
        text = (
            parts[0].get("text")
            if isinstance(parts, list) and parts and isinstance(parts[0], dict)
            else None
        )
        if not isinstance(text, str) or not text.strip():
            raise ProviderResponseError("Gemini Developer API returned empty output.")
        return text

    def embed(self, text: str) -> list[float]:
        """Return one embedding vector for the given text."""
        if not text or not text.strip():
            raise ProviderResponseError("Cannot embed empty text.")
        url = f"{_GEMINI_API_BASE}/{self.embedding_model_id}:embedContent"
        try:
            response = httpx.post(
                url,
                headers={
                    "x-goog-api-key": self.settings.gemini_api_key or "",
                    "content-type": "application/json",
                },
                json={
                    "model": f"models/{self.embedding_model_id}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": "RETRIEVAL_DOCUMENT",
                    "outputDimensionality": self.settings.gemini_embedding_dimensions,
                },
                timeout=self.settings.ai_provider_timeout_seconds,
            )
        except httpx.TransportError as error:
            raise classify_transport_error(
                error, "Gemini Developer API embeddings"
            ) from error
        classify_http_error(response, "Gemini Developer API embeddings")
        try:
            payload: Any = response.json()
        except ValueError as error:
            raise ProviderResponseError(
                "Gemini Developer API returned an invalid embedding response."
            ) from error
        embedding = payload.get("embedding") if isinstance(payload, dict) else None
        values = embedding.get("values") if isinstance(embedding, dict) else None
        if not isinstance(values, list) or not values:
            raise ProviderResponseError(
                "Gemini Developer API returned no embedding values."
            )
        try:
            return [float(value) for value in values]
        except (TypeError, ValueError) as error:
            raise ProviderResponseError(
                "Gemini Developer API returned non-numeric embedding values."
            ) from error

