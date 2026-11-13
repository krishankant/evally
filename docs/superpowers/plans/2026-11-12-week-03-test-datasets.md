# Week 3: Test datasets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the week 1 suite and week 2's findings into a tagged, versioned dataset of about 25 cases from four sources (hand-written, traffic-derived, model-generated and reviewed, adversarial), split into dev and test, with a coverage report per tag and a measured survival rate for generated cases.

**Architecture:** Tags carry dimensions as `dim:value` strings (`topic:returns`, `difficulty:hard`, `category:misses-the-relevant-policy`, `source:generated`), validated against one table in `evally/datasets/dimensions.py` by `load_cases`, the only loader every reader goes through. `evally/datasets/generate.py` samples dimension combinations and asks a model for customer messages (through `CachedModel`, so it replays free). `evally/datasets/review.py` is a keep/drop loop with reasons. `evally/datasets/build.py` merges sources, checks ids, splits dev/test (stratified by `category:`, deterministic by id hash) and writes a lock file with content hashes. `evally dataset stats` prints coverage; `evally run --by TAG-DIM` prints pass rates per value.

**Tech Stack:** Python 3.11+, uv, pytest, stdlib only (no new dependencies).

**Spec:** `docs/superpowers/specs/2026-11-12-evally-course-design.md` (section 7, week 3 row; sections 3, 6, 9a, 10)

## Global Constraints

- Python >=3.11, `uv`, pytest; `uv run pytest` passes offline with no API keys.
- No new runtime dependencies; no agent/RAG framework.
- Budget: generation and app runs use the local Ollama model only (`qwen3.5:4b`) → $0. Recordings committed; everything replays with no key.
- "a suite never grows past what the concept needs (roughly 10-20 cases at most)": each of `dev` and `test` stays at or under 20 cases.
- "Prompts are tuned against a **dev set** and the headline numbers come from a **held-out test set** the fixes never saw." This week builds the split; the lesson states the rule.
- Generated cases are "reviewed by the author"; the review is marked as the course author's (an AI), as labels were in week 2.
- Lesson output blocks copied from real runs (shortened only where marked `...`); every command re-run and matched.
- Branch `dev/week-03` from `main`; at the end fast-forward `main`, cut `week-03` branch + tag. `week-01`/`week-02` untouched. No push.

## Review Focus

1. **A tag with an unknown dimension or value** (`topic:shippng`, `difficulty:extreme`) in any case file → `load_cases` raises with file:line and the allowed values; every reader (run, build, stats, review output) gets the error because they all load through it. (Task 1 `test_unknown_dimension_value_rejected`, `test_free_tags_without_colon_allowed`; Task 4 `test_build_rejects_bad_tag`.)
2. **The same case id in two source files** → build fails naming both files; nothing written. (Task 4 `test_duplicate_id_across_sources_fails`.)
3. **Rebuilding a version whose sources changed** → build refuses to overwrite `bramble-vN` and says to bump the version; rebuilding with unchanged sources is a no-op success. (Task 4 `test_changed_sources_need_new_version`, `test_rebuild_same_sources_ok`.)
4. **Split stability:** adding one case to a source must not move any existing case between dev and test. (Task 4 `test_adding_a_case_moves_no_existing_case`.)
5. **Generator gets an empty, multi-line or quoted reply from a small model** → the candidate is kept with the raw text trimmed of surrounding quotes and whitespace, and empty replies are dropped with a counted reason, never a crash. (Task 2 `test_strips_quotes_and_whitespace`, `test_empty_reply_counted_not_kept`.)

---

### Task 1: Dimension tags, validated at load

**Files:**
- Create: `evally/datasets/__init__.py`, `evally/datasets/dimensions.py`
- Modify: `evally/evals_core/cases.py`
- Test: `tests/test_dimensions.py`

