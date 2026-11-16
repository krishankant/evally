# evally compare and evally gate: design (short)

Date: 2026-11-16 · Status: approved by the author

**Why.** Weeks 6-15 are concept pages with no app code, so learners can't run week 7's paired comparison or week 12's gate on Bramble. These two commands are the cheapest high-value code: they turn pages 07 and 12 into commands.

**Goals.** `evally compare <run-a> <run-b>` reports (always exits 0): per-run pass rate with a Wilson 95% range; flipped cases by name (better, worse); McNemar's exact test on the flips; a seeded paired-bootstrap 95% range for the difference; a warning when the runs cover different cases (compared on the shared ones). `evally gate <baseline> <current> [--floor F] [--allow CASE ...]` decides: exit 1 if a baseline-passing case no longer passes (ERROR counts as failing) and isn't allowed, or the Wilson lower bound of the current pass rate is below `--floor`; exit 0 otherwise; allowed regressions are printed.

**Non-goals.** No live model calls, no changes to week branches, no CI workflow in the repo (page 12 shows one).

**Approaches.** (1) Commands in `evally/evals_core/compare.py` + CLI wiring — chosen: matches the codebase, testable offline. (2) Standalone scripts like page 12's — rejected: not discoverable, untested. (3) Fold into `evally run` flags — rejected: mixes running with judging.

**Constraints.** Offline tests, deterministic output (fixed bootstrap seed), numbers match pages 07/12 on the real runs (Wilson 0.386-0.815 for 10/16; McNemar p 0.375; paired range about -6 to +44 points; gate FAIL on return-window).

**Docs.** Pages 07 and 12 use the commands instead of the hand-written script; README cheat sheet rows.
