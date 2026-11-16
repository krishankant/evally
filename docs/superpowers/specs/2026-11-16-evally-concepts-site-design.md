# evally concepts site: design

Date: 2026-11-16 · Status: draft for approval

## Intent

Weeks 1-5 of evally were built as code: each week added working Python, tests and recorded
runs, and a lesson explained them. That is slow (week 5 took three days, much of it waiting on a
local model on an 8 GB Mac) and the author isn't sure the code pays for itself past week 5.

From week 6 on, the course switches to **concept tutorials**: in-depth explanations with worked
examples, diagrams, infographics, small interactive demos, explainer videos and vetted YouTube
references. They serve two readers at once:

- **the author**, who wants to master LLM evaluation, not just ship pages;
- **the public**, who follow the course on GitHub and, now, on a course website.

Success: a learner who reads a concept page can explain the idea, compute it by hand on a small
example, say when it misleads, and pick a library that does it.

## Goals

1. A `concepts/` folder in the evally repo, one Markdown page per topic, covering the course
   plan's weeks 5-15 (week 5 also keeps its code lesson).
2. A course website built from the repo with **MkDocs Material**, published free on **GitHub
   Pages** by a GitHub Action on every push to `main`.
3. Every page has: diagrams, at least one worked example computed step by step, an infographic,
   pitfalls, a library section, self-check questions with answers, and further watching.
4. Heavy numeric concepts get an **interactive demo** (plain HTML/JS, runs in the browser).
5. One **explainer video** (3-5 min) per page where motion helps; **Shorts** only where one idea
   stands alone in under 60 s.
6. Finish week 5 the usual way: lesson, README, course plan, merge to `main`, `week-05` snapshot.

## Non-goals

- No new evally application code, tests or recorded runs for weeks 6-15.
- No rewrite of the week 1-4 lessons; the site links to them as they are.
- No paid hosting, paid tools or custom domain (one can be added later).

## Anti-goals (a failure even if it ships)

- **Shallow pages**: a glossary dressed up with diagrams. Each page must go deep enough to
  compute the metric by hand and defend a choice.
- **Invented numbers passed off as measured.** Week 1-5 numbers are real and are quoted as such.
  Every other number is labelled *illustrative* where it appears.
- **Broken library code.** A snippet that worked in an older release and fails today (observation
  0015). Every library snippet is run once against the pinned version before it ships, and the
  page states the version.
- **Dead or weak video links.** Every YouTube reference is opened and checked before it is added,
  with one line saying why it is worth the time.
- **A site that drifts from GitHub.** The Markdown in the repo is the single source; the site is
  only a build of it, so a page reads correctly on github.com too.

## Constraints

- Free to run (GitHub Pages, MkDocs Material, Actions on a public repo).
- Week branches are snapshots, never fast-forwarded. The site builds from `main` only.
- Pages must render on github.com (Mermaid works there; MkDocs features degrade gracefully).
- Videos are made with the local HyperFrames CLI/skills, never the hosted HeyGen MCP. Tech
  Shorts use the Bold Pop style.
- Uploading a video to YouTube is outward-facing: each upload is confirmed with the author first.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| A | Markdown pages in the repo only | Simplest, but static: no way to *feel* a bootstrap range or a kappa |
| **B** | **Markdown in the repo, published as a MkDocs Material site with interactive demos** | One hour of setup; best for mastery and a public course; single source |
| C | One claude.ai Artifact per week | Fastest visuals, but outside git, no history, the course's home splits |

**Chosen: B** (by the author, 2026-11-16).

## The pages

Numbering follows raggy's `concepts/` folder (proven format in the author's other course).

