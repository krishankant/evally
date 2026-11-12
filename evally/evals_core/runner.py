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
    status: str  # PASS, FAIL or ERROR
    checks: list[CheckResult] = field(default_factory=list)
    replies: list[str] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)
    tokens: dict = field(default_factory=dict)
    error: str = ""


@dataclass
class RunResult:
    suite: str
    model: str
    cases: list[CaseResult]
    totals: dict


def run_case(case: Case, assistant: Assistant) -> CaseResult:
    history: list[Message] = []
    replies: list[str] = []
    turn: Turn | None = None
    tin = tout = 0
    try:
        for text in case.turns:
            history.append(Message("user", text))
            turn, history = assistant.respond(history)
            replies.append(turn.reply)
            tin, tout = tin + turn.usage.input_tokens, tout + turn.usage.output_tokens
    except ReplayMiss as e:
        return CaseResult(case.id, case.tags, "ERROR", replies=replies, error=str(e))
    checks = [run_check(c, turn) for c in case.checks]
    docs = next((s.data["docs"] for s in turn.trace if s.kind == "retrieve"), [])
    return CaseResult(case.id, case.tags, "PASS" if all(c.passed for c in checks) else "FAIL", checks,
                      replies, turn.tools_called, docs, {"input": tin, "output": tout})


def run_suite(suite: str, cases: list[Case], make_assistant: Callable[[], Assistant], model_name: str) -> RunResult:
    results = [run_case(c, make_assistant()) for c in cases]  # fresh assistant + store per case
    totals = {
        "cases": len(results),
        "passed": sum(r.status == "PASS" for r in results),
        "errors": sum(r.status == "ERROR" for r in results),
        "checks": sum(len(r.checks) for r in results),
        "checks_passed": sum(c.passed for r in results for c in r.checks),
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


def format_table(result: RunResult) -> str:
    width = max([len(c.id) for c in result.cases] + [4])
    lines = [f"suite {result.suite} · model {result.model}", ""]
    for c in result.cases:
        why = c.error or "; ".join(f"{k.name} ({k.detail})" for k in c.checks if not k.passed)
        lines.append(f"  {c.id:<{width}}  {c.status:<5}  {why}".rstrip())
    t = result.totals
    lines += ["", f"passed {t['passed']}/{t['cases']} cases, {t['checks_passed']}/{t['checks']} checks"
              + (f", {t['errors']} errors" if t["errors"] else "")]
    return "\n".join(lines)
