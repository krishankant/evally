"""Adapter for Anthropic's Messages API."""

from __future__ import annotations

from typing import Any

from evally.types import Message, ModelResponse, StopReason, ToolCall, ToolSpec, Usage

_STOP: dict[str, StopReason] = {
    "end_turn": "end_turn",
    "stop_sequence": "end_turn",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
    "refusal": "refused",
}


def to_anthropic_tools(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    return [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools]


def to_anthropic_messages(messages: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        blocks: list[dict[str, Any]] = []
        if m.role == "assistant":
            if m.text:
                blocks.append({"type": "text", "text": m.text})
            blocks += [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments}
                       for c in m.tool_calls]
        else:
            blocks += [{"type": "tool_result", "tool_use_id": r.tool_call_id, "content": r.content,
                        "is_error": r.is_error} for r in m.tool_results]
            if m.text:
                blocks.append({"type": "text", "text": m.text})
        out.append({"role": m.role, "content": blocks})
    return out


def from_anthropic_response(resp: dict[str, Any]) -> ModelResponse:
    text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    calls = tuple(ToolCall(b["id"], b["name"], b.get("input") or {})
                  for b in resp.get("content", []) if b.get("type") == "tool_use")
    usage = resp.get("usage") or {}
    return ModelResponse(
        Message("assistant", text, tool_calls=calls, raw=resp.get("content")),
        _STOP.get(resp.get("stop_reason") or "", "error"),
        Usage(usage.get("input_tokens") or 0, usage.get("output_tokens") or 0),
    )


class AnthropicModel:
    def __init__(self, model: str, client: Any = None, max_tokens: int = 1024):
        self.name = model
        self.max_tokens = max_tokens
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self._client = client

    def complete(self, messages, tools, system=None) -> ModelResponse:
        kwargs: dict[str, Any] = {"model": self.name, "max_tokens": self.max_tokens,
                                  "messages": to_anthropic_messages(messages), "temperature": 0}
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = to_anthropic_tools(tools)
        resp = self._client.messages.create(**kwargs)
        return from_anthropic_response(resp.model_dump(mode="json", exclude_none=True))
