from evally.app.assistant import Assistant
from evally.app.retrieval import Retriever
from evally.app.store import Store
from evally.evals_core.cases import Case
from evally.evals_core.runner import format_table, load_run, run_suite, save_run
from evally.llm.cache import CachedModel
from evally.llm.scripted import ScriptedModel, text_reply, tool_reply
from evally.types import ToolCall

CASES = [
    Case("good", ["shipping"], ["how much is shipping"], [{"type": "contains", "value": "4.99"}]),
    Case("bad", ["shipping"], ["how much is express"], [{"type": "contains", "value": "12.99"}]),
]


def factory(model):
    return lambda: Assistant(model, Store.from_seed(), Retriever.from_dir())


def test_run_suite_counts():
    model = ScriptedModel([text_reply("It is $4.99."), text_reply("It is $10.")])
    result = run_suite("demo", CASES, factory(model), model_name="scripted")
    assert result.totals == {"cases": 2, "passed": 1, "errors": 0, "checks": 2, "checks_passed": 1, "unchecked": 0}
    assert [c.status for c in result.cases] == ["PASS", "FAIL"]
    table = format_table(result)
    assert "passed 1/2 cases, 1/2 checks" in table


def test_replay_miss_marks_case_error(tmp_path):
    model = CachedModel(None, tmp_path, "replay")
    result = run_suite("demo", CASES[:1], factory(model), model_name="x")
    assert result.cases[0].status == "ERROR"
    assert "--live" in result.cases[0].error


def test_save_run_deterministic_name(tmp_path):
    model = ScriptedModel([text_reply("It is $4.99.")])
    result = run_suite("demo", CASES[:1], factory(model), model_name="qwen3.5:4b")
    assert save_run(result, tmp_path).name == "demo-qwen3.5-4b.json"


def test_run_keeps_full_trace():
    call = ToolCall("c1", "lookup_order", {"order_id": "BB-1002", "email": "ben@example.com"})
    model = ScriptedModel([tool_reply(call), text_reply("It has shipped.")])
    case = Case("o", [], ["where is BB-1002, ben@example.com"], [])
    turns = run_suite("demo", [case], factory(model), "scripted").cases[0].turns
    assert [s["kind"] for s in turns[0]["trace"]] == ["retrieve", "model", "tool", "model"]
    tool = turns[0]["trace"][2]["data"]
    assert tool["arguments"] == {"order_id": "BB-1002", "email": "ben@example.com"}
    assert "shipped" in tool["result"]
    assert turns[0]["user"] == "where is BB-1002, ben@example.com"
    assert turns[0]["reply"] == "It has shipped."


def test_multi_turn_keeps_every_turn():
    model = ScriptedModel([text_reply("Which order?"), text_reply("Done.")])
    case = Case("m", [], ["I want a return", "BB-1001"], [])
    turns = run_suite("demo", [case], factory(model), "scripted").cases[0].turns
    assert [t["user"] for t in turns] == ["I want a return", "BB-1001"]
    assert [t["reply"] for t in turns] == ["Which order?", "Done."]


def test_no_checks_is_unchecked():
    model = ScriptedModel([text_reply("Hello.")])
    result = run_suite("demo", [Case("u", [], ["hi"], [])], factory(model), "scripted")
    assert result.cases[0].status == "UNCHECKED"
    assert result.totals["unchecked"] == 1 and result.totals["passed"] == 0
    table = format_table(result)
    assert "UNCHECKED" in table
    assert table.splitlines()[-1] == "passed 0/0 checked cases, 0/0 checks, 1 unchecked"


def test_week01_table_unchanged():
    model = ScriptedModel([text_reply("It is $4.99."), text_reply("It is $10.")])
    table = format_table(run_suite("demo", CASES, factory(model), "scripted"))
    assert table.splitlines()[-1] == "passed 1/2 cases, 1/2 checks"
    assert "  good  PASS" in table


def test_error_case_keeps_turns_so_far(tmp_path):
    inner = ScriptedModel([text_reply("Which order?")])
    rec = CachedModel(inner, tmp_path, "record")
    run_suite("demo", [Case("e", [], ["I want a return"], [])], factory(rec), "x")
    replay = CachedModel(None, tmp_path, "replay")
    case = Case("e", [], ["I want a return", "BB-1001"], [])
    r = run_suite("demo", [case], factory(replay), "x").cases[0]
    assert r.status == "ERROR"
    assert [t["reply"] for t in r.turns] == ["Which order?"]


def test_load_run_round_trip(tmp_path):
    model = ScriptedModel([text_reply("Hello.")])
    result = run_suite("demo", [Case("u", [], ["hi"], [])], factory(model), "scripted")
    data = load_run(save_run(result, tmp_path))
    assert data["cases"][0]["turns"][0]["reply"] == "Hello."
    assert data["totals"]["unchecked"] == 1
