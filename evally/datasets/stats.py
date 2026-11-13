"""Coverage of a dataset per dimension, and a run's pass rates per tag value."""

from __future__ import annotations

from evally.datasets.dimensions import DIMENSIONS, tag_value
from evally.evals_core.cases import Case

Coverage = dict[str, list[tuple[str, int, int]]]


def coverage(dev: list[Case], test: list[Case]) -> Coverage:
    cov: Coverage = {}
    for dim, values in DIMENSIONS.items():
        dv = [tag_value(c.tags, dim) for c in dev]
        tv = [tag_value(c.tags, dim) for c in test]
        cov[dim] = [(v, dv.count(v), tv.count(v)) for v in values]
    return cov


def format_coverage(name_version: str, cov: Coverage, n_dev: int, n_test: int) -> str:
    lines = [f"coverage of {name_version} (dev {n_dev} · test {n_test})"]
    for dim, rows in cov.items():
        shown = [row for row in rows if row[1] or row[2]]
        missing = [v for v, d, t in rows if not d and not t]
        w = max([len(dim)] + [len(v) for v, _, _ in shown]) + 2
        lines += ["", f"{dim:<{w + 2}}  dev  test"]
        for v, d, t in shown:
            mark = "  ← not in test" if not t else ""
            lines.append(f"  {v:<{w}}  {d:>3}  {t:>4}{mark}")
        if missing:
            lines.append(f"  missing: {', '.join(missing)}")
    return "\n".join(lines)


def format_by_tag(result, dim: str) -> str:
    counts: dict[str, list[int]] = {}
    for case in result.cases:
        if case.status == "UNCHECKED":
            continue
        value = tag_value(case.tags, dim) or "(untagged)"
        passed, checked = counts.setdefault(value, [0, 0])
        counts[value] = [passed + (case.status == "PASS"), checked + 1]
    rows = sorted(((v, p, n) for v, (p, n) in counts.items()),
                  key=lambda row: (row[0] == "(untagged)", row[1] / row[2], row[0]))
    w = max([len("value")] + [len(v) for v, _, _ in rows])
    lines = [f"by {dim}", f"  {'value':<{w}}  passed   rate"]
    lines += [f"  {v:<{w}}  {f'{p}/{n}':>6}  {round(100 * p / n):>4}%" for v, p, n in rows]
    return "\n".join(lines)
