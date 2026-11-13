"""Code-based checks: rules a program can verify with no model and no judgement.

Each check looks at the assistant's last turn: what it said and which tools it called.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from evally.app.assistant import Turn
from evally.app.tools import TOOLS
from evally.graders.refusal import refusal_match

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


def _calls(turn: Turn, tool: str) -> list[dict]:
    return [s.data.get("arguments") or {} for s in turn.trace if s.kind == "tool" and s.data["name"] == tool]


def _not_called(kind: str, tool: str) -> CheckResult:
    return CheckResult(f"{kind} {tool}", False, f"{tool} was not called")


def check_tool_args(turn: Turn, value: dict) -> CheckResult:
    """Some call to the tool has every listed argument with exactly this value."""
    tool, want = value["tool"], value["args"]
    calls = _calls(turn, tool)
    if not calls:
        return _not_called("tool_args", tool)
    ok = any(all(k in args and args[k] == v for k, v in want.items()) for args in calls)
    return CheckResult(f"tool_args {tool} {want}", ok, "" if ok else f"calls: {calls}")


def check_args_shape(turn: Turn, value: dict) -> CheckResult:
    """Every call to the tool has every listed argument as text fully matching its pattern."""
    tool, shape = value["tool"], value["args"]
    calls = _calls(turn, tool)
    if not calls:
        return _not_called("args_shape", tool)
    for args in calls:
        for k, pattern in shape.items():
            v = args.get(k)
            if not isinstance(v, str) or re.fullmatch(pattern, v) is None:
                return CheckResult(f"args_shape {tool}", False, f"{k}={v!r} doesn't match {pattern!r}")
    return CheckResult(f"args_shape {tool}", True, "")


def check_args_grounded(turn: Turn, value: dict, customer: list[str]) -> CheckResult:
    """Every call to the tool uses argument values the customer actually wrote (no invented ids).

    A rule about the calls that happen, not a demand to call: no call passes (with a note).
    Pair it with tool_called when a call is required."""
    tool, names = value["tool"], value["args"]
    calls = _calls(turn, tool)
    if not calls:
        return CheckResult(f"args_grounded {tool} {names}", True, f"{tool} was not called")
    said = "\n".join(customer).lower()
    for args in calls:
        for k in names:
            v = args.get(k)
            if isinstance(v, bool) or not isinstance(v, (str, int, float)) or str(v).lower() not in said:
                return CheckResult(f"args_grounded {tool} {names}", False,
                                   f"{k}={v!r} isn't in anything the customer wrote")
    return CheckResult(f"args_grounded {tool} {names}", True, "")


def check_refuses(turn: Turn, value: bool) -> CheckResult:
    m = refusal_match(turn.reply)
    return CheckResult("refuses", m is not None, f"matched {m!r}" if m else "no refusal phrase found")


def check_not_refuses(turn: Turn, value: bool) -> CheckResult:
    m = refusal_match(turn.reply)
    return CheckResult("not_refuses", m is None, f"refusal phrase {m!r}" if m else "")


CHECKS = {
    "contains": check_contains,
    "not_contains": check_not_contains,
    "tool_called": check_tool_called,
    "tool_not_called": check_tool_not_called,
    "max_words": check_max_words,
    "regex": check_regex,
    "not_regex": check_not_regex,
    "tool_args": check_tool_args,
    "args_shape": check_args_shape,
    "args_grounded": check_args_grounded,
    "refuses": check_refuses,
    "not_refuses": check_not_refuses,
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


def _tool_value(value, args_kind: str) -> str | None:
    if not isinstance(value, dict) or "tool" not in value or "args" not in value:
        return 'value must be {"tool": ..., "args": ...}'
    if err := _tool(value["tool"]):
        return err
    args = value["args"]
    if args_kind == "list":
        if not isinstance(args, list) or not args or not all(isinstance(a, str) for a in args):
            return "args must be a list of argument names"
        return None
    if not isinstance(args, dict) or not args:
        return "args must be an object of argument: value"
    if args_kind == "patterns":
        for k, pattern in args.items():
            if err := _pattern(pattern):
                return f"{k}: {err}"
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
    "tool_args": lambda v: _tool_value(v, "values"),
    "args_shape": lambda v: _tool_value(v, "patterns"),
    "args_grounded": lambda v: _tool_value(v, "list"),
    "refuses": lambda v: None if v is True else "value must be true",
    "not_refuses": lambda v: None if v is True else "value must be true",
}


def run_check(check: dict, turn: Turn, customer: list[str] | None = None) -> CheckResult:
    """`customer` is every message the customer sent, for checks that compare against them."""
    fn = CHECKS[check["type"]]
    if check["type"] in NEEDS_CUSTOMER:
        return fn(turn, check["value"], customer or [])
    return fn(turn, check["value"])


NEEDS_CUSTOMER = {"args_grounded"}
