"""Live Gemini API smoke test.

Opt-in real request that validates response, reports configured model/latency/status
without leaking credentials. Raises ProviderConfigurationError if GEMINI_API_KEY
is not set.

Usage (with key set):
    GEMINI_API_KEY=xxx python -m backend.scripts.gemini_smoke_test

Or import and call:
    from backend.scripts.gemini_smoke_test import run_smoke_test
    run_smoke_test()
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

from app.config import Settings
from app.providers.base import ProviderConfigurationError, ProviderError
from app.providers.gemini import GeminiProvider


def run_smoke_test() -> dict:
    """Run a minimal Gemini API request and return status dict.

    Returns a dict with response metadata. No credentials are emitted in
    any output.
    """
    settings = Settings()

    if not settings.gemini_api_key:
        raise ProviderConfigurationError(
            "GEMINI_API_KEY is required when AI_PROVIDER=gemini. "
            "Set it as a Codespace secret or in a .env file."
        )

    if not settings.gemini_model:
        raise ProviderConfigurationError(
            "GEMINI_MODEL is required when AI_PROVIDER=gemini."
        )

    provider = GeminiProvider(settings=settings)

    start = datetime.now(UTC)

    try:
        text = provider.chat(prompt="Say hello world", system="")
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        token_usage = getattr(provider, "last_token_usage", None)

        result: dict = {
            "status": "ok",
            "model": settings.gemini_model,
            "embedding_model_id": provider.embedding_model_id,
            "latency_ms": latency_ms,
            "response_preview": text[:60] + ("..." if len(text) > 60 else ""),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        if token_usage:
            result["token_usage"] = token_usage

        return result

    except Exception as error:  # noqa: BLE001
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        failure_category = (
            "retryable"
            if isinstance(error, ProviderError) and error.retryable
            else "provider_response"
        )
        return {
            "status": "failed",
            "model": settings.gemini_model,
            "latency_ms": latency_ms,
            "failure_category": failure_category,
            "error_type": type(error).__name__,
            "timestamp": datetime.now(UTC).isoformat(),
        }


def main() -> None:
    """CLI entry point: run smoke test and print JSON result."""
    try:
        result = run_smoke_test()
    except ProviderConfigurationError as error:
        print(json.dumps({"status": "configuration_error", "error": str(error)}))
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()