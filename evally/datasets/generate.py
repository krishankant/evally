"""Generate candidate test messages from combinations of dimensions.

Each combination (topic x persona x phrasing) becomes one request to the model. The replies are
candidates, not cases: a person reviews them (evally review) before any join the dataset.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from dataclasses import dataclass

from evally.llm.cache import ReplayMiss
from evally.types import Message

GEN_SYSTEM = (
    "You write realistic test messages for a customer support assistant at Bramble Books, an online "
    "bookstore. Write ONE message a real customer might send. Match the topic, persona and phrasing you "
    "are given. Reply with the message only: no quotes, no explanation."
)

QUOTES = ('"', "'", "“", "”")


@dataclass(frozen=True)
class Candidate:
    id: str
    text: str
    dims: dict[str, str]


def candidate_id(dims: dict[str, str]) -> str:
    blob = json.dumps(dims, sort_keys=True)
    return "gen-" + hashlib.sha256(blob.encode()).hexdigest()[:8]


def sample_combinations(dims: dict[str, list[str]], n: int, seed: int) -> list[dict[str, str]]:
    names = list(dims)
    product = [dict(zip(names, values)) for values in itertools.product(*(dims[k] for k in names))]
    if n >= len(product):
        return product
    picked = sorted(random.Random(seed).sample(range(len(product)), n))  # stable: product order
    return [product[i] for i in picked]


def _clean(text: str) -> str:
    text = text.strip()
    while len(text) >= 2 and text[0] in QUOTES and text[-1] in QUOTES:
        text = text[1:-1].strip()
    return "" if text in QUOTES else text


def generate(model, combos: list[dict[str, str]], skip_unrecorded: bool = False
             ) -> tuple[list[Candidate], dict[str, int]]:
    """With skip_unrecorded, a combination with no recording is counted as "not recorded"
    instead of stopping the run (for when the live model can't finish every request)."""
    candidates, dropped = [], {}
    for combo in combos:
        prompt = f"Topic: {combo['topic']}\nPersona: {combo['persona']}\nPhrasing: {combo['phrasing']}"
        try:
            reply = model.complete([Message("user", prompt)], [], GEN_SYSTEM)
        except ReplayMiss:
            if not skip_unrecorded:
                raise
            dropped["not recorded"] = dropped.get("not recorded", 0) + 1
            continue
        text = _clean(reply.message.text or "")
        if not text:
            dropped["empty"] = dropped.get("empty", 0) + 1
            continue
        candidates.append(Candidate(candidate_id(combo), text, dict(combo)))
    return candidates, dropped
