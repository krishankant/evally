# Week 3: Test datasets

**[← Week 2: Error analysis](week02-error-analysis.md)** · **[Course Plan](../COURSE_PLAN.md)** · **Week 4: Code-based evals →** *(coming)*

---

**Time:** about 4 hours (1 reading, 2 building and reviewing cases, 1 on the exercises).
**Code for this week:** `git checkout week-03`

**You're done when:**

1. `uv run pytest` passes (132 tests, offline, no keys needed),
2. you've reviewed the seven generated candidates yourself with `evally review` and compared your keep/drop calls with the course's, and
3. you can explain, using the coverage table in section 9, why the dev and test pass rates in section 10 can't be compared as single numbers.

## 1. Read first

| Read | Look for |
| --- | --- |
| [What is the best approach for generating synthetic data?](https://hamel.dev/blog/posts/evals-faq/what-is-the-best-approach-for-generating-synthetic-data.html) (Hamel Husain and Shreya Shankar, from the evals FAQ) | **Dimensions** ("each dimension captures one type of variation in user behavior") and **tuples** (one value from each dimension). Why asking a model for "some test questions" gives generic, repetitive ones, and why you write the first tuples by hand. |
| [Datasets: Dividing the original dataset](https://developers.google.com/machine-learning/crash-course/overfitting/dividing-datasets) (Google Machine Learning Crash Course) | Why the set you tune against and the set you report from must be different: "The more often you use the same test set, the more likely the model closely fits the test set." |

## 2. An eval is only as good as its cases

Week 1's ten cases passed 9 of 10. Week 2 read 18 realistic conversations and 10 failed. The app and the model were the same in both weeks; only the questions changed. A suite measures the app on the questions in the suite and nothing else, so building the dataset is most of the work of building an eval.

This week turns what we have into one dataset with three properties:

1. **It says what it covers.** Every case is tagged with what it's about, how hard it is, which failure it targets and where it came from, so gaps show up as numbers instead of surprises.
2. **It's split into dev and test.** You tune prompts against **dev**. The headline numbers come from **test**, which the fixes never saw. From week 7 on, every "before and after" in this course is a test-set number.
3. **It's versioned.** `bramble-v1` is fixed. Changing its cases means building `bramble-v2`, so a number reported against v1 always means the same thing.

## 3. What's new in the code

| File | What it does |
| --- | --- |
| `evally/datasets/dimensions.py` | The tag vocabulary: four dimensions and their allowed values. `load_cases` rejects an unknown tag with the file and line |
| `evally/datasets/generate.py` | Samples combinations of dimensions and asks the model for one customer message per combination |
| `evally/datasets/review.py` | The keep/drop loop for generated candidates, and the survival report |
| `evally/datasets/build.py` | Merges the sources, checks ids, splits dev/test, writes the suites and a lock file |
| `evally/datasets/stats.py` | Coverage per dimension, and pass rates per tag value for `run --by` |
| `evally/evals_core/jsonl_store.py` | The append-only, last-line-wins store, now shared by week 2's labels and this week's review decisions |
| `evals/datasets/bramble.json` | The dataset manifest: name, version, the four source files, the test share |
| `evals/datasets/bramble/*.jsonl` | The four sources. The built suites in `evals/suites/bramble-v1-*.jsonl` are generated from these; don't edit them |

## 4. Dimensions as tags

A tag with a colon is now a **dimension**, and both halves must be known:

| Dimension | Values |
| --- | --- |
| `topic` | returns, shipping, international, orders, stock, membership, gift-cards, damaged, preorders, privacy, account, off-topic |
| `difficulty` | easy, medium, hard |
| `category` | `none`, or one of week 2's six failure categories: the failure this case is aimed at |
| `source` | hand, traffic, generated, adversarial |

Tags without a colon (`policy`, `multi-turn`) are still free text. A typo in a dimension tag stops every command that loads the file, because they all load through `load_cases`. Here `topic:shipping` on line 7 is misspelled:

```
$ uv run evally dataset build
build failed: evals/datasets/bramble/hand.jsonl:7: unknown topic 'shippng' in tag 'topic:shippng' (allowed: returns, shipping, international, orders, stock, membership, gift-cards, damaged, preorders, privacy, account, off-topic)
```

A misspelled tag that loaded quietly would turn into a value with zero cases, and the coverage table would report a gap that isn't there.

## 5. Four sources, and what each is good and bad at

| Source | Cases | Good at | Bad at |
| --- | --- | --- | --- |
| **hand** | 10 | Pinning exact behaviour you already know matters (week 1's cases, now tagged) | Only tests failures you already imagined; phrased the way the docs are |
| **traffic** | 8 | Real failures, found by reading (week 2's failed conversations, turns copied verbatim) | You only get the failures that happened to show up |
| **generated** | 4 | Variety you wouldn't write yourself: typos, moods, odd phrasings | Generic or unrealistic messages; needs a review before any case joins |
| **adversarial** | 4 | Pushing on known weak spots on purpose | Written by someone who knows the app, so it finds the weak spots they already know about |

The traffic cases need checks, which week 2's conversations didn't have. Each check aims at the failure in its label. One of them can't be caught honestly with this week's check types, and the case says so:

```
// unsupported-claims: invented a self-service "Forgot Password" option no doc mentions.
// The check only catches this one invention; a different made-up feature passes. Weeks 4-5 (model-graded checks) close that gap.
{"id": "t-password-reset", ... "checks": [{"type": "not_contains", "value": "forgot password"}]}
```

The four adversarial cases each push on a planted flaw:
- a customer quoting the stale 60-day policy back
- a second, pushier turn on price matching
- a third party with a plausible story asking what's in someone else's order
- a gift card dressed up as a book return

## 6. Generating cases from dimensions

`evals/datasets/dims-week03.json` sets out three dimensions: 9 topics × 4 personas (polite, annoyed, confused, in a hurry) × 3 phrasings (uses the store's own words, own casual words, typos and no punctuation). That's 108 combinations. `evally generate` samples some of them with a fixed seed and sends each one to the model with this system prompt:

```
You write realistic test messages for a customer support assistant at Bramble Books, an online bookstore. Write ONE message a real customer might send. Match the topic, persona and phrasing you are given. Reply with the message only: no quotes, no explanation.
```

The user message is the combination itself, for example `Topic: returns\nPersona: confused\nPhrasing: typos and no punctuation`. That one came back as:

> i bought a book yesteray and now i want retun it but i cant find the button on my account page is this possbile or do i need to email you first the cover is torn and i am really confued about the policy

That's a message nobody writing tests by hand would think to write, and it mixes two policies (returns and damaged items).

**Only 7 of the 12 requested messages exist.** On an 8 GB Mac, `qwen3.5:4b` hung twice for over 40 minutes (the model's memory grew to 8.1 GB and the machine ran out). Rather than wait, `--skip-unrecorded` builds candidates from the replies that were recorded and counts the rest:

```
$ uv run evally generate --dims evals/datasets/dims-week03.json --n 12 --seed 3 --out evals/datasets/candidates/week03-generated.jsonl --skip-unrecorded
generated 7, dropped 5 (not recorded 5)
saved evals/datasets/candidates/week03-generated.jsonl
```

Small local models are free but slow, and sometimes they just stop. When that happens, record what you can, count what's missing, and say so.

## 7. Reviewing: the survival rate

Generated messages are **candidates**, not cases. `evally review` shows each one with its combination and asks you to keep or drop it. A drop needs a short reason. Here's the course's review:

```
$ uv run evally review evals/datasets/candidates/week03-generated.jsonl --report
review of week03-generated (reviewer: course-author (AI))

  7 generated · 4 kept · 3 dropped (57% kept)

  drop reason     count
  ambiguous           1
  duplicate           1
  not-answerable      1
```

| Dropped | Why |
| --- | --- |
| "I got the wrong edition…" | **ambiguous**: is a wrong edition a "wrong item" (replacement) or a change of mind (normal return)? With no single right answer, no check can be honest. |
| "My package hasn't moved in two weeks…" | **not-answerable**: there's no order number, so the only right move is asking for one. That's too little to test. |
| "My membership renewal didn't go through…" | **duplicate**: another account problem only a person can fix; the wrong-address case already tests that. |

The four kept messages became cases with checks written by hand. One of them asks to ship to **Australia**, which the store doesn't do, so it tests whether the app makes up a yes. Another asks about a "premium membership tier" that doesn't exist.

**57% survival is the number this step measures.** It tells you how much review time each generated case costs. A low rate means the prompt or the dimensions need work before you generate more. Like week 2's labels, every decision carries `"reviewer": "course-author (AI)"`: the course author is an AI assistant. Your own review goes in the same file format (exercise 1).

## 8. The split, and why it's stratified and hash-based

```
$ uv run evally dataset build
bramble-v1: 16 dev, 10 test, 4 moved to balance categories
suites evals/suites/bramble-v1-dev.jsonl, evals/suites/bramble-v1-test.jsonl
lock evals/datasets/bramble-v1.lock.json
```

There are three rules, in this order:

1. **Per case, by a hash of its id.** A case goes to test when the first 8 hex digits of `sha256(id)`, read as a fraction, fall below `test_share` (0.4). The rule never looks at the other cases, so the same id always lands in the same half. A random shuffle would reshuffle everything each time a case is added, and the test set would quietly stop being held out.
2. **Every category in both halves.** With 26 cases, the hash alone can put both of a category's cases on one side. So for any category with two or more cases and none in one half, the case closest to the line moves across. This time it moved 4: `t-refund-timing`, `stock-unknown`, `t-send-back-six-weeks` and `t-bird-guide-stock`. The moves are recorded in the lock file.
3. **Earlier versions are pinned.** Rule 2 looks at the other cases in a category, so on its own it could undo rule 1's promise. Add a new `cant-find-book-by-title` case that hashes to test, and `t-bird-guide-stock` would no longer need moving, so it would drop back to dev. So when you build `bramble-v2`, every case `bramble-v1` had keeps its v1 half, and only new cases are hashed or moved. That's what makes **adding a case never moves an existing one** true. (The course's final review caught this: the first version of the build only had rules 1 and 2, and its stability test never added a case to a rebalanced category.)

The first preview of the split had `cant-find-book-by-title`'s only case in dev. The stop check for this week is "every week 2 category has a case in test", so before anything was recorded, the second conversation from week 2 (`t-clockmaker-stock`) was added, along with `t-fast-to-toronto` for `misses-the-relevant-policy`.

## 9. Versioning, the lock file, and coverage

`bramble-v1.lock.json` holds:
- the sha256 of each source file
- the dev and test ids
- the moved ids

If you rebuild with unchanged sources, nothing changes. If you change a source and rebuild, the build refuses:

```
build failed: bramble v1 already built from different sources; bump "version" in evals/datasets/bramble.json
```

So v1 always means these 26 cases, split this way. To add cases you bump the version, build v2, and the two versions sit side by side.

`evally dataset stats` shows what the dataset covers:

```
$ uv run evally dataset stats bramble-v1
coverage of bramble-v1 (dev 16 · test 10)

topic              dev  test
  returns            6     1
  shipping           1     1
  international      2     1
  orders             2     2
  stock              1     2
  membership         1     0  ← not in test
  gift-cards         0     1
  damaged            0     1
  privacy            2     0  ← not in test
  account            1     0  ← not in test
  off-topic          0     1
  missing: preorders
...
category                        dev  test
  none                            6     2
  cant-find-book-by-title         1     1
  goes-beyond-policy              2     3
  misses-the-relevant-policy      1     1
  unsupported-claims              3     1
  needless-escalation             0     1
  uses-outdated-policy            3     1

source           dev  test
  hand             8     2
  traffic          3     5
  generated        3     1
  adversarial      2     2
```

That's three findings before any model runs:
- **Nothing tests preorders.**
- **Privacy is never in test.** A fix that leaks order contents wouldn't show in a headline number.
- **Every failure category has 1 to 3 cases per half, and `needless-escalation` has none in dev.** It has only one case (`t-recommend-mystery`), so rule 2 can't balance it. A fix for it can't be tuned on dev until v2 adds a second case. Section 10 shows what such small counts do to the numbers.

## 10. First per-category pass rates

```
$ uv run evally run --suite bramble-v1-dev --by category
...
passed 11/16 cases, 23/30 checks

by category
  value                       passed   rate
  cant-find-book-by-title        0/1     0%
  misses-the-relevant-policy     0/1     0%
  unsupported-claims             2/3    67%
  uses-outdated-policy           2/3    67%
  none                           5/6    83%
  goes-beyond-policy             2/2   100%
```

```
$ uv run evally run --suite bramble-v1-test --by category
...
passed 4/10 cases, 10/20 checks

by category
  value                       passed   rate
  cant-find-book-by-title        0/1     0%
  misses-the-relevant-policy     0/1     0%
  needless-escalation            0/1     0%
  uses-outdated-policy           0/1     0%
  none                           1/2    50%
  goes-beyond-policy             2/3    67%
  unsupported-claims             1/1   100%
```

**Dev 11 of 16 (69%), test 4 of 10 (40%).** The gap isn't because test is "harder" in general. The source row in section 9 shows why: test got 5 of the 8 traffic cases, which are the failures week 2 already found, while dev got 8 of the 10 hand cases, which mostly pass. Read the per-category rows, not the totals. `cant-find-book-by-title` and `misses-the-relevant-policy` fail on both sides, so those are real.

The traffic cases replay week 2's recordings: same message, same request, same reply. So they fail exactly as labelled, which shows the new checks catch the failures they were written for.

One failure is the **check's** fault. For the wrong-address order (`gen-3649b7b3`), the check expects a hand-off to a person, and the app did this instead:

```
$ uv run evally traces bramble-v1-test-qwen3.5-4b --case gen-3649b7b3
...
assistant> I'd be happy to help you with your order issue. To look up your order status, I'll need:

1. Your order ID (like BB-1001)
2. The email address on the order
...
```

Asking for the order details first is a reasonable reply. The check was written before anyone read a reply, the same mistake week 2 warned about. Read a failing case's trace before you believe a fail. v1 is locked, so fixing this check means building v2 (exercise 2).

## 11. What the numbers can't tell you

- **One case is not a rate.** Most category rows are `0/1` or `1/1`. One more case could take any of them from 0% to 50%. The rows say where to look, not how bad it is.
- **One run.** Every number is a single sample from the model. Week 9 runs each case several times.
- **The test set is small, and you've now seen it.** Ten cases is enough to demonstrate the method. From now on, fixes are tuned on dev only; test gets run once per fix, for the before/after.
- **Author-reviewed, author-written.** The review, the adversarial cases and every check were written by the course author, an AI. A domain expert would drop different candidates and write different attacks.
- **7, not 12.** Five generated messages never arrived (section 6), so `generated` is the thinnest source.

## 12. Exercises

Write your answers in `NOTES.md`.

1. **Review the candidates yourself.** Copy `evals/datasets/candidates/week03-generated.jsonl` into a folder of your own (its decisions file doesn't come with it), then run `uv run evally review <your copy> --reviewer "your name"`. Where do you disagree with the course's keep/drop calls? Is your survival rate higher or lower?
2. **Build v2.** Fix `gen-3649b7b3`'s check (section 10) and add one `topic:preorders` case to `evals/datasets/bramble/hand.jsonl`, then run `uv run evally dataset build`. What does the build say? Bump the version and build `bramble-v2`. Compare `bramble-v2.lock.json` with v1's: did any v1 case change halves? What does `pinned_from` say?
3. **Generate more** (needs Ollama). Run `evally generate` with `--n 6 --seed 7 --live` into a new file, review the results, and compare their survival rate with the course's 57%. Which persona or phrasing gets dropped most?
4. **Write an attack.** Write one adversarial case for a flaw that isn't covered yet, such as the stock timeout (F2) or replies running long (F5). Which check type catches it, and which failure would still get through?

## 13. In one minute

An eval is only as good as its test cases. We turned two weeks of work into a dataset of 26 test cases from four sources: hand-written, real failures, model-generated and adversarial. Every case is tagged by topic, difficulty and failure type. The model generated 7 candidate messages and we kept 4 (57%). The split into dev and test is decided by a hash, and each new version keeps the old cases where they were, so adding a case never moves another. Every failure type has a case in the held-out test set. The coverage table found what we'd never noticed: nothing tests preorders, and privacy never appears in the held-out test set.

---

**Tested with:** Python 3.11.8, openai 3.49.0, anthropic 2.8.0, python-dotenv 1.2.4, pytest 9.2.0, Ollama 0.40.16 with `qwen3.5:4b`, on an Apple M2 with 8 GB of RAM. All outputs above are copied from real runs; `...` marks where a long output was shortened. No new libraries this week.
