# evally: course plan

**[← Repository Home](README.md)** · **[Week 1: Baseline](lessons/week01-baseline.md)** · **[Week 2: Error analysis](lessons/week02-error-analysis.md)** · **[Week 5: LLM as a grader](lessons/week05-llm-graders.md)**

---

evally teaches one skill: **judging an LLM app with evidence instead of gut feel.** Hand a learner any LLM app (a RAG bot, an agent) and by the end they can say with numbers whether it's good, show where it fails, prove whether last week's change made it better or worse, and make all of that run automatically.

The whole course evaluates one small app, the **Bramble Books** support assistant: policy answers from Markdown docs, tools against a fake store, multi-turn chats, and planted flaws for the evals to find.

## How this course works

- **Weeks 1-5 are code; weeks 6-15 are concept tutorials.** From week 6 on, each topic is an in-depth concept page in `concepts/` on `main` (diagrams, worked examples, interactive demos, videos) instead of new code. The app and the week 1-5 tooling stay as the running example.
- **The code is already written.** No exercise stubs, no `solutions/` folder. Each week adds working code and a lesson that explains the idea, why it's built this way, the trade-offs, what goes wrong without it, and the numbers before and after.
- **By hand first, then the library.** Where a popular library exists (DeepEval, Ragas, promptfoo, Langfuse or Phoenix), the week builds the idea in plain Python first, then does the same job with the library and compares the two.
- **Principles over volume.** Each concept is shown with one or two worked cases. Suites stay small (about 10-20 cases), and lessons say plainly when numbers are too small to prove much.
- **Every week is a branch.** `git checkout week-03` gives you the code exactly as it stood after week 3. `main` holds everything. Matching tags `week-NN` exist too. Week branches are snapshots: they're never fast-forwarded, merged or reset; a fix for one week is cherry-picked onto that week only.
- **Tests run offline.** `uv run pytest` passes on every branch with no API keys. Model calls are faked in tests.
- **Free to follow.** Every model reply a lesson relies on is recorded in `evals/cache/` and committed, so demos replay with no key and no spend. Live calls are opt-in with `--live`.

For each week: check out its branch, read the lesson with the code open beside it, run the commands, then do the exercises and write notes in `NOTES.md`.

## The weeks

| Week | Idea | Builds | Status |
| :---: | --- | --- | --- |
| **1** | [Baseline: the app and the vibe check](lessons/week01-baseline.md) | The bookstore assistant (docs, BM25 retrieval, tools, SQLite store, tool loop with trace); Ollama, OpenAI and Anthropic adapters; record/replay cache; 10 JSONL cases with five code checks; `evally chat` and `evally run`. Baseline 9/10 on local `qwen3.5:4b` | ✅ `week-01` |
| **2** | [Error analysis](lessons/week02-error-analysis.md) | Full traces in every run; `evally traces`; `evally label` with notes, categories and a ranked report; 18 realistic conversations read and labelled (by the course author, marked as such). 10 of 18 fail, across six categories; week 1's checks partly cover two | ✅ `week-02` |
| **3** | [Test datasets](lessons/week03-test-datasets.md) | Dimension tags validated at load; `evally generate` and `evally review`; `evally dataset build` (hash-based, category-stratified dev/test split, lock file) and `dataset stats`; `run --by`. `bramble-v1`: 26 cases from four sources, 16 dev / 10 test. 4 of 7 generated messages kept (57%); coverage finds no preorders case and no privacy case in test. Dev 11/16, test 4/10 | ✅ `week-03` |
| **4** | [Code-based graders](lessons/week04-code-graders.md) | Regex, tool-argument (exact, shape, grounded) and refusal checks, validated at load; `run --by check`; `evally refusals`; `bramble-v2` (same cases, better checks, no model calls): dev 11/16 → 10/16 as a check catches an **invented order id** in a tool call, test 4/10 → 5/10 from a fixed check; refusal phrase list finds 3 of 7 refusals; then **DeepEval 4.3.2** side by side (fullmatch regex, whole-argument tool check, 0.5 default passes a wrong email) | ✅ `week-04` |
| **5** | [LLM as a grader](lessons/week05-llm-graders.md) · [concept](concepts/05-llm-as-a-grader.md) | Three rubrics and a pass/fail grader by tool call (reason first, never sees the case id); `evally grade` (binary and 1-5), `pad`, `bias`, `geval`; cost per command. On dev the grader catches a hinted exception no code check can, and misses a silent "60 days" a code check catches; 1-5 uses only 1s and 5s. Bias demos with the order swapped: padding never loses (6-0), qwen prefers its own replies 10-0, a llama judge picks the second reply 19/27; then **DeepEval 4.3.2 G-Eval** agrees on two cases at 8-18x the output tokens | ✅ `week-05` |
| **6** | [Testing the grader](concepts/06-testing-the-grader.md) | Labels; accuracy, Cohen's kappa, precision/recall of "fail"; rubric tuning | ✅ concept page |
| **7** | [Statistics](concepts/07-statistics-for-evals.md) | Bootstrap ranges; paired comparison; sample size; repeat runs; pass@k and pass^k; `evally compare` | ✅ concept page |
| **8** | [Side-by-side comparison](concepts/08-side-by-side.md) | Pairwise grading with order swapped; win/tie/loss; Elo/Bradley-Terry | ✅ concept page |
| **9** | [RAG checks](concepts/09-rag-checks.md) | Recall@k, MRR, faithfulness, answer relevance, context precision → then **Ragas** | ✅ concept page |
| **10** | [Agent and multi-turn checks](concepts/10-agent-checks.md) | Tool and argument accuracy; trajectory checks; a simulated customer; `evally simulate` | ✅ concept page |
| **11** | [Safety checks](concepts/11-safety-checks.md) | Prompt injection, data leaks, out-of-policy promises, over-refusal; `evally redteam` → then **promptfoo** / **DeepEval** red-teaming | ✅ concept page |
| **12** | [Automatic checks on every change](concepts/12-ci-gates.md) | Smoke vs full suite; pass marks; regression gates; **promptfoo** + **GitHub Actions** | ✅ concept page |
| **13** | Production monitoring | Tracing (by hand, then **Langfuse** or **Phoenix**); grading live samples; feedback; drift | concepts (coming) |
| **14** | Cost and speed | Quality, cost and latency together; quality per dollar; latency percentiles | concepts (coming) |
| **15** | Capstone | Baseline to best version with everything above; held-out test set as final judge | concepts (coming) |

The order is fixed; a heavy week may split in two.

## Setup

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone <this repo> && cd evally
uv sync
uv run pytest                          # offline, no keys
uv run evally run --suite week01       # replays the recorded baseline, free
```

To call a model yourself (optional):

- **Local and free:** install [Ollama](https://ollama.com), then `ollama pull qwen3.5:4b`. This is the default.
- **Hosted:** copy `.env.example` to `.env`, set `EVALLY_PROVIDER` to `openai` or `anthropic`, a model id in `EVALLY_MODEL`, and the matching API key. Keys are read from `.env` only.

Then add `--live` to `evally run`, or use `evally chat`.
