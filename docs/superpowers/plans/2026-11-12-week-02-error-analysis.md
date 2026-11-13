# Week 2: Error analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Save full conversation traces, add `evally traces` and `evally label`, run about 18 realistic customer conversations through the app, label every one (pass/fail + free note), group the notes into a failure taxonomy and print a ranked count, so the learner sees that you pick metrics *after* reading how the app fails, not before.

**Architecture:** The runner keeps each turn's full trace in the run JSON (`CaseResult.turns`). A new `evally/evals_core/traces.py` renders one conversation as text. A new `evally/evals_core/labels.py` holds the `Label` record, a JSONL store, the interactive labelling loop (open coding), the categorising loop (axial coding) and the ranked report. The CLI gets `evally traces <run>` and `evally label <run> [--code | --report]`. A "traffic" file of unchecked conversations stands in for production logs.

**Tech Stack:** Python 3.11+, uv, pytest, stdlib only (no new dependencies).

**Spec:** `docs/superpowers/specs/2026-11-12-evally-course-design.md` (section 7, week 2 row; sections 3, 6, 9a)

## Global Constraints

- Python >=3.11, `uv`, pytest; `uv run pytest` passes offline with no API keys.
- No new runtime dependencies. No LangChain/LlamaIndex or any agent/RAG framework.
- Budget: live calls use the local Ollama model only (`qwen3.5:4b`) → $0. Recordings are committed so every demo replays with no key.
- Labels "are written by the course author (an AI assistant) and marked as such"; the lesson explains that real teams use human labels and shows where to put them.
- About 15-20 conversations; "a suite never grows past what the concept needs".
- Lesson output blocks are copied from real runs; every lesson command re-run and matched.
- Work on branch `dev/week-02` cut from `main`. Snapshot branch `week-02` + tag `week-02` cut at the end; `week-01` is never touched.

## Review Focus

1. **Labelling is interrupted** (Ctrl-C, EOF, `q`) after a few conversations → labels already given are saved; re-running resumes at the first unlabelled conversation. (Task 3 `test_quit_keeps_earlier_labels`, `test_resume_skips_labelled`.)
2. **Labelling a run that was re-recorded** (the run JSON changed after labels were written) → labels for case ids no longer in the run are reported as stale, not silently counted. (Task 4 `test_report_ignores_and_counts_stale_labels`.)
3. **A case with no checks** (traffic conversations) → status `UNCHECKED`, never `PASS`, and the totals line counts them separately. Week 1's table is unchanged. (Task 1 `test_no_checks_is_unchecked`, `test_week01_table_unchanged`.)
4. **Bad input at a prompt** (`x`, empty line, a category number out of range) → the prompt repeats; no traceback, no label written. (Task 3 `test_bad_verdict_reprompts`, Task 4 `test_bad_category_number_reprompts`.)
5. **`evally traces`/`label` given a missing run file or unknown case id** → one-line message naming the runs folder, exit code 1. (Task 2 `test_traces_missing_run_message`.)

---

### Task 1: Full traces in run results, and unchecked cases

**Files:**
- Modify: `evally/evals_core/runner.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `Assistant.respond`, `Turn.trace: list[TraceStep]` (`kind`, `data`).
- Produces: `CaseResult.turns: list[dict]`, each `{"user": str, "reply": str, "trace": [{"kind": str, "data": dict}, ...]}`, in run JSON under `cases[i].turns`. Status values `PASS | FAIL | ERROR | UNCHECKED`; `totals["unchecked"]: int`. `load_run(path: Path) -> dict` (plain JSON dict, raises `FileNotFoundError`).

- [ ] **Step 1:** `git checkout main && git checkout -b dev/week-02`.
- [ ] **Step 2: failing tests:** `test_run_keeps_full_trace` (ScriptedModel tool round trip → `turns[0]["trace"]` kinds `["retrieve", "model", "tool", "model"]` and the tool step's `data` has `arguments` and `result`); `test_multi_turn_keeps_every_turn` (2 turns → `len(turns) == 2`, each with its own `user`); `test_no_checks_is_unchecked` (case with `checks: []` → status `UNCHECKED`; `totals["unchecked"] == 1`; `format_table` line shows `UNCHECKED` and the totals line ends `, 1 unchecked`); `test_week01_table_unchanged` (suite with checks only → totals line has no `unchecked` text); `test_error_case_keeps_turns_so_far`; `test_load_run_round_trip`.
- [ ] **Step 3:** `uv run pytest tests/test_runner.py -q` → FAIL.
- [ ] **Step 4:** implement. Trace step data is already JSON-safe dicts; store `asdict`-style `{"kind", "data"}`. `passed` counts only `PASS`; table width keeps `UNCHECKED` aligned (status column width 9).
- [ ] **Step 5:** full `uv run pytest -q` → PASS; `uv run evally run --suite week01` → same table as `lessons/week01-baseline.md` section 6 (replay; the run JSON gains `turns`, that's expected). Commit `feat: keep full traces in run results; unchecked cases`, including the regenerated `evals/runs/week01-qwen3.5-4b.json`.

### Task 2: `evally traces`

**Files:**
- Create: `evally/evals_core/traces.py`
- Modify: `evally/cli.py`
- Test: `tests/test_traces.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_run`, the `turns` shape from Task 1.
- Produces: `format_conversation(case: dict) -> str`; `run_path(name: str, runs_dir: Path) -> Path` (accepts `week02-traffic-qwen3.5-4b`, a `.json` filename, or a path). CLI `evally traces <run> [--case ID]`: no `--case` → one line per case `id  status  turns  tools`; with `--case` → the full conversation.

`format_conversation` layout (exact; the lesson and the labelling loop both print it):

```
── order-status ───────────────────────────── FAIL
customer> Hi, where is my order BB-1002? My email is ben@example.com
  docs: shipping.md, returns.md, privacy.md
  tool: lookup_order {"order_id": "BB-1002", "email": "ben@example.com"}
     → {"status": "shipped", ...}            (results cut to 200 chars; prefixed "ERROR " when is_error)
