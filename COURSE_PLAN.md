# evally: course plan

**[← Repository Home](README.md)** · **[Week 1: Baseline](lessons/week01-baseline.md)**

---

evally teaches one skill: **judging an LLM app with evidence instead of gut feel.** Hand a learner any LLM app (a RAG bot, an agent) and by the end they can say with numbers whether it's good, show where it fails, prove whether last week's change made it better or worse, and make all of that run automatically.

The whole course evaluates one small app, the **Bramble Books** support assistant: policy answers from Markdown docs, tools against a fake store, multi-turn chats, and planted flaws for the evals to find.

## How this course works

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
| **2** | Error analysis | Full traces; `evally label`; read 15-20 conversations, group failures into a taxonomy, count them | coming |
| **3** | Test datasets | Tags, hand-written, generated and adversarial cases; dev/test split; dataset versions | coming |
| **4** | Code-based graders | Regex, JSON shape, tool + argument checks, refusal detection → then **DeepEval** | coming |
| **5** | LLM as a grader | Rubric grader with structured output; pass/fail vs 1-5; grader biases → then **DeepEval G-Eval** | coming |
| **6** | Testing the grader | Labels; accuracy, Cohen's kappa, precision/recall of "fail"; rubric tuning | coming |
| **7** | Statistics | Bootstrap ranges; paired comparison; sample size; repeat runs; pass@k and pass^k; `evally compare` | coming |
| **8** | Side-by-side comparison | Pairwise grading with order swapped; win/tie/loss; Elo/Bradley-Terry | coming |
| **9** | RAG checks | Recall@k, MRR, faithfulness, answer relevance, context precision → then **Ragas** | coming |
| **10** | Agent and multi-turn checks | Tool and argument accuracy; trajectory checks; a simulated customer; `evally simulate` | coming |
| **11** | Safety checks | Prompt injection, data leaks, out-of-policy promises, over-refusal; `evally redteam` → then **promptfoo** / **DeepEval** red-teaming | coming |
| **12** | Automatic checks on every change | Smoke vs full suite; pass marks; regression gates; **promptfoo** + **GitHub Actions** | coming |
| **13** | Production monitoring | Tracing (by hand, then **Langfuse** or **Phoenix**); grading live samples; feedback; drift | coming |
| **14** | Cost and speed | Quality, cost and latency together; quality per dollar; latency percentiles | coming |
| **15** | Capstone | Baseline to best version with everything above; held-out test set as final judge | coming |

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
