from evally.app.assistant import FALLBACK_REPLY, Assistant
from evally.app.retrieval import Retriever
from evally.app.store import Store
from evally.llm.scripted import ScriptedModel, text_reply, tool_reply
from evally.types import Message, ToolCall


def make(replies, max_steps=5):
    model = ScriptedModel(replies)
    return Assistant(model, Store.from_seed(), Retriever.from_dir(), max_steps=max_steps), model


def ask(assistant, text):
    return assistant.respond([Message("user", text)])


def test_plain_answer():
    a, _ = make([text_reply("Standard shipping is $4.99.")])
    turn, history = ask(a, "how much is shipping")
    assert turn.reply == "Standard shipping is $4.99."
    assert history[-1] == Message("assistant", "Standard shipping is $4.99.")


def test_tool_round_trip():
    call = ToolCall("c1", "lookup_order", {"order_id": "BB-1002", "email": "ben@example.com"})
    a, model = make([tool_reply(call), text_reply("It has shipped.")])
    turn, _ = ask(a, "where is order BB-1002? ben@example.com")
    assert [s.kind for s in turn.trace] == ["retrieve", "model", "tool", "model"]
    assert turn.reply == "It has shipped."
    assert '"shipped"' in model.calls[1].messages[-1].tool_results[0].content
    assert turn.tools_called == ["lookup_order"]


def test_unknown_tool_returns_error_result():
    a, model = make([tool_reply(ToolCall("c1", "refund_everything", {})), text_reply("Sorry.")])
    ask(a, "refund me")
    assert model.calls[1].messages[-1].tool_results[0].is_error


def test_bad_arguments_return_error_result():
    a, model = make([tool_reply(ToolCall("c1", "lookup_order", {"_raw": "{oops"})), text_reply("Sorry.")])
    ask(a, "order BB-1001")
    assert model.calls[1].messages[-1].tool_results[0].is_error


def test_loop_stops_after_max_steps():
    calls = [tool_reply(ToolCall(f"c{i}", "check_stock", {"isbn": "9780000000011"})) for i in range(6)]
    a, model = make(calls)
    turn, _ = ask(a, "is it in stock")
    assert turn.reply == FALLBACK_REPLY
    assert len(model.calls) == 5


def test_system_prompt_contains_retrieved_docs():
    a, model = make([text_reply("ok")])
    ask(a, "how much is express shipping")
    assert "$12.99" in model.calls[0].system


def test_usage_is_summed():
    call = ToolCall("c1", "check_stock", {"isbn": "9780000000011"})
    a, _ = make([tool_reply(call), text_reply("12 in stock")])
    turn, _ = ask(a, "stock?")
    assert turn.usage.input_tokens == 20 and turn.usage.output_tokens == 10
