import os
import sys

import pytest

from evally import cli
from evally.evals_core.cases import Case


def recorded(reply, calls, checks):
    trace = [{"kind": "tool", "data": {"name": n, "arguments": a, "result": "", "is_error": False}} for n, a in calls]
    return {"id": "c", "replies": [reply], "checks": checks,
            "turns": [{"user": "Where is order BB-1002? ben@example.com", "reply": reply, "trace": trace}]}


ORDER = Case("c", [], ["Where is order BB-1002? ben@example.com"], [
    {"type": "regex", "value": r"\bshipped\b"},
    {"type": "tool_args", "value": {"tool": "lookup_order", "args": {"order_id": "BB-1002", "email": "ben@example.com"}}},
    {"type": "max_words", "value": 80},
])
REC = recorded("Your order BB-1002 has shipped.",
               [("lookup_order", {"order_id": "BB-1002", "email": "ben@example.com"})],
               [{"name": "regex", "passed": True, "detail": ""}, {"name": "tool_args", "passed": True, "detail": ""},
                {"name": "max_words", "passed": True, "detail": ""}])


def test_deepeval_missing_message(monkeypatch, tmp_path, capsys):
    monkeypatch.setitem(sys.modules, "deepeval", None)  # import deepeval -> ImportError
    monkeypatch.setenv("EVALLY_RUNS_DIR", str(tmp_path))
    assert cli.main(["deepeval", "any-run", "--suite", "week01", "--case", "x"]) == 1
    assert capsys.readouterr().out.strip() == "DeepEval isn't installed: uv sync --extra deepeval"


def test_pattern_match_is_fullmatch():
    pytest.importorskip("deepeval")
    from evally.graders.deepeval_side import _deepeval_env
    with _deepeval_env():
        from deepeval.metrics import PatternMatchMetric
        from deepeval.test_case import LLMTestCase
        m = PatternMatchMetric(pattern=r"\b30 days\b", ignore_case=True)
        m.measure(LLMTestCase(input="q", actual_output="You have 30 days to return it."))
    assert m.score == 0  # the whole reply must match; evally's regex searches


def test_tool_correctness_default_threshold_passes_wrong_arg():
    pytest.importorskip("deepeval")
    from evally.graders.deepeval_side import _deepeval_env
    with _deepeval_env():
        from deepeval.metrics import ToolCorrectnessMetric
        from deepeval.test_case import LLMTestCase, ToolCall, ToolCallParams
        tc = LLMTestCase(input="q", actual_output="x",
                         tools_called=[ToolCall(name="lookup_order", input_parameters={"order_id": "BB-1002", "email": "x@example.com"})],
                         expected_tools=[ToolCall(name="lookup_order", input_parameters={"order_id": "BB-1002", "email": "ben@example.com"})])
        m = ToolCorrectnessMetric(evaluation_params=[ToolCallParams.INPUT_PARAMETERS], include_reason=False, async_mode=False)
        m.measure(tc)
    assert m.score == 0.5 and m.success  # one wrong argument of two still passes at the default 0.5


def test_compare_rows():
    pytest.importorskip("deepeval")
    from evally.graders.deepeval_side import compare
    rows = compare(ORDER, REC)
    assert [r[0] for r in rows] == [
        r"regex '\\bshipped\\b'", "tool_args lookup_order", "tool_args lookup_order (DeepEval default threshold)",
        "max_words 80"]
    assert rows[0][1] == "PASS" and rows[0][2].startswith("FAIL")  # fullmatch
    assert rows[1][1] == "PASS" and rows[1][2].startswith("PASS")
    assert rows[3][2] == "no DeepEval equivalent"


def test_env_restored_after_compare(monkeypatch):
    pytest.importorskip("deepeval")
    from evally.graders.deepeval_side import compare
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPEVAL_TELEMETRY_OPT_OUT", raising=False)
    compare(ORDER, REC)
    assert "OPENAI_API_KEY" not in os.environ and "DEEPEVAL_TELEMETRY_OPT_OUT" not in os.environ
    monkeypatch.setenv("OPENAI_API_KEY", "real-key")
    compare(ORDER, REC)
    assert os.environ["OPENAI_API_KEY"] == "real-key"


def test_blank_key_gets_placeholder(monkeypatch):
    pytest.importorskip("deepeval")
    from evally.graders.deepeval_side import compare
    monkeypatch.setenv("OPENAI_API_KEY", "")  # what .env.example's `OPENAI_API_KEY=` loads as
    assert compare(ORDER, REC)
    assert os.environ["OPENAI_API_KEY"] == ""


def test_mismatched_run_and_suite_refused(tmp_path, monkeypatch, capsys):
    pytest.importorskip("deepeval")
    import json
    monkeypatch.setenv("EVALLY_RUNS_DIR", str(tmp_path))
    suite = tmp_path / "s-v2.jsonl"
    suite.write_text(json.dumps({"id": "c", "turns": ORDER.turns, "checks": ORDER.checks}) + "\n")
    run = {"suite": "s-v1", "model": "m", "totals": {}, "cases": [dict(REC, checks=REC["checks"][:2])]}
    (tmp_path / "r.json").write_text(json.dumps(run))
    assert cli.main(["deepeval", "r", "--suite", str(suite), "--case", "c"]) == 1
    assert "run r came from suite s-v1, not s-v2" in capsys.readouterr().out


def test_probe_import_runs_with_telemetry_off(monkeypatch):
    pytest.importorskip("deepeval")
    seen = {}
    import builtins
    real = builtins.__import__

    def spy(name, *a, **k):
        if name == "deepeval" and "probe" not in seen:
            seen["probe"] = os.environ.get("DEEPEVAL_TELEMETRY_OPT_OUT")
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", spy)
    monkeypatch.delenv("DEEPEVAL_TELEMETRY_OPT_OUT", raising=False)
    cli.main(["deepeval", "no-such-run", "--suite", "week01", "--case", "x"])
    assert seen.get("probe") == "1"
