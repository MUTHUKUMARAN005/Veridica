from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings
from app.providers.base import (
    ProviderResponseError,
    classify_http_error,
    classify_transport_error,
)


@dataclass(frozen=True)
class OllamaProvider:
    settings: Settings

    @property
    def model_id(self) -> str:
        return self.settings.ollama_chat_model

    def chat(self, prompt: str, system: str) -> str:
        try:
            response = httpx.post(
                f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": self.model_id,
                    "stream": False,
                    "format": "json",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=self.settings.ai_provider_timeout_seconds,
            )
        except httpx.TransportError as error:
            raise classify_transport_error(error, "Ollama") from error
        classify_http_error(response, "Ollama")
        try:
            message: Any = response.json().get("message")
        except ValueError as error:
            raise ProviderResponseError("Ollama returned an invalid response.") from error
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ProviderResponseError("Ollama returned no chat content.")
        return message["content"]

    def embed(self, text: str) -> list[float]:
        try:
            response = httpx.post(
                f"{self.settings.ollama_base_url.rstrip('/')}/api/embed",
                json={"model": self.settings.ollama_embedding_model, "input": text},
                timeout=self.settings.ai_provider_timeout_seconds,
            )
        except httpx.TransportError as error:
            raise classify_transport_error(error, "Ollama embeddings") from error
        classify_http_error(response, "Ollama embeddings")
        try:
            embeddings: Any = response.json().get("embeddings")
        except ValueError as error:
            raise ProviderResponseError(
                "Ollama returned an invalid embedding response."
            ) from error
        if (
            not isinstance(embeddings, list)
            or not embeddings
            or not isinstance(embeddings[0], list)
        ):
            raise ProviderResponseError("Ollama returned an invalid embedding response.")
        try:
            return [float(value) for value in embeddings[0]]
        except (TypeError, ValueError) as error:
            raise ProviderResponseError("Ollama returned non-numeric embedding values.") from error
