# Week 5: LLM as a grader

**[← Week 4: Code-based graders](week04-code-graders.md)** · **[Course Plan](../COURSE_PLAN.md)** · **Week 6: Testing the grader →** *(concept page, coming)*

---

**Time:** about 4 hours (1 reading, 2 on the grader and the bias demos, 1 on the exercises).
**Code for this week:** `git checkout week-05`

**You're done when:**

1. `uv run pytest` passes (208 tests and 12 skipped without DeepEval; 220 with `uv sync --extra deepeval`), offline, no keys needed,
2. you can explain why `return-too-late` passes every code check but fails the grader (section 2), and
3. you can name the three grader biases, the command that measures each, and why 15 pairs can't prove any of them.

## 1. Read first

| Read | Look for |
| --- | --- |
| [Creating a LLM-as-a-Judge That Drives Business Results](https://hamel.dev/blog/posts/llm-judge/) (Hamel Husain) | Why a pass/fail verdict with a written critique beats a 1-5 score, and why the judge must be checked against a person (that's week 6). |
| [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685) (Zheng et al., 2023), section 3 | The three biases this week measures: position, verbosity (length) and self-enhancement. Their fix for position: ask twice, swap the order. |
| [G-Eval](https://arxiv.org/abs/2303.16634) (Liu et al., 2023) and [DeepEval's G-Eval docs](https://deepeval.com/docs/metrics-llm-evals) | G-Eval writes its own evaluation steps from your criteria, then scores. Section 9 shows what that adds and what it hides. |

## 2. Why code isn't enough

Here is `return-too-late` from the dev run. The customer wants to return a book delivered 53 days ago; the policy says 30 days, no exceptions.

> Since your book was delivered 53 days ago, it's outside the acceptable window for a standard return.
>
> I've escalated this request to a human agent who can review your case further and **see if there are any exceptions we can make.**

Every code check on this case passes: the reply mentions 30, calls `lookup_order` with the customer's own order id, and escalates. But the last sentence hints at an exception the policy doesn't allow. A customer reads that as "maybe yes". No regex can see the difference between "a person will explain the policy" and "a person may bend it". That needs a reader. This week the reader is a model.

## 3. What's new in the code

| File | What it does |
| --- | --- |
| `evals/rubrics/*.md` | Three rubrics, one per week 2 failure category that code can't check: `goes-beyond-policy`, `unsupported-claims`, `uses-outdated-policy` |
| `evally/graders/rubrics.py` | `load_rubrics`: reads and validates the rubric files |
| `evally/graders/judge.py` | The grader: one rubric + one conversation + the current policies → a verdict with a reason, by tool call |
| `evally/graders/pairwise.py` | Which of two replies is better, asked twice with the order swapped; `pad_run` for the length demo |
| `evally/graders/deepeval_geval.py` | The same rubric through DeepEval's G-Eval, routed through our own model and cache |
| `evally/llm/prices.py` | Dollars per million tokens for every model the course has run; unknown models print "cost unknown", never a guess |

New commands: `evally grade`, `evally pad`, `evally bias`, `evally geval`. The grader's model is set apart from the app's in `.env`:

```
EVALLY_GRADER_PROVIDER=ollama
EVALLY_GRADER_MODEL=qwen3.5:4b
```

## 4. The grader

One call grades one conversation against one rubric. A rubric is a short Markdown file saying, in plain words, what PASS and FAIL mean, with one example of each. Here is the heart of `uses-outdated-policy`:

```
FAIL when the reply:
- states or relies on any rule from the old policy (60 days, store credit, 10 business days) ...
- agrees with a customer who quotes an old rule, or acts on it, instead of correcting them.

PASS when the reply uses only current rules, or doesn't touch the rules that changed.
```

Four design choices, each with a reason:

| Choice | Why |
| --- | --- |
| **One rubric per call**, not "is this reply good?" | A narrow question gets a checkable answer. A broad one gets a vague one, and you can't tell which failure it found. |
| **The verdict comes back as a tool call** (`record_verdict`) with `reason` before `verdict` | A tool schema gives parseable output every time. Reason first makes the model argue before it decides, instead of justifying a coin it already flipped. |
| **The grader sees the current policies**, never `returns-2023.md` | "Unsupported" only means something against a reference. The planted stale policy is never part of the truth. |
| **The grader never sees the case id or the code verdict** | Ids like `return-too-late` leak the answer; a code verdict anchors it. The grader must judge the reply alone. |

Anything that isn't a valid verdict comes back as `error`, shown in the table, never silently dropped.

## 5. Binary vs 1-5 on dev

```
$ uv run evally grade bramble-v2-dev-qwen3.5-4b
                         goes-beyond-policy  unsupported-claims  uses-outdated-policy
  return-too-late        FAIL                pass                pass
  t-password-reset       pass                FAIL                pass
  t-clockmaker-stock     pass                pass                pass
  (13 more rows, all pass)

  goes-beyond-policy    fails 1/16
  unsupported-claims    fails 1/16
  uses-outdated-policy  fails 0/16
tokens 84459 in / 24390 out · $0.0000
```

The same grader asked for a 1-5 score (`--scale 1-5`, where 3 and above counts as pass):

```
  return-too-late        FAIL 1              pass 5              pass 5
  t-password-reset       pass 5              FAIL 1              pass 5
  t-clockmaker-stock     pass 5              FAIL 1              pass 5
  (13 more rows: 5, 5, 5)
```

Two things to see:

- **The scale collapses to two values.** 48 scores, and every one is a 1 or a 5. The model was offered five levels and used two. The extra levels added nothing but a threshold to argue about.
- **The one disagreement is the interesting case.** `t-clockmaker-stock` asks the customer for "the 13-digit ISBN" before it will check stock. Binary said pass ("it only asks for information"); 1-5 said 1 ("this requirement is not mentioned in any of the provided policies"). Which is right? The claim is true of the system: the app's `check_stock` tool only accepts an ISBN, and there's no way to search by title. But no policy says so, and the grader sees the policies, not the tool definitions. The rubric never said whether "true, but nothing the grader can see supports it" counts as unsupported, so both verdicts can be argued. Same model, same rubric, same reply, different verdict, because the wording of the question changed and the rubric left room for both. (The customer's real problem, not being able to ask by title, is week 2's `cant-find-book-by-title` failure, and a code check already catches it.)

That second point is the real lesson. **A grader's verdict depends on how you ask.** You find out which way of asking is right only by checking verdicts against a person, which is week 6. Until then, binary is the default: a pass/fail verdict with a reason is easier to check against a person than a number nobody agreed on.

## 6. One grader per category, not one big prompt

Look at the fail counts: 1, 1 and 0 out of 16. With one "is this reply good?" grader, the `return-too-late` fail and the `t-password-reset` fail would be the same word, FAIL, and you'd have to read both reasons to know one is an out-of-policy promise and the other an invented "Forgot Password" button. Per-category graders give per-category counts, and a count you can track is what week 7 turns into a pass rate with a range. They also fail independently: a bad rubric breaks one column, not the whole grade.

The cost is calls: three rubrics × 16 cases = 48 calls per scale, where one big prompt would be 16.

## 7. Grader vs code check on `uses-outdated-policy`

`adv-quotes-60-days` is the dev case built for this category. The customer says *"Your returns page says I have 60 days"* and asks to start a return. The app replies:

> I'd be happy to help you start a return for order BB-1008. However, I need one more piece of information: what is the reason for your return?

| Grader | Verdict | Why |
| --- | --- | --- |
| Code check `contains "30"` (week 4) | **FAIL** | The reply never mentions 30 days. |
| LLM grader, `uses-outdated-policy` | **pass** | "does not explicitly agree with or act on the customer's claim about 60 days" |

The code check is right and the grader is wrong, by the rubric's own text: "acts on it, instead of correcting them" is a FAIL. The app carries on with the return and never corrects the 60 days. The grader read "acts on it" as "says 60" and missed that silence is also a way of going along.

So neither grader wins. On dev this week:

- **Only the LLM grader caught** `return-too-late` (a hinted exception) and, on 1-5 only, `t-clockmaker-stock` (an ISBN requirement no policy mentions; section 5 explains why that verdict is debatable).
- **Only the code check caught** `adv-quotes-60-days` (a missing correction).
- **Both caught** `t-password-reset` (the invented "Forgot Password" option): code with `not_contains`, the grader as an unsupported claim.

Keep the cheap check where it works, and add the grader for what it can't see.

## 8. Biases

A grader that compares two replies (*"which is better, A or B?"*) is how you'll compare app versions in week 8. Before trusting it, measure how it fails. `evally bias` asks about every case twice, once with each reply shown first, and calls the pair **consistent** only when both orders pick the same winner.

**Position: a run against itself** (the control). A and B are the same reply, so the only honest answer is a tie.

```
$ uv run evally bias bramble-v2-dev-qwen3.5-4b bramble-v2-dev-qwen3.5-4b
pairs 15 (skipped: 1 multi-turn, 0 errored)
consistent under swap 14/15
picked the reply shown first 0/30
consistent pairs: A 0, B 0, tie 14
grader errors 2
```

qwen passes the control: 14 ties and one pair where both calls errored. Good. But a control that only shows identical text can't show position bias that appears when the replies differ. The next two can.

**Length: the same replies plus one sentence of filler.** `evally pad` appends *"I hope this helps, and please don't hesitate to reach out…"* to every reply. The filler adds nothing.

```
$ uv run evally pad bramble-v2-dev-qwen3.5-4b
$ uv run evally bias bramble-v2-dev-qwen3.5-4b bramble-v2-dev-qwen3.5-4b-padded
consistent under swap 6/15
picked the reply shown first 13/30
consistent pairs: A 0, B 6, tie 0
```

The padded reply wins 6 pairs outright and the original wins none. In 7 more pairs the padded reply wins when it's shown first and ties when it's shown second. Only once (`return-too-late`, shown second) did the original win a single call. A reply with an extra sentence of filler was preferred over the same reply without it. That's length bias, and it rewards exactly the habit you're trying to stop.

**Self-preference: does a judge prefer its own model's replies?** The plan named mistral as the second app model, but mistral can't call tools in Ollama, so the run uses llama3.2:3b. Each judge compares qwen's replies (A) with llama's (B):

| Judge | Consistent: qwen wins | llama wins | Picked the reply shown first |
| --- | :---: | :---: | :---: |
| qwen3.5:4b | **10** | 0 | 16/30 |
| llama3.2:3b | 2 | 2 | 8/30 (3 errors) |

```
$ uv run evally bias bramble-v2-dev-qwen3.5-4b bramble-v2-dev-llama3.2-3b
$ uv run evally bias bramble-v2-dev-qwen3.5-4b bramble-v2-dev-llama3.2-3b --grader-model llama3.2:3b
```

qwen prefers qwen's replies 10 to 0. Is that self-preference or is qwen's run simply better? The code checks point the other way: llama's run passes **13/16** cases on dev, qwen's **10/16**, with replies of similar length (72 vs 77 words on average). So qwen picks its own replies 10 times out of 10 even though, by the checks we trust, they're the weaker set. That's the shape self-preference would make.

It still isn't proof. The code checks measure a few rules, not everything a judge weighs; and the other half of the test is weak, because llama as a judge is too noisy to show any preference (next paragraph). Self-preference would show as **each judge moving towards its own replies**; here only one judge moves and the other can barely hold a verdict.

The llama judge shows something else: **it picks the reply shown second 19 times out of 27** (the 3 errors excluded), and only 4 of 15 pairs survive the swap. A small judge can be mostly position. Without the swap you would have read its picks as preferences.

**How far can 15 pairs go?** Not far. 10 to 0 is suggestive; 6 to 0 is suggestive; 2 to 2 is noise. Week 7 puts ranges on numbers like these. What this week shows is the *method*: always swap, always run a control, change one thing at a time (padding changes only length), and report inconsistent pairs as ties, not as wins.

## 9. The same rubric in DeepEval G-Eval

G-Eval works in two calls. First it turns your rubric into numbered evaluation steps; then it scores the reply against those steps from 0 to 10, which DeepEval scales to 0-1 and compares with a threshold (0.5 by default). `evally geval` runs it through our model and cache and prints both verdicts:

```
$ uv run evally geval bramble-v2-dev-qwen3.5-4b --rubric goes-beyond-policy --case return-too-late
  evally   FAIL  The assistant suggests a human agent can review the case and make exceptions to the 30-day return policy ...
  G-Eval   FAIL  0.40 (threshold 0.5)  ... it explicitly promised to check for 'exceptions we can make' regarding a hard rule ...

G-Eval's steps (it wrote them from the rubric):
  1. Review the Context to identify specific policy rules applicable to the issue described in the Input.
  2. Extract all promises, offers, or actions from the Actual Output and compare them against the relevant policy rules.
  3. Determine if any promise exceeds policy limits ... or hints at unauthorized exceptions.
  4. Assign PASS if no promises exist or they align with policy; FAIL if any promise violates policy constraints.
tokens 4150 in / 9098 out · $0.0000
```

On `return-window` both say pass (G-Eval 1.00). On both cases the verdicts agree.

| | evally grader | G-Eval (DeepEval 4.3.2) |
| --- | --- | --- |
| Calls per verdict | 1 | 2 |
| Output tokens, `return-too-late` / `return-window` | ~500 | 9,098 / 4,315 |
| What you control | The whole prompt | The criteria; the step-writing and scoring prompts are DeepEval's |
| What you get | pass/fail + reason | 0-1 score + reason + generated steps |
| Hidden | nothing | The 0-10 → 0-1 scaling and the threshold decide pass/fail |

What G-Eval adds is the generated steps: a checklist you can read to see how the judge understood your rubric. What it costs is many more output tokens (free on a local model, real money on a hosted one) and one more place where a number turns into a verdict without you choosing how.

## 10. Cost

Everything this week, recorded once and replayed for free: about 359,000 input and 110,000 output tokens, all on local models, **$0.0000**. `prices.py` lists only the two local models; a hosted grader goes in with its price and the date it was copied from the provider's page. The same token counts through a hosted model would cost real money, which is one more reason the course grades on a local model and records every call.

## 11. When an LLM grader misleads

- **It reads the rubric's words, not its intent.** `adv-quotes-60-days` passed because "acts on it" was read narrowly. Every rubric needs its fail example to match a real failure.
- **The wording of the question changes the verdict.** Binary and 1-5 disagreed on `t-clockmaker-stock`.
- **It prefers longer replies.** The padded reply won 6 pairs; the original won none.
- **A small judge can be mostly position.** llama picked the second reply 19 times out of 27.
- **It's a model.** Two of 30 control calls and three of 30 llama calls returned no usable verdict.
- **Its agreement with you is unknown.** Every number in this lesson is the grader's opinion. Week 6 measures how often that opinion matches a person.

## 12. Exercises

1. Read `adv-quotes-60-days`'s grader reason (`uv run evally grade bramble-v2-dev-qwen3.5-4b --case adv-quotes-60-days`). Rewrite the FAIL bullet in `evals/rubrics/uses-outdated-policy.md` so a reply that silently goes along with "60 days" clearly fails. Don't re-grade yet; write down what you expect.
2. Pick one case where binary and 1-5 disagree and argue, in two sentences, which verdict a customer would agree with.
3. Write a fourth rubric for a week 2 category not covered here. Include one PASS and one FAIL example taken from a real dev trace.
4. The length demo padded with polite filler. Design a padding that adds a *wrong* sentence instead. Predict whether the judge would still prefer it, and say why that would be worse.
5. In `NOTES.md`: which of this week's numbers would you trust enough to make a decision, and which would you not?

## 13. In one minute

Code checks see rules; an LLM grader sees meaning. On the dev set the grader caught a hinted exception that no code check could, and missed a silent "60 days" that a one-line code check caught. Asked for 1-5, the grader used only 1s and 5s and changed one verdict. Asked to compare, the unpadded reply never won a pair against the same reply plus filler, picked its own model's replies 10 to 0 over a run that passes more checks, and a smaller judge was mostly picking by position. Keep the code checks, add a narrow pass/fail grader per failure category, always swap order, and don't trust any of it until week 6 has checked it against a person.
