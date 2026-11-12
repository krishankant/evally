from evally.llm.anthropic_model import from_anthropic_response, to_anthropic_messages
from evally.llm.factory import make_model
from evally.llm.openai_compat import OpenAICompatModel, from_openai_response, to_openai_messages
from evally.types import Message, ToolCall, ToolResult


def _openai_resp(arguments: str) -> dict:
    return {
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {"role": "assistant", "content": None, "tool_calls": [
                {"id": "c1", "type": "function",
                 "function": {"name": "lookup_order", "arguments": arguments}}]},
        }],
        "usage": {"prompt_tokens": 30, "completion_tokens": 8},
    }


def test_openai_tool_call_parsed():
    r = from_openai_response(_openai_resp('{"order_id": "BB-1001"}'))
    assert r.stop_reason == "tool_use"
    assert r.message.tool_calls == (ToolCall("c1", "lookup_order", {"order_id": "BB-1001"}),)
    assert r.usage.input_tokens == 30


def test_openai_bad_arguments_kept_raw():
    r = from_openai_response(_openai_resp("not json"))
    assert r.message.tool_calls[0].arguments == {"_raw": "not json"}


def test_openai_tool_result_message():
    msgs = to_openai_messages([Message("user", tool_results=(ToolResult("c1", "boom", True),))], "sys")
    assert msgs == [
        {"role": "system", "content": "sys"},
        {"role": "tool", "tool_call_id": "c1", "content": "ERROR: boom"},
    ]


def test_anthropic_tool_use_parsed():
    resp = {
        "content": [{"type": "text", "text": "Let me check."},
                    {"type": "tool_use", "id": "t1", "name": "check_stock", "input": {"isbn": "123"}}],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 40, "output_tokens": 9},
    }
    r = from_anthropic_response(resp)
    assert r.message.text == "Let me check."
    assert r.message.tool_calls == (ToolCall("t1", "check_stock", {"isbn": "123"}),)
    assert r.stop_reason == "tool_use"


def test_anthropic_tool_result_block():
    msgs = to_anthropic_messages([Message("user", tool_results=(ToolResult("t1", "boom", True),))])
    assert msgs == [{"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "boom", "is_error": True}]}]


def test_make_model_ollama_uses_local_base_url(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://localhost:9999/v1")
    m = make_model("ollama", "qwen3.5:4b")
    assert isinstance(m, OpenAICompatModel)
    assert m.name == "qwen3.5:4b"
    assert str(m._client.base_url).startswith("http://localhost:9999/v1")
