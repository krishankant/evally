# Week 4: Code-based graders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the code checks a support bot needs beyond `contains` (regex, tool arguments exact and by shape, arguments grounded in the conversation, refusal detection), use them to rebuild the dataset as `bramble-v2` with better checks on the same cases, report pass rates per check type, then do the same checks in DeepEval and compare.

**Architecture:** New check types join the `CHECKS` registry in `evally/evals_core/checks.py`; every check's `value` is validated in `load_cases` (one validator per type), so bad regexes or malformed tool checks fail at load with file:line. `run_check` gains the case's customer messages so a check can ask whether a tool argument came from the conversation. The only JSON this app produces is its tool-call arguments, so the spec's "JSON shape" check is `args_shape` over them; length limits already exist as `max_words`. Refusal detection is one phrase list in `evally/graders/refusal.py`. `bramble-v2` changes checks only, so its split is pinned from v1 and every reply replays from the cache (no model calls). DeepEval is an optional extra; `evally/graders/deepeval_side.py` turns a recorded case into DeepEval test cases and prints both verdicts side by side.

**Tech Stack:** Python 3.11+, uv, pytest, stdlib `re`; DeepEval 4.3.2 (optional extra `deepeval`, Apache-2.0).

**Spec:** `docs/superpowers/specs/2026-11-12-evally-course-design.md` (section 7 row 4; sections 3, 6, 9, 9a)

## Global Constraints