assistant> Your order BB-1002 has shipped...
```

- [ ] **Step 1: failing tests:** `test_format_shows_user_docs_tools_reply_in_order`; `test_tool_error_marked` (an `is_error` result line starts `→ ERROR `); `test_long_result_cut_to_200_chars`; `test_run_path_accepts_name_file_or_path`; `test_traces_lists_cases` (CLI on a temp run JSON prints each id); `test_traces_case_prints_conversation`; `test_traces_missing_run_message` (prints `no run named X in evals/runs` and returns 1); `test_traces_unknown_case_message` (returns 1).
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS. **Step 5:** commit `feat: evally traces`.

### Task 3: Labels and `evally label` (open coding)

**Files:**
- Create: `evally/evals_core/labels.py`
- Modify: `evally/cli.py`, `evally/config.py` (`labels_dir`)
- Test: `tests/test_labels.py`

**Interfaces:**
- Consumes: `format_conversation`, `run_path`, `load_run`.
- Produces:
  - `@dataclass Label: run: str; case_id: str; verdict: Literal["pass", "fail"]; note: str; category: str = ""; labeler: str = "human"`.
  - `labels_path(run_name: str, labels_dir: Path) -> Path` → `<labels_dir>/<run_name>.jsonl`; `Config.labels_dir` = `EVALLY_LABELS_DIR` or `evals/labels`.
  - `load_labels(path) -> dict[str, Label]` (keyed by case id, last line wins); `append_label(path, label)` (one JSON line, file created with parents).
  - `label_loop(run: dict, run_name: str, existing: dict[str, Label], labeler: str, ask: Callable[[str], str], say: Callable[[str], None], save: Callable[[Label], None]) -> int` (returns how many it labelled).
  - CLI: `evally label <run> [--labeler NAME]`.

Loop behaviour: for each case not in `existing`, `say(format_conversation(case))`, then `ask("verdict [p]ass / [f]ail / [s]kip / [q]uit: ")`; anything else re-asks. On `p`/`f`, `ask("note (what went wrong, or what was good): ")`; a fail needs a non-empty note (re-ask), a pass may be empty. `save` is called immediately after each label. `q`, `EOFError` or `KeyboardInterrupt` end the loop cleanly. Ends with `say("labelled N, M left")`.

- [ ] **Step 1: failing tests** (fake `ask` from a list, `save` into a list): `test_labels_pass_and_fail_with_notes`; `test_fail_needs_a_note`; `test_bad_verdict_reprompts` (`"x"` then `"p"` → one label, no exception); `test_skip_writes_nothing`; `test_quit_keeps_earlier_labels` (label 1, then `q` → `save` called once); `test_eof_ends_cleanly`; `test_resume_skips_labelled` (existing has case 1 → first conversation shown is case 2); `test_labeler_recorded`; `test_append_then_load_round_trip`; `test_last_line_wins`.
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS. **Step 5:** commit `feat: evally label (pass/fail with notes)`.

### Task 4: Categories and the ranked report (axial coding)

**Files:**
- Modify: `evally/evals_core/labels.py`, `evally/cli.py`
- Test: `tests/test_labels.py`

**Interfaces:**
- Consumes: `Label`, `load_labels`, `append_label`.
- Produces:
  - `code_loop(labels: dict[str, Label], ask, say, save) -> int`: for each `fail` label with no category, show `case_id` and its note, list the categories used so far as `1. name`, and `ask("category (number, or a new name): ")`; a number picks an existing one (out of range re-asks), any other non-empty text is a new category (lowercase, spaces → `-`). `q`/EOF stops. `save` writes the updated label (append; last line wins).
  - `category_counts(labels: dict[str, Label], case_ids: set[str]) -> tuple[list[tuple[str, int]], int]`: counts fail labels per category, most first (ties by name), `"uncategorised"` for fails with no category; second value = labels whose case id isn't in `case_ids` (stale, not counted).
  - `format_report(run_name, labels, case_ids) -> str` (exact layout):

```
labels for week02-traffic-qwen3.5-4b (labeller: course-author (AI))

  18 labelled · 11 pass · 7 fail

  category                     fails
  invents-facts                    3
  ...

