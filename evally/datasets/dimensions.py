"""Dimensions: the fixed tag vocabulary for cases.

A tag with a colon is `dim:value` and both must be known; a tag without one is free text.
"""

from __future__ import annotations

DIMENSIONS: dict[str, tuple[str, ...]] = {
    "topic": ("returns", "shipping", "international", "orders", "stock", "membership",
              "gift-cards", "damaged", "preorders", "privacy", "account", "off-topic"),
    "difficulty": ("easy", "medium", "hard"),
    # week 2's failure taxonomy, plus none
    "category": ("none", "cant-find-book-by-title", "goes-beyond-policy", "misses-the-relevant-policy",
                 "unsupported-claims", "needless-escalation", "uses-outdated-policy"),
    "source": ("hand", "traffic", "generated", "adversarial"),
}


def parse_tag(tag: str) -> tuple[str, str] | None:
    if ":" not in tag:
        return None
    dim, value = tag.split(":", 1)
    return dim, value


def validate_tags(tags: list[str]) -> list[str]:
    errors, seen = [], {}
    for tag in tags:
        parsed = parse_tag(tag)
        if parsed is None:
            continue
        dim, value = parsed
        if dim not in DIMENSIONS:
            errors.append(f"unknown dimension {dim!r} in tag {tag!r} (known: {', '.join(DIMENSIONS)})")
        elif value not in DIMENSIONS[dim]:
            errors.append(f"unknown {dim} {value!r} in tag {tag!r} (allowed: {', '.join(DIMENSIONS[dim])})")
        elif dim in seen:
            errors.append(f"two values for {dim}: {seen[dim]!r} and {value!r}")
        else:
            seen[dim] = value
    return errors


def tag_value(tags: list[str], dim: str) -> str | None:
    for tag in tags:
        parsed = parse_tag(tag)
        if parsed and parsed[0] == dim:
            return parsed[1]
    return None
