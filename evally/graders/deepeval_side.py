"""The same code checks in DeepEval, side by side with evally's own (week 4).

DeepEval 4.3.2 has code-only metrics for two of our check types: PatternMatchMetric (regex) and
ToolCorrectnessMetric (tool + arguments). Neither calls a model, but ToolCorrectnessMetric builds an
OpenAI client when it's created, so it needs *a* key. `_deepeval_env` sets a placeholder key (only
if none is set) and turns DeepEval's telemetry off for the call, then puts the environment back.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

from evally.evals_core.cases import Case

PLACEHOLDER_KEY = "sk-placeholder-deepeval-makes-no-call"


@contextmanager
def _deepeval_env():
    saved = {k: os.environ.get(k) for k in ("OPENAI_API_KEY", "DEEPEVAL_TELEMETRY_OPT_OUT")}
    if not os.environ.get("OPENAI_API_KEY"):  # unset or blank (.env.example's `OPENAI_API_KEY=`)
        os.environ["OPENAI_API_KEY"] = PLACEHOLDER_KEY
    os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "1"
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _verdict(metric) -> str:
    return f"{'PASS' if metric.success else 'FAIL'} (score {metric.score:g})"


def compare(case: Case, recorded: dict) -> list[tuple[str, str, str]]:
    """(check, evally verdict, DeepEval verdict) for each of the case's checks.

    `recorded` is the case from a saved run (its last turn's reply and tool calls, and evally's
    verdicts in the same order as `case.checks`). Raises ValueError if the two don't line up."""
    kinds = [c["type"] for c in case.checks]
    names = [c["name"].split(" ", 1)[0] for c in recorded["checks"]]
    if kinds != names:
        raise ValueError(f"the run's checks ({', '.join(names)}) don't match the suite's ({', '.join(kinds)})")
    with _deepeval_env():
        from deepeval.metrics import PatternMatchMetric, ToolCorrectnessMetric
        from deepeval.test_case import LLMTestCase, ToolCall, ToolCallParams

        last = recorded["turns"][-1]
        called = [ToolCall(name=s["data"]["name"], input_parameters=s["data"].get("arguments") or {})
                  for s in last["trace"] if s["kind"] == "tool"]
        ours = ["PASS" if c["passed"] else "FAIL" for c in recorded["checks"]]
        rows: list[tuple[str, str, str]] = []
        for check, verdict in zip(case.checks, ours):
            kind, value = check["type"], check["value"]
            if kind == "regex":
                m = PatternMatchMetric(pattern=value, ignore_case=True)
                m.measure(LLMTestCase(input=last["user"], actual_output=last["reply"]))
                rows.append((f"regex {value!r}", verdict, _verdict(m)))
            elif kind == "tool_args":
                expected = [ToolCall(name=value["tool"], input_parameters=value["args"])]
                tc = LLMTestCase(input=last["user"], actual_output=last["reply"],
                                 tools_called=called, expected_tools=expected)
                for label, threshold in (("", 1.0), (" (DeepEval default threshold)", None)):
                    kwargs = {} if threshold is None else {"threshold": threshold}
                    m = ToolCorrectnessMetric(evaluation_params=[ToolCallParams.INPUT_PARAMETERS],
                                              include_reason=False, async_mode=False, **kwargs)
                    m.measure(tc)
                    rows.append((f"tool_args {value['tool']}{label}", verdict, _verdict(m)))
            else:
                rows.append((f"{kind} {value}" if not isinstance(value, dict) else kind, verdict, "no DeepEval equivalent"))
        return rows


def format_compare(case_id: str, rows: list[tuple[str, str, str]]) -> str:
    w = max([len("check")] + [len(r[0]) for r in rows])
    lines = [f"{case_id}: evally vs DeepEval 4.3.2", f"  {'check':<{w}}  evally  DeepEval"]
    lines += [f"  {c:<{w}}  {ours:<6}  {theirs}" for c, ours, theirs in rows]
    return "\n".join(lines)