**Interfaces:**
- Produces: `DIMENSIONS: dict[str, tuple[str, ...]]` =
  - `topic`: `returns, shipping, international, orders, stock, membership, gift-cards, damaged, preorders, privacy, account, off-topic`
  - `difficulty`: `easy, medium, hard`
  - `category`: `none, cant-find-book-by-title, goes-beyond-policy, misses-the-relevant-policy, unsupported-claims, needless-escalation, uses-outdated-policy` (week 2's taxonomy)
  - `source`: `hand, traffic, generated, adversarial`
- `parse_tag(tag: str) -> tuple[str, str] | None` (None for a free tag with no colon); `validate_tags(tags: list[str]) -> list[str]` (error strings). `tag_value(tags, dim) -> str | None`.
- `load_cases` raises `ValueError(f"{path}:{n}: {error}")` on the first bad tag.

- [ ] **Step 1:** `git checkout main && git checkout -b dev/week-03`; commit this plan (`docs: week 3 plan (test datasets)`).
- [ ] **Step 2: failing tests:** `test_parse_dim_tag`; `test_free_tags_without_colon_allowed` (`"policy"` loads); `test_unknown_dimension_value_rejected` (`topic:shippng` → message names the file:line and lists `shipping`); `test_unknown_dimension_rejected` (`mood:sad`); `test_two_values_for_one_dimension_rejected` (`difficulty:easy` + `difficulty:hard`); `test_week01_suite_still_loads`.
- [ ] **Step 3:** FAIL. **Step 4:** implement. **Step 5:** full suite PASS; commit `feat: dimension tags validated at load`.

### Task 2: Generating candidate cases

**Files:**
- Create: `evally/datasets/generate.py`, `evals/datasets/dims-week03.json`
- Modify: `evally/cli.py`
- Test: `tests/test_generate.py`

**Interfaces:**
- Consumes: `Model.complete(messages, tools, system)`, `CachedModel`, `DIMENSIONS`.
- Produces:
  - `sample_combinations(dims: dict[str, list[str]], n: int, seed: int) -> list[dict[str, str]]`: `n` distinct combinations from the full product, chosen with `random.Random(seed)`, in a stable order; `n` larger than the product → all of them.
  - `@dataclass Candidate: id: str; text: str; dims: dict[str, str]`, `id` = `gen-` + first 8 hex of sha256 of the sorted dims JSON.
  - `generate(model, combos) -> tuple[list[Candidate], dict[str, int]]` (candidates, drop counts e.g. `{"empty": 1}`).
  - `GEN_SYSTEM` (exact): `"You write realistic test messages for a customer support assistant at Bramble Books, an online bookstore. Write ONE message a real customer might send. Match the topic, persona and phrasing you are given. Reply with the message only: no quotes, no explanation."` User message: `"Topic: {topic}\nPersona: {persona}\nPhrasing: {phrasing}"`.
  - CLI `evally generate --dims FILE --n N --seed S --out FILE [--live]` writes candidates JSONL (`{"id", "text", "dims"}`) and prints `generated N, dropped M (reasons)`.
- `evals/datasets/dims-week03.json`: `{"topic": [returns, shipping, international, orders, stock, membership, gift-cards, damaged, preorders], "persona": ["polite", "annoyed", "confused", "in a hurry"], "phrasing": ["uses the store's own words", "own casual words", "typos and no punctuation"]}`. `persona`/`phrasing` are generation-only dimensions, not dataset tags.

- [ ] **Step 1: failing tests** (ScriptedModel): `test_sample_is_deterministic_and_distinct`; `test_sample_n_larger_than_product_returns_all`; `test_prompt_carries_the_combination` (ScriptedModel's recorded call has `GEN_SYSTEM` and the three lines); `test_strips_quotes_and_whitespace` (`'  "Where is my book?"\n'` → `Where is my book?`); `test_empty_reply_counted_not_kept`; `test_candidate_id_stable_for_same_dims`; `test_generate_cli_replay_miss_message` (no recording → the `--live` hint, exit 1).
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS. **Step 5:** commit `feat: evally generate (candidate cases from dimensions)`.

### Task 3: Reviewing candidates

**Files:**
- Create: `evally/datasets/review.py`
- Modify: `evally/cli.py`
- Test: `tests/test_review.py`

**Interfaces:**
- Consumes: `Candidate` JSONL from Task 2.
- Produces:
  - `@dataclass Decision: candidate_id: str; keep: bool; reason: str; reviewer: str`.
  - `review_loop(candidates, existing: dict[str, Decision], reviewer, ask, say, save) -> int`: shows `id`, dims and text; asks `keep? [k]eep / [d]rop / [q]uit: `; a drop needs a reason (re-ask on empty), a keep's reason may be empty; `q`/EOF/Ctrl-C stop; resumes past decided ids. Same append-one-line, last-line-wins store as week 2 labels (reuse the JSONL helpers by generalising them, not copying).
  - `survival_report(candidates, decisions) -> str` (exact):

```
review of week03-generated (reviewer: course-author (AI))

  12 generated · 8 kept · 4 dropped (67% kept)

  drop reason          count
  not-a-real-request       2
  ...
```
  Drop reasons are normalised like categories (lowercase, dashes); a candidate with no decision is listed as `  N not reviewed yet`. Decisions whose id isn't among the candidates are reported stale and not counted (obs 0040: the same rule as labels).
  - CLI `evally review FILE [--reviewer NAME] [--report]`; decisions saved next to the file as `<stem>.review.jsonl`.

- [ ] **Step 1: failing tests:** `test_keep_and_drop_with_reason`; `test_drop_needs_reason`; `test_bad_answer_reprompts`; `test_quit_keeps_earlier_decisions`; `test_resume_skips_decided`; `test_report_layout` (exact string); `test_report_counts_unreviewed_and_ignores_stale`.
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS. **Step 5:** commit `feat: evally review (keep/drop generated cases)`.

### Task 4: Building a versioned dataset with a dev/test split

**Files:**
- Create: `evally/datasets/build.py`, `evals/datasets/bramble.json`
- Modify: `evally/cli.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: `load_cases`, `tag_value`.
- Produces:
  - Manifest `evals/datasets/bramble.json`: `{"name": "bramble", "version": 1, "sources": ["evals/datasets/bramble/hand.jsonl", ".../traffic.jsonl", ".../generated.jsonl", ".../adversarial.jsonl"], "test_share": 0.4}`.
  - `split(cases: list[Case], test_share: float) -> tuple[list[Case], list[Case]]`: group by `category:` value (missing → `none`); a case goes to test when `int(sha256(id)[:8], 16) / 0xFFFFFFFF < test_share`. Per-case, so adding a case never moves another (focus 4). Then, for each category with 2+ cases and none in test (or none in dev), move the case with the lowest hash across, and record the move in the lock. Order within each split = source order.
  - `build(manifest_path: Path, suites_dir: Path, datasets_dir: Path) -> Path`: writes `evals/suites/bramble-v{N}-dev.jsonl`, `...-test.jsonl` and `evals/datasets/bramble-v{N}.lock.json` (`{"name", "version", "sources": {path: sha256}, "dev": [ids], "test": [ids], "moved": [ids]}`). Raises `ValueError` on: a duplicate id (names both files), a source that fails `load_cases` (re-raised), an existing lock for this version with different source hashes (message: `bramble v1 already built from different sources; bump "version" in evals/datasets/bramble.json`). Same hashes → returns the existing lock path, writes nothing.
  - CLI `evally dataset build [--manifest FILE]`.

- [ ] **Step 1: failing tests:** `test_split_deterministic`; `test_adding_a_case_moves_no_existing_case` (the hash rule only; the rebalancing step may add moves, so assert on cases outside rebalanced categories); `test_each_category_with_two_cases_in_both_splits`; `test_duplicate_id_across_sources_fails`; `test_build_rejects_bad_tag`; `test_changed_sources_need_new_version`; `test_rebuild_same_sources_ok`; `test_lock_records_hashes_and_ids`.
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS. **Step 5:** commit `feat: versioned dataset build with dev/test split`.

### Task 5: Coverage and per-tag results

**Files:**
- Create: `evally/datasets/stats.py`
- Modify: `evally/evals_core/runner.py`, `evally/cli.py`
- Test: `tests/test_stats.py`, `tests/test_runner.py`

**Interfaces:**
- Consumes: lock file, `load_cases`, `tag_value`, `RunResult`.
- Produces:
  - `coverage(dev: list[Case], test: list[Case]) -> dict[str, list[tuple[str, int, int]]]` (per dimension: value, dev count, test count, in `DIMENSIONS` order, including zero rows).
  - `format_coverage(name_version, cov) -> str`: one table per dimension; rows with a 0 in test are marked `  ← not in test`; values with 0 in both are listed on one line `  missing: a, b`.
  - CLI `evally dataset stats bramble-v1`.
  - `format_by_tag(result: RunResult, dim: str) -> str`: per value of `dim`, `passed/checked` and `%`, most failing first; cases without that dimension under `(untagged)`. CLI `evally run --suite S --by DIM` prints it after the table.

- [ ] **Step 1: failing tests:** `test_coverage_counts_and_zero_rows`; `test_format_marks_missing_in_test`; `test_by_tag_rates_and_order`; `test_by_tag_untagged_bucket`; `test_run_by_unknown_dimension_message` (CLI: one line naming the dimensions, exit 1).
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS. **Step 5:** commit `feat: dataset coverage and per-tag pass rates`.

### Task 6: The dataset itself

**Files:**
- Create: `evals/datasets/bramble/hand.jsonl`, `traffic.jsonl`, `generated.jsonl`, `adversarial.jsonl`; `evals/datasets/candidates/week03-generated.jsonl` (+ `.review.jsonl`)

- [ ] **Step 1: hand.** Week 1's 10 cases, same ids and checks, with `topic:`, `difficulty:`, `category:` (`none` unless one fits) and `source:hand` tags. `evals/suites/week01.jsonl` is not edited.
- [ ] **Step 2: traffic.** One case per week 2 fail category, from the labelled week 2 conversations (6 cases, ids `t-<week2 id>`), turns copied verbatim, checks written with the five existing check types to catch the failure the label describes. Where no code check can catch it (`unsupported-claims`), write the closest honest check and say in a `//` comment what it misses (week 4/5 fix that).
- [ ] **Step 3: generated.** `uv run evally generate --dims evals/datasets/dims-week03.json --n 12 --seed 3 --out evals/datasets/candidates/week03-generated.jsonl --live`, then replay to confirm; `uv run evally review evals/datasets/candidates/week03-generated.jsonl --reviewer "course-author (AI)"` (drop anything unrealistic, duplicated, ambiguous or not answerable from the docs or tools; reasons in plain words); kept ones become cases in `generated.jsonl` with checks written by hand, `source:generated`, `topic:` from the combination.
- [ ] **Step 4: adversarial.** 4 cases written to break the app on purpose (`source:adversarial`, `difficulty:hard`): a customer quoting the 60-day policy back; a pushy second turn on price matching; a third party with a plausible story asking for an order's contents with only the order id; a return request for a gift card dressed as a book. Checks with existing types.
- [ ] **Step 5: measurement check (obs 0033).** Build (`uv run evally dataset build`), then `uv run evally dataset stats bramble-v1`. Every week 2 category must have at least one case in **test**; dev and test each ≤ 20. If either fails, adjust the sources (add a case to the thin category, or drop generated ones) **before** recording anything, rebuild, re-check.
- [ ] **Step 6:** record both splits live (`uv run evally run --suite bramble-v1-dev --live --by category`, same for test), replay both to confirm identical tables.
- [ ] **Step 7:** commit `evals: bramble v1 dataset (hand, traffic, generated, adversarial) with dev/test split`.

### Task 7: Lesson, README, course plan, week branch

**Files:**
- Create: `lessons/week03-test-datasets.md`
- Modify: `README.md`, `COURSE_PLAN.md`, `lessons/week02-error-analysis.md` (breadcrumb)

- [ ] **Step 1:** lesson in week 2's format: breadcrumbs, time, `git checkout week-03`, "You're done when", Read first (2 sources, links checked: one on test-set design / synthetic data with dimensions, one on dev/test splits or held-out sets), why the eval is only as good as its cases, the four sources and what each is good and bad at, dimensions as tags, generation with dimensions (the prompt, a few real candidates), the review and survival rate (copied), adversarial cases, the split and why it's stratified and hash-based, versioning and the lock file, coverage (copied), the first per-category pass rates on dev and test (copied), what the numbers can't tell you (sizes, one run, author-reviewed), exercises, versions, **In one minute**.
- [ ] **Step 2:** README cheat-sheet rows (`generate`, `review`, `dataset build`, `dataset stats`, `run --by`), weeks table, test count; COURSE_PLAN week 3 row linked, ✅ `week-03`, one-line summary with the survival rate and coverage headline; week 2 breadcrumb links week 3.
- [ ] **Step 3:** `uv run pytest -q`; every lesson command re-run and output matched.
- [ ] **Step 4:** commit `docs: week 3 lesson, README, course plan`. Final whole-branch review, fixes, then fast-forward `main`, `git branch week-03 && git tag week-03` on that commit. Do not push.
