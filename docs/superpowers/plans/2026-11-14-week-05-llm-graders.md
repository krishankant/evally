# Week 5: LLM as a grader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Grade what code can't check with a model. Build a rubric-based grader that returns a structured verdict (reason, then pass/fail), with one rubric per week 2 failure category, plus a 1-5 scale to compare against. Show three grader biases with numbers: position, length and self-preference. Then do the same grading with DeepEval's G-Eval and compare.

**Architecture:**
- **Grading saved runs.** The grader works on saved runs (`evals/runs/*.json`), never by re-running the app. `evally grade <run>` loads a run and the rubrics. For each case and rubric it asks the grader model for a verdict, then prints a table and saves a grades file.
- **Structured output without changing the `Model` interface.** The grader gets one tool, `record_verdict` (`record_score` on the 1-5 scale), and is told to always call it. The verdict is read from that tool call, so the same code works on Anthropic, OpenAI and Ollama.
- **Recording and replay.** Grader calls go through `CachedModel`, so recordings are committed and replay costs nothing.
- **Grader settings.** The grader model is set apart from the app model (spec §4) by `EVALLY_GRADER_PROVIDER` / `EVALLY_GRADER_MODEL`.
- **Bias demos.** A pairwise "which reply is better" prompt runs in both orders.
  - **Position bias:** one run against itself. The replies are identical, so any non-tie verdict is position bias.
  - **Length bias:** a run against its padded copy. Padding is a fixed sentence added by code, no model call.
  - **Self-preference:** the qwen run against a mistral run, judged once by qwen and once by mistral.
- **G-Eval.** DeepEval (already an optional extra) runs G-Eval through an adapter that wraps our `CachedModel`, so its calls are recorded and replayed like ours.

