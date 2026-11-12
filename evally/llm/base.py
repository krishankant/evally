from __future__ import annotations

from typing import Protocol, runtime_checkable

from evally.types import Message, ModelResponse, ToolSpec


@runtime_checkable
class Model(Protocol):
    """Anything that takes a conversation and returns the next assistant turn."""

    name: str

    def complete(
        self, messages: list[Message], tools: list[ToolSpec], system: str | None = None
    ) -> ModelResponse: ...