- Python >=3.11, `uv`, pytest; `uv run pytest` passes offline with no API keys, with or without the `deepeval` extra (DeepEval tests skip when it isn't installed).
- "Build it by hand first, then use the library": tasks 1-5 are plain Python; DeepEval comes last and the lesson compares the two ("same result? What does the library add? What does it hide?").
- "Every library is checked against its current release at build time, pinned in `uv.lock`, and its version named in the lesson." DeepEval pinned `==4.3.2` (released 2026-10-27; 4.3.4 is current, 4.3.2 chosen for two weeks' age). Its API below was checked by running it.
- Budget: no new model calls are expected this week (v2 has the same cases and turns). Library demos run on one or two cases.
- Headline numbers are test-set numbers; checks are written and tuned looking at **dev** traces only. The test traces are read only after v2's checks are fixed (lesson says so).
- Lesson output blocks copied from real runs (`...` marks shortening); every command re-run and matched.
- Branch `dev/week-04` from `main`; at the end fast-forward `main`, cut `week-04` branch + tag at a verified SHA. No push.

## Review Focus

1. **A bad check value in a case file** (`regex` that doesn't compile, `tool_args` with no `"tool"` or a tool the app doesn't have, `args` that isn't an object, `max_words` that isn't a number) → `load_cases` raises `file:line: <check type>: <what's wrong>`; every reader (run, build, stats, deepeval) gets it because they load through `load_cases`. (Task 1 `test_bad_regex_rejected_at_load`, `test_bad_check_values_rejected_at_load`; Task 2 `test_tool_check_values_validated`; Task 5 build is checked by `uv run evally dataset build` in Step 3.)
2. **Tool arguments that aren't strings** (a number, null, nested object) → `tool_args` compares JSON values for equality and `args_shape` fails that argument with a detail naming it, never a crash. (Task 2 `test_non_string_args`.)
3. **A check on a tool that was never called** → `tool_args`, `args_shape` and `args_grounded` all FAIL with detail `<tool> was not called`, never pass vacuously. (Task 2 `test_tool_checks_fail_when_tool_not_called`.)
4. **Refusal detection on the fallback reply and on partial refusals** ("I can't share order details, but I can tell you…") → the fallback reply counts as a refusal; a partial refusal counts as a refusal and the lesson shows it as the detector's known blind spot. (Task 3 `test_fallback_reply_is_refusal`, `test_partial_refusal_counts`.)
5. **DeepEval not installed, or no OpenAI key** → `evally deepeval` prints `DeepEval isn't installed: uv sync --extra deepeval` and exits 1; with no key it runs anyway, setting a placeholder key and `DEEPEVAL_TELEMETRY_OPT_OUT=1` only for the call and restoring the environment after. (Task 6 `test_deepeval_missing_message`, `test_env_restored_after_compare`.)

---

### Task 1: Regex checks, and every check value validated at load

**Files:**
- Modify: `evally/evals_core/checks.py`, `evally/evals_core/cases.py`
- Test: `tests/test_checks.py`, `tests/test_dimensions.py`

**Interfaces:**
- Produces: check types `regex` and `not_regex` (`re.search`, case-insensitive; detail on fail names the pattern; on `not_regex` fail, quotes the matched text). `VALIDATORS: dict[str, Callable[[object], str | None]]` in `checks.py` (error string or None), one per check type; `load_cases` calls it for every check and raises `ValueError(f"{path}:{n}: {type}: {error}")`. `run_check(check: dict, turn: Turn, customer: list[str]) -> CheckResult`: every check function now takes `(turn, value, customer)`; existing checks ignore `customer`. Update the runner's call site.

- [ ] **Step 1:** `git checkout main && git checkout -b dev/week-04`; commit this plan (`docs: week 4 plan (code-based graders)`).
- [ ] **Step 2: failing tests:** `test_regex_search_not_fullmatch` (`r"\b30 days\b"` passes on `"You have 30 days to return it."`); `test_regex_ignores_case`; `test_not_regex_quotes_the_match` (`r"\b60[- ]days?\b"` on `"...within 60 days..."` → fail, detail contains `'60 days'`); `test_bad_regex_rejected_at_load` (`"value": "(unclosed"` → `file:2: regex: ...`); `test_bad_check_values_rejected_at_load` (`max_words` `"sixty"`, `contains` `5`, `tool_called` `"refund_money"` (unknown tool) each rejected); `test_week01_and_bramble_v1_still_load`.
- [ ] **Step 3:** FAIL. **Step 4:** implement. **Step 5:** full suite PASS; commit `feat: regex checks; check values validated at load`.

### Task 2: Tool-argument checks

**Files:**
- Modify: `evally/evals_core/checks.py`
- Test: `tests/test_checks.py`

**Interfaces:**
- Consumes: Task 1's `run_check(check, turn, customer)`, `VALIDATORS`; the trace's `{"kind": "tool", "data": {"name", "arguments", ...}}` steps.
- Produces three check types, each with `value = {"tool": NAME, ...}` and NAME one of the app's `TOOLS`:
  - `tool_args`: `{"tool": T, "args": {k: v}}`. Passes when **some** call to T has every listed argument equal to `v` (JSON equality). Detail on fail lists the calls' actual arguments.
  - `args_shape`: `{"tool": T, "args": {k: pattern}}`. Passes when **every** call to T has every listed argument as a string fully matching its pattern (`re.fullmatch`). Detail names the first bad argument and value.
  - `args_grounded`: `{"tool": T, "args": [k, ...]}`. Passes when, in every call to T, each listed argument's value appears (case-insensitive substring) in one of the customer's messages. Catches invented order ids and emails.
  - All three fail with `<T> was not called` when T has no call (focus 3).

- [ ] **Step 1: failing tests:** `test_tool_args_subset_match` (start_return with `order_id` BB-1001 + extra `reason` passes); `test_tool_args_wrong_value_shows_actual`; `test_args_shape_fullmatch` (`^BB-\d{4}$` passes `BB-1001`, fails `BB-1001x`); `test_args_grounded_catches_invented_email` (customer said "my book arrived torn"; call has `user@example.com` → fail naming `email`); `test_args_grounded_passes_when_given` (customer turn 2 holds the order id and email); `test_tool_checks_fail_when_tool_not_called`; `test_non_string_args` (`order_id: 1001`, `None`, `{"a": 1}`: no crash, shape fails naming the arg); `test_tool_check_values_validated` (missing `tool`, unknown tool, `args` a string, `args_grounded` args not a list → load errors).
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS. **Step 5:** commit `feat: tool-argument checks (exact, shape, grounded)`.

### Task 3: Refusal detection

**Files:**
- Create: `evally/graders/__init__.py`, `evally/graders/refusal.py`
- Modify: `evally/evals_core/checks.py`, `evally/cli.py`
- Test: `tests/test_refusal.py`

**Interfaces:**
- Produces: `REFUSAL_PATTERNS: tuple[str, ...]` (regexes, case-insensitive: `\bI (?:can(?:no|')t|am unable to|'m unable to|'m not able to|am not able to)\b`, `\bI(?: am|'m) (?:sorry|afraid),? (?:but )?I\b`, `\b(?:not able|unable) to (?:help|share|provide|do)\b`, `\bcouldn't finish\b`); `refusal_match(text: str) -> str | None` (the first matched phrase, or None); check types `refuses` / `not_refuses` (value `true`; validator requires `true`). CLI `evally refusals <run>`: one line per case, `id  REFUSES  "<matched phrase>"` or `id  -`, then `N of M replies flagged`.

- [ ] **Step 1: failing tests:** `test_plain_refusal`; `test_answer_is_not_refusal` (`"Express shipping is $12.99."`); `test_fallback_reply_is_refusal` (`FALLBACK_REPLY`); `test_partial_refusal_counts` (`"I can't share what's in that order, but I can help you track yours."` → matched `"I can't"`); `test_apology_without_refusal_not_flagged` (`"Sorry for the wait! Your order shipped."`); `test_refusals_cli_lists_and_counts` (temp run JSON, two cases).
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS. **Step 5:** commit `feat: refusal detection (refuses / not_refuses, evally refusals)`.

### Task 4: Pass rates per check type

**Files:**
- Modify: `evally/datasets/stats.py`, `evally/cli.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- Consumes: `RunResult` (`CaseResult.checks: list[CheckResult]`, `CheckResult.name` starts with the check type).
- Produces: `format_by_check(result) -> str`: header `by check type`, then per type `passed/total` checks and `%`, plus a column `sole fail` = cases where this type is the only failing check (the cases this check alone decides). Ordered most failing first. `evally run --by check` prints it; `--by` accepts `check` plus the four dimensions; the unknown-dimension message lists `check` too.

- [ ] **Step 1: failing tests:** `test_by_check_counts_and_order`; `test_by_check_sole_fail_column`; `test_run_by_check_accepted` and updated `test_run_by_unknown_dimension_message` (`(known: topic, difficulty, category, source, check)`).
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS. **Step 5:** commit `feat: run --by check (pass rates per check type)`.

### Task 5: `bramble-v2`: same cases, better checks

**Files:**
- Modify: `evals/datasets/bramble/*.jsonl`, `evals/datasets/bramble.json` (version 2)
- Create (built): `evals/suites/bramble-v2-{dev,test}.jsonl`, `evals/datasets/bramble-v2.lock.json`, `evals/runs/bramble-v2-{dev,test}-qwen3.5-4b.json`

- [ ] **Step 1: rewrite checks, reading dev traces only** (`evally traces bramble-v1-dev-qwen3.5-4b --case ...`). Required changes (week 3 deferred minors plus new types):
  - `gen-14a2a76c`: `not_contains "premium tier"` → `not_regex` for a claimed premium tier (`\bpremium (membership )?tier (includes|offers|gives)`), keep `contains "10%"`.
  - `gen-853dbcd7`: add `not_regex "\bship(s|ping)? to australia (is|costs|takes)"`; comment states what it still misses.
  - `adv-quotes-60-days`: drop `tool_not_called start_return` (the tool itself refuses late returns), keep `not_contains "R-BB-1008"` and `contains "30"`.
  - `adv-gift-card-as-book`: comment notes BB-1010 holds a book, not a gift card.
  - `gen-3649b7b3` (a test case whose trace week 3's lesson already quoted; the lesson says so): `tool_called escalate_to_human` → `regex "order (id|number)|email"` (asks for the order details) plus `tool_not_called start_return`. The check is changed because it was wrong, not to raise the score; it would also pass a hand-off reply that asks for the order number.
  - Add `tool_args` to `order-status` (lookup_order BB-1002) and `return-two-turns` (start_return BB-1001); `args_grounded` on `lookup_order` [order_id, email] to `gen-fa79bb81` and `other-customer-order`; `not_refuses` to `express-price` and `free-shipping`; `return-window`'s `not_contains "60"` → `not_regex "\b60[- ]days?\b"` (a "$60" price no longer fails it).
- [ ] **Step 2:** bump `"version": 2`; `uv run evally dataset build` → prints `bramble-v2: 16 dev, 10 test` and the lock has `"pinned_from": 1` and the same dev/test ids as v1.
- [ ] **Step 3: measurement check (obs 0033): can the new checks move a verdict?** `uv run evally run --suite bramble-v2-dev --by check` and `bramble-v2-test`. Expected: no `ReplayMiss` (if any case errors, stop: v2 changed a turn by mistake). At least one verdict differs from v1 for a reason the lesson can name (expected: `gen-fa79bb81` now fails on invented arguments; `gen-3649b7b3` now passes). If no verdict moved, the new checks measure nothing new; revisit before recording.
- [ ] **Step 4:** a before/after table v1 vs v2 (dev and test, cases and checks) for the lesson, from the two runs' totals lines.
- [ ] **Step 5:** commit `evals: bramble v2 (same cases, code-grader checks)`.

### Task 6: The same checks in DeepEval

**Files:**
- Modify: `pyproject.toml` (`[project.optional-dependencies] deepeval = ["deepeval==4.3.2"]`), `uv.lock`, `.gitignore` (`.deepeval/`), `evally/cli.py`
- Create: `evally/graders/deepeval_side.py`
- Test: `tests/test_deepeval_side.py` (`pytest.importorskip("deepeval")` for the library tests; the missing-library message test runs always)

**Interfaces:**
- Consumes: a run JSON case (`turns[].trace`), its `Case` from the suite (via `load_cases`), Task 1-2 checks.
- Produces: `compare(case: Case, recorded: dict) -> list[tuple[str, str, str]]` (check, evally verdict, DeepEval verdict + score), covering `regex` → `PatternMatchMetric(pattern, ignore_case=True)`, `tool_args` → `ToolCorrectnessMetric(threshold=1.0, evaluation_params=[ToolCallParams.INPUT_PARAMETERS], include_reason=False, async_mode=False)` with `expected_tools` from the check, plus the same tool check at DeepEval's **default** threshold (0.5) to show what it lets through; other check types print `no DeepEval equivalent`. A context manager `_deepeval_env()` sets `OPENAI_API_KEY` (placeholder, only if unset) and `DEEPEVAL_TELEMETRY_OPT_OUT=1`, restores both after. CLI `evally deepeval <run> --case ID --suite SUITE`.
- Verified behaviour of 4.3.2 (by running it): `PatternMatchMetric` uses `fullmatch`, so `\b30 days\b` scores 0 on a sentence containing it; `ToolCorrectnessMetric` builds an OpenAI client at construction (needs a key even though it makes no call); with `INPUT_PARAMETERS`, a call with one wrong argument of two scores 0.5 and **passes** at the default threshold 0.5; DeepEval creates an empty `.deepeval/` folder in the working directory; telemetry is on unless `DEEPEVAL_TELEMETRY_OPT_OUT=1`.

- [ ] **Step 1: failing tests:** `test_deepeval_missing_message` (monkeypatch import failure → message, exit 1); `test_pattern_match_is_fullmatch` (documents the library's behaviour against ours); `test_tool_correctness_default_threshold_passes_wrong_arg`; `test_compare_rows` (order-status-like case: regex + tool_args rows, verdicts agree at threshold 1.0); `test_env_restored_after_compare` (no `OPENAI_API_KEY` before → none after; existing value untouched).
- [ ] **Step 2:** `uv sync --extra deepeval`; FAIL. **Step 3:** implement. **Step 4:** PASS with the extra, and `uv sync` (no extra) + `uv run pytest -q` → DeepEval tests skipped, rest pass. **Step 5:** run `uv run evally deepeval bramble-v2-dev-qwen3.5-4b --suite bramble-v2-dev --case order-status` and the same for `return-window` (the lesson's two demo cases). **Step 6:** commit `feat: evally deepeval (same checks, side by side)`.

### Task 7: Lesson, README, course plan, week branch

**Files:**
- Create: `lessons/week04-code-graders.md`
- Modify: `README.md`, `COURSE_PLAN.md`, `lessons/week03-test-datasets.md` (breadcrumb)

- [ ] **Step 1:** lesson in week 3's format: breadcrumbs, time, `git checkout week-04`, "You're done when", Read first (2 sources, links checked: one on code-based/deterministic evals, one the DeepEval docs page for the metrics used), "check with code whatever code can check" and why first (free, fast, exact, never drifts), each new check type with a real case (the invented-arguments finding from `gen-fa79bb81`, quoted from its trace), refusal detection and its blind spot (from `evally refusals`), when a code check misleads (the `"$60"` false fail, the substring that one rephrasing beats, partial refusals), v1 → v2 before/after (copied), per-check-type rates and "sole fail" (copied), which week 2 categories code can check and which need week 5's LLM grader, the DeepEval comparison (same result? what it adds; what it hides: fullmatch, the key it needs without calling, the 0.5 default, telemetry, `.deepeval/`), what the numbers can't tell you, exercises, versions (DeepEval 4.3.2), **In one minute**.
- [ ] **Step 2:** README cheat-sheet rows (`refusals`, `run --by check`, `deepeval`, `uv sync --extra deepeval`), the new check types in the case-format section, weeks table, test count; COURSE_PLAN week 4 row linked, ✅ `week-04`, one-line summary with v1→v2 and the invented-arguments finding; week 3 breadcrumb links week 4.
- [ ] **Step 3:** `uv run pytest -q` (with and without the extra); every lesson command re-run and output matched.
- [ ] **Step 4:** commit `docs: week 4 lesson, README, course plan`. Final whole-branch review on a frozen snapshot, fixes, then fast-forward `main` and cut `week-04` branch + tag at the verified SHA. Do not push.