```
  (plus `  N stale labels ignored (case not in this run)` when N > 0; the labeller line lists distinct labellers.)
  - CLI: `evally label <run> --code` and `evally label <run> --report`.

- [ ] **Step 1: failing tests:** `test_code_picks_existing_by_number`; `test_code_new_name_normalised` (`"Invents Facts"` → `invents-facts`); `test_bad_category_number_reprompts`; `test_code_skips_passes_and_categorised`; `test_counts_ranked_with_ties_by_name`; `test_uncategorised_fail_counted`; `test_report_ignores_and_counts_stale_labels`; `test_report_layout` (exact string for a 3-label fixture).
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS. **Step 5:** commit `feat: failure categories and ranked report`.

### Task 5: The traffic set, recorded

**Files:**
- Create: `evals/traffic/week02-traffic.jsonl`
- Modify: `evally/cli.py` only if `--suite` path handling needs it (it shouldn't)

18 conversations, no checks, in the case format, written as *realistic customer traffic*, not as tests of known flaws: mixed topics (orders, returns, shipping, stock, gift cards, membership, pre-orders, damaged items, privacy), at least 5 multi-turn (the customer adds details later, changes their mind, gets annoyed), at least 3 phrased unlike the docs ("can I send it back", "how fast can you get it to me"), 2 off-topic or out-of-scope (opening hours, a book recommendation), 1 asking about another person's order. Each line has a `//` comment saying which real-world situation it stands for. Written in full **before** the live run, and not edited afterwards to produce failures.

- [ ] **Step 1:** write the file. `uv run evally run --suite evals/traffic/week02-traffic.jsonl --live` → every case `UNCHECKED`, 0 errors; run saved as `evals/runs/week02-traffic-qwen3.5-4b.json` (the run name comes from the file stem).
- [ ] **Step 2:** replay (no `--live`) gives the identical table.
- [ ] **Step 3:** commit `evals: week 2 traffic set recorded on local qwen3.5:4b` (cache + run JSON + traffic file).

### Task 6: The analysis (labels, taxonomy, ranked list)

- [ ] **Step 1: open coding.** `uv run evally label week02-traffic-qwen3.5-4b --labeler "course-author (AI)"`. Read each conversation in full (reply, docs, every tool call and result) and check facts against `evally/app/docs/` and `seed.json`. Notes describe what went wrong in plain words, specific to the conversation ("quoted 60 days from returns-2023.md"), not category names. Answers may be piped on stdin; the labels file is the record either way.
- [ ] **Step 2: axial coding.** `uv run evally label week02-traffic-qwen3.5-4b --code`. Aim for 4-7 categories, each defined by one sentence in the lesson. Categories describe the failure as seen by the customer, not the planted flaw's id.
- [ ] **Step 3: measurement check (obs 0033).** Fewer than 4 fail labels in total, or every fail in one category, means the traffic set can't rank anything. If so, stop and report to the owner with the counts; don't add conversations aimed at known flaws.
- [ ] **Step 4:** `uv run evally label week02-traffic-qwen3.5-4b --report`; also run the week 1 suite cases' verdicts past the taxonomy: for each category, does any week 1 check catch it? (Table in the lesson; this is what shows week 1's checks were chosen before looking.)
- [ ] **Step 5:** commit `evals: week 2 labels and failure taxonomy (author-labelled)`.

### Task 7: Lesson, README, course plan, week branch

**Files:**
- Create: `lessons/week02-error-analysis.md`
- Modify: `README.md`, `COURSE_PLAN.md`, `lessons/week01-baseline.md` (breadcrumb: Week 2 link)

- [ ] **Step 1:** `lessons/week02-error-analysis.md` in week 1's format: breadcrumbs, time, `git checkout week-02`, "You're done when", Read first (2 sources, links checked: an error-analysis source such as Hamel Husain's and Shreya Shankar's material, and one on open/axial coding), why metrics come after reading, traces (an `evally traces` example copied), open coding with 3 real notes, axial coding with the category definitions, the ranked report (copied), which categories week 1's checks would and wouldn't catch, **who labelled this** (the course author, an AI; how a team does it with humans; where their labels go: `--labeler`), what the counts can't tell you (18 conversations, one run, one labeller), exercises (label 5 yourself with your own name and compare; re-categorise; add a traffic conversation), versions, **In one minute**.
- [ ] **Step 2:** README: cheat-sheet rows for `evally traces` and `evally label` (+ `--code`, `--report`), week 2 in the weeks table. COURSE_PLAN: week 2 row linked, status `✅ week-02`, one-line build summary with the top category. Week 1 lesson breadcrumb links week 2.
- [ ] **Step 3:** `uv run pytest -q` passes; every command in the lesson re-run and output matched.
- [ ] **Step 4:** commit `docs: week 2 lesson, README, course plan`; merge `dev/week-02` into `main` (fast-forward); `git branch week-02 && git tag week-02` on that commit. Do not push.
