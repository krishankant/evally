"""The Bramble Books support assistant: the app this course evaluates.

One turn works like this: search the policies with the customer's last message, put the
top results in the system prompt, then let the model answer or call tools until it gives
a text reply (or hits the step limit). Everything that happens is kept in a trace, so an
eval can check not only what the assistant said but what it did.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from evally.app.retrieval import Retriever
from evally.app.store import Store
from evally.app.tools import TOOLS, run_tool
from evally.llm.base import Model
from evally.types import Message, Usage

# Planted flaw F3: this prompt is deliberately thin. Later weeks measure what that costs.
SYSTEM_PROMPT = """You are the customer support assistant for Bramble Books, an online bookstore.
Answer the customer's question using the policy excerpts below.
Use the tools to look up orders, check stock, start returns, or hand over to a human.

Policy excerpts:
{docs}"""

FALLBACK_REPLY = "Sorry, I couldn't finish that. Let me connect you with a person."


@dataclass(frozen=True)
class TraceStep:
    kind: Literal["retrieve", "model", "tool"]
    data: dict


@dataclass
class Turn:
    reply: str
    trace: list[TraceStep] = field(default_factory=list)
    usage: Usage = Usage()

    @property
    def tools_called(self) -> list[str]:
        return [s.data["name"] for s in self.trace if s.kind == "tool"]


class Assistant:
    def __init__(self, model: Model, store: Store, retriever: Retriever, max_steps: int = 5, k: int = 3):
        self.model, self.store, self.retriever = model, store, retriever
        self.max_steps, self.k = max_steps, k

    def respond(self, history: list[Message]) -> tuple[Turn, list[Message]]:
        history = list(history)
        query = next((m.text for m in reversed(history) if m.role == "user" and m.text), "")
        hits = self.retriever.search(query, k=self.k)
        trace = [TraceStep("retrieve", {"query": query, "docs": [h.name for h in hits]})]
        docs = "\n\n".join(f"[{h.name}]\n{h.text.strip()}" for h in hits) or "(none found)"
        system = SYSTEM_PROMPT.format(docs=docs)
        tin = tout = 0

        for _ in range(self.max_steps):
            resp = self.model.complete(history, TOOLS, system)
            tin, tout = tin + resp.usage.input_tokens, tout + resp.usage.output_tokens
            msg = resp.message
            trace.append(TraceStep("model", {"text": msg.text, "tool_calls": [c.name for c in msg.tool_calls],
                                             "stop_reason": resp.stop_reason}))
            history.append(Message("assistant", msg.text, tool_calls=msg.tool_calls))
            if not msg.tool_calls:
                return Turn(msg.text, trace, Usage(tin, tout)), history
            results = []
            for call in msg.tool_calls:
                result = run_tool(self.store, call)
                trace.append(TraceStep("tool", {"name": call.name, "arguments": call.arguments,
                                                "result": result.content, "is_error": result.is_error}))
                results.append(result)
            history.append(Message("user", tool_results=tuple(results)))

        trace.append(TraceStep("model", {"text": FALLBACK_REPLY, "tool_calls": [], "stop_reason": "max_steps"}))
        history.append(Message("assistant", FALLBACK_REPLY))
        return Turn(FALLBACK_REPLY, trace, Usage(tin, tout)), history
