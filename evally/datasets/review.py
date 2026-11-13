"""Review generated candidates: keep or drop each one, with a reason for every drop.

Decisions are stored next to the candidates file as `<stem>.review.jsonl`, one line per answer,
last line wins (the same store as week 2's labels). The survival rate (kept / reviewed) is the
number this step measures.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from evally.datasets.generate import Candidate
from evally.evals_core.jsonl_store import append_record, load_last_wins
from evally.evals_core.labels import Ask, Say, normalise


@dataclass(frozen=True)
class Decision:
    candidate_id: str
    keep: bool
    reason: str
    reviewer: str


def decisions_path(candidates_path: Path) -> Path:
    p = Path(candidates_path)
    return p.with_name(f"{p.stem}.review.jsonl")


def load_candidates(path: Path) -> list[Candidate]:
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    return [Candidate(r["id"], r["text"], r["dims"]) for r in rows]


def load_decisions(path: Path) -> dict[str, Decision]:
    return load_last_wins(path, Decision, lambda d: d.candidate_id)


def save_decision(path: Path, decision: Decision) -> None:
    append_record(path, decision)


def _ask_until(ask: Ask, prompt: str, ok: Callable[[str], bool]) -> str:
    while True:
        answer = ask(prompt).strip()
        if ok(answer):
            return answer


def review_loop(candidates: list[Candidate], existing: dict[str, Decision], reviewer: str,
                ask: Ask, say: Say, save: Callable[[Decision], None]) -> int:
    todo = [c for c in candidates if c.id not in existing]
    done = 0
    try:
        for c in todo:
            dims = "  ".join(f"{k}: {v}" for k, v in c.dims.items())
            say(f"── {c.id}   {dims}\n{c.text}\n")
            answer = _ask_until(ask, "keep? [k]eep / [d]rop / [q]uit: ", lambda a: a.lower() in ("k", "d", "q"))
            if answer.lower() == "q":
                break
            keep = answer.lower() == "k"
            prompt = "reason (optional; q to quit): " if keep else "reason for dropping (q to quit): "
            reason = _ask_until(ask, prompt, lambda a: keep or bool(a))
            if reason.lower() == "q":
                break
            save(Decision(c.id, keep, reason, reviewer))
            done += 1
    except (EOFError, KeyboardInterrupt):
        pass
    say(f"reviewed {done}, {len(todo) - done} left")
    return done


def survival_report(name: str, candidates: list[Candidate], decisions: dict[str, Decision]) -> str:
    ids = {c.id for c in candidates}
    current = [d for d in decisions.values() if d.candidate_id in ids]
    stale = len(decisions) - len(current)
    kept = sum(d.keep for d in current)
    dropped = len(current) - kept
    reviewers = ", ".join(sorted({d.reviewer for d in current})) or "none"
    rate = f" ({round(100 * kept / len(current))}% kept)" if current else ""
    lines = [f"review of {name} (reviewer: {reviewers})", "",
             f"  {len(candidates)} generated · {kept} kept · {dropped} dropped{rate}"]
    if len(candidates) > len(current):
        lines.append(f"  {len(candidates) - len(current)} not reviewed yet")
    counts: dict[str, int] = {}
    for d in current:
        if not d.keep:
            counts[normalise(d.reason)] = counts.get(normalise(d.reason), 0) + 1
    if counts:
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        w = max(len("drop reason"), *(len(r) for r, _ in ranked))
        lines += ["", f"  {'drop reason':<{w}}  {'count':>5}"]
        lines += [f"  {r:<{w}}  {n:>5}" for r, n in ranked]
    if stale:
        lines += ["", f"  {stale} stale decision{'s' if stale != 1 else ''} ignored (candidate not in this file)"]
    return "\n".join(lines)
