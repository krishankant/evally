import pytest

from evally.app.assistant import TraceStep, Turn
from evally.evals_core.cases import load_cases
from evally.evals_core.checks import run_check

TURN = Turn("Standard shipping is $4.99 and is FREE over $35.",
            [TraceStep("tool", {"name": "lookup_order", "arguments": {}, "result": "", "is_error": False})])


@pytest.mark.parametrize("check,passed", [
    ({"type": "contains", "value": "free"}, True),          # case-insensitive
    ({"type": "contains", "value": "12.99"}, False),
    ({"type": "not_contains", "value": "12.99"}, True),
    ({"type": "not_contains", "value": "$35"}, False),
    ({"type": "tool_called", "value": "lookup_order"}, True),
    ({"type": "tool_called", "value": "start_return"}, False),
    ({"type": "tool_not_called", "value": "start_return"}, True),
    ({"type": "tool_not_called", "value": "lookup_order"}, False),
    ({"type": "max_words", "value": 10}, True),
    ({"type": "max_words", "value": 5}, False),
])
def test_check(check, passed):
    r = run_check(check, TURN)
    assert r.passed is passed
    assert r.name.startswith(check["type"])


def test_unknown_check_type_rejected_at_load(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text('{"id": "x", "turns": ["hi"], "checks": [{"type": "sounds_nice", "value": 1}]}\n')
    with pytest.raises(ValueError, match="sounds_nice"):
        load_cases(p)


def test_load_skips_comments_and_blanks(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text('// a comment\n\n{"id": "x", "tags": ["t"], "turns": ["hi"], "checks": []}\n')
    [case] = load_cases(p)
    assert case.id == "x" and case.tags == ["t"]
