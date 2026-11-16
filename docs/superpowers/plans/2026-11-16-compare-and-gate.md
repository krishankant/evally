# evally compare and gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `evally compare` and `evally gate` on `main`.

**Architecture:** Pure functions in `evally/evals_core/compare.py` operating on saved run dicts; thin CLI commands in `evally/cli.py` using the existing `_load_run`.

**Tech Stack:** Python stdlib only (math, random); pytest.

**Spec:** `docs/superpowers/specs/2026-11-16-compare-and-gate-design.md`

## Global Constraints

- Offline, deterministic, stdlib only. ERROR/UNCHECKED count as not passing. Numbers must match pages 07/12 on `bramble-v2-dev-qwen3.5-4b` vs `bramble-v2-dev-llama3.2-3b`.

## Review Focus

1. Runs with different case sets → compare on the intersection, warn with counts; gate treats a baseline-passing case missing from current as a regression.
2. Zero flips → McNemar p = 1, no crash. 3. Empty run → message, exit 1 (both commands).
4. `--allow` naming a case that isn't a regression → printed as unused, not an error.
5. Floor without enough cases → Wilson lower bound used, never the point estimate.

---

### Task 1: compare.py functions (TDD)

**Files:** Create `evally/evals_core/compare.py`, `tests/test_compare.py`.
**Produces:** `outcomes(run) -> dict[str, bool]`; `wilson(k, n, z=1.959963984540054) -> tuple[float, float] | None`; `mcnemar(a: dict, b: dict) -> tuple[int, int, float]` (worse, better, p) over shared ids; `paired_bootstrap(a, b, B=10000, seed=0) -> tuple[float, float, float]` (diff, low, high); `compare_runs(a_run, b_run) -> dict`; `format_compare(name_a, name_b, result) -> str`; `gate(base_run, cur_run, floor=0.0, allow=()) -> dict` with keys `passed, regressions, allowed, unused_allow, low, rate`; `format_gate(result) -> str`.
- [ ] Tests: Wilson 10/16 = (0.386, 0.815) to 3 dp, n=0 None; McNemar on real-shaped qwen/llama vectors = (1, 4, 0.375), no flips p = 1; paired bootstrap diff 0.1875 and range crossing 0, deterministic; compare on mismatched ids reports `only_a/only_b`; gate: regression → not passed, allowed regression → passed with `allowed`, unused allow listed, ERROR in current counts as regression, floor uses Wilson lower bound.
- [ ] Watch fail → implement → pass → full suite → commit `feat: compare and gate functions`.

### Task 2: CLI commands (TDD)

**Files:** Modify `evally/cli.py`; Test `tests/test_compare_cli.py`.
- [ ] Tests (tmp runs dir with two small run JSONs): `compare` prints both rates and flips, exit 0; `gate` exits 1 with "GATE: FAIL" and the case id; `--allow` makes it exit 0; missing run → exit 1.
- [ ] Implement, pass, full suite; run both commands on the real runs and compare with pages 07/12 numbers. Commit `feat: evally compare and evally gate`.

### Task 3: Docs

- [ ] Pages 07 and 12 use the commands (real output pasted); README cheat sheet; strict build; commit `docs: compare and gate in pages 07, 12 and README`; fast-forward main; push.
