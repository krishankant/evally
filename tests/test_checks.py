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


# --- week 4: regex, and check values validated at load ---------------------------------

def reply(text):
    return Turn(text, [])


def suite_file(tmp_path, checks):
    import json
    p = tmp_path / "s.jsonl"
    p.write_text("// header\n" + json.dumps({"id": "c", "turns": ["hi"], "checks": checks}) + "\n")
    return p


def test_regex_search_not_fullmatch():
    assert run_check({"type": "regex", "value": r"\b30 days\b"}, reply("You have 30 days to return it.")).passed


def test_regex_ignores_case():
    assert run_check({"type": "regex", "value": "express"}, reply("EXPRESS is $12.99")).passed


def test_not_regex_quotes_the_match():
    r = run_check({"type": "not_regex", "value": r"\b60[- ]days?\b"}, reply("Returns are fine within 60 days here."))
    assert not r.passed and "'60 days'" in r.detail
    assert run_check({"type": "not_regex", "value": r"\b60[- ]days?\b"}, reply("That book is $60.")).passed


def test_bad_regex_rejected_at_load(tmp_path):
    p = suite_file(tmp_path, [{"type": "regex", "value": "(unclosed"}])
    with pytest.raises(ValueError, match=rf"{p}:2: regex: "):
        load_cases(p)


@pytest.mark.parametrize("check", [
    {"type": "max_words", "value": "sixty"},
    {"type": "contains", "value": 5},
    {"type": "contains", "value": ""},
    {"type": "tool_called", "value": "refund_money"},
    {"type": "not_regex"},
])
def test_bad_check_values_rejected_at_load(tmp_path, check):
    with pytest.raises(ValueError, match=rf":2: {check['type']}: "):
        load_cases(suite_file(tmp_path, [check]))


def test_week01_and_bramble_v1_still_load():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for name in ("week01", "bramble-v1-dev", "bramble-v1-test"):
        assert load_cases(root / "evals/suites" / f"{name}.jsonl")
