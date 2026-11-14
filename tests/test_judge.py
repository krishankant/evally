from pathlib import Path

import pytest

from evally.graders.judge import (
    VERDICT_TOOL,
    conversation_for_grader,
    judge_case,
    parse_verdict,
    policy_reference,
)
from evally.graders.rubrics import Rubric, load_rubrics
from evally.llm.scripted import ScriptedModel, text_reply, tool_reply
from evally.types import ToolCall

ROOT = Path(__file__).resolve().parent.parent
RUBRIC = Rubric("goes-beyond-policy", "FAIL if the reply promises anything the policies don't allow.")


def case(reply="Your order BB-1001 shipped yesterday.", **extra):
    c = {
        "id": "adv-quotes-60-days",
        "status": "FAIL",
        "tags": ["topic:returns"],
        "checks": [{"name": "contains", "passed": False, "detail": "reply doesn't mention '30'"}],
        "replies": [reply],
        "turns": [{
            "user": "Where is my order BB-1001? I'm alice@example.com",
            "reply": reply,
            "trace": [
                {"kind": "retrieve", "data": {"docs": ["shipping.md"]}},
                {"kind": "tool", "data": {"name": "lookup_order",
                                          "arguments": {"order_id": "BB-1001", "email": "alice@example.com"},
                                          "result": "{\"status\": \"shipped\"}", "is_error": False}},
            ],
        }],
    }
    c.update(extra)
    return c


def verdict_call(**args):
    return tool_reply(ToolCall("1", "record_verdict", args))


def score_call(**args):
    return tool_reply(ToolCall("1", "record_score", args))


def test_rubric_names_are_categories(tmp_path):
    (tmp_path / "beyond.md").write_text("FAIL if ...")
    with pytest.raises(ValueError, match="beyond.md"):
        load_rubrics(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    (other / "goes-beyond-policy.md").write_text("  \n")
    with pytest.raises(ValueError, match="goes-beyond-policy.md"):
        load_rubrics(other)
    assert list(load_rubrics(ROOT / "evals/rubrics")) == [
        "goes-beyond-policy", "unsupported-claims", "uses-outdated-policy"]


def test_policy_reference_drops_superseded():
    ref = policy_reference()
    assert "## returns.md" in ref and "30 days" in ref
    assert "returns-2023.md" not in ref and "60 days" not in ref


def test_grader_input_hides_id_status_checks_and_tags():
    text = conversation_for_grader(case())
    assert "customer:" in text and "assistant:" in text and "lookup_order" in text
    for leak in ("adv-quotes-60-days", "FAIL", "contains", "topic:", "shipping.md"):
        assert leak not in text, leak


def test_judge_reads_tool_verdict():
    model = ScriptedModel([verdict_call(reason="promises a refund", verdict="fail")])
    v = judge_case(model, RUBRIC, case(), policy_reference())
    assert (v.case_id, v.rubric, v.verdict, v.reason) == (
        "adv-quotes-60-days", "goes-beyond-policy", "fail", "promises a refund")
    call = model.calls[0]
    assert call.tools == [VERDICT_TOOL]
    assert RUBRIC.text in call.system and "## returns.md" in call.system
    assert v.tokens == {"input": 10, "output": 5}


def test_judge_scale_maps_score():
    four = judge_case(ScriptedModel([score_call(reason="ok", score=4)]), RUBRIC, case(), "", scale="1-5")
    three = judge_case(ScriptedModel([score_call(reason="meh", score=3)]), RUBRIC, case(), "", scale="1-5")
    assert (four.verdict, four.score) == ("pass", 4)
    assert (three.verdict, three.score) == ("fail", 3)


@pytest.mark.parametrize("response,scale", [
    (text_reply("I think it's fine."), "binary"),
    (verdict_call(reason="hmm", verdict="maybe"), "binary"),
    (score_call(reason="x", score=7), "1-5"),
    (score_call(reason="x", score=0), "1-5"),
    (score_call(reason="x", score="4"), "1-5"),
    (text_reply(""), "binary"),
])
def test_malformed_grader_replies(response, scale):
    verdict, reason, score = parse_verdict(response, scale)
    assert verdict == "error" and score is None


def test_json_in_text_is_accepted():
    assert parse_verdict(text_reply('Sure. {"reason": "fine", "verdict": "pass"}'), "binary") == (
        "pass", "fine", None)


def test_error_reason_is_cut():
    verdict, reason, _ = parse_verdict(text_reply("x" * 500), "binary")
    assert verdict == "error" and len(reason) <= 200 + len("grader gave no verdict: ")
