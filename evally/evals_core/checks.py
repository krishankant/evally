"""Code-based checks: rules a program can verify with no model and no judgement.

Each check looks at the assistant's last turn: what it said and which tools it called.
"""

from __future__ import annotations

from dataclasses import dataclass

from evally.app.assistant import Turn


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _contains(turn: Turn, value: str) -> bool:
    return value.lower() in turn.reply.lower()


def check_contains(turn: Turn, value: str) -> CheckResult:
    ok = _contains(turn, value)
    return CheckResult(f"contains {value!r}", ok, "" if ok else f"reply doesn't mention {value!r}")


def check_not_contains(turn: Turn, value: str) -> CheckResult:
    ok = not _contains(turn, value)
    return CheckResult(f"not_contains {value!r}", ok, "" if ok else f"reply mentions {value!r}")


def check_tool_called(turn: Turn, value: str) -> CheckResult:
    ok = value in turn.tools_called
    return CheckResult(f"tool_called {value}", ok, "" if ok else f"tools called: {turn.tools_called or 'none'}")


def check_tool_not_called(turn: Turn, value: str) -> CheckResult:
    ok = value not in turn.tools_called
    return CheckResult(f"tool_not_called {value}", ok, "" if ok else f"{value} was called")


def check_max_words(turn: Turn, value: int) -> CheckResult:
    n = len(turn.reply.split())
    return CheckResult(f"max_words {value}", n <= value, f"{n} words")


CHECKS = {
    "contains": check_contains,
    "not_contains": check_not_contains,
    "tool_called": check_tool_called,
    "tool_not_called": check_tool_not_called,
    "max_words": check_max_words,
}


def run_check(check: dict, turn: Turn) -> CheckResult:
    return CHECKS[check["type"]](turn, check["value"])
