import pytest

from evally.llm.scripted import ScriptedModel, text_reply
from evally.types import Message


def test_scripted_replays_in_order_and_records_calls():
    m = ScriptedModel([text_reply("one"), text_reply("two")])
    hist = [Message("user", "hi")]
    assert m.complete(hist, [], system="sys").message.text == "one"
    assert m.complete(hist, []).message.text == "two"
    assert m.calls[0].system == "sys"


def test_scripted_raises_when_empty():
    m = ScriptedModel([text_reply("one")])
    m.complete([], [])
    with pytest.raises(RuntimeError):
        m.complete([], [])
