"""What a model costs, in US dollars per million tokens (input, output).

Only models this course has actually run are listed. Local Ollama models cost nothing.
A hosted model goes in here with its price copied from the provider's price page and
the date it was copied; a model that isn't listed prints "cost unknown", never a guess.
"""

from __future__ import annotations

PRICES: dict[str, tuple[float, float]] = {
    "qwen3.5:4b": (0.0, 0.0),  # local, Ollama
    "llama3.2:3b": (0.0, 0.0),  # local, Ollama
}


def cost(model: str, tokens_in: int, tokens_out: int) -> float | None:
    if model not in PRICES:
        return None
    per_in, per_out = PRICES[model]
    return (tokens_in * per_in + tokens_out * per_out) / 1_000_000


def format_cost(model: str, tokens_in: int, tokens_out: int) -> str:
    c = cost(model, tokens_in, tokens_out)
    return f"tokens {tokens_in} in / {tokens_out} out · " + ("cost unknown" if c is None else f"${c:.4f}")
