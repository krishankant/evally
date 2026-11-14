import json
import os
import sys

import pytest

from evally import cli
from evally.graders.rubrics import load_rubrics
from evally.llm.scripted import ScriptedModel, text_reply, tool_reply
from evally.types import ToolCall

CASE = {"id": "b", "status": "FAIL", "replies": ["Sure, 90 days!"],
        "turns": [{"user": "Can I have longer?", "reply": "Sure, 90 days!", "trace": []}]}


def geval_model():
    m = ScriptedModel([text_reply('{"steps": ["Check promises", "Check offers"]}'),
                       text_reply('{"score": 3, "reason": "promises 90 days"}')])
    m.name = "qwen3.5:4b"
    return m


def write_run(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "dev-qwen.json").write_text(json.dumps({"suite": "dev", "model": "qwen", "cases": [CASE], "totals": {}}))
    return runs


def test_cached_judge_routes_through_model():
    pytest.importorskip("deepeval")
    from evally.graders.deepeval_geval import make_cached_judge
    m = ScriptedModel([text_reply("hello back")])
    judge = make_cached_judge(m)
    assert judge.generate("hi") == "hello back"
    assert [x.text for x in m.calls[0].messages] == ["hi"] and m.calls[0].tools == []


def test_geval_case_with_scripted_judge(monkeypatch):
    pytest.importorskip("deepeval")
    from evally.graders.deepeval_geval import geval_case, split_case
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPEVAL_TELEMETRY_OPT_OUT", raising=False)
    model = geval_model()
    r = geval_case(model, load_rubrics()["goes-beyond-policy"], CASE, "## returns.md\n\n30 days")
    assert r["score"] == pytest.approx(0.3) and r["passed"] is False
    assert r["steps"] == ["Check promises", "Check offers"] and r["reason"] == "promises 90 days"
    assert len(model.calls) == 2
    assert "OPENAI_API_KEY" not in os.environ and "DEEPEVAL_TELEMETRY_OPT_OUT" not in os.environ
    conversation, reply = split_case(CASE)
    assert conversation == "customer: Can I have longer?" and reply == "Sure, 90 days!"


def test_split_case_keeps_earlier_turns():
    from evally.graders.deepeval_geval import split_case
    two = {"turns": [{"user": "Return?", "reply": "Order id?", "trace": []},
                     {"user": "BB-1001", "reply": "Started.", "trace": []}]}
    assert split_case(two) == ("customer: Return?\nassistant: Order id?\ncustomer: BB-1001", "Started.")


def test_geval_cli_side_by_side(tmp_path, monkeypatch, capsys):
    pytest.importorskip("deepeval")
    monkeypatch.setenv("EVALLY_RUNS_DIR", str(write_run(tmp_path)))
    ours = ScriptedModel([tool_reply(ToolCall("1", "record_verdict", {"reason": "promises 90", "verdict": "fail"}))])
    ours.name = "qwen3.5:4b"
    theirs = geval_model()
    models = iter([ours, theirs])
    monkeypatch.setattr(cli, "_grader_model", lambda args, cfg: next(models))
    assert cli.main(["geval", "dev-qwen", "--rubric", "goes-beyond-policy", "--case", "b"]) == 0
    out = capsys.readouterr().out
    assert "evally   FAIL  promises 90" in out
    assert "G-Eval   FAIL  0.30 (threshold 0.5)  promises 90 days" in out
    assert "1. Check promises" in out and "2. Check offers" in out
    assert "tokens 30 in / 15 out · $0.0000" in out


def test_geval_unknown_rubric(tmp_path, monkeypatch, capsys):
    pytest.importorskip("deepeval")
    monkeypatch.setenv("EVALLY_RUNS_DIR", str(write_run(tmp_path)))
    assert cli.main(["geval", "dev-qwen", "--rubric", "beyond", "--case", "b"]) == 1
    assert "unknown rubric 'beyond'" in capsys.readouterr().out


def test_geval_missing_message(monkeypatch, tmp_path, capsys):
    monkeypatch.setitem(sys.modules, "deepeval", None)
    monkeypatch.setenv("EVALLY_RUNS_DIR", str(write_run(tmp_path)))
    assert cli.main(["geval", "dev-qwen", "--rubric", "goes-beyond-policy", "--case", "b"]) == 1
    assert capsys.readouterr().out.strip() == "DeepEval isn't installed: uv sync --extra deepeval"
