# evally: a course on evaluating LLM apps, built one week at a time (design)

**Date:** 2026-11-12
**Status:** draft, waiting for approval
**Repo:** `~/claudecode/evally`, next to `raggy` and `harnessy`, to be pushed to the owner's GitHub like raggy

## 1. Intent

The owner has built two courses the same way: harnessy (agent harnesses) and raggy (RAG). evally is the third. It teaches the skill that sits under both: **judging an LLM app with evidence instead of gut feel.**

The outcome, in the owner's words agreed in conversation: hand a learner any LLM app (a RAG bot, an agent) and they can

- say **with numbers** whether it is good,
- show **where** it fails,
- prove whether last week's change made it **better or worse**,
- and make all of that **run automatically**.

The owner also teaches from these courses (the Techie KK channel), so each week must produce clear before/after numbers and one idea strong enough to explain in a one-minute Short.

**Why now:** raggy's week 2 introduced evals for one pipeline. evally makes evaluation the subject itself, general enough for any LLM app.

**Principles over volume (owner's rule, 2026-11-12).** evally teaches the basic principles of evaluation: how evals work for LLMs, how to use them in production, and how to use the existing libraries. It is not a benchmark project. Each concept and each library is shown with **one or two worked test cases** that make the idea clear, and a suite never grows past what the concept needs (roughly 10-20 cases at most). The budget is **minimal**: see section 9a.

## 2. The app under test (decided by the owner)

A **new app built only for this course**: a customer-support assistant for a fictional online bookstore (working name **Bramble Books**; fictional, so the model can't answer from memory).

What it does:

- **Answers policy questions** (returns, shipping, membership, gift cards) from a small set of Markdown policy documents, through simple retrieval.
- **Uses tools** against a local fake store database (SQLite): look up an order, check stock, start a return, escalate to a human.
- **Holds multi-turn conversations** (the customer changes their mind, gives the order number later, gets annoyed).
- **Refuses** what it shouldn't do (other customers' data, refunds beyond policy, off-topic requests).

**Deliberate weaknesses (assistant's call, owner agreed to the playback).** The app ships with planted flaws so learners have real failures to find, for example:

- one policy document is out of date and contradicts the current one,
- a tool sometimes returns an error or an empty result,
- the system prompt is easy to talk out of its rules,
- the retrieval misses questions phrased differently from the documents,
- the app is wordy and sometimes promises things policy doesn't allow.

The flaws are listed in a hidden-from-lessons file (`app/FLAWS.md`, read only by maintainers) so the course can check that its evals actually catch each one. Weekly pattern: **measure a failure → fix it → prove the fix with numbers, and check nothing else got worse.**

The app is deliberately small (a few hundred lines). The course's subject is evaluation, not the app.

## 3. How the course works (same as raggy, decided by the owner)

- **No exercise stubs, no `solutions/` folder.** One finished, working codebase. The learner reads each lesson next to the real code.
- **Each week = working code + a lesson** covering the concept, why it is built this way, trade-offs, what goes wrong without it, and the numbers before and after.
- **Build it by hand first, then use the library (owner's rule).** For every topic that has a popular library, the week first builds the idea from scratch in plain Python, then does the same job with the library and compares the two: same result? What does the library add? What does it hide?
- **Snapshot branches `week-NN` plus matching tags.** Each holds the code as it stood at the end of that week. `main` holds everything. **Snapshot branches are never fast-forwarded, merged or reset to main.** A fix for one week is cherry-picked onto that week's branch only.
- **Tests verify the code; they are not exercises.** `uv run pytest` passes on every week branch, offline, with no API keys. Model calls are faked in tests.
- **Every week has a runnable demo** through the CLI.
- **No fixed number of weeks (owner's rule):** quality of working code and concept tutorials decides the length. The outline in section 7 is the agreed order; the builder may split a heavy week, and reports any change.

## 4. Goals

- A CLI, `evally`, used as `uv run evally <cmd>`:
  - `evally chat`: talk to the bookstore assistant (the system under test).
  - `evally run --suite <name> [--config <app-config>]`: run a test suite, grade every case, save the run as JSON, print a results table.
  - `evally compare <run-a> <run-b>`: what changed, per case and per tag, with confidence ranges.
  - `evally label`: a small terminal tool for a human to label conversations (pass/fail plus a failure category), used for error analysis and for checking the LLM grader.
  - `evally traces`: browse saved conversations and their tool calls.
  - later weeks add `evally simulate` (a simulated customer), `evally redteam`, `evally monitor`.
- A Python package with small, swappable parts: the app (`app/`), datasets, graders (code-based and LLM), runners, statistics, reports.
- **Provider-neutral models, as in raggy:** one small LLM interface with adapters for **Anthropic, OpenAI and Ollama** (local). The app model and the grader model are set separately in config.
- A fake model for tests, so the whole test suite is free and offline.
- A lesson per week plus concept guides in `docs/`, with Mermaid diagrams and raggy's navigation style (breadcrumbs, course-plan table, README with a cheat sheet).
- **Each lesson ends with "In one minute":** the week's single idea in 3-4 sentences plus the before/after number, ready to become a Short.

## 5. Non-goals

- No web UI of our own. The CLI is the interface. (A library's own dashboard, such as the tracing tool in week 13, is fine.)
- No agent or RAG framework inside the app (no LangChain, LlamaIndex). The app is plain Python plus provider SDKs, so learners can see everything it does.
- No building a general eval product. evally's eval code is teaching code: clear first, reusable second.
- No model fine-tuning, no training of grader models.
- No cloud deployment and no multi-user setup.

## 6. Anti-goals: it fails even if it "works" when...

- A claim of improvement isn't backed by a real run. (With tiny suites, lessons say plainly that the numbers illustrate the method and are too small to prove much. Week 7 uses that very point to teach why sample size matters.)
- An LLM grader is trusted without being checked against labels (week 6 onward). The labels in this repo are **written by the course author (an AI assistant) and marked as such**; lessons explain that real teams use human labels and show where to put them.
- A concept is buried under volume: a lesson needs many cases or a big run to make its point, where one or two would do.
- The test set leaks into the fixes. Prompts are tuned against a **dev set** and the headline numbers come from a **held-out test set** the fixes never saw.
- Lessons quote code or output that doesn't match the week's branch, or library code written from memory against an old API. Every quoted output is copied from a real run, and library versions are named. (This failure is in the owner's observation log from an earlier tutorial.)
- A week's branch doesn't run or its tests fail.
- The "by hand" and "library" versions of a topic disagree and the lesson doesn't explain why.
- Lessons explain *what* a metric is but not *when it misleads*.

## 7. Course outline (order agreed by the owner)

Each week: the idea, what gets built (by hand → library), and what gets measured on the bookstore app.

| Week | Idea | Built | Measured by |
| --- | --- | --- | --- |
| **1. Baseline: the app and the vibe check** | Checking "by feel" lies. | The bookstore assistant (docs, retrieval, tools, fake DB, multi-turn chat); LLM adapters; `evally chat`; about 10 hand-written test cases in JSONL; the first runner with simple checks; run results saved as JSON | First baseline; an example where good-looking chats hide a failure the test cases catch |
| **2. Error analysis** | You can't pick metrics until you know how it fails. | Save full traces; `evally label`; read about 15-20 conversations (labelled by the course author, marked as such), write free notes, then group them into a failure taxonomy; count failures per category | A ranked list of failure categories. Later weeks are aimed at the top ones |
| **3. Test datasets** | The eval is only as good as its cases. | Dataset format with tags (topic, difficulty, failure category); hand-written, LLM-generated (with dimensions to vary, then reviewed by the author) and adversarial cases; dev/test split; dataset versions | Coverage per tag; how many generated cases survive review |
| **4. Code-based graders** | Check with code whatever code can check. | Exact/contains/regex checks, JSON shape, right tool + right arguments, refusal detection, length limits → then the same in **DeepEval** | Pass rates per check; cases where a simple check is enough and an LLM would be waste |
| **5. LLM as a grader** | For what code can't check, use a model, carefully. | Rubric-based grader with structured output (score + reason); binary pass/fail vs 1-5 scales; one grader per failure category; showing the biases (position, length, self-preference) → then **DeepEval G-Eval** | Grader scores on the dev set; a bias demo with numbers |
| **6. Testing the grader** | A grader is a model too: measure it. | Labels via `evally label` (about 15-20, written by the course author and marked as such); agreement (accuracy, Cohen's kappa, precision/recall of "fail"); tune the rubric until it agrees; keep a labelled set to re-check the grader whenever its prompt or model changes | Agreement with the labels before and after rubric tuning |
| **7. Statistics** | Is that 3% gain real? | Bootstrap confidence ranges; paired comparison of two runs on the same cases; how many cases you need; repeat runs to see randomness; pass@k and pass^k (passes every time) | `evally compare` now shows ranges; an example "improvement" that turns out to be noise |
| **8. Side-by-side comparison** | Sometimes "which is better" beats "how good". | Pairwise grader A vs B with order swapped to cancel position bias; win/tie/loss rates; Elo/Bradley-Terry ranking of several app versions | Ranking of prompt or model versions, with ranges |
| **9. RAG checks** | Retrieval and answering fail separately. | Retrieval metrics (recall@k, MRR) against labelled source docs; faithfulness (claims supported by the docs), answer relevance, context precision → then **Ragas** | Finding and fixing the stale-document and missed-phrasing flaws, with before/after numbers |
| **10. Agent and multi-turn checks** | An agent can get the answer right by the wrong path. | Tool-choice and argument accuracy; full-trajectory checks; task completion; a **simulated customer** (an LLM playing a persona with a goal) for whole conversations; `evally simulate` | Task success rate across personas; the flaky-tool flaw caught and fixed |
| **11. Safety checks** | Refusing too little is a risk; refusing too much is a broken product. | Prompt injection (including through a policy doc), other-customer data leaks, out-of-policy promises, over-refusal on normal requests; `evally redteam` → then **promptfoo** red-team and/or **DeepEval** red-teaming (builder picks what works best at build time) | Attack success rate vs over-refusal rate, before and after hardening |
| **12. Automatic checks on every change** | Evals only help if they run without anyone remembering. | Fast smoke suite vs full suite; pass marks per metric and "no regression beyond the range"; caching grader calls by input hash; cost per run; **promptfoo** config + **GitHub Actions** workflow that fails a pull request on regression | A demo PR that's blocked by the eval, then fixed |
| **13. Production monitoring** | Tests cover what you imagined; users find the rest. | Tracing every call (by hand as JSONL, then a tracing tool: **Langfuse** or **Arize Phoenix**, whichever runs locally with less setup at build time); grading a sample of live traffic; user thumbs up/down; drift alerts; feeding real failures back into the dataset | A simulated week of traffic with one new failure discovered and turned into test cases |
| **14. Cost and speed** | The best model isn't always the right model. | Measure quality, cost and latency together for several app models; quality-per-dollar; latency percentiles; choosing with all three | A model-choice table with the trade-offs shown |
| **15. Capstone** | Eval-driven development, end to end. | Take the app from baseline to its best version using everything above; held-out test set as final judge | One report: every week's numbers in one table, plus which planted flaws were caught by which eval |

## 8. Repo layout (target)

```
evally/
  README.md                  # what it is, quick start, cheat sheet
  COURSE_PLAN.md             # week table, branches, setup
  pyproject.toml / uv.lock
  .env.example
  evally/
    cli.py
    config.py
    llm/                     # adapters: anthropic, openai, ollama, fake
    app/                     # the bookstore assistant (system under test)
      docs/                  # policy documents (incl. the stale one)
      store.py               # fake SQLite store + seed data
      tools.py
      assistant.py
      FLAWS.md               # maintainer-only list of planted flaws
    datasets/                # loading, tagging, splits, generation
    graders/                 # code checks, LLM grader, pairwise
    runner.py
    stats.py
    labeling.py
    simulate.py              # simulated customer (wk 10)
    redteam.py               # (wk 11)
    tracing.py / monitor.py  # (wk 13)
    report.py
  lessons/week01-*.md …
  docs/                      # concept guides (grader biases, kappa, bootstrap, …)
  evals/                     # suites (dev/test), author labels, recorded runs (cache)
  ci/                        # promptfoo config, GitHub Actions workflow (wk 12)
  tests/
```

## 9. Constraints

- Python 3.11+, `uv`, pytest, matching raggy. promptfoo is a Node tool, run with `npx` at a pinned version; it is optional, so the Python course still works without Node.
- Runs on the owner's Apple Silicon Mac with no GPU.
- Tests are offline and fast. API calls happen only in demos and eval runs.
- API keys come from `.env`, never the shell rc file (non-interactive runs don't read it).
- Every library is checked against its **current release at build time**, pinned in `uv.lock`, and its version named in the lesson that introduces it.
- Eval runs cost money; every run prints its token cost, and grader results are cached so re-runs are cheap.

## 9a. Budget (owner's rule: minimal)

- **Recorded runs are committed.** Every model response the lessons rely on (app answers, grader verdicts) is saved in a cache file in the repo, keyed by a hash of the input. A learner can run every lesson's demo with **no API key and no spend**, by replaying the cache. Live calls are opt-in (`--live`).
- **Building the course uses few live calls:** small suites, one or two cases per concept, the cheapest model that shows the point, and a local Ollama model wherever it is good enough. The stronger hosted grader is used only where grader quality is the lesson.
- Library demos (DeepEval, Ragas, promptfoo, Langfuse/Phoenix) run on one or two cases each.
- Target total spend for the build: **a few dollars**. If any week looks like it needs more, the builder shrinks the demo first and reports it.
- Small, reviewable commits, one week at a time; each week branch cut when the week is finished.

## 10. Decisions made by the assistant (owner can override)

- Name **evally**; fictional store **Bramble Books**.
- Planted flaws, tracked in a maintainer-only file.
- Default models: the app runs on a small, cheap model (local Ollama or a small hosted model) so it has visible failures. The grader uses a stronger hosted model only where grader quality is the lesson; elsewhere the cheapest model that works. Exact model ids chosen at build time from current releases.
- Dev/test split from week 3, with headline numbers from the held-out test set.
- Grading uses mostly **binary pass/fail per failure category**, with 1-5 scales shown as the comparison, because pass/fail is easier to check against humans.
- Error analysis in week 2, before any metric.
- Tracing tool in week 13 is Langfuse or Phoenix, chosen at build time by which runs locally with least setup.
- Each lesson ends with an "In one minute" section for Shorts.
- `FLAWS.md` can't be truly hidden in a public repo: it is labelled as a spoiler file, and only the capstone lesson links to it.
- The GitHub Actions workflow (week 12) runs offline against cached grader results by default, and makes live model calls only when an API-key secret is set, so forks don't fail.
- If Ollama isn't installed, the app falls back to a small hosted model; the README says which.

## 11. Left to the builder

- Library versions and exact APIs (DeepEval, Ragas, promptfoo, Langfuse/Phoenix), confirmed against current docs.
- The retrieval method inside the app (simple BM25 or local embeddings; it must be simple and fast).
- Sizes: number of policy docs (about 8-12), orders in the fake DB (a dozen or so), cases per suite (as few as the concept needs, never more than about 20).
- Prompt wording, rubric wording, pass marks. These are set from data, not guessed.
- Whether any week should split in two.
