from dataclasses import replace

from evally.types import (
    Message, ModelResponse, ToolCall, ToolResult, Usage,
    message_from_dict, message_to_dict, response_from_dict, response_to_dict,
)


def _msg():
    return Message(
        role="assistant",
        text="checking",
        tool_calls=(ToolCall("c1", "lookup_order", {"order_id": "BB-1001"}),),
        tool_results=(ToolResult("c0", "boom", is_error=True),),
        raw={"provider": "blob"},
    )


def test_message_round_trip():
    m = _msg()
    assert message_from_dict(message_to_dict(m)) == replace(m, raw=None)


def test_response_round_trip():
    r = ModelResponse(_msg(), "tool_use", Usage(12, 7))
    back = response_from_dict(response_to_dict(r))
    assert back == replace(r, message=replace(r.message, raw=None))
