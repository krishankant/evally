"""An LLM grader: one rubric, one saved conversation, one verdict with a reason.

The grader answers by calling a tool (`record_verdict`, or `record_score` on the 1-5
scale). Every provider supports tool calls, so the same code gets structured output
from Anthropic, OpenAI and Ollama. The reason comes before the verdict, so the model
explains first and decides second.

The grader sees only the conversation and the current policies. It never sees the case
id, the code checks' verdict or the tags: any of those would hand it the answer.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from evally.app.retrieval import DOCS_DIR
from evally.graders.rubrics import Rubric
from evally.llm.base import Model
from evally.types import Message, ModelResponse, ToolSpec

Scale = Literal["binary", "1-5"]
SUPERSEDED = {"returns-2023.md"}  # the planted stale policy: never part of the truth
RESULT_CHARS = 200
PASS_SCORE = 4  # on the 1-5 scale, 4 and 5 pass

VERDICT_TOOL = ToolSpec(
    "record_verdict",
    "Record your verdict on the last assistant reply.",
    {"type": "object",
     "properties": {"reason": {"type": "string", "description": "One or two sentences: why."},
                    "verdict": {"type": "string", "enum": ["pass", "fail"]}},
     "required": ["reason", "verdict"]},
)
SCORE_TOOL = ToolSpec(
    "record_score",
    "Record your score for the last assistant reply.",
    {"type": "object",
     "properties": {"reason": {"type": "string", "description": "One or two sentences: why."},
                    "score": {"type": "integer", "minimum": 1, "maximum": 5,
                              "description": "1 = fails the rubric completely, 5 = fully meets it"}},
     "required": ["reason", "score"]},
)

GRADER_SYSTEM = """You grade replies from Bramble Books' customer support assistant.

Judge only the LAST assistant reply in the conversation, and only against this rubric:

{rubric}

The policies below are the only truth. Anything they don't say is not policy.

{reference}

Answer only by calling the {tool} tool. Give your reason first, then your {what}."""


@dataclass(frozen=True)
class Verdict:
    case_id: str
    rubric: str
    verdict: Literal["pass", "fail", "error"]
    reason: str
    score: int | None = None
    tokens: dict = field(default_factory=dict)


def policy_reference(docs_dir: Path | None = None) -> str:
    docs = sorted(p for p in Path(docs_dir or DOCS_DIR).glob("*.md") if p.name not in SUPERSEDED)
    return "\n\n".join(f"## {p.name}\n\n{p.read_text().strip()}" for p in docs)


def _cut(text: str) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= RESULT_CHARS else text[:RESULT_CHARS - 1] + "…"


def conversation_for_grader(case: dict) -> str:
    lines: list[str] = []
    for turn in case.get("turns", []):
        lines.append(f"customer: {turn['user']}")
        for step in turn.get("trace", []):
            if step["kind"] == "tool":
                d = step["data"]
                err = "ERROR " if d.get("is_error") else ""
                lines.append(f"  (tool {d['name']} {json.dumps(d['arguments'])} → {err}{_cut(d['result'])})")
        lines.append(f"assistant: {turn['reply']}")
    return "\n".join(lines)


def _first_json_object(text: str) -> dict | None:
    for m in re.finditer(r"\{", text):
        try:
            value, _ = json.JSONDecoder().raw_decode(text[m.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def parse_verdict(response: ModelResponse, scale: Scale) -> tuple[str, str, int | None]:
    """(verdict, reason, score). Anything that isn't a valid verdict is ("error", why, None)."""
    tool = (SCORE_TOOL if scale == "1-5" else VERDICT_TOOL).name
    args = next((c.arguments for c in response.message.tool_calls if c.name == tool), None)
    if args is None:
        args = _first_json_object(response.message.text)
    if isinstance(args, dict):
        reason = str(args.get("reason", "")).strip()
        if scale == "1-5":
            score = args.get("score")
            if type(score) is int and 1 <= score <= 5:
                return ("pass" if score >= PASS_SCORE else "fail"), reason, score
        elif args.get("verdict") in ("pass", "fail"):
            return args["verdict"], reason, None
    raw = response.message.text or json.dumps([c.arguments for c in response.message.tool_calls])
    return "error", f"grader gave no verdict: {_cut(raw)}", None


def judge_case(model: Model, rubric: Rubric, case: dict, reference: str, scale: Scale = "binary") -> Verdict:
    tool = SCORE_TOOL if scale == "1-5" else VERDICT_TOOL
    system = GRADER_SYSTEM.format(rubric=rubric.text, reference=reference, tool=tool.name,
                                  what="score from 1 to 5" if scale == "1-5" else "verdict, pass or fail")
    response = model.complete([Message("user", conversation_for_grader(case))], [tool], system)
    verdict, reason, score = parse_verdict(response, scale)
    tokens = {"input": response.usage.input_tokens, "output": response.usage.output_tokens}
    return Verdict(case["id"], rubric.name, verdict, reason, score, tokens)
