# evally

**[Course Plan](COURSE_PLAN.md)** · **[Week 1: Baseline](lessons/week01-baseline.md)** · **[Week 2: Error analysis](lessons/week02-error-analysis.md)** · **[Week 3: Test datasets](lessons/week03-test-datasets.md)** · **[Week 4: Code-based graders](lessons/week04-code-graders.md)** · **[Week 5: LLM as a grader](lessons/week05-llm-graders.md)**

---

**evally** is a course on evaluating LLM apps, built one week at a time. It teaches the skill that sits under every LLM project: **judging an app with evidence instead of gut feel.** Can you say with numbers whether it's good? Show where it fails? Prove whether last week's change made it better or worse? Make all of that run on its own?

The course evaluates one small app all the way through: a support assistant for **Bramble Books**, a fictional online bookstore. It answers policy questions from Markdown docs, uses tools against a fake store (look up an order, check stock, start a return, hand over to a human), holds multi-turn chats, and ships with **planted flaws** for the evals to find.

It's a course you **read and run**, not one you fill in. Each week adds working code and a lesson with numbers from real runs, and each week is kept on its own branch.

No agent or RAG framework: plain Python plus the official model SDKs, so everything the app does is code you can read.

## Quick start

```bash
uv sync
uv run pytest                          # 208 tests (220 with the deepeval extra), offline, no keys
uv run evally run --suite week01       # replay the recorded baseline: no key, no cost
```

```
suite week01 · model qwen3.5:4b

  return-window         PASS
  ...
  short-answer          FAIL   max_words 60 (61 words)

passed 9/10 cases, 16/17 checks
```

Every model reply the lessons use is recorded in `evals/cache/` and committed, so the demos replay for free. To call a model yourself, install [Ollama](https://ollama.com) and `ollama pull qwen3.5:4b` (the default), then add `--live`. For a hosted model, copy `.env.example` to `.env` and set the provider, model and key.

## Cheat sheet

Check types for a case's `checks`: `contains`, `not_contains`, `regex`, `not_regex`, `tool_called`, `tool_not_called`, `tool_args`, `args_shape`, `args_grounded`, `refuses`, `not_refuses`, `max_words`. See [week 4](lessons/week04-code-graders.md) for what each one passes.

| Command | What it does |
| --- | --- |
| `uv run evally run --suite week01` | run a suite by replaying recordings; prints the table, saves `evals/runs/<suite>-<model>.json` |
| `uv run evally run --suite week01 --live` | call the model, record anything new, then grade |
| `uv run evally run --suite path/to/cases.jsonl` | run any suite file |
| `uv run evally chat` | talk to the assistant (live); shows the docs retrieved and tools called each turn |
| `uv run evally traces <run>` | list a saved run's conversations; add `--case ID` to read one in full (docs, tool calls, results, replies) |
| `uv run evally label <run> --labeler NAME` | label each conversation pass/fail with a note; resumes where you stopped |
| `uv run evally label <run> --code` | put each fail note in a category (reuse by number or name a new one) |
| `uv run evally label <run> --report` | fails per category, most first |
| `uv run evally generate --dims F --n N --seed S --out F --live` | ask the model for one customer message per sampled combination of dimensions; `--skip-unrecorded` uses only recorded replies |
| `uv run evally review <candidates.jsonl> --reviewer NAME` | keep or drop each generated candidate (a drop needs a reason); `--report` prints the survival rate |
| `uv run evally dataset build` | merge `evals/datasets/bramble.json`'s sources, split dev/test, write the suites and the lock file |
| `uv run evally dataset stats bramble-v1` | coverage per dimension, dev vs test; flags values missing from test |
| `uv run evally run --suite bramble-v2-dev --by category` | pass rates per tag value after the table; `--by check` gives pass rates per check type |
| `uv run evally refusals <run>` | which saved replies the refusal detector flags, and the phrase it matched |
| `uv sync --extra deepeval` | install the optional DeepEval extra (week 4) |
| `uv run evally deepeval <run> --suite S --case ID` | run a recorded case's checks in DeepEval too, side by side |
| `uv run evally grade <run>` | grade every reply against every rubric in `evals/rubrics/` (pass/fail with a reason); `--scale 1-5` for scores, `--rubric NAME`, `--case ID` to look at one case without saving |
| `uv run evally pad <run>` | copy a run with one sentence of filler added to every reply (for the length-bias demo) |
| `uv run evally bias <run-a> <run-b>` | which reply is better, asked twice with the order swapped; prints consistency and position counts |
| `uv run evally geval <run> --rubric NAME --case ID` | the same rubric through DeepEval's G-Eval, side by side with our grader |
| `--grader-provider P --grader-model M` | override the grader's model (`EVALLY_GRADER_PROVIDER`, `EVALLY_GRADER_MODEL` in `.env`) for one command |
| `--provider ollama\|openai\|anthropic --model <id>` | override `.env` for one command |
| `uv run pytest` | the offline test suite |

| Where | What |
| --- | --- |
| `evally/app/` | the app under test: policies, BM25 retrieval, store, tools, the tool loop |
| `evally/llm/` | one `Model` interface; Ollama/OpenAI, Anthropic and fake adapters; record/replay cache |
| `evally/evals_core/` | cases, checks, runner, run report |
| `evally/graders/` | the refusal detector; the LLM grader and rubrics; pairwise bias tests; the DeepEval side-by-sides |
| `evals/rubrics/` | one Markdown rubric per failure category the LLM grader checks |
| `evally/datasets/` | dimensions, generation, review, dataset build, coverage |
| `evals/suites/` | test cases (JSONL) |
| `evals/traffic/` | unchecked conversations standing in for real traffic |
| `evals/labels/` | labels: verdict, note, category, labeller |
| `evals/cache/`, `evals/runs/` | recorded model replies and saved run results |
| `lessons/` | one lesson per week |

## Weeks

See [COURSE_PLAN.md](COURSE_PLAN.md) for all 15. Done so far:

| Week | Lesson | Branch |
| :---: | --- | --- |
| 1 | [Baseline: the app and the vibe check](lessons/week01-baseline.md) | `week-01` |
| 2 | [Error analysis](lessons/week02-error-analysis.md) | `week-02` |
| 3 | [Test datasets](lessons/week03-test-datasets.md) | `week-03` |
| 4 | [Code-based graders](lessons/week04-code-graders.md) | `week-04` |
| 5 | [LLM as a grader](lessons/week05-llm-graders.md) | `week-05` |
