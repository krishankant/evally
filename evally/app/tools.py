"""The four tools the assistant can call. Each returns text: JSON on success, a sentence otherwise."""

from __future__ import annotations

import json
from datetime import date

from evally.app.store import RETURN_WINDOW_DAYS, TODAY, Store
from evally.types import ToolCall, ToolResult, ToolSpec


class ToolError(Exception):
    """A tool failed; the message goes back to the model as an error result."""


def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
            "required": required}


TOOLS = [
    ToolSpec("lookup_order", "Look up an order. Needs the order id (like BB-1001) and the email on the order.",
             _obj({"order_id": "Order id, like BB-1001", "email": "Email address on the order"}, ["order_id", "email"])),
    ToolSpec("check_stock", "Check how many copies of a book are in stock, by ISBN.",
             _obj({"isbn": "13-digit ISBN"}, ["isbn"])),
    ToolSpec("start_return", "Start a return for a delivered order.",
             _obj({"order_id": "Order id", "email": "Email on the order", "reason": "Why it's being returned"},
                  ["order_id", "email", "reason"])),
    ToolSpec("escalate_to_human", "Hand the conversation to a human agent.",
             _obj({"summary": "One-line summary of the problem"}, ["summary"])),
]


def lookup_order(store: Store, order_id: str, email: str) -> str:
    order = store.order(order_id, email)
    return json.dumps(order) if order else "No order found for that order id and email."


def check_stock(store: Store, isbn: str) -> str:
    book = store.book(isbn)
    if book is None:
        return "No book with that ISBN."
    if book["warehouse"] == "north":
        # Planted flaw F2: the north warehouse's inventory service always times out.
        raise ToolError("inventory service timeout")
    return json.dumps({"isbn": book["isbn"], "title": book["title"], "in_stock": book["stock"]})


def start_return(store: Store, order_id: str, email: str, reason: str) -> str:
    order = store.order(order_id, email)
    if order is None:
        return "No order found for that order id and email."
    if order["status"] != "delivered":
        raise ToolError(f"Order {order['order_id']} is {order['status']}; only delivered orders can be returned.")
    days = (TODAY - date.fromisoformat(order["delivered"])).days
    if days > RETURN_WINDOW_DAYS:
        raise ToolError(f"Delivered {days} days ago; returns are only accepted within {RETURN_WINDOW_DAYS} days.")
    return json.dumps({"return_id": f"R-{order['order_id']}", "status": "return started",
                       "refund": "to the original payment method within 5-7 business days of receipt"})


def escalate_to_human(store: Store, summary: str) -> str:
    return json.dumps({"ticket": store.next_ticket(), "summary": summary})


_IMPL = {"lookup_order": lookup_order, "check_stock": check_stock,
         "start_return": start_return, "escalate_to_human": escalate_to_human}
_REQUIRED = {t.name: t.parameters["required"] for t in TOOLS}


def run_tool(store: Store, call: ToolCall) -> ToolResult:
    """Run one tool call. Never raises: every problem becomes an error result for the model."""
    fn = _IMPL.get(call.name)
    if fn is None:
        return ToolResult(call.id, f"Unknown tool {call.name!r}.", is_error=True)
    args = call.arguments
    missing = [k for k in _REQUIRED[call.name] if not isinstance(args.get(k), str) or not args.get(k)]
    if missing:
        return ToolResult(call.id, f"Missing or invalid argument(s): {', '.join(missing)}.", is_error=True)
    try:
        return ToolResult(call.id, fn(store, **{k: args[k] for k in _REQUIRED[call.name]}))
    except ToolError as e:
        return ToolResult(call.id, str(e), is_error=True)
