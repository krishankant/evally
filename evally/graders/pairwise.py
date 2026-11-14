"""Which reply is better, A or B? Asked twice, with the order swapped.

A grader that picks A whatever A is has a position bias. Asking in both orders shows it:
a fair grader gives the same answer (in run labels) both times. Week 5 uses this to show
three biases with numbers:

- position: a run against itself (identical replies, so anything but a tie is bias);
- length: a run against `pad_run` of itself (same content plus one sentence of filler);
- self-preference: two models' runs, each judged by both models.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from evally.graders.judge import _first_json_object
from evally.llm.base import Model
from evally.llm.prices import format_cost
from evally.types import Message, ToolSpec

PADDING = ("I hope this helps, and please don't hesitate to reach out if you have any other "
           "questions about your order or our policies. We're always happy to help!")

PREFER_TOOL = ToolSpec(
    "record_preference",
    "Record which reply is better.",
    {"type": "object",
     "properties": {"reason": {"type": "string", "description": "One or two sentences: why."},
                    "winner": {"type": "string", "enum": ["A", "B", "tie"]}},
     "required": ["reason", "winner"]},
)

PAIRWISE_SYSTEM = """You compare two replies from Bramble Books' customer support assistant to the same customer message.

The better reply answers the customer correctly and helpfully, following the policies below. The policies are the only truth.

{reference}

Answer only by calling the record_preference tool: your reason first, then the winner, A, B or tie."""


@dataclass(frozen=True)
class PairResult:
    case_id: str
    first_a: str  # the winner in run labels ("a", "b", "tie", "error") when A was shown first
    first_b: str  # ... when B was shown first


def prefer(model: Model, context: str, reply_a: str, reply_b: str, reference: str) -> tuple[str, str, dict]:
    """(winner "A"/"B"/"tie"/"error", reason, tokens)."""
    prompt = f"Customer message:\n{context}\n\nReply A:\n{reply_a}\n\nReply B:\n{reply_b}"
    resp = model.complete([Message("user", prompt)], [PREFER_TOOL], PAIRWISE_SYSTEM.format(reference=reference))
    tokens = {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens}
    args = next((c.arguments for c in resp.message.tool_calls if c.name == PREFER_TOOL.name), None)
    if args is None:
        args = _first_json_object(resp.message.text)
    if isinstance(args, dict) and args.get("winner") in ("A", "B", "tie"):
        return args["winner"], str(args.get("reason", "")), tokens
    return "error", resp.message.text[:200], tokens


def _usable(case: dict | None) -> str:
    if case is None or case.get("status") == "ERROR":
        return "error"
    return "ok" if len(case.get("turns", [])) == 1 else "multiturn"


def bias_test(model: Model, run_a: dict, run_b: dict, reference: str) -> tuple[list[PairResult], dict]:
    if run_a.get("suite") != run_b.get("suite"):
        raise ValueError(f"runs came from different suites: {run_a.get('suite')}, {run_b.get('suite')}")
    b_cases = {c["id"]: c for c in run_b["cases"]}
    s = {"pairs": 0, "skipped_multiturn": 0, "skipped_errors": 0, "consistent": 0, "first_position_wins": 0,
         "a_wins": 0, "b_wins": 0, "ties": 0, "errors": 0, "tokens": {"input": 0, "output": 0}}
    pairs: list[PairResult] = []
    for ca in run_a["cases"]:
        cb = b_cases.get(ca["id"])
        states = {_usable(ca), _usable(cb)}
        if "error" in states:
            s["skipped_errors"] += 1
            continue
        if "multiturn" in states:
            s["skipped_multiturn"] += 1
            continue
        # Only the customer's message: each run's tool calls differ, and sharing one run's
        # tool results would favour that run.
        context = ca["turns"][0]["user"]
        reply_a, reply_b = ca["turns"][-1]["reply"], cb["turns"][-1]["reply"]
        raw1, _, t1 = prefer(model, context, reply_a, reply_b, reference)
        raw2, _, t2 = prefer(model, context, reply_b, reply_a, reference)
        first_a = {"A": "a", "B": "b"}.get(raw1, raw1)
        first_b = {"A": "b", "B": "a"}.get(raw2, raw2)
        pairs.append(PairResult(ca["id"], first_a, first_b))
        s["pairs"] += 1
        s["first_position_wins"] += (raw1 == "A") + (raw2 == "A")
        s["errors"] += (raw1 == "error") + (raw2 == "error")
        for t in (t1, t2):
            s["tokens"]["input"] += t["input"]
            s["tokens"]["output"] += t["output"]
        if first_a == first_b and first_a != "error":
            s["consistent"] += 1
            s[{"a": "a_wins", "b": "b_wins", "tie": "ties"}[first_a]] += 1
    return pairs, s


def format_bias(name_a: str, name_b: str, grader: str, pairs: list[PairResult], s: dict) -> str:
    w = max([len(p.case_id) for p in pairs] + [4])
    lines = [f"A = {name_a}", f"B = {name_b}", f"grader {grader}", ""]
    for p in pairs:
        same = "consistent" if p.first_a == p.first_b and p.first_a != "error" else "inconsistent"
        lines.append(f"  {p.case_id:<{w}}  A-first: {p.first_a:<5}  B-first: {p.first_b:<5}  {same}")
    lines += [
        "",
        f"pairs {s['pairs']} (skipped: {s['skipped_multiturn']} multi-turn, {s['skipped_errors']} errored)",
        f"consistent under swap {s['consistent']}/{s['pairs']}",
        f"picked the reply shown first {s['first_position_wins']}/{2 * s['pairs']}",
        f"consistent pairs: A {s['a_wins']}, B {s['b_wins']}, tie {s['ties']}",
        f"grader errors {s['errors']}",
        format_cost(grader, s["tokens"]["input"], s["tokens"]["output"]),
    ]
    return "\n".join(lines)


def pad_run(run: dict) -> dict:
    padded = copy.deepcopy(run)
    padded["model"] = f"{run['model']}+padded"
    for case in padded["cases"]:
        if case.get("replies"):
            case["replies"][-1] = f"{case['replies'][-1]} {PADDING}"
        if case.get("turns"):
            case["turns"][-1]["reply"] = f"{case['turns'][-1]['reply']} {PADDING}"
    return padded
