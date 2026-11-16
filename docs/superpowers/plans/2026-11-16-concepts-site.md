# Concepts site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close week 5, stand up the free MkDocs Material course site on GitHub Pages, and ship
concept page 06 as the pilot the author reviews before pages 05 and 07-15.

**Architecture:** Markdown in the repo stays the single source (`README.md`, `COURSE_PLAN.md`,
`lessons/`, new `concepts/`). A `site/` folder holds only symlinks to them plus `mkdocs.yml`'s
assets; a small MkDocs hook rewrites links that point outside the site to GitHub URLs. A GitHub
Action builds with `--strict` and deploys to Pages from `main`.

**Tech Stack:** MkDocs 1.6 + mkdocs-material 9 (docs extra in `pyproject.toml`), Mermaid via
`pymdownx.superfences`, plain HTML/JS demos, inline-free SVG infographics, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-16-evally-concepts-site-design.md`

## Global Constraints

- Free to run: GitHub Pages, MkDocs Material, Actions on the public repo. No paid tools, no domain.
- Week branches are snapshots, never fast-forwarded; the site builds from `main` only.
- Pages must read correctly on github.com: no MkDocs-only syntax that turns into noise there
  (use `> **Pitfall:**` blockquotes and `<details>` for answers, which render in both).
- Week 1-5 numbers are real and quoted as measured; every other number is labelled *illustrative*
  where it appears.
- Every library snippet is run once against the pinned version in a scratch env before it ships;
  the page names the version.
- Every YouTube reference is checked to exist (oEmbed returns 200) and listed with channel,
  length and one line on why.
- Videos: local HyperFrames only, linked not committed; each upload confirmed with the author.
- No new application code, tests or recorded runs for weeks 6-15.

## Review Focus

1. **A lesson link to a file outside the site** (`../evals/vibe-check.md`, `../evally/cli.py`)
   must open that file on GitHub, not 404 and not fail `--strict`. → Task 2, `test_rewrites_outside_link`.
2. **The same page on github.com** must not show raw MkDocs syntax (`!!! note`, `===` tabs).
   → Task 3 step 5, a grep that fails on `^!!! ` or `^=== ` under `concepts/`.
3. **Dark mode**: Mermaid diagrams and SVG infographics must stay readable on the dark theme.
   → Task 3 step 4 checks the SVG uses `currentColor`/CSS variables, and a screenshot in both themes.
4. **The kappa demo with a degenerate table** (all agree on one label, so chance agreement = 1)
   must show "undefined" rather than `NaN` or `Infinity`. → Task 3, `kappa(…)` check in step 3.
5. **Phone width (390 px)**: demos and tables must not force horizontal page scroll.
   → Task 3 step 4 screenshot at 390 px.

---

### Task 1: Finish week 5 and cut the snapshot

**Files:**
- Create: `lessons/week05-llm-graders.md`
- Modify: `README.md`, `COURSE_PLAN.md`, `lessons/week04-code-graders.md`

**Interfaces:**
- Consumes: the recordings and ledger in `.superpowers/sdd/2026-11-14-week-05-llm-graders/progress.md`
  (bias numbers, G-Eval numbers, rulings); the week 5 plan's Task 6 section list.
- Produces: `main` and `week-05` (branch + tag) containing week 5.

- [ ] **Step 1: write the lesson** exactly to the section list in
  `docs/superpowers/plans/2026-11-14-week-05-llm-graders.md` Task 6 Step 1, with the self-preference
  model named as llama3.2:3b (ruling in the ledger) and the G-Eval token comparison
  (4,315-9,098 output tokens per case vs ours).
- [ ] **Step 2: update the docs** per that plan's Task 6 Step 2. In `COURSE_PLAN.md` also add to
  "How this course works": *From week 6 the course is concept tutorials (see `concepts/`); the code
  stops at week 5.* and mark weeks 6-15 "concepts" instead of "coming".
- [ ] **Step 3: verify.** Re-run every command quoted in the lesson without `--live` and match its
  output; `uv run pytest -q` → `220 passed`; with `--extra deepeval` too. Update README test counts.
- [ ] **Step 4: commit** `docs: week 5 lesson, README, course plan`, push `dev/week-05`.
- [ ] **Step 5: release.** `git checkout main && git merge --ff-only dev/week-05 && git branch week-05 && git tag week-05 && git push origin main week-05 refs/tags/week-05`.
  Chain with `&&` only (observation 0034). Expected: `main` == `week-05` == `dev/week-05` head.

### Task 2: Site skeleton

Branch: `dev/site` from `main` after Task 1.

**Files:**
- Create: `mkdocs.yml`, `site/` (symlinks `README.md`, `COURSE_PLAN.md`, `lessons`, `concepts` → `../…`),
  `site/stylesheets/extra.css`, `site_hooks/links.py`, `tests/test_site_links.py`,
  `.github/workflows/site.yml`, `concepts/README.md` (index stub listing 05-15, linked rows only
  for pages that exist)
- Modify: `pyproject.toml` (extra `docs = ["mkdocs>=1.6,<2", "mkdocs-material>=9.5,<10"]`),
  `.gitignore` (`/_site/`), `README.md` (link to the site)

**Interfaces:**
- Produces: `rewrite_outside_links(markdown: str, page_src: str, repo_url: str) -> str` in
  `site_hooks/links.py`, and `on_page_markdown(markdown, page, config, files)` calling it with
  `repo_url = "https://github.com/krishankant/evally/blob/main/"`. A link is "outside" when its
  resolved path (from `page_src`, a path relative to the repo root) is not under `README.md`,
  `COURSE_PLAN.md`, `lessons/` or `concepts/`. External URLs and `#anchors` are untouched.
