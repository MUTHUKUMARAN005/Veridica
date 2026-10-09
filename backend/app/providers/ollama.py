from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings


@dataclass(frozen=True)
class OllamaProvider:
    settings: Settings

    def chat(self, prompt: str, system: str) -> str:
        response = httpx.post(
            f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
            json={
                "model": self.settings.ollama_chat_model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        message: Any = response.json().get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise RuntimeError("Ollama returned an invalid chat response.")
        return message["content"]

    def embed(self, text: str) -> list[float]:
        response = httpx.post(
            f"{self.settings.ollama_base_url.rstrip('/')}/api/embed",
            json={"model": self.settings.ollama_embedding_model, "input": text},
            timeout=60,
        )
        response.raise_for_status()
        embeddings: Any = response.json().get("embeddings")
        if (
            not isinstance(embeddings, list)
            or not embeddings
            or not isinstance(embeddings[0], list)
        ):
            raise RuntimeError("Ollama returned an invalid embedding response.")
        return [float(value) for value in embeddings[0]]
