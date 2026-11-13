import json

from evally import cli
from evally.evals_core.traces import format_conversation, run_path

CASE = {
    "id": "order-status", "status": "UNCHECKED",
    "turns": [{
        "user": "where is BB-1002?",
        "reply": "It has shipped.",
        "trace": [
            {"kind": "retrieve", "data": {"query": "where is BB-1002?", "docs": ["shipping.md", "returns.md"]}},
            {"kind": "model", "data": {"text": "", "tool_calls": ["lookup_order"], "stop_reason": "tool_use"}},
            {"kind": "tool", "data": {"name": "lookup_order", "arguments": {"order_id": "BB-1002"},
                                      "result": '{"status": "shipped"}', "is_error": False}},
            {"kind": "model", "data": {"text": "It has shipped.", "tool_calls": [], "stop_reason": "end_turn"}},
        ],
    }],
}


def test_format_shows_user_docs_tools_reply_in_order():
    out = format_conversation(CASE)
    lines = out.splitlines()
    assert lines[0].startswith("── order-status ") and lines[0].endswith(" UNCHECKED")
    order = [out.index(s) for s in ("customer> where is BB-1002?", "docs: shipping.md, returns.md",
                                    'tool: lookup_order {"order_id": "BB-1002"}', '→ {"status": "shipped"}',
                                    "assistant> It has shipped.")]
    assert order == sorted(order)


def _with_result(result, is_error=False):
    case = json.loads(json.dumps(CASE))
    case["turns"][0]["trace"][2]["data"].update(result=result, is_error=is_error)
    return format_conversation(case)


def test_tool_error_marked():
    assert "→ ERROR timeout talking to the north warehouse" in _with_result(
        "timeout talking to the north warehouse", is_error=True)


def test_long_result_cut_to_200_chars():
    line = next(l for l in _with_result("x" * 500).splitlines() if "→" in l)
    assert line.count("x") == 200 and line.endswith("…")


def test_run_path_accepts_name_file_or_path(tmp_path):
    runs = tmp_path / "runs"
    assert run_path("week02-traffic-m", runs) == runs / "week02-traffic-m.json"
    assert run_path("week02-traffic-m.json", runs) == runs / "week02-traffic-m.json"
    other = tmp_path / "elsewhere.json"
    other.write_text("{}")
    assert run_path(str(other), runs) == other


def _run_file(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    runs.mkdir()
    monkeypatch.setenv("EVALLY_RUNS_DIR", str(runs))
    (runs / "demo-m.json").write_text(json.dumps({"suite": "demo", "model": "m", "cases": [CASE], "totals": {}}))
    return runs


def test_traces_lists_cases(tmp_path, monkeypatch, capsys):
    _run_file(tmp_path, monkeypatch)
    assert cli.main(["traces", "demo-m"]) == 0
    out = capsys.readouterr().out
    assert "order-status" in out and "UNCHECKED" in out and "lookup_order" in out


def test_traces_case_prints_conversation(tmp_path, monkeypatch, capsys):
    _run_file(tmp_path, monkeypatch)
    assert cli.main(["traces", "demo-m", "--case", "order-status"]) == 0
    assert "customer> where is BB-1002?" in capsys.readouterr().out


def test_traces_missing_run_message(tmp_path, monkeypatch, capsys):
    runs = _run_file(tmp_path, monkeypatch)
    assert cli.main(["traces", "nope"]) == 1
    assert f"no run named nope in {runs}" in capsys.readouterr().out


def test_traces_unknown_case_message(tmp_path, monkeypatch, capsys):
    _run_file(tmp_path, monkeypatch)
    assert cli.main(["traces", "demo-m", "--case", "zzz"]) == 1
    assert "no case zzz in demo-m" in capsys.readouterr().out
