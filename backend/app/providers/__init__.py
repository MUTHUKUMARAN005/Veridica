"""External provider boundaries used by local and production implementations."""

from app.config import Settings
from app.providers.base import ChatProvider, ProviderConfigurationError
from app.providers.gemini import GeminiProvider
from app.providers.ollama import OllamaProvider


def build_chat_provider(settings: Settings) -> ChatProvider:
    if settings.ai_provider == "gemini":
        if not settings.gemini_api_key:
            raise ProviderConfigurationError(
                "GEMINI_API_KEY is required when AI_PROVIDER=gemini."
            )
        if not settings.gemini_model:
            raise ProviderConfigurationError(
                "GEMINI_MODEL is required when AI_PROVIDER=gemini."
            )
        return GeminiProvider(settings)
    return OllamaProvider(settings)
