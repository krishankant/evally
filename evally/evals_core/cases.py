"""Test cases: one JSON object per line in a .jsonl file.

    {"id": "return-window", "tags": ["returns"], "turns": ["How long do I have to return a book?"],
     "checks": [{"type": "contains", "value": "30"}]}

`turns` are the customer's messages, sent one after another. Checks apply to the last reply.
Lines starting with // are comments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from evally.datasets.dimensions import validate_tags
from evally.evals_core.checks import CHECKS, VALIDATORS


@dataclass(frozen=True)
class Case:
    id: str
    tags: list[str]
    turns: list[str]
    checks: list[dict]
    note: str = ""


def load_cases(path: Path) -> list[Case]:
    cases = []
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        d = json.loads(line)
        for c in d.get("checks", []):
            if c.get("type") not in CHECKS:
                raise ValueError(f"{path}:{n}: unknown check type {c.get('type')!r} (known: {', '.join(CHECKS)})")
            error = "missing value" if "value" not in c else VALIDATORS[c["type"]](c["value"])
            if error:
                raise ValueError(f"{path}:{n}: {c['type']}: {error}")
        errors = validate_tags(d.get("tags", []))
        if errors:
            raise ValueError(f"{path}:{n}: {errors[0]}")
        cases.append(Case(d["id"], d.get("tags", []), d["turns"], d.get("checks", []), d.get("note", "")))
    return cases
