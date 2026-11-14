"""Rubrics: one plain-text file per failure category, in `evals/rubrics/<category>.md`.

Each rubric says what PASS and FAIL mean for one week 2 failure category, so one grader
checks one thing. File names must be category names, so a typo can't create a grader
nobody asked for.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evally.datasets.dimensions import DIMENSIONS

RUBRICS_DIR = Path("evals/rubrics")


@dataclass(frozen=True)
class Rubric:
    name: str
    text: str


def load_rubrics(dir: Path = RUBRICS_DIR) -> dict[str, Rubric]:
    allowed = [c for c in DIMENSIONS["category"] if c != "none"]
    rubrics: dict[str, Rubric] = {}
    for path in sorted(Path(dir).glob("*.md")):
        if path.stem not in allowed:
            raise ValueError(f"{path}: rubric names must be week 2 categories ({', '.join(allowed)})")
        text = path.read_text().strip()
        if not text:
            raise ValueError(f"{path}: rubric is empty")
        rubrics[path.stem] = Rubric(path.stem, text)
    return rubrics
