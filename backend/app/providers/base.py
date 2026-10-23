from typing import Protocol

import httpx


class ProviderError(Exception):
    retryable = False


class RetryableProviderError(ProviderError):
    retryable = True


class ProviderConfigurationError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


class ChatProvider(Protocol):
    model_id: str

    def chat(self, prompt: str, system: str) -> str: ...


def classify_http_error(response: httpx.Response, provider: str) -> None:
    if response.is_success:
        return
    if response.status_code in {408, 425, 429} or response.status_code >= 500:
        raise RetryableProviderError(
            f"{provider} is temporarily unavailable (HTTP {response.status_code})."
        )
    raise ProviderError(f"{provider} rejected the request (HTTP {response.status_code}).")


def classify_transport_error(error: httpx.TransportError, provider: str) -> ProviderError:
    if isinstance(error, httpx.TimeoutException):
        return RetryableProviderError(f"{provider} request timed out.")
    return RetryableProviderError(f"Could not connect to {provider}.")
