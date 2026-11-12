"""Adapter for OpenAI's Chat Completions API and any server that speaks it, such as Ollama."""

from __future__ import annotations

import json
from typing import Any

from evally.types import Message, ModelResponse, StopReason, ToolCall, ToolSpec, Usage

_FINISH: dict[str, StopReason] = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
    "content_filter": "refused",
}


def to_openai_tools(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    return [{"type": "function", "function": {"name": t.name, "description": t.description,
                                              "parameters": t.parameters}} for t in tools]


def to_openai_messages(messages: list[Message], system: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if system:
        out.append({"role": "system", "content": system})
    for m in messages:
        if m.role == "assistant":
            msg: dict[str, Any] = {"role": "assistant", "content": m.text or (None if m.tool_calls else "")}
            if m.tool_calls:
                msg["tool_calls"] = [{"id": c.id, "type": "function",
                                      "function": {"name": c.name, "arguments": json.dumps(c.arguments)}}
                                     for c in m.tool_calls]
            out.append(msg)
            continue
        # This API has no error flag on tool results, so we mark errors in the text.
        for r in m.tool_results:
            out.append({"role": "tool", "tool_call_id": r.tool_call_id,
                        "content": f"ERROR: {r.content}" if r.is_error else r.content})
        if m.text:
            out.append({"role": "user", "content": m.text})
    return out


def _parse_arguments(raw: str) -> dict:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw}
    return value if isinstance(value, dict) else {"_raw": raw}


def from_openai_response(resp: dict[str, Any]) -> ModelResponse:
    choice = (resp.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    calls = tuple(
        ToolCall(tc.get("id", ""), (tc.get("function") or {}).get("name", ""),
                 _parse_arguments((tc.get("function") or {}).get("arguments") or "{}"))
        for tc in msg.get("tool_calls") or []
    )
    usage = resp.get("usage") or {}
    return ModelResponse(
        Message("assistant", msg.get("content") or "", tool_calls=calls, raw=msg),
        _FINISH.get(choice.get("finish_reason") or "", "error"),
        Usage(usage.get("prompt_tokens") or 0, usage.get("completion_tokens") or 0),
    )


class OpenAICompatModel:
    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None, client: Any = None):
        self.name = model
        if client is None:
            import openai

            client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self._client = client

    def complete(self, messages, tools, system=None) -> ModelResponse:
        kwargs: dict[str, Any] = {"model": self.name, "messages": to_openai_messages(messages, system),
                                  "temperature": 0}
        if tools:  # the API rejects an empty tools list
            kwargs["tools"] = to_openai_tools(tools)
        resp = self._client.chat.completions.create(**kwargs)
        return from_openai_response(resp.model_dump(mode="json", exclude_none=True))
