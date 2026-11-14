import json

import pytest

from evally import cli, config
from evally.llm.prices import cost
from evally.llm.scripted import ScriptedModel, tool_reply
from evally.types import ToolCall


def turn(user, reply):
    return {"user": user, "reply": reply, "trace": []}


def write_run(tmp_path, errored=False):
    cases = [
        {"id": "a", "status": "PASS", "replies": ["30 days."], "turns": [turn("How long?", "30 days.")]},
        {"id": "b", "status": "FAIL", "replies": ["Sure, 90 days!"], "turns": [turn("Longer?", "Sure, 90 days!")]},
    ]
    if errored:
        cases[1] = {"id": "b", "status": "ERROR", "replies": [], "turns": [], "error": "no recording"}
    p = tmp_path / "runs" / "dev-qwen.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"suite": "dev", "model": "qwen", "cases": cases, "totals": {}}))
    return p


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("EVALLY_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("EVALLY_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("EVALLY_GRADES_DIR", str(tmp_path / "grades"))
    monkeypatch.delenv("EVALLY_GRADER_PROVIDER", raising=False)
    monkeypatch.delenv("EVALLY_GRADER_MODEL", raising=False)
    return tmp_path


def scripted(*verdicts):
    model = ScriptedModel([tool_reply(ToolCall("1", "record_verdict", {"reason": r, "verdict": v}))
                           for v, r in verdicts])
    model.name = "qwen3.5:4b"
    return model


def test_grade_prints_table_and_saves(env, monkeypatch, capsys):
    run = write_run(env)
    model = scripted(("pass", "says 30 days"), ("fail", "promises 90 days"))
    monkeypatch.setattr(cli, "_grader_model", lambda args, cfg: model)
    assert cli.main(["grade", str(run), "--rubric", "goes-beyond-policy"]) == 0
    out = capsys.readouterr().out
    assert "goes-beyond-policy  fails 1/2" in out
    assert "tokens 20 in / 10 out · $0.0000" in out and "saved" in out
    saved = json.loads((env / "grades" / "dev-qwen__qwen3.5-4b__binary.json").read_text())
    assert saved["run"] == "dev-qwen" and saved["grader"] == "qwen3.5:4b" and saved["scale"] == "binary"
    assert [v["verdict"] for v in saved["verdicts"]] == ["pass", "fail"]


def test_errors_counted_apart(env, monkeypatch, capsys):
    run = write_run(env, errored=True)
    monkeypatch.setattr(cli, "_grader_model", lambda args, cfg: scripted(("pass", "ok")))
    assert cli.main(["grade", str(run), "--rubric", "goes-beyond-policy"]) == 0
    assert "goes-beyond-policy  fails 0/1, 1 errors" in capsys.readouterr().out


def test_grade_case_grades_one_and_saves_nothing(env, monkeypatch, capsys):
    run = write_run(env)
    model = scripted(("fail", "promises 90 days"))
    monkeypatch.setattr(cli, "_grader_model", lambda args, cfg: model)
    assert cli.main(["grade", str(run), "--rubric", "goes-beyond-policy", "--case", "b"]) == 0
    out = capsys.readouterr().out
    assert "goes-beyond-policy  FAIL  promises 90 days" in out
    assert len(model.calls) == 1 and "Sure, 90 days!" in model.calls[0].messages[0].text
    assert not (env / "grades").exists()  # one case never overwrites a whole run's grades


def test_grade_unknown_case(env, capsys):
    run = write_run(env)
    assert cli.main(["grade", str(run), "--case", "zzz"]) == 1
    assert "no case zzz" in capsys.readouterr().out


def test_unknown_rubric_flag(env, capsys):
    run = write_run(env)
    assert cli.main(["grade", str(run), "--rubric", "beyond"]) == 1
    out = capsys.readouterr().out
    assert "beyond" in out
    for name in ("goes-beyond-policy", "unsupported-claims", "uses-outdated-policy"):
        assert name in out


def test_grade_replay_miss_writes_nothing(env, capsys):
    run = write_run(env)
    grades = env / "grades" / "dev-qwen__qwen3.5-4b__binary.json"
    grades.parent.mkdir(parents=True)
    grades.write_text("earlier")
    assert cli.main(["grade", str(run)]) == 1
    assert "--live" in capsys.readouterr().out
    assert grades.read_text() == "earlier"


def test_missing_key_message(env, monkeypatch, capsys):
    run = write_run(env)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    assert cli.main(["grade", str(run), "--live", "--grader-provider", "anthropic",
                     "--grader-model", "claude-haiku-5-5"]) == 1
    assert "ANTHROPIC_API_KEY isn't set: add it to .env" in capsys.readouterr().out


def test_blank_grader_env_means_default(monkeypatch):
    monkeypatch.setenv("EVALLY_GRADER_PROVIDER", "")
    monkeypatch.setenv("EVALLY_GRADER_MODEL", "")
    cfg = config.load()
    assert (cfg.grader_provider, cfg.grader_model) == ("ollama", "qwen3.5:4b")


def test_cost_known_and_unknown():
    assert cost("qwen3.5:4b", 1000, 100) == 0.0
    assert cost("some-hosted-model", 1000, 100) is None
