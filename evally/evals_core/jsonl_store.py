"""Append-only JSON-lines records where the last line for a key wins.

Week 2's labels and week 3's review decisions both use it: each answer is appended as one line,
so an interrupted session loses nothing, and changing your mind is just another line.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


def load_last_wins(path: Path, make: Callable[..., T], key: Callable[[T], str]) -> dict[str, T]:
    path = Path(path)
    if not path.exists():
        return {}
    records: dict[str, T] = {}
    for line in path.read_text().splitlines():
        if line.strip():
            record = make(**json.loads(line))
            records[key(record)] = record
    return records


def append_record(path: Path, record) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
