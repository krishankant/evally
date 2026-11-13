import json

import pytest

from evally import cli
from evally.app.assistant import FALLBACK_REPLY, Turn
from evally.evals_core.checks import run_check
from evally.graders.refusal import refusal_match


def test_plain_refusal():
    assert refusal_match("I'm sorry, but I can't help with that.") is not None


def test_answer_is_not_refusal():
    assert refusal_match("Express shipping is $12.99.") is None


def test_fallback_reply_is_refusal():
    assert refusal_match(FALLBACK_REPLY) == "couldn't finish"


def test_partial_refusal_counts():
    assert refusal_match("I can't share what's in that order, but I can help you track yours.") == "I can't"


def test_apology_without_refusal_not_flagged():
    assert refusal_match("Sorry for the wait! Your order shipped.") is None


@pytest.mark.parametrize("ctype,text,passed", [
    ("refuses", "I'm unable to share order details.", True),
    ("refuses", "It ships in 3-5 days.", False),
    ("not_refuses", "It ships in 3-5 days.", True),
    ("not_refuses", "I cannot do that.", False),
])
def test_refusal_checks(ctype, text, passed):
    r = run_check({"type": ctype, "value": True}, Turn(text, []))
    assert r.passed is passed and r.name.startswith(ctype)


def test_refusals_cli_lists_and_counts(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("EVALLY_RUNS_DIR", str(tmp_path))
    run = {"suite": "s", "model": "m", "totals": {}, "cases": [
        {"id": "a", "tags": [], "status": "PASS", "replies": ["I can't share that."], "turns": []},
        {"id": "b", "tags": [], "status": "PASS", "replies": ["It's $4.99."], "turns": []}]}
    (tmp_path / "r.json").write_text(json.dumps(run))
    assert cli.main(["refusals", "r"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].split() == ["a", "REFUSES", '"I', "can't\""]
    assert out[1].split() == ["b", "-"]
    assert out[-1] == "1 of 2 replies flagged"
