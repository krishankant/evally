"""Code-based checks: rules a program can verify with no model and no judgement.

Each check looks at the assistant's last turn: what it said and which tools it called.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from evally.app.assistant import Turn
from evally.app.tools import TOOLS

TOOL_NAMES = tuple(t.name for t in TOOLS)


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


def check_regex(turn: Turn, value: str) -> CheckResult:
    ok = re.search(value, turn.reply, re.IGNORECASE) is not None
    return CheckResult(f"regex {value!r}", ok, "" if ok else f"reply doesn't match {value!r}")


def check_not_regex(turn: Turn, value: str) -> CheckResult:
    m = re.search(value, turn.reply, re.IGNORECASE)
    return CheckResult(f"not_regex {value!r}", m is None, "" if m is None else f"reply matches: {m.group(0)!r}")


CHECKS = {
    "contains": check_contains,
    "not_contains": check_not_contains,
    "tool_called": check_tool_called,
    "tool_not_called": check_tool_not_called,
    "max_words": check_max_words,
    "regex": check_regex,
    "not_regex": check_not_regex,
}


def _text(value) -> str | None:
    return None if isinstance(value, str) and value else "value must be non-empty text"


def _tool(value) -> str | None:
    if value not in TOOL_NAMES:
        return f"unknown tool {value!r} (tools: {', '.join(TOOL_NAMES)})"
    return None


def _count(value) -> str | None:
    ok = isinstance(value, int) and not isinstance(value, bool) and value > 0
    return None if ok else "value must be a whole number above 0"


def _pattern(value) -> str | None:
    if err := _text(value):
        return err
    try:
        re.compile(value)
    except re.error as e:
        return f"bad regex {value!r}: {e}"
    return None


# One validator per check type: an error message, or None. load_cases runs them, so a bad
# value stops every command that reads the case file, naming the file and line.
VALIDATORS: dict[str, Callable[[object], str | None]] = {
    "contains": _text,
    "not_contains": _text,
    "tool_called": _tool,
    "tool_not_called": _tool,
    "max_words": _count,
    "regex": _pattern,
    "not_regex": _pattern,
}


def run_check(check: dict, turn: Turn, customer: list[str] | None = None) -> CheckResult:
    """`customer` is every message the customer sent, for checks that compare against them."""
    fn = CHECKS[check["type"]]
    if check["type"] in NEEDS_CUSTOMER:
        return fn(turn, check["value"], customer or [])
    return fn(turn, check["value"])


NEEDS_CUSTOMER: set[str] = set()
