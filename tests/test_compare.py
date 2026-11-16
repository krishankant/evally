"""evally compare / gate: paired comparison of two saved runs, and a regression gate."""

import pytest

from evally.evals_core import compare as cmp

IDS = ["return-window", "free-shipping", "order-status", "other-customer-order", "price-match",
       "return-two-turns", "return-too-late", "short-answer", "t-send-back-six-weeks", "t-password-reset",
       "t-clockmaker-stock", "gen-fa79bb81", "gen-853dbcd7", "gen-14a2a76c", "adv-quotes-60-days",
       "adv-third-party-order"]
QWEN = [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1]     # real bramble-v2 dev results
LLAMA = [0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1]


def run(bits, ids=IDS, error=()):
    return {"suite": "bramble-v2-dev", "cases": [
        {"id": i, "status": "ERROR" if i in error else ("PASS" if b else "FAIL")} for i, b in zip(ids, bits)]}


def test_outcomes_counts_only_pass():
    r = run([1, 0, 1], ids=["a", "b", "c"], error=("c",))
    assert cmp.outcomes(r) == {"a": True, "b": False, "c": False}


def test_wilson_matches_scipy():
    low, high = cmp.wilson(10, 16)
    assert (round(low, 3), round(high, 3)) == (0.386, 0.815)
    assert cmp.wilson(0, 0) is None


def test_mcnemar_real_runs():
    assert cmp.mcnemar(cmp.outcomes(run(QWEN)), cmp.outcomes(run(LLAMA))) == (1, 4, pytest.approx(0.375))


def test_mcnemar_no_flips_is_one():
    assert cmp.mcnemar({"a": True}, {"a": True}) == (0, 0, 1.0)


def test_paired_bootstrap_deterministic_and_crosses_zero():
    a, b = cmp.outcomes(run(QWEN)), cmp.outcomes(run(LLAMA))
    d1, d2 = cmp.paired_bootstrap(a, b), cmp.paired_bootstrap(a, b)
    assert d1 == d2
    diff, low, high = d1
    assert diff == pytest.approx(3 / 16)
    assert low < 0 < high


def test_compare_runs_reports_flips_and_mismatch():
    res = cmp.compare_runs(run(QWEN), run(LLAMA[:15] + [1], ids=IDS[:15] + ["new-case"]))
    assert res["worse"] == ["return-window"]
    assert "short-answer" in res["better"]
    assert res["only_a"] == ["adv-third-party-order"] and res["only_b"] == ["new-case"]
    assert res["n"] == 15


def test_gate_fails_on_regression():
    res = cmp.gate(run(QWEN), run(LLAMA))
    assert not res["passed"] and res["regressions"] == ["return-window"]


def test_gate_allow_and_unused_allow():
    res = cmp.gate(run(QWEN), run(LLAMA), allow=["return-window", "price-match"])
    assert res["passed"] and res["allowed"] == ["return-window"] and res["unused_allow"] == ["price-match"]


def test_gate_error_and_missing_count_as_regression():
    cur = run(QWEN[:15], ids=IDS[:15], error=("free-shipping",))
    res = cmp.gate(run(QWEN), cur)
    assert res["regressions"] == ["adv-third-party-order", "free-shipping"]


def test_gate_floor_uses_wilson_lower_bound():
    same = run(QWEN)
    assert cmp.gate(same, same, floor=0.6)["passed"] is False      # 10/16: lower bound 0.386
    assert cmp.gate(same, same, floor=0.35)["passed"] is True


def test_empty_run_rejected():
    with pytest.raises(ValueError):
        cmp.compare_runs({"cases": []}, run(QWEN))
