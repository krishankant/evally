# Concept pages 05, 07-15 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write the remaining ten concept pages in the format the author approved on page 06, and publish each as it's finished.

**Architecture:** One Markdown page per topic in `concepts/`, built into the existing MkDocs site. Demos are plain HTML plus a small JS module whose maths is checked by a Node script under `tests/demos/`, run by `tests/test_demos.py`.

**Tech Stack:** Markdown + Mermaid, SVG, plain HTML/JS, Node for demo checks; library snippets run in throwaway envs (`uv run --no-project --with <pkg>==<ver>`).

**Spec:** `docs/superpowers/specs/2026-11-16-evally-concepts-site-design.md`; template reference: `concepts/06-testing-the-grader.md` (approved pilot).

## Global Constraints

- Everything in the previous plan's Global Constraints (`docs/superpowers/plans/2026-11-16-concepts-site.md`) still applies.
- Page shape = page 06: nav line; idea paragraph; why it matters; picture (Mermaid, `flowchart TB` for anything with more than four nodes); numbered deep sections with hand-worked maths; infographic (SVG, internal light/dark `<style>`, ≤ 60 KB, wrapped in a link to itself); demo (iframe `class="demo"` + live-site link) where listed; `> **Pitfall:**` blockquotes; library section with version and real output; Watch table; 5-question `<details>` self-check; "In one minute".
- Every number is either real (from `evals/` with the command that shows it) or labelled *illustrative*. No claim about the project's data without the command that shows it (observation 0015).
- A randomised demo (bootstrap, simulators) gets a check of its *spread*, not just one seeded value (observation 0032).
- A library that needs an LLM to run gets its snippet run only if it can run on the local Ollama model in a few minutes; otherwise the page uses that library's non-LLM part for the runnable snippet and shows the LLM part as config, labelled "not run here".
- Each page: its own branch `dev/concepts-NN` from `main`, strict build green, `uv run pytest -q` green, fast-forward to `main`, push.

## Review Focus

1. **A demo at an edge input** (n = 0, all ties, k > n, empty ranking) shows a readable message, never `NaN`/`Infinity`. → each demo's check script has an edge case.
2. **Phone width**: no page-level horizontal scroll; demo frames fit (the auto-fit code from `kappa.html`). → one 390 px check per page that has a demo.
3. **Cross-page consistency**: a term defined on one page (pass rate, kappa, bootstrap range, win rate) means the same thing on every page that uses it. → each page links back to where a term is defined instead of redefining it differently.
4. **Formulas written by hand vs the library's output**: the worked example and the library snippet use the same numbers and agree. → each library step compares its output with the hand-worked numbers.
5. **Dead references**: every link 200s, every video passes oEmbed. → link check step on every page.

---

Every task has the same steps; the table under each task gives what's specific to it.

- [ ] **Step 1: gather the real numbers** listed for the page and the command that prints each; ledger them.
- [ ] **Step 2: demo check first** (if the page has a demo): write `tests/demos/check-<name>.js` with the listed values and an edge case; run it → FAIL (module missing).
- [ ] **Step 3: demo** `concepts/demos/<name>.js` + `.html` (copy the theme sync and auto-fit blocks from `kappa.html`); run the check → `all checks pass`; add it to `tests/test_demos.py`.
- [ ] **Step 4: library snippet** run in a scratch env; paste the real output; note the version.
- [ ] **Step 5: write the page** and the SVG; add nav entry, `concepts/README.md` link, `COURSE_PLAN.md` row link + "✅ concept page"; link the previous page's "Next" to it.
- [ ] **Step 6: references**: find 2-3 videos, oEmbed 200 + description read; all page links 200.
- [ ] **Step 7: verify**: `mkdocs build` strict green; `uv run pytest -q` green; `grep -nE '^(!!!|===) '` empty; for demo pages, 390 px overflow check.
- [ ] **Step 8: commit** `docs: concept NN, <title>`; fast-forward `main`; push.

### Task 1: 05 · LLM as a grader

| | |
| --- | --- |
| File | `concepts/05-llm-as-a-grader.md`, `img/05-grader-anatomy.svg`, demo `position-bias` |
| Must carry | the concept behind week 5's code: pointwise vs pairwise vs reference-based judges; rubric anatomy; structured output; reason-first; binary vs scales (with week 5's 1s-and-5s finding); one grader per failure category; biases (position, length/verbosity, self-preference, plus authority/sycophancy as a named risk); mitigations (swap and count only consistent pairs, length-matched comparisons, judge from another model family, a control); cost; G-Eval in brief; links to the week 5 lesson for the code |
| Real numbers | week 5 lesson's: fails 1/1/0 of 16; 1-5 all 1s and 5s; padding 6-0, picked first 13/30; qwen 10-0; llama second 19/27; G-Eval 4,315/9,098 output tokens vs ~500 |
| Demo | `position-bias.js`: a simulated judge that picks the first reply with probability `b` when the two replies are equally good; runs `n` swapped pairs and reports consistent/inconsistent counts and the share "picked first". Check: with seed 1, `b=0.5, n=15` is deterministic; across 2,000 seeds, mean picked-first share for `b=0.7` is within 0.68-0.72 (spread check); `n=0` → message, not NaN |
| Library | DeepEval 4.3.2 `GEval` construction (runs only with an LLM): show as config, **not run here**; the runnable snippet is evally's own `uv run evally geval ...` replay output (already real) |

