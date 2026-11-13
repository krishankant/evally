"""Labels: a person's verdict on a saved conversation, with a note saying why.

Week 2's error analysis has two passes over the same labels file:

1. open coding (`evally label <run>`): read each conversation, mark it pass or fail, and
   write a free note in your own words about what went wrong;
2. axial coding (`evally label <run> --code`): group the fail notes into categories.

Labels are appended one JSON line at a time, so an interrupted session loses nothing;
when a case is labelled twice, the last line wins.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Literal

from evally.evals_core.traces import format_conversation

Ask = Callable[[str], str]
Say = Callable[[str], None]


@dataclass(frozen=True)
class Label:
    run: str
    case_id: str
    verdict: Literal["pass", "fail"]
    note: str
    category: str = ""
    labeler: str = "human"


def labels_path(run_name: str, labels_dir: Path) -> Path:
    return Path(labels_dir) / f"{run_name}.jsonl"


def load_labels(path: Path) -> dict[str, Label]:
    path = Path(path)
    if not path.exists():
        return {}
    labels: dict[str, Label] = {}
    for line in path.read_text().splitlines():
        if line.strip():
            label = Label(**json.loads(line))
            labels[label.case_id] = label
    return labels


def append_label(path: Path, label: Label) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(asdict(label), ensure_ascii=False) + "\n")


def _ask_until(ask: Ask, prompt: str, ok: Callable[[str], bool]) -> str:
    while True:
        answer = ask(prompt).strip()
        if ok(answer):
            return answer


def label_loop(run: dict, run_name: str, existing: dict[str, Label], labeler: str,
               ask: Ask, say: Say, save: Callable[[Label], None]) -> int:
    todo = [c for c in run["cases"] if c["id"] not in existing]
    done = 0
    try:
        for case in todo:
            say(format_conversation(case))
            verdict = _ask_until(ask, "verdict [p]ass / [f]ail / [s]kip / [q]uit: ",
                                 lambda a: a.lower() in ("p", "f", "s", "q"))
            verdict = verdict.lower()
            if verdict == "q":
                break
            if verdict == "s":
                continue
            needs_note = verdict == "f"
            note = _ask_until(ask, "note (what went wrong, or what was good): ",
                              lambda a: bool(a) or not needs_note)
            save(Label(run_name, case["id"], "pass" if verdict == "p" else "fail", note, "", labeler))
            done += 1
    except (EOFError, KeyboardInterrupt):
        pass
    say(f"labelled {done}, {len(todo) - done} left")
    return done
