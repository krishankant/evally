"""Compare two saved runs on the same cases, and gate a change on regressions.

Concept pages 07 (statistics) and 12 (CI gates) explain the ideas. Only PASS counts as
passing: FAIL, ERROR (a replay miss) and UNCHECKED all count as not passing.
"""

from __future__ import annotations

import math
import random

Z95 = 1.959963984540054


def outcomes(run: dict) -> dict[str, bool]:
    """case id -> passed?"""
    return {c["id"]: c.get("status") == "PASS" for c in run.get("cases", [])}


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float] | None:
    """Wilson 95% range for k passes out of n."""
    if n <= 0:
        return None
    p, d = k / n, 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar(a: dict[str, bool], b: dict[str, bool]) -> tuple[int, int, float]:
    """(worse, better, p) on the shared cases: exact two-sided binomial test on the flips."""
    shared = a.keys() & b.keys()
    worse = sum(1 for i in shared if a[i] and not b[i])
    better = sum(1 for i in shared if b[i] and not a[i])
    m = worse + better
    if m == 0:
        return 0, 0, 1.0
    tail = sum(math.comb(m, i) for i in range(min(worse, better) + 1)) / 2 ** m
    return worse, better, min(1.0, 2 * tail)


def paired_bootstrap(a: dict[str, bool], b: dict[str, bool], B: int = 10_000,
                     seed: int = 0) -> tuple[float, float, float]:
    """(difference b - a in pass rate, low, high): resample shared cases, keeping each pair together."""
    ids = sorted(a.keys() & b.keys())
    d = [int(b[i]) - int(a[i]) for i in ids]
    n = len(d)
    rng = random.Random(seed)
    stats = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return sum(d) / n, _percentile(stats, 0.025), _percentile(stats, 0.975)


def _percentile(sorted_xs: list[float], q: float) -> float:
    i = (len(sorted_xs) - 1) * q
    lo, hi = math.floor(i), math.ceil(i)
    return sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (i - lo)


def compare_runs(run_a: dict, run_b: dict) -> dict:
    a, b = outcomes(run_a), outcomes(run_b)
    if not a or not b:
        raise ValueError("a run has no cases")
    shared = sorted(a.keys() & b.keys())
    if not shared:
        raise ValueError("the runs have no cases in common")
    sa, sb = {i: a[i] for i in shared}, {i: b[i] for i in shared}
    _, _, p = mcnemar(sa, sb)
    diff, low, high = paired_bootstrap(sa, sb)
    return {
        "n": len(shared), "pass_a": sum(sa.values()), "pass_b": sum(sb.values()),
        "range_a": wilson(sum(sa.values()), len(shared)), "range_b": wilson(sum(sb.values()), len(shared)),
        "better": [i for i in shared if sb[i] and not sa[i]], "worse": [i for i in shared if sa[i] and not sb[i]],
        "p": p, "diff": diff, "diff_range": (low, high),
        "only_a": sorted(a.keys() - b.keys()), "only_b": sorted(b.keys() - a.keys()),
    }


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def format_compare(name_a: str, name_b: str, r: dict) -> str:
    n = r["n"]
    lines = [f"A = {name_a}", f"B = {name_b}", f"shared cases: {n}", ""]
    for label, k, rng in (("A", r["pass_a"], r["range_a"]), ("B", r["pass_b"], r["range_b"])):
        lines.append(f"  {label}  {k}/{n} = {_pct(k / n)}   Wilson 95%: {_pct(rng[0])} - {_pct(rng[1])}")
    lines += ["", f"  better in B ({len(r['better'])}): {', '.join(r['better']) or 'none'}",
              f"  worse in B ({len(r['worse'])}): {', '.join(r['worse']) or 'none'}", "",
              f"difference B - A: {'+' if r['diff'] >= 0 else ''}{_pct(r['diff'])}   "
              f"paired bootstrap 95%: {_pct(r['diff_range'][0])} to {_pct(r['diff_range'][1])}",
              f"McNemar exact test on the {len(r['better']) + len(r['worse'])} flipped cases: p = {r['p']:.3f}"]
    low, high = r["diff_range"]
    lines.append("reading: the range for the difference includes 0: not evidence of a difference"
                 if low <= 0 <= high else "reading: the range for the difference excludes 0")
    for label, ids in (("only in A", r["only_a"]), ("only in B", r["only_b"])):
        if ids:
            lines.append(f"warning: {len(ids)} case(s) {label}, not compared: {', '.join(ids)}")
    return "\n".join(lines)


def gate(baseline: dict, current: dict, floor: float = 0.0, allow=()) -> dict:
    base, cur = outcomes(baseline), outcomes(current)
    if not base or not cur:
        raise ValueError("a run has no cases")
    allow = list(dict.fromkeys(allow))
    lost = sorted(i for i, ok in base.items() if ok and not cur.get(i, False))
    regressions = [i for i in lost if i not in allow]
    k, n = sum(cur.values()), len(cur)
    low = wilson(k, n)[0]  # type: ignore[index]  # n > 0: empty runs rejected above
    return {
        "passed": not regressions and low >= floor,
        "regressions": regressions, "allowed": [i for i in lost if i in allow],
        "unused_allow": [i for i in allow if i not in lost],
        "fixed": sorted(i for i, ok in cur.items() if ok and not base.get(i, False)),
        "base_pass": sum(base.values()), "base_n": len(base), "pass": k, "n": n,
        "low": low, "floor": floor, "missing": sorted(base.keys() - cur.keys()),
    }


def format_gate(r: dict) -> str:
    lines = [f"pass rate {r['base_pass']}/{r['base_n']} -> {r['pass']}/{r['n']}"
             f"   (Wilson lower bound {_pct(r['low'])}, floor {_pct(r['floor'])})",
             f"fixed: {', '.join(r['fixed']) or 'none'}",
             f"regressions: {', '.join(r['regressions']) or 'none'}"]
    if r["missing"]:
        lines.append(f"missing from the current run: {', '.join(r['missing'])}")
    if r["allowed"]:
        lines.append(f"allowed regressions (override): {', '.join(r['allowed'])}")
    if r["unused_allow"]:
        lines.append(f"--allow not needed for: {', '.join(r['unused_allow'])}")
    if r["low"] < r["floor"]:
        lines.append(f"pass rate lower bound {_pct(r['low'])} is below the floor {_pct(r['floor'])}")
    lines.append("GATE: PASS" if r["passed"] else "GATE: FAIL")
    return "\n".join(lines)