- `mkdocs.yml`: `docs_dir: site`, `site_dir: _site`, `strict: true`, theme `material` with palette
  toggle (light/dark), features `navigation.sections`, `navigation.footer`, `search.highlight`,
  `content.code.copy`; markdown_extensions `admonition`, `pymdownx.details`, `tables`, `attr_list`,
  `md_in_html`, `pymdownx.superfences` with the mermaid custom fence; `hooks: [site_hooks/links.py]`;
  `repo_url: https://github.com/krishankant/evally`; nav: Home (README.md) · Course plan · Lessons
  (week01-05) · Concepts (concepts/README.md + pages that exist).

- [ ] **Step 1: write the failing tests** in `tests/test_site_links.py`:
  - `test_rewrites_outside_link`: `rewrite_outside_links("[v](../evals/vibe-check.md)", "lessons/week01-baseline.md", R)` == `"[v](" + R + "evals/vibe-check.md)"`.
  - `test_keeps_inside_link`: `[p](../COURSE_PLAN.md)` from a lesson is unchanged; `[c](../concepts/06-testing-the-grader.md#2-kappa)` unchanged.
  - `test_keeps_external_and_anchor`: `[u](https://ollama.com)` and `[a](#3-why)` unchanged.
  - `test_code_file_link`: `[cli](../evally/cli.py)` → `R + "evally/cli.py"`.
- [ ] **Step 2: run** `uv run pytest tests/test_site_links.py -q` → FAIL (module missing).
- [ ] **Step 3: implement** `site_hooks/links.py` (regex over `](target)`; `posixpath.normpath`
  of `dirname(page_src)/target`). `page.file.src_uri` gives `page_src` because the symlinked
  folders keep repo-relative names.
- [ ] **Step 4: run** the tests → PASS; full suite `uv run pytest -q` → 224 passed.
- [ ] **Step 5: build.** `uv run --extra docs mkdocs build` → exit 0, no warnings (strict). Then
  `uv run --extra docs mkdocs serve`, open `/`, `/lessons/week01-baseline/` and follow the
  vibe-check link → github.com URL. If MkDocs doesn't follow the symlinks, ledger it and switch to a
  `site/` populated by a copy step in the workflow and a `make site` target; same tests.
- [ ] **Step 6: workflow** `.github/workflows/site.yml`: on push to `main` + manual; `astral-sh/setup-uv`,
  `uv run --extra docs mkdocs build`, `actions/upload-pages-artifact` (`_site`),
  `actions/deploy-pages`; permissions `pages: write`, `id-token: write`.
- [ ] **Step 7: commit** `feat: course site (MkDocs Material, GitHub Pages)`; merge `dev/site` into
  `main` (`--ff-only`), push `main`. Enable Pages: `gh api -X POST repos/krishankant/evally/pages -f build_type=workflow`
  (or `PUT` if it exists). Expected: the Action goes green and `https://krishankant.github.io/evally/` serves the home page.

