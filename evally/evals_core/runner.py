"""Run a suite of cases through the assistant, apply the checks, save and print the results."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from evally.app.assistant import Assistant, Turn
from evally.evals_core.cases import Case
from evally.evals_core.checks import CheckResult, run_check
from evally.llm.cache import ReplayMiss
from evally.types import Message


@dataclass
class CaseResult:
    id: str
    tags: list[str]
    status: str  # PASS, FAIL, ERROR, or UNCHECKED (a case with no checks, e.g. traffic)
    checks: list[CheckResult] = field(default_factory=list)
    replies: list[str] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)
    tokens: dict = field(default_factory=dict)
    error: str = ""
    turns: list[dict] = field(default_factory=list)  # every turn: user, reply, full trace


@dataclass
class RunResult:
    suite: str
    model: str
    cases: list[CaseResult]
    totals: dict


def run_case(case: Case, assistant: Assistant) -> CaseResult:
    history: list[Message] = []
    replies: list[str] = []
    turns: list[dict] = []
    turn: Turn | None = None
    tin = tout = 0
    try:
        for text in case.turns:
            history.append(Message("user", text))
            turn, history = assistant.respond(history)
            replies.append(turn.reply)
            turns.append({"user": text, "reply": turn.reply,
                          "trace": [{"kind": s.kind, "data": s.data} for s in turn.trace]})
            tin, tout = tin + turn.usage.input_tokens, tout + turn.usage.output_tokens
    except ReplayMiss as e:
        return CaseResult(case.id, case.tags, "ERROR", replies=replies, error=str(e), turns=turns)
    checks = [run_check(c, turn, list(case.turns)) for c in case.checks]
    docs = next((s.data["docs"] for s in turn.trace if s.kind == "retrieve"), [])
    if not checks:
        status = "UNCHECKED"
    else:
        status = "PASS" if all(c.passed for c in checks) else "FAIL"
    return CaseResult(case.id, case.tags, status, checks, replies, turn.tools_called, docs,
                      {"input": tin, "output": tout}, turns=turns)


def run_suite(suite: str, cases: list[Case], make_assistant: Callable[[], Assistant], model_name: str) -> RunResult:
    results = [run_case(c, make_assistant()) for c in cases]  # fresh assistant + store per case
    totals = {
        "cases": len(results),
        "passed": sum(r.status == "PASS" for r in results),
        "errors": sum(r.status == "ERROR" for r in results),
        "checks": sum(len(r.checks) for r in results),
        "checks_passed": sum(c.passed for r in results for c in r.checks),
        "unchecked": sum(r.status == "UNCHECKED" for r in results),
    }
    return RunResult(suite, model_name, results, totals)


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "-", text).strip("-")


def save_run(result: RunResult, runs_dir: Path) -> Path:
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{result.suite}-{slug(result.model)}.json"
    path.write_text(json.dumps(asdict(result), indent=2) + "\n")
    return path


def load_run(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def format_table(result: RunResult) -> str:
    width = max([len(c.id) for c in result.cases] + [4])
    status_w = max(len(c.status) for c in result.cases) if result.cases else 5
    status_w = max(status_w, 5)
    lines = [f"suite {result.suite} · model {result.model}", ""]
    for c in result.cases:
        why = c.error or "; ".join(f"{k.name} ({k.detail})" for k in c.checks if not k.passed)
        lines.append(f"  {c.id:<{width}}  {c.status:<{status_w}}  {why}".rstrip())
    t = result.totals
    unchecked = t.get("unchecked", 0)
    scope = f"{t['cases'] - unchecked} checked cases" if unchecked else f"{t['cases']} cases"
    lines += ["", f"passed {t['passed']}/{scope}, {t['checks_passed']}/{t['checks']} checks"
              + (f", {t['errors']} errors" if t["errors"] else "")
              + (f", {t['unchecked']} unchecked" if t.get("unchecked") else "")]
    return "\n".join(lines)
