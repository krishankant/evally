from __future__ import annotations

import os
from typing import Literal

from evally.llm.base import Model

Provider = Literal["ollama", "openai", "anthropic"]
DEFAULT_OLLAMA_URL = "http://localhost:11434/v1"


def make_model(provider: Provider, model: str) -> Model:
    """Build a live model. Keys come from the environment (.env), loaded by config."""
    if provider == "ollama":
        from evally.llm.openai_compat import OpenAICompatModel

        # Ollama ignores the key, but the SDK insists on one.
        return OpenAICompatModel(model, base_url=os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL), api_key="ollama")
    if provider == "openai":
        from evally.llm.openai_compat import OpenAICompatModel

        return OpenAICompatModel(model)
    if provider == "anthropic":
        from evally.llm.anthropic_model import AnthropicModel

        return AnthropicModel(model)
    raise ValueError(f"Unknown provider {provider!r}: use ollama, openai or anthropic.")