**Tech Stack:** Python 3.11+, uv, pytest. Grader: **local** Ollama `qwen3.5:4b` (owner's choice, 2026-11-14: "use local"; no hosted spend). Self-preference second model and judge: local `mistral:latest`. DeepEval 4.3.2 `GEval` (optional extra, already pinned).

**Owner override (2026-11-14):** the grader is local, not hosted. Hosted providers still work through `--grader-provider`, but nothing in this week records one. Wherever a step below names Haiku, read `qwen3.5:4b` as the grader and `mistral:latest` as the second model in the self-preference demo. The lesson says plainly that a 4B grader is weak, and that a stronger grader is a one-flag change.

**Spec:** `docs/superpowers/specs/2026-11-12-evally-course-design.md` (§7 row 5; §3, §4, §6, §9, §9a, §10)

## Global Constraints

- **Offline tests.** `uv run pytest` passes offline with no API keys, with or without the `deepeval` extra. Model calls in tests use `ScriptedModel`.
- **By hand first** (spec §3). Tasks 1-5 are plain Python; G-Eval comes last, and the lesson answers three questions: same result? What does the library add? What does it hide?
- **Pass/fail is the main grader; 1-5 is the comparison** (spec §10).
- **One grader per failure category** (spec §7). There are three rubrics, all named after week 2 categories:
  - `goes-beyond-policy`
  - `unsupported-claims`
  - `uses-outdated-policy` (this one also has code checks, so the lesson can compare the two)
- **No test-set leak** (spec §6). Rubrics are written and tuned looking only at **dev** traces and the week 2 traffic labels. Week 5 reports dev numbers only (spec §7 row 5: "grader scores on the dev set").
- **Labels are marked.** Anything the course author judges is marked "course author (AI)" (spec §6). This week adds no labels; checking the grader against labels is week 6.
- **Budget** (spec §9a): **$0**. Every model is local (owner override). Every `grade`, `bias` and `geval` command still prints its tokens and its cost (`$0.0000` for local models, `cost unknown` for a model that isn't in the price table).
- **One live Ollama job at a time** (observation 0035, plus the memory limits on this 8 GB Mac). Each recording run goes in the background with a stall watch, and a job that stalls for more than 20 minutes is stopped and reported.
- **Library versions.** DeepEval stays `==4.3.2`. The custom-model contract below was checked by running it (G-Eval falls back to `generate(prompt) -> str` and parses the JSON when the model has no structured-output or logprob support).
- **Lesson output.** Every output block is copied from a real run (`...` marks shortening), and every command is re-run and matched.
- **Git.**
  - Work on branch `dev/week-05`, made from `main`.
  - At the end, fast-forward `main` and cut the `week-05` branch and tag at a verified SHA.
  - **Pushing waits for the owner to approve.** The repo is public now, with protected branches and `week-*` tags.

## Review Focus

1. **The grader input leaks the answer.** The case id (`adv-quotes-60-days`), the PASS/FAIL status, the check details or the tags must never reach the grader; it sees only the conversation and the policies. (Task 1 `test_grader_input_hides_id_status_checks_and_tags`.)
2. **The grader replies with something that isn't a valid verdict.** For example:
   - no tool call;
   - a `verdict` outside `pass`/`fail`;
   - a score of 0, 7 or `"4"`;
   - the JSON written in the text instead of in a tool call;
   - an empty reply.

   JSON in the text is accepted. Everything else becomes verdict `error`, with the raw text cut to 200 characters as the reason. It is never counted as a pass or a fail, and totals report errors separately. (Task 1 `test_malformed_grader_replies`; Task 2 `test_errors_counted_apart`.)
3. **A grader with no recordings, or no key.**
   - In replay mode: print the `ReplayMiss` message, exit 1 and write no grades file. An existing grades file is not overwritten by a partial one.
   - `--live` with the anthropic grader and a blank or missing `ANTHROPIC_API_KEY`: print `ANTHROPIC_API_KEY isn't set: add it to .env`, exit 1.
   - Blank `EVALLY_GRADER_*` values mean the default.

   (Task 2 `test_grade_replay_miss_writes_nothing`, `test_missing_key_message`; Task 2 `test_blank_grader_env_means_default`.)
4. **Bias pairs that aren't comparable.** Two runs from different suites are refused (`runs came from different suites: A, B`). Multi-turn cases and cases that errored in either run are skipped, and the skips are counted in the summary, because the earlier assistant turns differ between runs. A padded reply is exactly the original plus `PADDING`. (Task 4 `test_bias_refuses_different_suites`, `test_bias_skips_multiturn_and_errors`, `test_pad_run_appends_exactly`.)
5. **Rubric files that don't load.**
   - A rubric whose file name isn't a week 2 category (`DIMENSIONS["category"]` minus `none`) fails, naming the file.
   - So does an empty rubric.
   - `--rubric NAME` for a rubric that doesn't exist fails, listing the known ones.

   Every reader (`grade`, `geval`) loads through `load_rubrics`. (Task 1 `test_rubric_names_are_categories`; Task 2 `test_unknown_rubric_flag`; Task 5 `test_geval_unknown_rubric`.)

---

### Task 1: The rubric grader

**Files:**
- Create: `evally/graders/rubrics.py`, `evally/graders/judge.py`, `evals/rubrics/goes-beyond-policy.md`, `evals/rubrics/unsupported-claims.md`, `evals/rubrics/uses-outdated-policy.md`
- Test: `tests/test_judge.py`

**Interfaces:**
- Produces, in `evally/graders/rubrics.py`:
  - `Rubric(name: str, text: str)` (frozen dataclass).
  - `load_rubrics(dir: Path = Path("evals/rubrics")) -> dict[str, Rubric]`. Reads every `*.md` and sorts them by name. Raises `ValueError(f"{path}: ...")` when a name isn't a week 2 category or the text is empty (focus 5).
- Produces, in `evally/graders/judge.py`:
  - `SUPERSEDED = {"returns-2023.md"}`.
  - `policy_reference(docs_dir: Path | None = None) -> str`. Every app policy doc except `SUPERSEDED`, each under a `## <file name>` heading. The default dir is the app's docs.
  - `conversation_for_grader(case: dict) -> str`. Every turn as `customer: ...` / `assistant: ...`, with tool calls as `  (tool lookup_order {"order_id": ...} → <result cut to 200>)`. No id, status, checks, tags or doc names (focus 1).
  - `VERDICT_TOOL`, a `ToolSpec` named `record_verdict`. Parameters `{"reason": string, "verdict": enum ["pass","fail"]}`, both required, with `reason` listed first.
  - `SCORE_TOOL`, named `record_score`. Parameters `{"reason": string, "score": integer 1-5}`.
  - `GRADER_SYSTEM`, a fixed template with `{rubric}` and `{reference}`. It says: judge only the last assistant reply, against the rubric, using the policies as the only truth, and always answer by calling the tool.
  - `Verdict(case_id: str, rubric: str, verdict: Literal["pass","fail","error"], reason: str, score: int | None = None, tokens: dict = field(default_factory=dict))`.
  - `judge_case(model: Model, rubric: Rubric, case: dict, reference: str, scale: Literal["binary","1-5"] = "binary") -> Verdict`. On the 1-5 scale, verdict is `pass` when score >= 4. `ReplayMiss` propagates.
  - `parse_verdict(response: ModelResponse, scale) -> tuple[str, str, int | None]`. Returns (verdict, reason, score). It reads the tool call, falls back to the first `{...}` JSON object in the text, and returns `error` otherwise.

- [ ] **Step 1: create the branch and commit the plan.** Run `git checkout main && git checkout -b dev/week-05` and commit this plan with the message `docs: week 5 plan (LLM as a grader)`.
- [ ] **Step 2: write the failing tests.**
  - `test_rubric_names_are_categories`: `tmp/beyond.md` → `ValueError` naming `beyond.md`; an empty `goes-beyond-policy.md` → `ValueError`; the repo's `evals/rubrics` loads exactly the 3 names above.
  - `test_policy_reference_drops_superseded`: has `## returns.md` and `30 days`; has no `returns-2023.md` and no `60 days`.
  - `test_grader_input_hides_id_status_checks_and_tags`: a case dict with `id="adv-quotes-60-days"`, `status="FAIL"`, a check named `contains`, tags `["topic:returns"]`, and one turn with a lookup_order tool step. The output contains `customer:`, `assistant:` and `lookup_order`. It contains none of `adv-quotes-60-days`, `FAIL`, `contains` or `topic:`.
  - `test_judge_reads_tool_verdict`: a `ScriptedModel` returning `tool_reply(ToolCall("1", "record_verdict", {"reason": "promises a refund", "verdict": "fail"}))` → `Verdict(..., "fail", "promises a refund")`. Also assert the scripted call's tools are `[VERDICT_TOOL]` and the system prompt contains the rubric text and `## returns.md`.
  - `test_judge_scale_maps_score`: score 4 → pass, score 3 → fail, `score` kept.
  - `test_malformed_grader_replies`. These replies give `error`:
    - plain text with no JSON;
    - `verdict: "maybe"`;
    - score `7`, score `0`, score `"4"`;
    - an empty reply.

    `'Sure. {"reason": "fine", "verdict": "pass"}'` as text gives `pass`. The error reason holds at most 200 characters of the raw text.
- [ ] **Step 3: watch them fail.** Expected: FAIL (`ModuleNotFoundError: evally.graders.judge`).
- [ ] **Step 4: implement, and write the three rubrics.** Each rubric says, in plain words, what PASS and FAIL mean for that category. Each is written from the week 2 notes and the **dev** traces only (`uv run evally traces bramble-v2-dev-qwen3.5-4b --case ...`), and each has one FAIL example and one PASS example in the form "a reply that ...".
- [ ] **Step 5: watch them pass,** then run the full suite (it should pass). Commit with the message `feat: rubric grader with structured verdicts`.

### Task 2: `evally grade`, grader config, cost

**Files:**
- Create: `evally/llm/prices.py`
- Modify: `evally/config.py`, `evally/cli.py`, `.env.example`, `evally/graders/judge.py`
- Test: `tests/test_grade_cli.py`

**Interfaces:**
- Consumes: Task 1's `load_rubrics`, `judge_case`, `policy_reference`, `Verdict`.
- Produces, in `evally/config.py`:
  - `Config.grader_provider` (`EVALLY_GRADER_PROVIDER`, default `ollama`).
  - `Config.grader_model` (`EVALLY_GRADER_MODEL`, default `qwen3.5:4b`).
  - `Config.grades_dir` (`evals/grades`).
  - A blank value means the default (`or`, as the existing fields do).
- Produces, in `evally/llm/prices.py`:
  - `PRICES: dict[str, tuple[float, float]]`, USD per 1M input and output tokens. It holds the local models `qwen3.5:4b` and `mistral:latest` at `(0, 0)`. No hosted prices are guessed.
  - `cost(model: str, tokens_in: int, tokens_out: int) -> float | None`. Returns `None` for a model not in the table.
- Produces, in `evally/graders/judge.py`:
  - `grade_run(model, run: dict, rubrics: list[Rubric], reference: str, scale) -> list[Verdict]`. A case with status `ERROR` gets verdict `error`, reason `case errored`, and no model call.
  - `format_grades(run_name: str, grader: str, scale: str, verdicts: list[Verdict]) -> str`. It prints:
    - one row per case, with one column per rubric: `pass` / `FAIL` / `error`, and on the 1-5 scale the score after the verdict, like `FAIL 2`;
    - one line per rubric: `<rubric>  fails N/M` (M = cases that aren't errors), plus `, E errors` when there are any;
    - a last line, `tokens <in> in / <out> out · $<cost to 4 decimals>` (or `cost unknown`).
  - `save_grades(...) -> Path`. Writes `evals/grades/<run>__<grader slug>__<scale>.json` holding `{run, grader, scale, rubrics, verdicts: [asdict]}`.
- Produces the CLI command:
  `evally grade <run> [--rubric NAME ...] [--scale binary|1-5] [--case ID] [--live] [--grader-provider P] [--grader-model M]`
  - `--case` prints the full verdict reasons for one case.
  - Grader cache: `cfg.cache_dir / f"{provider}-{slug(model)}"`, the same layout as the app cache. The grader's requests carry its own system prompt and tool, so they never collide with the app's recordings in the same folder.

- [ ] **Step 1: write the failing tests.**
  - `test_grade_prints_table_and_saves`. A temp run with 2 cases, scripted grader model injected through a `make_grader` hook on `cmd_grade`. The output has `fails 1/2`, a `tokens` line and `saved`; the grades file holds 2 verdicts.
  - `test_errors_counted_apart`: 1 errored case → `fails 0/1, 1 errors`.
  - `test_unknown_rubric_flag`: `--rubric beyond` → exit 1, message lists the 3 names.
  - `test_grade_replay_miss_writes_nothing`. Write a grades file first, then replay with an empty cache → exit 1, the ReplayMiss text is printed, and the grades file is unchanged.
  - `test_missing_key_message`. Run `--live` with `ANTHROPIC_API_KEY=""` (monkeypatch) → exit 1, `ANTHROPIC_API_KEY isn't set: add it to .env`.
  - `test_blank_grader_env_means_default`.
  - `test_cost_known_and_unknown`.
- [ ] **Step 2: watch them fail.**
- [ ] **Step 3: implement.**
  - Add `EVALLY_GRADER_PROVIDER=ollama` and `EVALLY_GRADER_MODEL=qwen3.5:4b` to `.env.example`, with a comment saying the grader is separate from the app model.
  - The key check runs before any model is built, only when `--live` is set and the provider is `anthropic` or `openai`.
  - Verdicts are collected in full before `save_grades` runs, so a `ReplayMiss` midway writes nothing.
- [ ] **Step 4: watch them pass,** then run the full suite (it should pass).
- [ ] **Step 5: commit** with the message `feat: evally grade (rubric grader on a saved run, cost printed)`.

### Task 3: Binary vs 1-5, measured on dev

**Files:**
- Create: `evals/grades/*.json` (recorded); grader recordings under `evals/cache/ollama-qwen3.5-4b/`
- Test: none new (data task); the full suite must stay green.

**Interfaces:**
- Consumes: Task 2's `evally grade`.

- [ ] **Step 1: check that the dev set can show a difference** (observation 0033). From the dev run's code checks and week 2 notes, list which dev cases should fail each rubric (expected fails). If a rubric has no expected fail on dev, say so in the lesson and drop it from the bias and G-Eval demos rather than adding cases. **Do not open test traces.**
- [ ] **Step 2: check Ollama is up and nothing else is running on it** (`ollama ps`).
- [ ] **Step 3: record.** Run `uv run evally grade bramble-v2-dev-qwen3.5-4b --live`, then the same with `--scale 1-5`. Expected: 48 verdicts per scale, a cost line of `$0.0000`, and at most a few `error` verdicts. Errors stay visible in the table and the lesson; they are part of what a small grader does. If there are errors, read the raw replies and fix the prompt (and ledger a ruling) rather than accepting them.
- [ ] **Step 4: replay both commands with no `--live`.** Expected: identical tables, including the tokens/cost line (it comes from the recorded usage), and no network. Commit `evals/grades/` plus the new cache with the message `evals: week 5 grades on dev (binary and 1-5)`.

### Task 4: Bias demos (pairwise, both orders)

**Files:**
- Create: `evally/graders/pairwise.py`
- Modify: `evally/cli.py`
- Test: `tests/test_pairwise.py`

**Interfaces:**
- Consumes: Task 1's `conversation_for_grader`, `policy_reference`; Task 2's grader config, key check and `cost`.
- Produces, in `evally/graders/pairwise.py`:
  - `PREFER_TOOL`, a `ToolSpec` named `record_preference`. Parameters `{"reason": string, "winner": enum ["A","B","tie"]}`.
  - `PADDING`, one fixed sentence. It adds no facts and makes no promises; it is polite filler that restates nothing (e.g. "I hope this helps, and please don't hesitate to reach out if you have any other questions about your order or our policies — we're always happy to help!").
  - `prefer(model, context: str, reply_a: str, reply_b: str, reference: str) -> tuple[str, str, dict]`. Returns (winner, reason, tokens). A malformed reply → winner `error`.
  - `PairResult(case_id: str, first_a: str, first_b: str)`. These are the winners **in run labels** (`"a"`, `"b"`, `"tie"`, `"error"`) for order (A first) and order (B first).
  - `bias_test(model, run_a: dict, run_b: dict, reference: str) -> tuple[list[PairResult], dict]`. It returns the pair results and a summary dict with these keys:
    - `pairs`;
    - `skipped_multiturn`, `skipped_errors`;
    - `consistent` (same run label in both orders);
    - `first_position_wins` (verdicts out of `2*pairs` that picked whichever reply was shown first);
    - `a_wins`, `b_wins`, `ties` (counted over consistent pairs only);
    - `errors`;
    - `tokens`.

    It raises `ValueError("runs came from different suites: X, Y")`.
  - `pad_run(run: dict) -> dict`. A deep copy in which each case's last reply (in both `replies` and `turns[-1]["reply"]`) becomes `reply + " " + PADDING`, and `model` becomes `<model>+padded`.
- Produces the CLI commands:
  - `evally pad <run>`. Saves `evals/runs/<run stem>-padded.json` and prints its path.
  - `evally bias <run-a> <run-b> [--live] [--grader-provider P] [--grader-model M]`. Prints one line per pair (`id  A-first: a  B-first: b  inconsistent`), then the summary and the tokens/cost line.
  - The context passed to `prefer` is the single customer message and the shared tool results from run A. Lesson note: replies are compared as text.

- [ ] **Step 1: write the failing tests.**
  - `test_pad_run_appends_exactly`: the original run dict is unchanged after the call.
  - `test_bias_refuses_different_suites`.
  - `test_bias_skips_multiturn_and_errors`: 3 cases, one 2-turn and one ERROR → `pairs 1`, both skips counted.
  - `test_order_swap_maps_back_to_run_labels`. Scripted winners `A` then `A` → `first_a="a"`, `first_b="b"`, inconsistent, `first_position_wins == 2`.
  - `test_identical_replies_tie_is_consistent`: `tie`, `tie` → consistent, `ties == 1`, `first_position_wins == 0`.
  - `test_malformed_preference_is_error`.
- [ ] **Step 2: watch them fail.**
- [ ] **Step 3: implement.**
- [ ] **Step 4: watch them pass,** then run the full suite (it should pass).
- [ ] **Step 5: commit** with the message `feat: evally bias and evally pad (pairwise, both orders)`.
- [ ] **Step 6: record the three demos** (qwen as the judge unless noted).
  1. **Position, a run against itself** (the control: any non-tie is bias): `uv run evally bias bramble-v2-dev-qwen3.5-4b bramble-v2-dev-qwen3.5-4b --live`.
  2. **Length:** `uv run evally pad bramble-v2-dev-qwen3.5-4b`, then `uv run evally bias bramble-v2-dev-qwen3.5-4b bramble-v2-dev-qwen3.5-4b-padded --live`.
  3. **Self-preference.**
     - First record the app on mistral: `uv run evally run --suite bramble-v2-dev --provider ollama --model mistral:latest --live`. If mistral can't call tools through Ollama, ledger it and use the mistral replies as text only. That's enough, because pairs compare reply text.
     - Then judge the qwen run against the mistral run twice: once with qwen as the judge (the default), and once with `--grader-model mistral:latest`.
     - The bias is how far each judge's preference for its own replies moves away from the other judge's. Say in the lesson that quality differences confound this, and that 15 pairs illustrate the method but can't prove anything.

  If the local qwen judge stalls for more than 20 minutes (the memory problem from week 3), stop it. Report the self-preference demo as incomplete, and say so in the lesson and the ledger.

  Expected: every command prints a summary with `pairs 15`. Replay all of them without `--live` and check the output is identical. Commit the runs, the cache and the padded run with the message `evals: week 5 bias demos (position, length, self-preference)`.

### Task 5: DeepEval G-Eval side by side

**Files:**
- Create: `evally/graders/deepeval_geval.py`
- Modify: `evally/cli.py`
- Test: `tests/test_deepeval_geval.py` (skips without the extra)

**Interfaces:**
- Consumes: Task 1's `load_rubrics`, `judge_case`, `conversation_for_grader`, `policy_reference`; week 4's `_deepeval_env` (it wraps every DeepEval import and call).
- Produces, in `evally/graders/deepeval_geval.py`:
  - `CachedJudge(DeepEvalBaseLLM)`, built as `CachedJudge(model: Model)`. Its `generate(prompt, schema=None) -> str` returns `model.complete([Message("user", prompt)], [], None).message.text`. `a_generate` calls `generate`, `get_model_name` returns `model.name`, and `load_model` returns `model`. It reports no logprob or structured-output support, so G-Eval parses JSON from the text.
  - `geval_case(model, rubric, case, reference) -> dict`. Runs `GEval(name=rubric.name, criteria=rubric.text, evaluation_params=[INPUT, ACTUAL_OUTPUT, CONTEXT], model=CachedJudge(model), threshold=0.5, async_mode=False)` on `LLMTestCase(input=<conversation without the last reply>, actual_output=<last reply>, context=[reference])`. Returns `{score, reason, passed, steps}`, where `steps` are the evaluation steps G-Eval generated (`metric.evaluation_steps` after measuring).
- Produces the CLI command `evally geval <run> --rubric NAME --case ID [--live] [--grader-provider P] [--grader-model M]`. It prints:
  - our verdict (`judge_case`, binary, from the cache);
  - G-Eval's score, pass flag and reason;
  - G-Eval's generated steps, numbered;
  - the tokens/cost line.

  If DeepEval isn't installed, it prints the week 4 message.

- [ ] **Step 1: write the failing tests.**
  - `test_cached_judge_routes_through_model`: a scripted model returning text; `generate("hi")` returns it, and the scripted call holds one user message `"hi"`.
  - `test_geval_case_with_scripted_judge`. Script the two replies G-Eval asks for: steps JSON `{"steps": ["Check ...", "Check ..."]}`, then `{"score": 3, "reason": "..."}`. Assert `0 <= score <= 1`, `steps` has length 2, and the env is restored afterwards.
  - `test_geval_unknown_rubric`.
  - `test_geval_missing_message`.

  If G-Eval asks for a different number of calls or a different JSON shape than scripted, run it, read the prompts, update the script to match, and ledger a ruling naming what you saw.
- [ ] **Step 2: watch them fail.**
- [ ] **Step 3: implement.**
- [ ] **Step 4: watch them pass,** then run the full suite (it should pass).
- [ ] **Step 5: commit** with the message `feat: evally geval (DeepEval G-Eval side by side)`.
- [ ] **Step 6: record two cases** with `--live` on `goes-beyond-policy`: one that our grader fails and one it passes, both from dev. Replay both, then commit the cache with the message `evals: week 5 G-Eval demo`.

### Task 6: Lesson, README, course plan

**Files:**
- Create: `lessons/week05-llm-graders.md`
- Modify: `README.md`, `COURSE_PLAN.md`, `lessons/week04-code-graders.md` (breadcrumb)

- [ ] **Step 1: write the lesson.** Use raggy's style and the week 4 lesson's shape. Sections:
  - **Why code isn't enough.** A dev reply that passes every code check but goes beyond policy, from Task 3's output.
  - **The grader.** Rubric, policy reference, the tool-call verdict with the reason first, and why the grader never sees the case id or the code verdict.
  - **Binary vs 1-5 on dev.** Both tables. Show where the 1-5 scores bunch, how 3 maps to pass or fail, and why pass/fail is easier to check against a person (week 6).
  - **One grader per category vs one big "is it good?" prompt.** Argue it from the per-rubric fail counts. Make no new runs.
  - **Grader vs code check on `uses-outdated-policy`.** Where they agree, and where each one catches what the other misses.
  - **Biases.** Each with its numbers and the command that produced them:
    - position (the self-vs-self control);
    - length (padding);
    - self-preference (both judges).

    Say plainly how few pairs there are.
  - **G-Eval.** Same verdict as ours? What does G-Eval add (generated steps, a 0-1 score)? What does it hide (the prompts and the score scaling)? Name DeepEval 4.3.2.
  - **Cost.** Total tokens and dollars for the week, and the date of the price table.
  - **When an LLM grader misleads.**
  - **In one minute:** 3-4 sentences and one before/after number.
- [ ] **Step 2: update the docs.**
  - README: breadcrumb, cheat sheet rows for `grade`, `pad`, `bias`, `geval`, the `.env` grader lines, the test count, and the weeks table.
  - COURSE_PLAN: week 5 marked done.
  - Week 4 lesson: breadcrumb link to week 5.
- [ ] **Step 3: check every output and command.** Re-run every command quoted in the lesson in replay mode and match its output. Run `uv run pytest` with and without the extra, and update the README's test counts to the real numbers.
- [ ] **Step 4: commit** with the message `docs: week 5 lesson, README, course plan`.