### Task 2: 07 · Statistics for evals

| | |
| --- | --- |
| File | `concepts/07-statistics-for-evals.md`, `img/07-ranges.svg`, demos `bootstrap`, `sample-size` |
| Must carry | a pass rate is an estimate; standard error of a proportion; Wilson interval (why not ±1.96·SE near 0 or 1); bootstrap by hand (resample cases, recompute, take percentiles); paired comparisons (same cases, two versions: count the cases that flipped; McNemar's exact test); sample size for a target margin; repeat runs and nondeterminism (temperature, run the same case k times); pass@k vs pass^k with the unbiased pass@k estimator `1 − C(n−c,k)/C(n,k)`; multiple comparisons in brief |
| Real numbers | bramble-v2 dev qwen 10/16 (`uv run evally run --suite bramble-v2-dev`) and llama 13/16; week 4 dev 11/16 → 10/16; their Wilson intervals and the McNemar result for qwen vs llama on the same 16 cases |
| Demos | `bootstrap.js`: resample a list of 0/1 outcomes, return the percentile interval; check: seeded result deterministic; over 500 seeds the 95% interval for 10/16 covers 0.625 in ≥ 99% of runs and its mean width is within ±0.05 of the Wilson width (spread check); empty list → message. `sample-size.js`: `nFor(margin, p=0.5, z=1.96)` → `nFor(0.05)=385`, `nFor(0.1)=97`; margin ≤ 0 → null |
| Library | `scipy.stats.binomtest(10, 16).proportion_ci(method="wilson")`, `scipy.stats.bootstrap`, McNemar via `binomtest` on the discordant pairs; version pinned |

### Task 3: 08 · Side-by-side comparison

| | |
| --- | --- |
| File | `concepts/08-side-by-side.md`, `img/08-pairwise.svg`, demo `elo` |
| Must carry | why compare instead of score; the pairwise protocol (swap, tie handling, consistent pairs only); win rate with ties and its range (link page 07); from pairs to a ranking: Elo (update rule, K, why order of games changes the result), Bradley-Terry (probability model, fit by maximum likelihood, order-free), how Chatbot Arena reports; when not to trust a ranking (few comparisons, intransitive preferences, judge bias from page 05) |
| Real numbers | week 5 qwen vs llama pairs (qwen judge 10-0-5 inconsistent; llama judge 2-2) |
| Demo | `elo.js`: `eloUpdate(ra, rb, score, k)`, `runElo(games, k, order)`, `bradleyTerry(games, iters)`. Check: one 1500-vs-1500 win with K=32 → 1516/1484; the same games in two orders give different Elo but identical BT strengths (to 1e-6); a player with no games → message |
| Library | Bradley-Terry fitted with numpy (MM algorithm, ~10 lines) run in a scratch env, compared with the demo's numbers; no extra library |

### Task 4: 09 · RAG checks

| | |
| --- | --- |
| File | `concepts/09-rag-checks.md`, `img/09-rag-metrics.svg`, demo `ranking` |
| Must carry | split the pipeline: retrieval vs generation; retrieval metrics with relevance labels: hit rate, recall@k, precision@k, MRR, nDCG (graded); generation metrics: faithfulness (claim decomposition + support check), answer relevance, context precision/recall (Ragas's definitions); how to build relevance labels; Bramble's planted stale doc `returns-2023.md` as a retrieval failure example (from traces); link raggy's evaluation concepts for deeper RAG |
| Real numbers | from saved traces: for dev cases, which docs were retrieved (e.g. `return-too-late` retrieved `returns.md`, `returns-2023.md`, `shipping.md`); count how often `returns-2023.md` is retrieved in bramble-v2 dev (command recorded) |
| Demo | `ranking.js`: `recallAtK`, `precisionAtK`, `mrr`, `ndcgAtK`. Check: ranking [r, n, r] with 2 relevant → recall@1 0.5, recall@3 1.0, precision@3 0.667, MRR 1.0; graded nDCG on a hand-computed example; no relevant docs → null with message |
| Library | Ragas: runnable snippet uses a non-LLM metric (string/ID-based context precision or recall) if present in the current release; LLM metrics shown as config, not run here; version pinned |

### Task 5: 10 · Agent and multi-turn checks

| | |
| --- | --- |
| File | `concepts/10-agent-checks.md`, `img/10-trajectory.svg`, no demo |
| Must carry | what's different about agents (many steps, side effects); tool selection and argument accuracy (exact, shape, grounded, with week 4's checks); trajectory checks (exact order, in-order subsequence, any-order, superset; when each fits); end-state checks (what changed in the store) vs path checks; step and cost budgets; multi-turn: conversation-level rubrics, simulated customers (persona + goal + stop rule) and their failure modes; grading a whole conversation vs each turn |
| Real numbers | week 4: `gen-fa79bb81` invented order id caught by `args_grounded`; `t-clockmaker-stock` no tool call; `return-too-late` trajectory lookup_order → start_return (error) → escalate_to_human (from its trace) |
| Library | DeepEval 4.3.2 `ToolCorrectnessMetric` (no LLM needed) run on `return-too-late`'s real tool calls vs an expected list; real output pasted |

### Task 6: 11 · Safety checks

| | |
| --- | --- |
| File | `concepts/11-safety-checks.md`, `img/11-attack-surface.svg`, no demo |
| Must carry | the threat list for a support bot: direct prompt injection, indirect injection (text in retrieved docs or tool results), data leaks (other customers' orders, system prompt), out-of-policy promises, harmful content; over-refusal as the opposite failure (measure both); red-teaming process (attack taxonomy, attack success rate, regression set of past attacks); defences briefly and why evals must test them; Bramble cases `other-customer-order`, `adv-third-party-order`, week 4's refusal detector result (3 of 7) |
| Real numbers | the two privacy cases' verdicts in bramble-v2 dev; week 4 refusals figure |
| Library | promptfoo: a red-team or assertion config validated with the CLI at a pinned version (`npx promptfoo@<ver> validate` or the equivalent that exists), not run against a model; DeepEval red-teaming named, not run |

### Task 7: 12 · Evals on every change

| | |
| --- | --- |
| File | `concepts/12-ci-gates.md`, `img/12-ci-pipeline.svg`, no demo |
| Must carry | smoke vs full suites and when each runs; record/replay so CI is free and deterministic (evally's cache as the example); pass marks: absolute thresholds vs "no worse than baseline"; gating on the lower end of a range (page 07); flaky evals and how to tell flakiness from regressions; who can override a gate; a GitHub Actions workflow running evally's replay on a pull request; promptfoo's CI mode as the library version |
| Real numbers | evally's replay runtime and exit behaviour (measure: `time uv run evally run --suite bramble-v2-dev`, `echo $?`) |
| Library | the workflow YAML checked with `actionlint` if available (else ledger and validate by `python -c yaml.safe_load`); promptfoo config validated as in Task 6 |

### Task 8: 13 · Production monitoring

| | |
| --- | --- |
| File | `concepts/13-monitoring.md`, `img/13-monitoring-loop.svg`, no demo |
| Must carry | traces and spans for an LLM app (what to record per step); OpenTelemetry GenAI conventions in brief; sampling live traffic for grading (random + targeted); online graders (cheap code checks on 100%, LLM graders on a sample); user feedback (explicit thumbs, implicit signals) and its biases; drift (inputs, retrieval, outputs, grader scores) and how to detect it; turning production failures into new eval cases (back to week 3); Langfuse and Phoenix as the tools |
| Real numbers | evally's trace format (a real trace excerpt from `return-too-late`) |
| Library | OpenTelemetry Python SDK with the console exporter, emitting one span with GenAI attributes for a Bramble call; run, output pasted; Langfuse/Phoenix described, not run |

### Task 9: 14 · Cost and speed

| | |
| --- | --- |
| File | `concepts/14-cost-and-speed.md`, `img/14-pareto.svg`, demo `pareto` |
| Must carry | cost per call from tokens and prices; cost per *successful* case; latency: time to first token vs total, percentiles (p50/p95/p99) and why averages mislead; quality per dollar; the Pareto front across models/configs; levers (smaller model, caching, shorter prompts, fewer tool calls, routing); the grader's own cost (week 5: G-Eval 8-18× tokens) |
| Real numbers | week 5 token totals; evally's `prices.py` approach; if traces hold timings, real latencies, else illustrative and labelled |
| Demo | `pareto.js`: `paretoFront(points)` on {name, quality, cost, latency}; check: a dominated point is excluded, ties kept, empty list → message; percentiles `percentile([..], 95)` against hand values |
| Library | numpy percentile on an illustrative latency list (linear interpolation), compared with the demo's function |

### Task 10: 15 · Capstone

| | |
| --- | --- |
| File | `concepts/15-capstone.md`, `img/15-whole-loop.svg`, no demo |
| Must carry | the whole loop on Bramble, end to end, as a guided project: baseline → error analysis → dataset → code checks → LLM graders → testing the grader → statistics → comparison → RAG/agent/safety checks → CI gate → monitoring → cost; a decision log template; the held-out test set as the final judge (opened once); a grading checklist for the learner's write-up; links to every page and lesson |
| Real numbers | the course's real milestones: week 1 9/10, week 3 dev 11/16 test 4/10, week 4 dev 10/16 test 5/10, week 5 grader results |
| Library | none |
