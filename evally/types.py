"""The shapes every part of evally passes around: messages, tool calls, model replies.

Provider adapters translate to and from these, so the app, the cache and the evals
never see a provider's own format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

StopReason = Literal["end_turn", "tool_use", "max_tokens", "refused", "error"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON Schema for the arguments


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class ToolResult:
    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant"]
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()
    raw: Any = field(default=None, compare=True)  # provider's own payload; never cached


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class ModelResponse:
    message: Message
    stop_reason: StopReason
    usage: Usage = Usage()


def message_to_dict(m: Message) -> dict:
    return {
        "role": m.role,
        "text": m.text,
        "tool_calls": [{"id": c.id, "name": c.name, "arguments": c.arguments} for c in m.tool_calls],
        "tool_results": [
            {"tool_call_id": r.tool_call_id, "content": r.content, "is_error": r.is_error}
            for r in m.tool_results
        ],
    }


def message_from_dict(d: dict) -> Message:
    return Message(
        role=d["role"],
        text=d.get("text", ""),
        tool_calls=tuple(ToolCall(c["id"], c["name"], c["arguments"]) for c in d.get("tool_calls", [])),
        tool_results=tuple(
            ToolResult(r["tool_call_id"], r["content"], r.get("is_error", False))
            for r in d.get("tool_results", [])
        ),
    )


def response_to_dict(r: ModelResponse) -> dict:
    return {
        "message": message_to_dict(r.message),
        "stop_reason": r.stop_reason,
        "usage": {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens},
    }


def response_from_dict(d: dict) -> ModelResponse:
    u = d.get("usage", {})
    return ModelResponse(
        message_from_dict(d["message"]),
        d["stop_reason"],
        Usage(u.get("input_tokens", 0), u.get("output_tokens", 0)),
    )
