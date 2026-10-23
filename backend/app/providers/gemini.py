"""Gemini Developer API provider backed by the official google-genai SDK.

This provider is backend-only. Credentials and model identifiers are read from
application settings (environment / .env) and are never leaked to the frontend.
A configured Gemini call that fails persists an honest failed state; it never
falls back to Ollama, fixtures, or a mocked success.
"""

from dataclasses import dataclass, field
from typing import Any

import httpx
from google import genai
from google.genai.types import EmbedContentConfig, GenerateContentConfig

from app.config import Settings
from app.providers.base import (
    ProviderConfigurationError,
    ProviderError,
    ProviderResponseError,
    RetryableProviderError,
)

_DEFAULT_TEMPERATURE = 0.1
_DEFAULT_MAX_OUTPUT_TOKENS = 4096

_RETRYABLE_MESSAGE_FRAGMENTS = (
    "quota",
    "rate limit",
    "try again",
    "unavailable",
    "overloaded",
    "internal error",
    "deadline exceeded",
)


def _classify_error(error: Exception, provider: str) -> ProviderError:
    if isinstance(error, ProviderError):
        return error
    if isinstance(error, httpx.TransportError):
        return RetryableProviderError(f"Could not connect to {provider}.")
    if isinstance(error, httpx.HTTPStatusError):
        response = error.response
        if response is not None:
            if response.status_code in {408, 425, 429} or response.status_code >= 500:
                return RetryableProviderError(
                    f"{provider} is temporarily unavailable (HTTP {response.status_code})."
                )
            return ProviderResponseError(
                f"{provider} rejected the request (HTTP {response.status_code})."
            )
    message = str(error).casefold()
    if any(fragment in message for fragment in _RETRYABLE_MESSAGE_FRAGMENTS):
        return RetryableProviderError(f"{provider} transient failure: {error}")
    return ProviderResponseError(f"{provider} request failed: {error}")


def _usage_metadata(response: Any) -> dict[str, int] | None:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return None
    return {
        "prompt_tokens": int(getattr(usage, "prompt_token_count", 0) or 0),
        "candidates_tokens": int(getattr(usage, "candidates_token_count", 0) or 0),
        "total_tokens": int(getattr(usage, "total_token_count", 0) or 0),
    }


@dataclass
class GeminiProvider:
    settings: Settings
    _client: Any = field(init=False, repr=False)
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
        object.__setattr__(
            self,
            "_client",
            genai.Client(api_key=self.settings.gemini_api_key),
        )

    @property
    def model_id(self) -> str:
        return self.settings.gemini_model or ""

    @property
    def embedding_model_id(self) -> str:
        return self.settings.gemini_embedding_model or "text-embedding-004"

    def chat(self, prompt: str, system: str) -> str:
        """Return a raw JSON text response for the given prompt/system pair."""
        config = GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            temperature=_DEFAULT_TEMPERATURE,
            max_output_tokens=_DEFAULT_MAX_OUTPUT_TOKENS,
        )
        try:
            response = self._client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=config,
            )
        except Exception as error:  # noqa: BLE001 - translate all SDK errors
            raise _classify_error(error, "Gemini Developer API") from error
        self.last_token_usage = _usage_metadata(response)
        try:
            text = response.text
        except (ValueError, AttributeError) as error:
            raise ProviderResponseError(
                "Gemini Developer API returned no usable model response."
            ) from error
        if not isinstance(text, str) or not text.strip():
            raise ProviderResponseError("Gemini Developer API returned empty output.")
        return text

    def embed(self, text: str) -> list[float]:
        """Return one embedding vector for the given text."""
        if not text or not text.strip():
            raise ProviderResponseError("Cannot embed empty text.")
        try:
            response = self._client.models.embed_content(
                model=self.embedding_model_id,
                contents=text,
                config=EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
        except Exception as error:  # noqa: BLE001 - translate all SDK errors
            raise _classify_error(error, "Gemini Developer API embeddings") from error
        embeddings = getattr(response, "embeddings", None) or []
        if not embeddings or not getattr(embeddings[0], "values", None):
            raise ProviderResponseError("Gemini Developer API returned no embedding values.")
        try:
            return [float(value) for value in embeddings[0].values]
        except (TypeError, ValueError) as error:
            raise ProviderResponseError(
                "Gemini Developer API returned non-numeric embedding values."
            ) from error

