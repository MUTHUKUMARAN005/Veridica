from dataclasses import dataclass
from urllib.parse import quote

import httpx

from app.config import Settings
from app.providers.base import (
    ProviderConfigurationError,
    ProviderResponseError,
    classify_http_error,
    classify_transport_error,
)


@dataclass(frozen=True)
class GeminiProvider:
    settings: Settings

    @property
    def model_id(self) -> str:
        return self.settings.gemini_model or ""

    def chat(self, prompt: str, system: str) -> str:
        if not self.settings.gemini_api_key:
            raise ProviderConfigurationError(
                "GEMINI_API_KEY is required when AI_PROVIDER=gemini."
            )
        if not self.model_id:
            raise ProviderConfigurationError(
                "GEMINI_MODEL must be configured when AI_PROVIDER=gemini."
            )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{quote(self.model_id, safe='')}:generateContent"
        )
        try:
            response = httpx.post(
                url,
                headers={"x-goog-api-key": self.settings.gemini_api_key},
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.1,
                    },
                },
                timeout=self.settings.ai_provider_timeout_seconds,
            )
        except httpx.TransportError as error:
            raise classify_transport_error(error, "Gemini Developer API") from error
        classify_http_error(response, "Gemini Developer API")
        try:
            payload = response.json()
            parts = payload["candidates"][0]["content"]["parts"]
            text = "".join(part["text"] for part in parts if isinstance(part, dict))
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderResponseError(
                "Gemini Developer API returned no usable model response."
            ) from error
        if not text.strip():
            raise ProviderResponseError("Gemini Developer API returned empty output.")
        return text
