# Week 1 vibe check

Three easy questions, typed by hand into `evally chat` (live, local `qwen3.5:4b` via Ollama),
on 2026-11-12. Each is a fresh chat. Output is copied as printed; the `[docs | tools]` line is
what the assistant retrieved and called.

## 1. Opening hours

```
you> Hi, what are your opening hours?
bot> I'd be happy to help you with your question about opening hours! However, I don't have access to our specific business hours information through my current tools.

For the most accurate and up-to-date information about Bramble Books' opening hours, I'd recommend:

1. Checking our official website at bramblebooks.com
2. Contacting our customer service team directly
3. Looking for any physical store locations if you're in a specific area

Would you like me to help you with anything else regarding your order, stock availability, or return process?
     [docs: none | tools: none]
```

## 2. Gift cards

```
you> Do you sell gift cards?
bot> Yes, Bramble Books does sell gift cards! According to our policy, we offer gift cards in any amount from $10 to $200, and they never expire. Gift cards can be used for books and memberships.
     [docs: gift-cards.md, membership.md, returns.md | tools: none]
```

## 3. Standard shipping

```
you> How long does standard shipping take?
bot> Standard shipping takes **3-5 business days** for delivery.

For reference, standard shipping costs $4.99 but is free on orders over $35. Orders placed before 2 pm Eastern on a business day ship the same day.
     [docs: membership.md, shipping.md, international-shipping.md | tools: none]
```

## Verdict

All three read well, and a vibe check would call the assistant good. Checked against the docs:

- **2 and 3 are correct**, word for word with `gift-cards.md` and `shipping.md`.
- **1 sounds helpful but invents a fact.** No document mentions a website, and
  `bramblebooks.com` appears nowhere in the policies. The polite refusal hides a made-up URL.
  Reading it, you'd nod along. Only checking it against the sources catches it, which is the
  point of week 1: a reply that sounds right isn't evidence that it is right.
