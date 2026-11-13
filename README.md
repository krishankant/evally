# evally

**[Course Plan](COURSE_PLAN.md)** · **[Week 1: Baseline](lessons/week01-baseline.md)** · **[Week 2: Error analysis](lessons/week02-error-analysis.md)**

---

**evally** is a course on evaluating LLM apps, built one week at a time. It teaches the skill that sits under every LLM project: **judging an app with evidence instead of gut feel.** Can you say with numbers whether it's good? Show where it fails? Prove whether last week's change made it better or worse? Make all of that run on its own?

The course evaluates one small app all the way through: a support assistant for **Bramble Books**, a fictional online bookstore. It answers policy questions from Markdown docs, uses tools against a fake store (look up an order, check stock, start a return, hand over to a human), holds multi-turn chats, and ships with **planted flaws** for the evals to find.

It's a course you **read and run**, not one you fill in. Each week adds working code and a lesson with numbers from real runs, and each week is kept on its own branch.

No agent or RAG framework: plain Python plus the official model SDKs, so everything the app does is code you can read.

## Quick start

```bash
uv sync
uv run pytest                          # 85 tests, offline, no keys
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
| `--provider ollama\|openai\|anthropic --model <id>` | override `.env` for one command |
| `uv run pytest` | the offline test suite |

| Where | What |
| --- | --- |
| `evally/app/` | the app under test: policies, BM25 retrieval, store, tools, the tool loop |
| `evally/llm/` | one `Model` interface; Ollama/OpenAI, Anthropic and fake adapters; record/replay cache |
| `evally/evals_core/` | cases, checks, runner, run report |
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
