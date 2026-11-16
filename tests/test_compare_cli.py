"""The evally compare and evally gate commands."""

import json

from evally import cli


def write_run(d, name, statuses):
    d.mkdir(exist_ok=True)
    cases = [{"id": i, "status": s} for i, s in statuses.items()]
    (d / f"{name}.json").write_text(json.dumps({"suite": "s", "model": "m", "cases": cases}))


def setup(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    monkeypatch.setenv("EVALLY_RUNS_DIR", str(runs))
    write_run(runs, "base", {"a": "PASS", "b": "PASS", "c": "FAIL", "d": "FAIL"})
    write_run(runs, "new", {"a": "FAIL", "b": "PASS", "c": "PASS", "d": "PASS"})


def test_compare_prints_rates_and_flips(tmp_path, monkeypatch, capsys):
    setup(tmp_path, monkeypatch)
    assert cli.main(["compare", "base", "new"]) == 0
    out = capsys.readouterr().out
    assert "2/4" in out and "3/4" in out
    assert "worse in B (1): a" in out and "better in B (2): c, d" in out
    assert "McNemar" in out


def test_gate_fails_on_regression(tmp_path, monkeypatch, capsys):
    setup(tmp_path, monkeypatch)
    assert cli.main(["gate", "base", "new"]) == 1
    out = capsys.readouterr().out
    assert "regressions: a" in out and "GATE: FAIL" in out


def test_gate_allow_passes(tmp_path, monkeypatch, capsys):
    setup(tmp_path, monkeypatch)
    assert cli.main(["gate", "base", "new", "--allow", "a"]) == 0
    out = capsys.readouterr().out
    assert "allowed regressions (override): a" in out and "GATE: PASS" in out


def test_gate_floor(tmp_path, monkeypatch, capsys):
    setup(tmp_path, monkeypatch)
    assert cli.main(["gate", "base", "base", "--floor", "0.9"]) == 1
    assert "below the floor" in capsys.readouterr().out


def test_missing_run(tmp_path, monkeypatch, capsys):
    setup(tmp_path, monkeypatch)
    assert cli.main(["compare", "base", "nope"]) == 1
    assert cli.main(["gate", "nope", "base"]) == 1
    assert "no run named nope" in capsys.readouterr().out


def test_empty_run(tmp_path, monkeypatch, capsys):
    setup(tmp_path, monkeypatch)
    write_run(tmp_path / "runs", "empty", {})
    assert cli.main(["gate", "base", "empty"]) == 1
    assert "no cases" in capsys.readouterr().out
