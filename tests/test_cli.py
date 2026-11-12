import httpx2
import openai

from evally import cli
from evally.app.assistant import Assistant
from evally.app.retrieval import Retriever
from evally.app.store import Store
from evally.llm.cache import CachedModel
from evally.llm.scripted import ScriptedModel, text_reply
from evally.types import Message

SUITE = '{"id": "ship", "turns": ["how much is shipping"], "checks": [{"type": "contains", "value": "4.99"}]}\n'


def setup(tmp_path, monkeypatch, record=True):
    suite = tmp_path / "s.jsonl"
    suite.write_text(SUITE)
    monkeypatch.setenv("EVALLY_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("EVALLY_RUNS_DIR", str(tmp_path / "runs"))
    if record:
        model = CachedModel(ScriptedModel([text_reply("It's $4.99.")]), tmp_path / "cache" / "ollama-m", "record")
        Assistant(model, Store.from_seed(), Retriever.from_dir()).respond([Message("user", "how much is shipping")])
    return suite


def test_run_replay_prints_table(tmp_path, monkeypatch, capsys):
    suite = setup(tmp_path, monkeypatch)
    assert cli.main(["run", "--suite", str(suite), "--provider", "ollama", "--model", "m"]) == 0
    out = capsys.readouterr().out
    assert "passed 1/1 cases" in out
    assert (tmp_path / "runs" / "s-scripted.json").exists()


def test_run_replay_miss_shows_message(tmp_path, monkeypatch, capsys):
    suite = setup(tmp_path, monkeypatch, record=False)
    assert cli.main(["run", "--suite", str(suite), "--provider", "ollama", "--model", "m"]) == 0
    assert "Re-run with --live" in capsys.readouterr().out


class Unreachable:
    name = "m"

    def complete(self, messages, tools, system=None):
        raise openai.APIConnectionError(request=httpx2.Request("POST", "http://localhost:11434/v1"))


def test_live_connection_error_message(tmp_path, monkeypatch, capsys):
    suite = setup(tmp_path, monkeypatch, record=False)
    monkeypatch.setattr(cli, "make_model", lambda provider, model: Unreachable())
    assert cli.main(["run", "--suite", str(suite), "--live", "--provider", "ollama", "--model", "m"]) == 1
    assert "Is Ollama running? (ollama serve)" in capsys.readouterr().out
