import pytest

from evally.llm.cache import CachedModel, ReplayMiss, cache_key
from evally.llm.scripted import ScriptedModel, text_reply
from evally.types import Message, ToolSpec

HIST = [Message("user", "hi")]
TOOLS = [ToolSpec("check_stock", "Check stock", {"type": "object", "properties": {"isbn": {"type": "string"}}})]


def test_record_then_replay_without_inner(tmp_path):
    rec = CachedModel(ScriptedModel([text_reply("hello")]), tmp_path, "record")
    first = rec.complete(HIST, TOOLS, "sys")
    rep = CachedModel(None, tmp_path, "replay")
    assert rep.complete(HIST, TOOLS, "sys") == first
    assert rep.name == "scripted"


def test_replay_miss_message(tmp_path):
    rep = CachedModel(None, tmp_path, "replay")
    with pytest.raises(ReplayMiss) as e:
        rep.complete(HIST, TOOLS, "sys")
    assert str(e.value) == (
        "No recorded response for this request. Re-run with --live to call the model "
        "(needs Ollama or an API key)."
    )


def test_key_ignores_raw_and_dict_order():
    a = cache_key("m", [Message("user", "hi", raw={"x": 1})], TOOLS, "sys")
    flipped = [ToolSpec("check_stock", "Check stock", {"properties": {"isbn": {"type": "string"}}, "type": "object"})]
    b = cache_key("m", [Message("user", "hi", raw={"y": 2})], flipped, "sys")
    assert a == b
    assert a != cache_key("m", [Message("user", "hello")], TOOLS, "sys")


def test_record_hit_does_not_call_inner(tmp_path):
    inner = ScriptedModel([text_reply("only once")])
    rec = CachedModel(inner, tmp_path, "record")
    rec.complete(HIST, TOOLS, "sys")
    assert rec.complete(HIST, TOOLS, "sys").message.text == "only once"
    assert len(inner.calls) == 1
