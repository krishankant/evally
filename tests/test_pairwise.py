import copy
import json

import pytest

from evally import cli
from evally.graders.pairwise import PADDING, PREFER_TOOL, bias_test, pad_run, prefer
from evally.llm.scripted import ScriptedModel, text_reply, tool_reply
from evally.types import ToolCall


def case(cid, reply, status="PASS", turns=1):
    ts = [{"user": f"q{i} for {cid}", "reply": reply, "trace": []} for i in range(turns)]
    return {"id": cid, "status": status, "replies": [t["reply"] for t in ts], "turns": ts}


def run(suite="dev", model="qwen", cases=None):
    return {"suite": suite, "model": model, "cases": cases or [], "totals": {}}


def winners(*ws):
    m = ScriptedModel([tool_reply(ToolCall("1", "record_preference", {"reason": "r", "winner": w})) for w in ws])
    m.name = "qwen3.5:4b"
    return m


def test_pad_run_appends_exactly():
    original = run(cases=[case("a", "30 days."), case("b", "Hi.", turns=2)])
    before = copy.deepcopy(original)
    padded = pad_run(original)
    assert original == before
    assert padded["model"] == "qwen+padded"
    assert padded["cases"][0]["replies"][-1] == "30 days. " + PADDING
    assert padded["cases"][0]["turns"][-1]["reply"] == "30 days. " + PADDING
    assert padded["cases"][1]["turns"][0]["reply"] == "Hi."  # only the last reply is padded


def test_bias_refuses_different_suites():
    with pytest.raises(ValueError, match="runs came from different suites: dev, test"):
        bias_test(winners(), run("dev"), run("test"), "")


def test_bias_skips_multiturn_and_errors():
    a = run(cases=[case("one", "x"), case("two", "y", turns=2), case("err", "", status="ERROR")])
    b = run(cases=[case("one", "x2"), case("two", "y2", turns=2), case("err", "z")])
    pairs, s = bias_test(winners("A", "B"), a, b, "")
    assert (s["pairs"], s["skipped_multiturn"], s["skipped_errors"]) == (1, 1, 1)
    assert [p.case_id for p in pairs] == ["one"]


def test_order_swap_maps_back_to_run_labels():
    model = winners("A", "A")
    pairs, s = bias_test(model, run(cases=[case("one", "reply a")]), run(cases=[case("one", "reply b")]), "")
    assert (pairs[0].first_a, pairs[0].first_b) == ("a", "b")
    assert s["consistent"] == 0 and s["first_position_wins"] == 2
    first, second = (c.messages[0].text for c in model.calls)
    assert first.index("reply a") < first.index("reply b")
    assert second.index("reply b") < second.index("reply a")
    assert model.calls[0].tools == [PREFER_TOOL]


def test_identical_replies_tie_is_consistent():
    pairs, s = bias_test(winners("tie", "tie"), run(cases=[case("one", "same")]), run(cases=[case("one", "same")]), "")
    assert s["consistent"] == 1 and s["ties"] == 1 and s["first_position_wins"] == 0


def test_consistent_winner_counted_for_its_run():
    _, s = bias_test(winners("B", "A"), run(cases=[case("one", "a")]), run(cases=[case("one", "b")]), "")
    assert (s["consistent"], s["b_wins"], s["a_wins"], s["first_position_wins"]) == (1, 1, 0, 1)


def test_malformed_preference_is_error():
    m = ScriptedModel([text_reply("both are nice")])
    assert prefer(m, "ctx", "a", "b", "")[0] == "error"
    assert prefer(ScriptedModel([text_reply('{"reason": "shorter", "winner": "B"}')]), "c", "a", "b", "")[0] == "B"


def test_bias_cli_prints_summary(tmp_path, monkeypatch, capsys):
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "dev-qwen.json").write_text(json.dumps(run(cases=[case("one", "a")])))
    monkeypatch.setenv("EVALLY_RUNS_DIR", str(runs))
    monkeypatch.setattr(cli, "_grader_model", lambda args, cfg: winners("A", "A"))
    assert cli.main(["pad", "dev-qwen"]) == 0
    assert (runs / "dev-qwen-padded.json").exists()
    assert cli.main(["bias", "dev-qwen", "dev-qwen-padded"]) == 0
    out = capsys.readouterr().out
    assert "one" in out and "inconsistent" in out
    assert "consistent under swap 0/1" in out and "picked the reply shown first 2/2" in out
    assert "tokens 20 in / 10 out · $0.0000" in out


def test_bias_cli_different_suites(tmp_path, monkeypatch, capsys):
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "a.json").write_text(json.dumps(run("dev")))
    (runs / "b.json").write_text(json.dumps(run("test")))
    monkeypatch.setenv("EVALLY_RUNS_DIR", str(runs))
    assert cli.main(["bias", "a", "b"]) == 1
    assert "runs came from different suites: dev, test" in capsys.readouterr().out
