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

import os
import sys
import time
import json
from datetime import UTC, datetime

from google import genai

from app.config import Settings, load_settings
from app.providers.gemini import GeminiProvider
from app.providers.base import ProviderConfigurationError


def run_smoke_test() -> dict:
    """Run a minimal Gemini API request and return status dict.

    Returns a dict with response metadata. No credentials are emitted in
    any output.
    """
    settings: Settings = load_settings()

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
        # Use a minimal, harmless prompt; we only need to verify the call succeeds
        # and we get a non-empty response. No system instruction to avoid
        # unnecessary complexity; just a simple text generation.
        text = provider.chat(prompt="Say hello world", system="")
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)

        # Report last token usage if available
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

    except Exception as error:  # noqa: BLE001 - translate all SDK errors
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        # Classify the error category without leaking the full error message
        from app.providers.base import _classify_error

        classified = _classify_error(error, "Gemini Developer API")
        return {
            "status": "failed",
            "model": settings.gemini_model,
            "latency_ms": latency_ms,
            "failure_category": classified.retryable if hasattr(classified, "retryable") else "provider_response",
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