### Task 3: Pilot concept page 06 — Testing the grader

Branch: `dev/concepts-06` from `main`.

**Files:**
- Create: `concepts/06-testing-the-grader.md`, `concepts/img/06-grader-agreement.svg`,
  `concepts/demos/kappa.html`, `concepts/demos/kappa.js`
- Modify: `concepts/README.md` (row 06 linked), `mkdocs.yml` (nav), `COURSE_PLAN.md` (week 6 row links the page)

**Interfaces:**
- Produces in `concepts/demos/kappa.js` (also used by the page's worked example):
  `confusion(human: string[], grader: string[]) -> {tp, fp, fn, tn}` with "fail" as the positive
  class; `kappa({tp, fp, fn, tn}) -> number | null` (null when expected agreement is 1);
  `precisionRecall({tp, fp, fn, tn}) -> {precision: number|null, recall: number|null}`.
  Exported for Node via `if (typeof module !== "undefined") module.exports = {...}`.
- The page template (spec "Page template", 11 parts) is fixed here and reused by every later page.

- [ ] **Step 1: write the page** to the spec's 11-part template. Content it must carry:
  - Why: week 5's qwen grader said 1 of 16 dev replies goes beyond policy (real); is the grader right?
  - Human labels: who labels, a labelling guide, blind to the grader, two labellers for a subset.
  - Confusion matrix with "fail" as positive; accuracy and the **accuracy trap** worked on an
    *illustrative* 20-case table where 18 pass (always-pass grader = 90 % accuracy, kappa 0).
  - Cohen's kappa by hand: p_o, p_e, κ = (p_o − p_e)/(1 − p_e) on a 2×2 example, with the
    Landis-Koch bands and why they're only a convention.
  - Precision/recall of "fail", and which one matters for a regression gate vs a triage queue.
  - Rubric tuning loop (Mermaid): label → grade → disagreements → read → edit rubric → re-grade on
    dev only → test set once at the end; the overfitting risk of tuning on the same labels.
  - How many labels: a short table of κ's confidence range by n (illustrative), pointing to page 07.
  - Library: `sklearn.metrics.cohen_kappa_score`, `precision_recall_fscore_support`, pinned version.
- [ ] **Step 2: verify the library snippet** in a scratch env (`uv run --with scikit-learn==<current> python snippet.py`),
  output pasted into the page matches. Write the version into the page.
- [ ] **Step 3: build the demo** `kappa.html`: a 2×2 table of steppers (0-50 each), live p_o, p_e,
  κ, precision, recall, and a band label; works offline, no libraries. Check with Node:
  `node -e "const k=require('./concepts/demos/kappa.js'); console.log(k.kappa({tp:4,fp:2,fn:1,tn:13}), k.kappa({tp:0,fp:0,fn:0,tn:20}))"`
  → the page's worked-example value, then `null`; the page shows "undefined (everyone agrees on one label)".
- [ ] **Step 4: infographic** `06-grader-agreement.svg` (confusion matrix → kappa → decision), colours via
  `currentColor` and CSS variables, ≤ 60 KB. Serve the site; screenshot the page in light, dark and
  at 390 px width. No horizontal scroll; diagrams readable in dark.
- [ ] **Step 5: references.** Find 2-3 YouTube videos on inter-rater agreement / LLM-judge
  validation; check each `https://www.youtube.com/oembed?url=<url>&format=json` returns 200; list
  title, channel, length, one line why. Run `grep -nE '^(!!!|===) ' concepts/06-testing-the-grader.md` → no output.
- [ ] **Step 6: build** `uv run --extra docs mkdocs build` → exit 0. Read the page on github.com
  after pushing the branch.
- [ ] **Step 7: commit** `docs: concept 06, testing the grader (pilot)`; push `dev/concepts-06`.
  **Stop here for the author's review** of depth and format. After approval: merge to `main` (`--ff-only`), push.

### After the pilot (planned once page 06 is approved)

Pages 05, 07-15 follow Task 3's shape, one branch and commit each, demos per the spec's table.
Explainer videos and Shorts follow their pages and need the author's answer on **which YouTube
channel** first. Any change the author asks for in the pilot is applied to the template before page 07.
