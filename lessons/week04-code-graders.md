# Week 4: Code-based graders

**[← Week 3: Test datasets](week03-test-datasets.md)** · **[Course Plan](../COURSE_PLAN.md)** · **Week 5: LLM as a grader →** *(coming)*

---

**Time:** about 4 hours (1 reading, 2 on the checks and the dataset, 1 on the exercises).
**Code for this week:** `git checkout week-04`

**You're done when:**

1. `uv run pytest` passes (173 tests and 4 skipped without DeepEval; 177 with `uv sync --extra deepeval`), offline, no keys needed,
2. you can read `gen-fa79bb81`'s trace (section 5) and say why its reply looks fine but its case now fails, and
3. you can name one week 2 failure category that code can check and one it can't, and say why.

## 1. Read first

| Read | Look for |
| --- | --- |
| [Should I build automated evaluators for every failure mode I find?](https://hamel.dev/blog/posts/evals-faq/should-i-build-automated-evaluators-for-every-failure-mode-i-find.html) (Hamel Husain and Shreya Shankar, from the evals FAQ) | "Start with cheap code-based checks where possible." Why an LLM judge costs 100+ labelled examples and weekly upkeep, while an assertion costs a line. |
| [Tool Correctness](https://deepeval.com/docs/metrics-tool-correctness) (DeepEval docs) | What `ToolCallParams.INPUT_PARAMETERS` does, and the default threshold of 0.5. Section 10 shows what that default lets through. |

## 2. Check with code whatever code can check

A code check is a few lines of Python that look at a reply or a trace and say pass or fail. Compared with asking a model to grade:

- **free and instant:** no API call, so you can run it on every case, every time;
- **exact:** the same input always gets the same verdict, so a change in the score means the app changed, not the grader;
- **readable:** when it fails, the detail says exactly what it saw.

Its limit is that it only sees what you can describe as a rule. "Mentions 30" is a rule. "Gives correct, policy-backed advice" isn't. This week builds every code check the bookstore needs and shows where each one stops working. Week 5 takes over from there.

Weeks 1-3 already had five check types: `contains`, `not_contains`, `tool_called`, `tool_not_called` and `max_words` (the length limit). This week adds seven more.

## 3. What's new in the code

| File | What it does |
| --- | --- |
| `evally/evals_core/checks.py` | New check types `regex`, `not_regex`, `tool_args`, `args_shape`, `args_grounded`, `refuses`, `not_refuses`; `VALIDATORS`, one per check type, run when a case file loads |
| `evally/evals_core/cases.py` | `load_cases` validates every check's value, so a regex that doesn't compile stops every command, naming the file and line |
| `evally/graders/refusal.py` | The refusal detector: four phrase patterns, nothing smarter |
| `evally/graders/deepeval_side.py` | Runs a recorded case's checks through DeepEval and prints both verdicts |
| `evally/datasets/stats.py` | `format_by_check`: pass rates per check type, for `evally run --by check` |
| `evals/datasets/bramble/*.jsonl` | `bramble-v2`: the same 26 cases with better checks |

A bad check value is caught when the file loads, not halfway through a run:

```
$ uv run evally run --suite my-cases.jsonl
my-cases.jsonl:2: regex: bad regex '(unclosed': missing ), unterminated subpattern at position 0
```

## 4. Regex: when `contains` isn't precise enough

`regex` and `not_regex` use Python's `re.search`, ignoring case. Week 1's `return-window` case checked `not_contains "60"` to catch the stale 60-day policy. That also fails on "$60", "BB-1060" or "160 pages". In v2 it's:

```json
{"type": "not_regex", "value": "\\b60[- ]days?\\b"}
```

When `not_regex` fails, it quotes what it matched, so you can see whether the regex caught the real problem or an innocent phrase.

## 5. Tool arguments: the trace knows what the reply hides

`tool_called` only says a tool ran. Three new checks look at the **arguments** it ran with. Tool arguments are the only JSON this app produces, so these are its "JSON shape" checks:

| Check | Passes when | Example |
| --- | --- | --- |
| `tool_args` | some call to the tool has these exact argument values (extra arguments are fine) | `start_return` with `order_id` `BB-1001` |
| `args_shape` | every call has these arguments as text fully matching a pattern | `order_id` matches `BB-\d{4}` |
| `args_grounded` | every call uses values the customer actually wrote | the email in `lookup_order` appears in the chat |

`tool_args` and `args_shape` fail if the tool was never called. `args_grounded` doesn't: it's a rule about calls that happen ("don't invent arguments"), not a demand to make one. Pair it with `tool_called` when a call is required.

`args_grounded` found a failure that nothing in weeks 1-3 caught. Here's the torn-cover message from week 3's generated cases:

```
$ uv run evally traces bramble-v2-dev-qwen3.5-4b --case gen-fa79bb81
── gen-fa79bb81 ───────────────────────────── FAIL
customer> i bought a book yesteray and now i want retun it but i cant find the button on my account page is this possbile or do i need to email you first the cover is torn and i am really confued about the policy
  docs: damaged-items.md, preorders.md, membership.md
  tool: lookup_order {"email": "user@example.com", "order_id": "BB-1001"}
     → No order found for that order id and email.
assistant> Yes, it is absolutely possible to return a damaged book. According to our policy, if a book arrives damaged, you can contact us within **14 days of delivery** and send a photo. ...

To help you with the return, I'll need:
- Your order ID (like BB-1001)
- The email address on the order
...
```

The customer gave no order number and no email. The model **made both up** (`BB-1001` is the example in the tool's own description) and looked the order up. The lookup failed, so the reply asks for the details, and it reads perfectly well. In v1 this case passed. In v2 it fails:

```
  gen-fa79bb81           FAIL   args_grounded lookup_order ['order_id', 'email'] (order_id='BB-1001' isn't in anything the customer wrote)
```

Why it matters: `BB-1001` exists in the store, and it belongs to alice@example.com. With a guessed email that happened to match, the app would have read out a stranger's order. Only the trace shows this. A grader that reads only the reply, whether code or a model, can't see it.

`args_grounded` compares by substring, so a very short value (an order id of `1`) would count as grounded almost anywhere. Keep it for ids and emails.

## 6. Refusal detection, and when a code check misleads

`refuses` / `not_refuses` use one list of phrases ("I can't", "I'm unable to", "I'm sorry, but I…", the fallback reply's "couldn't finish"). `evally refusals` shows which replies the list flags:

```
$ uv run evally refusals bramble-v2-dev-qwen3.5-4b
return-window          -
free-shipping          -
order-status           -
other-customer-order   REFUSES  "I'm sorry, but I"
price-match            -
return-two-turns       -
return-too-late        -
short-answer           -
t-send-back-six-weeks  REFUSES  "I'm sorry, but I"
t-password-reset       REFUSES  "I'm sorry, but I"
t-clockmaker-stock     -
gen-fa79bb81           -
gen-853dbcd7           -
gen-14a2a76c           -
adv-quotes-60-days     -
adv-third-party-order  -
3 of 16 replies flagged
```

```
$ uv run evally refusals bramble-v2-test-qwen3.5-4b
...
adv-pushy-price-match  REFUSES  "I can't"
...
1 of 10 replies flagged
```

The course author read all 26 replies and marked which ones decline what the customer asked for. The course author is an AI, so these are author labels, as in week 2. Seven do. The detector caught three of them, and it flagged one reply that isn't a refusal:

| | Refuses (author) | Doesn't |
| --- | --- | --- |
| **Flagged** | 3 (`t-send-back-six-weeks`, `t-password-reset`, `adv-pushy-price-match`) | 1: `other-customer-order`, "I'm sorry, but I couldn't find an order…" is a lookup result |
| **Not flagged** | 4: `price-match` "No, **we cannot** match that price", `return-too-late` "Unfortunately… you're only eligible…", `t-recommend-mystery` "I **don't have access** to book recommendation features", `adv-gift-card-as-book` (escalates, quoting "gift cards cannot be returned") | 18 |

**3 of 7 refusals found, and 1 false alarm.** People decline in many more ways than a phrase list can name. Adding "we cannot" would catch one more and miss the next rewording. This is what "when a check misleads" looks like: a `not_refuses` check passes a reply that refused, and the score looks better than the app is. Use the phrase list where the wording is predictable (the fallback reply) and leave "did it refuse?" to week 5's grader. The two `not_refuses` checks in v2 sit on simple price questions, where any refusal would be a failure and the phrase list only has to catch the obvious ones.

## 7. `bramble-v2`: same cases, better checks

v2 changes only checks, so week 3's rules apply:
- the version goes up;
- every v1 case is pinned to its v1 half;
- every reply replays from the recordings, with no model calls.

```
$ uv run evally dataset build
bramble-v2: 16 dev, 10 test
suites evals/suites/bramble-v2-dev.jsonl, evals/suites/bramble-v2-test.jsonl
lock evals/datasets/bramble-v2.lock.json
```

Each changed check carries a `// v2:` comment saying why. The main changes:
- `tool_args` on `order-status` and `return-two-turns`;
- `args_grounded` on `gen-fa79bb81` and `other-customer-order`;
- `not_regex` in place of three `not_contains` checks that were too loose (week 3's deferred minors);
- `not_refuses` on two price questions;
- `adv-quotes-60-days` no longer forbids `start_return`, since the tool itself refuses a late return;
- `gen-3649b7b3` now accepts a reply that asks for the order details. Week 3's lesson showed its check was wrong, and its reply was quoted there. It's a test case, so fixing it raises a test-set number. The check changed because it was wrong, not to raise the score.

| | v1 | v2 |
| --- | --- | --- |
| dev | 11/16 cases, 23/30 checks | **10/16** cases, 26/34 checks |
| test | 4/10 cases, 10/20 checks | **5/10** cases, 12/21 checks |

The app and its replies are byte-for-byte the same. **Every change in this table comes from the checks.** Dev went down because a check now sees an invented order id. Test went up because a check that failed a good reply was fixed. When you compare two eval runs, ask which changed first: the app or the checks. A score is only comparable across runs that used the same dataset version.

## 8. Pass rates per check type

```
$ uv run evally run --suite bramble-v2-dev --by check
...
by check type
  type             passed   rate  sole fail
  max_words           0/1     0%          1
  args_grounded       1/2    50%          1
  tool_not_called     1/2    50%          0
  tool_called         2/3    67%          0
  contains           8/10    80%          1
  not_contains       8/10    80%          1
  not_refuses         1/1   100%          0
  not_regex           3/3   100%          0
  tool_args           2/2   100%          0
```

`sole fail` counts the cases where this check type is the only one failing: the cases it alone decides. `args_grounded` decides one case (`gen-fa79bb81`), and without it that case passes. A check type that never fails might be guarding something the app already does well (`tool_args` here). It might also be too loose to ever fire. Section 6 shows how to tell: read the replies it passes.

## 9. Which failures can code check?

Week 2 found six failure categories. Here's what code can do with each, on this app:

| Category | Code check? | How, or why not |
| --- | --- | --- |
| `cant-find-book-by-title` | **Yes** | `tool_called check_stock` and `not_contains "ISBN"`: the failure is visible in the trace and in one word |
| `needless-escalation` | **Yes** | `tool_not_called escalate_to_human` on cases that don't need a person |
| `uses-outdated-policy` | **Mostly** | `not_regex` on the stale facts (60 days, 10 business days, store credit). Catches the old numbers, not a reworded old rule |
| `misses-the-relevant-policy` | **Partly** | `contains` on the fact the right doc holds (`30`, `7-14`), plus `tool_not_called escalate_to_human`. Passes a reply that mentions the number in the wrong sense |
| `goes-beyond-policy` | **Partly** | `tool_not_called start_return` and `not_contains "will match"` catch the actions and the stock phrases; a promise worded freshly gets through |
| `unsupported-claims` | **No** | An invented feature or wrong arithmetic has no fixed wording. `t-password-reset`'s check only catches the one invention it was written for. That's week 5's job. |

Two of the six are fully code-checkable, and for those an LLM grader would cost money and add noise without adding accuracy. For the rest, code catches the known shapes and misses the next new wording.

## 10. The same checks in DeepEval

[DeepEval](https://deepeval.com) 4.3.2 is an open-source eval library (Apache-2.0). Two of its metrics need no model and match our check types: `PatternMatchMetric` (regex) and `ToolCorrectnessMetric` (tool + arguments). It's an optional extra, so the core course installs nothing new:

```
uv sync --extra deepeval
```

`evally deepeval` runs a recorded case's checks through both:

```
$ uv run evally deepeval bramble-v2-dev-qwen3.5-4b --suite bramble-v2-dev --case order-status
order-status: evally vs DeepEval 4.3.2
  check                                                evally  DeepEval
  tool_called lookup_order                             PASS    no DeepEval equivalent
  tool_args lookup_order                               PASS    PASS (score 1)
  tool_args lookup_order (DeepEval default threshold)  PASS    PASS (score 1)
  contains shipped                                     PASS    no DeepEval equivalent
```

```
$ uv run evally deepeval bramble-v2-dev-qwen3.5-4b --suite bramble-v2-dev --case return-two-turns
return-two-turns: evally vs DeepEval 4.3.2
  check                                                evally  DeepEval
  tool_called start_return                             PASS    no DeepEval equivalent
  tool_args start_return                               PASS    FAIL (score 0.666667)
  tool_args start_return (DeepEval default threshold)  PASS    PASS (score 0.666667)
  contains R-BB-1001                                   PASS    no DeepEval equivalent
```

```
$ uv run evally deepeval bramble-v2-test-qwen3.5-4b --suite bramble-v2-test --case gen-3649b7b3
gen-3649b7b3: evally vs DeepEval 4.3.2
  check                            evally  DeepEval
  regex 'order (id|number)|email'  PASS    FAIL (score 0)
  tool_not_called start_return     PASS    no DeepEval equivalent
```

(The last one compares two graders on an already-recorded test reply. No dev case has a positive `regex` check, and nothing here feeds an app fix.)

**Same result?** Only on the simplest case. The two disagreements both come from definitions, not bugs:

- **`PatternMatchMetric` matches the whole reply (`re.fullmatch`), and our `regex` searches inside it.** A pattern that finds "order id" somewhere in the reply scores 0 in DeepEval unless you wrap it in `.*…`. Neither is wrong, but the same regex means different things in the two tools.
- **`ToolCorrectnessMetric` compares the whole argument set.** The return was started with `order_id`, `email` and a `reason`. The case lists only the first two, so DeepEval scores 2 of 3 and fails at threshold 1.0. Our `tool_args` checks only the arguments you list. Extra tool calls cost nothing in DeepEval (the `lookup_order` before the return doesn't count), while extra arguments do.

**What it adds:** these metrics plug into DeepEval's runner, its dashboard and its LLM metrics (week 5), so a team already on DeepEval gets one report for everything.

**What it hides** (all checked by running 4.3.2):

- **The default threshold is 0.5.** A `lookup_order` with the right order id and the **wrong email** scores 0.5, and that **passes**. For tool arguments, anything below 1.0 lets a wrong call through, so `evally deepeval` shows both thresholds.
- **It needs an OpenAI key to grade without OpenAI.** `ToolCorrectnessMetric` builds an OpenAI client when you create it, even though this metric never calls it. `evally deepeval` sets a placeholder key just for the call, then restores your environment.
- **Telemetry is on by default.** DeepEval reports usage unless `DEEPEVAL_TELEMETRY_OPT_OUT=1`; `evally deepeval` sets it.
- **It writes to your project.** It creates an empty `.deepeval/` folder in the working directory (now in `.gitignore`). It also installs pytest plugins that hook into **your** test run. With the extra installed, `uv run pytest` prints a pytest-asyncio warning and a "Running teardown with pytest sessionfinish..." line that weren't there before.
- **No negative metrics.** There's no `not_regex`, no `tool_not_called` and no refusal check. Only 3 of v2's 55 checks (one `regex`, two `tool_args`) have a DeepEval equivalent.

For code checks, the library adds little over ten lines of Python and changes their meaning in quiet ways. It earns its place in week 5, where its LLM metrics do work you'd otherwise build yourself.

## 11. What the numbers can't tell you

- **The before/after measures the checks, not the app.** Nothing about the bookstore assistant changed this week.
- **Small and single-run.** 16 and 10 cases, one recorded reply each. One case moving changes a rate by 6 to 10 points.
- **The refusal counts are author labels on 26 replies.** "Refusal" is a judgement: is "we don't ship to Australia" a refusal or an answer? (Marked as an answer here.) Week 6 measures how often two labellers agree.
- **A passing check passes only what it checks.** `gen-853dbcd7` passes because the reply didn't say "shipping to Australia costs…". A yes worded any other way would also pass. Each such check says what it misses in its `//` comment.

## 12. Exercises

Write your answers in `NOTES.md`.

1. **Break a check on purpose.** In a copy of `evals/datasets/bramble/hand.jsonl`, change `return-window`'s regex to `(60` and run `uv run evally run --suite <your copy>`. What happens, and why is that better than a crash halfway through a run?
2. **Fix the refusal list on dev only.** Add one pattern to `REFUSAL_PATTERNS` that catches `price-match`'s "we cannot", and run `evally refusals` on dev. How many of the four misses does it fix? Did it add a false alarm? Then run it on test once. Did the gain hold?
3. **Shape vs grounded.** Add `args_shape` (`order_id` matches `BB-\d{4}`) to `gen-fa79bb81` and run it. Does it catch the invented order id? What does that tell you about checking a value's shape compared with checking where it came from?
4. **DeepEval at threshold 1.0.** With the extra installed, run `evally deepeval` on `return-two-turns`. Which check would you trust for "the return was started on the right order", ours or DeepEval's, and what would you have to change in the case to make DeepEval agree?

## 13. In one minute

Before you pay a model to grade your chatbot, check with code whatever code can check. We added regex, tool-argument and refusal checks to our bookstore bot's 26 test cases and re-scored the same recorded replies, with no model calls. One reply looked perfect, but the trace showed the bot had **invented a real customer's order number** to look an order up. Only a check on the tool's arguments caught it. Code fully covers two of our six failure types. A phrase-list refusal detector found 3 of 7 refusals. DeepEval's tool check, at its default setting, passes a call with the wrong email.

---

**Tested with:** Python 3.11.8, openai 3.49.0, anthropic 2.8.0, python-dotenv 1.2.4, pytest 9.2.0, deepeval 4.3.2 (optional extra), Ollama 0.40.16 with `qwen3.5:4b`, on an Apple M2 with 8 GB of RAM. All outputs above are copied from real runs; `...` marks where a long output was shortened. No model calls this week: every reply is week 3's recording.
