"""Read saved conversations: one run JSON in, readable text out.

`evally traces` and `evally label` both print a conversation with `format_conversation`,
so what you label is exactly what you read.
"""

from __future__ import annotations

import json
from pathlib import Path

RESULT_CHARS = 200
WIDTH = 50


def run_path(name: str, runs_dir: Path) -> Path:
    """A run by name (`week02-traffic-qwen3.5-4b`), by file name, or by path."""
    p = Path(name)
    if p.suffix == ".json" and p.exists():
        return p
    return Path(runs_dir) / (name if name.endswith(".json") else f"{name}.json")


def _cut(text: str) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= RESULT_CHARS else text[:RESULT_CHARS] + "…"


def format_conversation(case: dict) -> str:
    head = f"── {case['id']} "
    status = case.get("status", "")
    lines = [head + "─" * max(3, WIDTH - len(head) - len(status) - 1) + f" {status}"]
    for turn in case.get("turns", []):
        lines.append(f"customer> {turn['user']}")
        for step in turn.get("trace", []):
            d = step["data"]
            if step["kind"] == "retrieve":
                lines.append(f"  docs: {', '.join(d['docs']) or 'none'}")
            elif step["kind"] == "tool":
                lines.append(f"  tool: {d['name']} {json.dumps(d['arguments'])}")
                lines.append(f"     → {'ERROR ' if d.get('is_error') else ''}{_cut(d['result'])}")
        lines.append(f"assistant> {turn['reply']}")
    if case.get("error"):
        lines.append(f"  (stopped: {case['error']})")
    return "\n".join(lines)


def format_case_list(run: dict) -> str:
    cases = run["cases"]
    w = max([len(c["id"]) for c in cases] + [4])
    sw = max([len(c["status"]) for c in cases] + [5])
    lines = [f"run {run['suite']} · model {run['model']} · {len(cases)} conversations", ""]
    for c in cases:
        n = len(c.get("turns", []))
        names = [s["data"]["name"] for t in c.get("turns", []) for s in t["trace"] if s["kind"] == "tool"]
        tools = ", ".join(dict.fromkeys(names)) or "none"
        lines.append(f"  {c['id']:<{w}}  {c['status']:<{sw}}  {n} turn{'s' if n != 1 else ''}  tools: {tools}")
    return "\n".join(lines)
