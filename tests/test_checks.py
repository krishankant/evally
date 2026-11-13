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


# --- week 4: tool-argument checks ---------------------------------------------------------

def calls(*pairs):
    return Turn("ok", [TraceStep("tool", {"name": n, "arguments": a, "result": "", "is_error": False}) for n, a in pairs])


RETURN = calls(("lookup_order", {"order_id": "BB-1001", "email": "alice@example.com"}),
               ("start_return", {"order_id": "BB-1001", "email": "alice@example.com", "reason": "duplicate gift"}))


def test_tool_args_subset_match():
    assert run_check({"type": "tool_args", "value": {"tool": "start_return", "args": {"order_id": "BB-1001"}}}, RETURN).passed


def test_tool_args_wrong_value_shows_actual():
    r = run_check({"type": "tool_args", "value": {"tool": "start_return", "args": {"order_id": "BB-1002"}}}, RETURN)
    assert not r.passed and "BB-1001" in r.detail
    assert r.name.startswith("tool_args")


def test_args_shape_fullmatch():
    shape = {"type": "args_shape", "value": {"tool": "lookup_order", "args": {"order_id": r"BB-\d{4}"}}}
    assert run_check(shape, RETURN).passed
    r = run_check(shape, calls(("lookup_order", {"order_id": "BB-1001x"})))
    assert not r.passed and "order_id" in r.detail and "BB-1001x" in r.detail


def test_args_grounded_catches_invented_email():
    turn = calls(("lookup_order", {"order_id": "BB-1001", "email": "user@example.com"}))
    r = run_check({"type": "args_grounded", "value": {"tool": "lookup_order", "args": ["order_id", "email"]}},
                  turn, ["my book arrived with the cover torn"])
    assert not r.passed and "order_id" in r.detail


def test_args_grounded_passes_when_given():
    r = run_check({"type": "args_grounded", "value": {"tool": "start_return", "args": ["order_id", "email"]}},
                  RETURN, ["I want to return a book.", "Order bb-1001, email Alice@example.com"])
    assert r.passed


@pytest.mark.parametrize("ctype,value", [
    ("tool_args", {"tool": "start_return", "args": {"order_id": "BB-1001"}}),
    ("args_shape", {"tool": "start_return", "args": {"order_id": "BB-.*"}}),
])
def test_tool_checks_fail_when_tool_not_called(ctype, value):
    r = run_check({"type": ctype, "value": value}, calls(("lookup_order", {"order_id": "BB-1001"})), ["BB-1001"])
    assert not r.passed and r.detail == "start_return was not called"


@pytest.mark.parametrize("arg", [1001, None, {"a": 1}])
def test_non_string_args(arg):
    turn = calls(("lookup_order", {"order_id": arg}))
    assert not run_check({"type": "tool_args", "value": {"tool": "lookup_order", "args": {"order_id": "1001"}}}, turn).passed
    r = run_check({"type": "args_shape", "value": {"tool": "lookup_order", "args": {"order_id": r"\d+"}}}, turn)
    assert not r.passed and "order_id" in r.detail
    assert not run_check({"type": "args_grounded", "value": {"tool": "lookup_order", "args": ["order_id"]}},
                         turn, ["order 1001"]).passed or arg == 1001


@pytest.mark.parametrize("check", [
    {"type": "tool_args", "value": {"args": {"order_id": "BB-1"}}},
    {"type": "tool_args", "value": {"tool": "refund_money", "args": {}}},
    {"type": "tool_args", "value": {"tool": "lookup_order", "args": "BB-1001"}},
    {"type": "args_shape", "value": {"tool": "lookup_order", "args": {"order_id": "(bad"}}},
    {"type": "args_grounded", "value": {"tool": "lookup_order", "args": "order_id"}},
    {"type": "args_grounded", "value": "lookup_order"},
])
def test_tool_check_values_validated(tmp_path, check):
    with pytest.raises(ValueError, match=rf":2: {check['type']}: "):
        load_cases(suite_file(tmp_path, [check]))


def test_args_grounded_passes_when_tool_not_called():
    # grounded is a rule about calls that happen ("don't invent arguments"), not a demand to call;
    # pair it with tool_called when a call is required
    r = run_check({"type": "args_grounded", "value": {"tool": "start_return", "args": ["order_id"]}},
                  calls(("lookup_order", {"order_id": "BB-1001"})), ["BB-1001"])
    assert r.passed and r.detail == "start_return was not called"