| Page | Course week | Core content | Interactive demo | Library section |
|---|---|---|---|---|
| 05 LLM as a grader | 5 | rubrics, structured verdicts, binary vs 1-5, position/length/self-preference bias, cost | position-bias coin-flip simulator | DeepEval G-Eval (real week 5 numbers) |
| 06 Testing the grader | 6 | human labels, confusion matrix, accuracy trap, Cohen's kappa, precision/recall of "fail", rubric tuning loop | kappa lab | scikit-learn metrics |
| 07 Statistics for evals | 7 | sampling error, bootstrap, paired comparison, sample size, repeat runs, pass@k vs pass^k | bootstrap simulator, sample-size calculator | scipy / numpy |
| 08 Side-by-side comparison | 8 | pairwise with swapped order, win/tie/loss, Elo, Bradley-Terry | Elo playground | (by hand) |
| 09 RAG checks | 9 | recall@k, MRR, nDCG, faithfulness, answer relevance, context precision/recall | ranking-metric calculator | Ragas |
| 10 Agent and multi-turn checks | 10 | tool/argument accuracy, trajectory checks, simulated users, end-state checks | (none) | DeepEval agent metrics |
| 11 Safety checks | 11 | prompt injection (direct/indirect), data leaks, out-of-policy promises, over-refusal, red-teaming | (none) | promptfoo / DeepEval red-team |
| 12 Evals on every change | 12 | smoke vs full suite, pass marks, regression gates, flaky evals | (none) | promptfoo + GitHub Actions |
| 13 Production monitoring | 13 | tracing, sampling live traffic for grading, feedback signals, drift | (none) | Langfuse or Phoenix |
| 14 Cost and speed | 14 | quality/cost/latency together, quality per dollar, latency percentiles, Pareto front | Pareto-front picker | (by hand) |
| 15 Capstone | 15 | the whole loop on Bramble, from baseline to best, held-out test as final judge | (none) | all of the above |

A heavy page may split in two (e.g. 07a/07b), as the course plan already allows.

### Page template

Each page follows this shape (raggy's, plus the new media):

1. Nav line: concepts index, previous/next, the matching course week.
2. **The idea in one paragraph**, then **why it matters** with a Bramble example.
3. **The idea in one picture** (Mermaid).
4. Numbered deep sections: definitions, the maths worked by hand on a tiny example, what each
   number means and when it lies.
5. **Infographic** (one SVG per page, light/dark safe) summarising the page.
6. **Interactive demo** (where listed), embedded on the site and linked from GitHub.
7. **Pitfalls** (MkDocs admonitions; plain blockquotes on GitHub).
8. **Library section**: the same job in the library, version pinned, snippet run once.
9. **Watch**: the explainer video (if made) and 2-3 vetted YouTube references.
10. **Self-check**: 5 questions, answers in collapsible blocks.
11. **In one minute**: the summary.

## The site

- `mkdocs.yml` at the repo root; theme Material with dark/light toggle, search, Mermaid
  (`pymdownx.superfences`), admonitions, collapsible details, tabs.
- Navigation: Home (README) · Course plan · Lessons (weeks 1-5) · Concepts (05-15) · Demos.
- Assets: `concepts/img/` for SVG infographics, `concepts/demos/` for demo HTML/JS (no build
  step, no frameworks, no external calls).
- `mkdocs` goes in a `docs` extra in `pyproject.toml` so the app's install is unchanged.
- `.github/workflows/site.yml` builds with `mkdocs build --strict` and deploys to GitHub Pages on
  push to `main`.

## Videos and references

- Explainer: one per page where motion helps (target: 06, 07, 08, 09, 11), 3-5 minutes,
  rendered locally with HyperFrames (`faceless-explainer`), committed only as a YouTube link,
  never as an MP4 in the repo.
- Shorts: only for a one-idea moment (e.g. "position bias in 50 seconds"), Bold Pop style.
- Production order: the page first, the video from the finished page.
- YouTube references: found by web search, each watched-through or skimmed by transcript where
  possible, kept only if accurate and current; listed with channel, length and one line on why.

## Rollout

1. Finish week 5: lesson (code lesson as before), README, course plan; merge to `main`; cut
   `week-05` branch and tag.
2. Site skeleton on `main`: `mkdocs.yml`, workflow, nav, the week 1-5 lessons visible.
3. **Pilot: page 06** with its demo, infographic and references. The author reviews depth and
   format before the rest.
4. Pages 07-15, one commit each, pushed as they finish. The course plan's week rows link to them.
5. Videos after their page, each upload confirmed with the author.

## Decisions made without the author (correct any)

- Pages cover weeks 5-15; weeks 1-4 keep their code lessons and get no concept page.
- Code stops after week 5. The course plan says so in "How this course works".
- Library snippets are verified by a one-off run in a scratch environment, not by repo tests.
- Videos are linked, not hosted in the repo.
- The pilot is page 06 (week 5 already has a full code lesson to compare against).

## Open, for the author

- **Which YouTube channel** hosts the explainer videos and Shorts?

## Left to the builder

- How MkDocs reaches `lessons/` and `concepts/` at the repo root (MkDocs won't take the config's
  own folder as `docs_dir`): a small build step that copies them, or a `docs/` folder with the
  pages moved and GitHub-relative links kept working. Pick one; the GitHub reading experience
  must not break.
- Exact demo UI, infographic layouts, video scripts.
