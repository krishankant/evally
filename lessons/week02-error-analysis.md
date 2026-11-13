# Week 2: Error analysis

**[← Week 1: Baseline](week01-baseline.md)** · **[Course Plan](../COURSE_PLAN.md)** · **[Week 3: Test datasets →](week03-test-datasets.md)**

---

**Time:** about 4 hours (1 reading, 2 reading conversations and labelling, 1 on the exercises).
**Code for this week:** `git checkout week-02`

**You're done when:**

1. `uv run pytest` passes (85 tests, offline, no keys needed),
2. you've read at least five of this week's 18 conversations with `evally traces` and labelled them yourself with `evally label`, and
3. you can explain why week 1's ten checks were the wrong place to start, using the ranked list in section 6.

## 1. Read first

| Read | Look for |
| --- | --- |
| [A Field Guide to Rapidly Improving AI Products](https://hamel.dev/blog/posts/field-guide/) (Hamel Husain): "The Most Common Mistake: Skipping Error Analysis" and "A Simple Data Viewer" | Why generic metrics give "a false sense of progress", and the bottom-up approach: read real conversations, write notes, let the categories come out of the data. |
| [AI Evals: Everything You Need to Know](https://hamel.dev/blog/posts/evals-faq/) (Hamel Husain and Shreya Shankar): the questions on why error analysis matters and how many examples you need | The two passes this week builds, **open coding** (free notes on each trace) and **axial coding** (grouping the notes into a failure taxonomy), and their advice to review at least 100 traces. |

## 2. Why metrics come after reading

Week 1 wrote ten cases and five kinds of check before anyone had read what the app actually does with real questions. That's the usual order, and it's backwards. A check can only catch a failure someone thought of in advance, so a suite written first measures the author's guesses about the app.

Error analysis flips the order:

1. **Collect conversations** that look like real use, not like tests.
2. **Read every one in full**: what was asked, what was retrieved, which tools ran with which arguments, what came back, what the assistant said.
3. **Open coding:** mark each one pass or fail and write a note in your own words about what went wrong. No categories yet.
4. **Axial coding:** read the fail notes together and group them into categories.
5. **Count:** fails per category, most first. That ranked list is what decides which metrics to build next.

This week builds the tools for steps 2 to 5 and does one full pass on the bookstore app.

## 3. What's new in the code

| File | What it does |
| --- | --- |
| `evally/evals_core/runner.py` | Each case in a run JSON now keeps `turns`: every turn's message, reply and **full trace**. A case with no checks is `UNCHECKED`, never `PASS` |
| `evally/evals_core/traces.py` | `format_conversation`: one conversation as readable text. `evally traces` and `evally label` both use it, so you label exactly what you read |
| `evally/evals_core/labels.py` | `Label` (verdict, note, category, labeller), the JSONL labels file, the labelling loop, the categorising loop and the ranked report |
| `evally/cli.py` | `evally traces <run> [--case ID]` and `evally label <run> [--code \| --report] [--labeler NAME]` |
| `evals/traffic/week02-traffic.jsonl` | 18 conversations standing in for a day of real chats |
| `evals/labels/week02-traffic-qwen3.5-4b.jsonl` | this week's labels |

Labels are appended one line at a time, so quitting halfway (`q`, Ctrl-C or Ctrl-D) loses nothing, and running `evally label` again picks up at the first unlabelled conversation. If a case is labelled twice, the last line wins.

## 4. Traffic, not tests

A deployed app has logs. This one doesn't, so `evals/traffic/week02-traffic.jsonl` stands in for them: 18 conversations written to look like ordinary customer messages. They cover orders, returns, shipping, stock, gift cards, membership, pre-orders, damaged books and privacy. Five have several turns (details given later, a change of mind, an annoyed customer). Several are phrased the way people type ("can i send back a book i didnt like?"), and some ask for things the app isn't built for.

They have **no checks**. Nobody decided in advance what a right answer looks like; that's what reading is for. They were written before the run and not edited afterwards to produce failures.

Recorded once on the local model, then replayed for free:

```
$ uv run evally run --suite evals/traffic/week02-traffic.jsonl
suite week02-traffic · model qwen3.5:4b

  refund-timing        UNCHECKED
  send-back-six-weeks  UNCHECKED
  ...
  password-reset       UNCHECKED

passed 0/0 checked cases, 0/0 checks, 18 unchecked

saved evals/runs/week02-traffic-qwen3.5-4b.json
```

## 5. Reading and labelling

List the conversations, then open one:

```
$ uv run evally traces week02-traffic-qwen3.5-4b
run week02-traffic · model qwen3.5:4b · 18 conversations

  refund-timing        UNCHECKED  1 turn  tools: none
  send-back-six-weeks  UNCHECKED  1 turn  tools: escalate_to_human
  damaged-cover        UNCHECKED  2 turns  tools: lookup_order, start_return
  fast-to-toronto      UNCHECKED  1 turn  tools: escalate_to_human
  ...
```

```
$ uv run evally traces week02-traffic-qwen3.5-4b --case send-back-six-weeks
── send-back-six-weeks ───────────────── UNCHECKED
customer> can i send back a book i didnt like? got it about 6 weeks ago
  docs: damaged-items.md, preorders.md, gift-cards.md
  tool: escalate_to_human {"summary": "Customer asking about returning a book they didn't like, received 6 weeks ago - needs clarification on general returns policy beyond damaged/wrong item policy"}
     → {"ticket": "T-1", "summary": "Customer asking about returning a book they didn't like, received 6 weeks ago - needs clarification on general returns policy beyond damaged/wrong item policy"}
assistant> I'm sorry, but I don't have access to your specific order details or the full return policy for books you simply don't like. The policies I can see only cover damaged/wrong items, pre-orders, and gift cards.
...
```

Read only the reply and this looks like a cautious, polite assistant. The `docs:` line shows what really happened: the customer said "send back", the policy says "return", and keyword search never found `returns.md`. The model answered honestly from what it was given, and what it was given was wrong. This is why you read the whole trace and not only the reply.

### Open coding: a note for every conversation

`evally label` shows each conversation and asks for a verdict and a note:

```
$ uv run evally label week02-traffic-qwen3.5-4b --labeler "your name"
labelling week02-traffic-qwen3.5-4b: 0 of 18 already labelled, saving to evals/labels/week02-traffic-qwen3.5-4b.jsonl

── refund-timing ─────────────────────── UNCHECKED
customer> I mailed my return back last week. When will I get my money?
...
verdict [p]ass / [f]ail / [s]kip / [q]uit: f
note (what went wrong, or what was good; q to quit): Blends the 2023 policy into the answer: ...
```

(An interactive session, shortened where you see `...`; the text after each prompt is what you type.)

A fail needs a note. Write what you saw, specifically, before you have any categories. Three of this week's notes:

> **refund-timing (fail):** Blends the 2023 policy into the answer: offers a 10-business-day store-credit refund and says returns are fine within 60 days "under the older policy". Neither is current (returns.md: 5-7 days, original payment, 30 days).

> **damaged-cover (fail):** Wrong process for a damaged book: starts a normal return and tells her to post it back in its packaging, and promises both a refund and a new copy. damaged-items.md says replacement OR refund, and no need to send the book back. damaged-items.md was never retrieved.

> **club-worth-it (fail):** Wrong maths: 12 books at $20-30 with 10% off is $24-36 a year, not "$12-$15", and free shipping on orders under $35 adds about $60. Then contradicts itself ("likely worth it" / "savings might be minimal").

Every fact in a note was checked against `evally/app/docs/` and the store's seed data. A note that says "bad answer" is no use in the next step; one that says *what* was wrong and *where the right answer was* is.

### Axial coding: grouping the notes

`evally label <run> --code` shows each fail note in turn with the categories made so far, numbered. You pick one by number or type a new name:

```
damaged-cover: Wrong process for a damaged book: starts a normal return and tells her to post it back in its packaging, ...
categories so far:
  1. uses-outdated-policy
  2. misses-the-relevant-policy
category (number, or a new name; q to stop): goes beyond policy
```

(Shortened at `...`. A new name is saved in lowercase with dashes, so this becomes `goes-beyond-policy`.)

Name a category for what the **customer** experienced, not for the code you suspect. "misses-the-relevant-policy" is what happened; "BM25 is weak on synonyms" is a guess about why, and it belongs in the fix, not the label. The six categories this pass produced:

| Category | Definition |
| --- | --- |
| `cant-find-book-by-title` | The customer names a book and gets asked for an ISBN instead of an answer. |
| `goes-beyond-policy` | Promises or suggests something the policy doesn't support, or follows the wrong process. |
| `misses-the-relevant-policy` | The answer is in a policy doc, but the reply says it isn't covered (or escalates) because that doc wasn't retrieved. |
| `unsupported-claims` | States facts or numbers that no source supports: invented features, wrong arithmetic. |
| `needless-escalation` | Opens a human ticket for something a short reply would have handled. |
| `uses-outdated-policy` | Quotes the 2023 returns policy alongside, or instead of, the current one. |

## 6. The ranked list

```
$ uv run evally label week02-traffic-qwen3.5-4b --report
labels for week02-traffic-qwen3.5-4b (labeller: course-author (AI))

  18 labelled · 8 pass · 10 fail

  category                    fails
  cant-find-book-by-title         2
  goes-beyond-policy              2
  misses-the-relevant-policy      2
  unsupported-claims              2
  needless-escalation             1
  uses-outdated-policy            1
```

**10 of 18 conversations failed**, against 9 of 10 cases *passing* in week 1. Same app, same model. The difference is who chose the questions.

Now compare the list with week 1's checks:

| Category | Would a week 1 check catch it? |
| --- | --- |
| `cant-find-book-by-title` | No. Week 1's stock case hands over the ISBN, so it never meets this. |
| `goes-beyond-policy` | Only for price matching (`not_contains "will match"`). The damaged-book and cancellation failures are invisible to it. |
| `misses-the-relevant-policy` | No. Week 1's questions use the docs' own words, so retrieval always found the right file. |
| `unsupported-claims` | No. No check looks at numbers or features the reply invents. |
| `needless-escalation` | No. `tool_not_called` exists but no case uses it. |
| `uses-outdated-policy` | Partly. `return-window`'s check fails any reply containing "60". It would catch `refund-timing`, but only because that reply also quoted the 60-day window; a reply giving just the old "10 business days" refund time would get through. |

Week 1's suite tested the failures its author imagined. Of the six that real-looking traffic shows, it partly covers two.

A pattern runs across the categories too: in four of the ten fails (`send-back-six-weeks`, `fast-to-toronto`, `damaged-cover`, and arguably `refund-timing`), the `docs:` line shows retrieval brought back the wrong policy, or the stale one next to the right one. The labels don't say "retrieval" because they describe what the customer saw. Noticing a shared cause behind several categories is how the analysis points at a fix.

## 7. What these counts can't tell you

Be honest about what this is:

- **18 conversations, one run, one labeller.** Four categories are tied at 2. That's not a ranking; one more conversation could reorder it. Husain and Shankar recommend reviewing at least 100 traces. This lesson uses 18 to show the method, not to rank the app's problems with confidence.
- **The traffic was written, not logged.** It was written to look like real use, but by someone who knows the app. Real logs have questions nobody would think to write.
- **The labels are the course author's.** The course author is an AI assistant, and every label carries `"labeler": "course-author (AI)"`. Real teams label with people who know the domain (here, someone who works in bookstore support), and the person who owns the product should do at least the first pass. Their labels go in the same format: run `evally label` with `--labeler "their name"`, and point `EVALLY_LABELS_DIR` at a separate folder so two people's labels can be compared (exercise 1).
- **Pass/fail is a judgement.** `husbands-order` is labelled pass because nothing leaked and the reply follows `privacy.md`. You might fail it because it offered to tell a third party what's in the parcel if she finds the email. Disagreement between labellers is a finding, and week 6 measures it.

## 8. Exercises

Write your answers in `NOTES.md`.

1. **Label five yourself.** Set `EVALLY_LABELS_DIR=my-labels` so your labels don't mix with the course's, then run `uv run evally label week02-traffic-qwen3.5-4b --labeler "your name"` and label at least five conversations without reading `evals/labels/` first. Then compare. Where do you disagree, and who's right?
2. **Re-categorise.** Copy the course's labels file into `my-labels`, delete the `category` values, and run `--code` yourself. Do you end up with the same six? Fewer? What would you merge?
3. **Add a conversation.** Add one realistic message to the traffic file (something a real customer would send that none of the 18 cover), record it with `--live` (needs Ollama), read it and label it. Did it land in an existing category or make a new one?
4. **Plan week 3.** From the ranked list, pick the two categories you'd measure first, and say what kind of case would catch each. Which of them can a code check (`contains`, `tool_called`) catch, and which needs something smarter?

## 9. In one minute

Writing your eval checks before you've read your app's conversations means you only test the failures you already imagined. We read 18 realistic customer chats with our bookstore assistant, wrote a note on each, and grouped the notes into six kinds of failure. **10 of 18 failed**, against 9 of 10 passing on the hand-written checks from week 1, and week 1's checks only partly cover two of the six. Read first, then decide what to measure.

---

**Tested with:** Python 3.11.8, openai 3.49.0, anthropic 2.8.0, python-dotenv 1.2.4, pytest 9.2.0, Ollama 0.40.16 with `qwen3.5:4b`, on an Apple M2 with 8 GB of RAM. All outputs above are copied from real runs; `...` marks where a long output was shortened. No new libraries this week.
