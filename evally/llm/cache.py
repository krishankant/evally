"""Record and replay model calls.

In record mode every new request goes to the real model and the reply is saved as a
JSON file, keyed by a hash of the request. In replay mode the saved replies come back
and nothing is sent anywhere. The course commits its recordings, so every demo runs
with no API key and no cost.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from evally.llm.base import Model
from evally.types import Message, ModelResponse, ToolSpec, message_to_dict, response_from_dict, response_to_dict


class ReplayMiss(Exception):
    def __init__(self) -> None:
        super().__init__(
            "No recorded response for this request. Re-run with --live to call the model "
            "(needs Ollama or an API key)."
        )


def _request(model_name: str, messages: list[Message], tools: list[ToolSpec], system: str | None) -> dict:
    return {
        "model": model_name,
        "system": system,
        "messages": [message_to_dict(m) for m in messages],  # drops provider raw blobs
        "tools": [asdict(t) for t in tools],
    }


def cache_key(model_name: str, messages: list[Message], tools: list[ToolSpec], system: str | None) -> str:
    blob = json.dumps(_request(model_name, messages, tools, system), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


class CachedModel:
    def __init__(self, inner: Model | None, cache_dir: Path, mode: Literal["replay", "record"]):
        if mode == "record" and inner is None:
            raise ValueError("record mode needs a live model")
        self.inner, self.dir, self.mode = inner, Path(cache_dir), mode
        name_file = self.dir / "model.txt"
        if inner is not None:
            self.name = inner.name
        elif name_file.exists():
            self.name = name_file.read_text().strip()
        else:
            self.name = "unrecorded"

    def complete(self, messages, tools, system=None) -> ModelResponse:
        key = cache_key(self.name, messages, tools, system)
        path = self.dir / key[:2] / f"{key}.json"
        if path.exists():
            return response_from_dict(json.loads(path.read_text())["response"])
        if self.mode == "replay":
            raise ReplayMiss()
        response = self.inner.complete(messages, tools, system)
        path.parent.mkdir(parents=True, exist_ok=True)
        (self.dir / "model.txt").write_text(self.name + "\n")
        record = {"request": _request(self.name, messages, tools, system), "response": response_to_dict(response)}
        path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
        return response_from_dict(response_to_dict(response))  # same shape as a replay
