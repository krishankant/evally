from evally.app.assistant import Assistant
from evally.app.retrieval import Retriever
from evally.app.store import Store
from evally.evals_core.cases import Case
from evally.evals_core.runner import format_table, run_suite, save_run
from evally.llm.cache import CachedModel
from evally.llm.scripted import ScriptedModel, text_reply

CASES = [
    Case("good", ["shipping"], ["how much is shipping"], [{"type": "contains", "value": "4.99"}]),
    Case("bad", ["shipping"], ["how much is express"], [{"type": "contains", "value": "12.99"}]),
]


def factory(model):
    return lambda: Assistant(model, Store.from_seed(), Retriever.from_dir())


def test_run_suite_counts():
    model = ScriptedModel([text_reply("It is $4.99."), text_reply("It is $10.")])
    result = run_suite("demo", CASES, factory(model), model_name="scripted")
    assert result.totals == {"cases": 2, "passed": 1, "errors": 0, "checks": 2, "checks_passed": 1}
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
