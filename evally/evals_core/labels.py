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
            note = _ask_until(ask, "note (what went wrong, or what was good; q to quit): ",
                              lambda a: bool(a) or not needs_note)
            if note.lower() == "q":
                break
            save(Label(run_name, case["id"], "pass" if verdict == "p" else "fail", note, "", labeler))
            done += 1
    except (EOFError, KeyboardInterrupt):
        pass
    say(f"labelled {done}, {len(todo) - done} left")
    return done


def _normalise(name: str) -> str:
    return "-".join(name.lower().split())


def code_loop(labels: dict[str, Label], ask: Ask, say: Say, save: Callable[[Label], None],
              case_ids: set[str] | None = None) -> int:
    """Axial coding: give every fail label a category, reusing earlier ones by number.

    With `case_ids`, labels for cases no longer in the run (stale) are left alone.
    """
    categories = sorted({lab.category for lab in labels.values() if lab.category})
    todo = [lab for lab in labels.values() if lab.verdict == "fail" and not lab.category
            and (case_ids is None or lab.case_id in case_ids)]
    done = 0

    def valid(a: str) -> bool:
        if a.isdigit():
            return 1 <= int(a) <= len(categories)
        return bool(a)

    try:
        for lab in todo:
            listing = "\n".join(f"  {i}. {c}" for i, c in enumerate(categories, 1)) or "  (none yet)"
            say(f"{lab.case_id}: {lab.note}\ncategories so far:\n{listing}")
            answer = _ask_until(ask, "category (number, or a new name; q to stop): ", valid)
            if answer.lower() == "q":
                break
            name = categories[int(answer) - 1] if answer.isdigit() else _normalise(answer)
            if name not in categories:
                categories.append(name)
            new = Label(lab.run, lab.case_id, lab.verdict, lab.note, name, lab.labeler)
            labels[lab.case_id] = new
            save(new)
            done += 1
    except (EOFError, KeyboardInterrupt):
        pass
    say(f"categorised {done}, {len(todo) - done} left")
    return done


def category_counts(labels: dict[str, Label], case_ids: set[str]) -> tuple[list[tuple[str, int]], int]:
    """Fail counts per category, most first (ties by name), and how many labels are stale."""
    counts: dict[str, int] = {}
    stale = 0
    for lab in labels.values():
        if lab.case_id not in case_ids:
            stale += 1
        elif lab.verdict == "fail":
            name = lab.category or "uncategorised"
            counts[name] = counts.get(name, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])), stale


def format_report(run_name: str, labels: dict[str, Label], case_ids: set[str]) -> str:
    counts, stale = category_counts(labels, case_ids)
    current = [lab for lab in labels.values() if lab.case_id in case_ids]
    labelers = ", ".join(sorted({lab.labeler for lab in current})) or "none"
    fails = sum(lab.verdict == "fail" for lab in current)
    lines = [f"labels for {run_name} (labeller: {labelers})", "",
             f"  {len(current)} labelled · {len(current) - fails} pass · {fails} fail"]
    if counts:
        w = max(len("category"), *(len(name) for name, _ in counts))
        lines += ["", f"  {'category':<{w}}  {'fails':>5}"]
        lines += [f"  {name:<{w}}  {n:>5}" for name, n in counts]
    if stale:
        lines += ["", f"  {stale} stale label{'s' if stale != 1 else ''} ignored (case not in this run)"]
    return "\n".join(lines)
