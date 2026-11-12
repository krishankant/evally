"""A fake model that replays prepared replies. Tests use it so they run free and offline."""

from __future__ import annotations

from dataclasses import dataclass

from evally.types import Message, ModelResponse, ToolCall, ToolSpec, Usage


@dataclass(frozen=True)
class ScriptedCall:
    messages: list[Message]
    tools: list[ToolSpec]
    system: str | None


class ScriptedModel:
    name = "scripted"

    def __init__(self, responses: list[ModelResponse | Exception]):
        self._responses = list(responses)
        self.calls: list[ScriptedCall] = []

    def complete(self, messages, tools, system=None) -> ModelResponse:
        self.calls.append(ScriptedCall(list(messages), list(tools), system))
        if not self._responses:
            raise RuntimeError("ScriptedModel ran out of responses")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def text_reply(text: str) -> ModelResponse:
    return ModelResponse(Message("assistant", text), "end_turn", Usage(10, 5))


def tool_reply(*calls: ToolCall, text: str = "") -> ModelResponse:
    return ModelResponse(Message("assistant", text, tool_calls=calls), "tool_use", Usage(10, 5))
