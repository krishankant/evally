import json

from evally import cli
from evally.datasets.generate import GEN_SYSTEM, Candidate, candidate_id, generate, sample_combinations
from evally.llm.scripted import ScriptedModel, text_reply

DIMS = {"topic": ["returns", "shipping", "stock"], "persona": ["polite", "annoyed"], "phrasing": ["casual"]}


def test_sample_is_deterministic_and_distinct():
    a = sample_combinations(DIMS, 4, seed=3)
    assert a == sample_combinations(DIMS, 4, seed=3)
    assert len(a) == 4
    assert len({json.dumps(c, sort_keys=True) for c in a}) == 4
    assert all(set(c) == {"topic", "persona", "phrasing"} for c in a)
    assert sample_combinations(DIMS, 4, seed=4) != a


def test_sample_n_larger_than_product_returns_all():
    assert len(sample_combinations(DIMS, 50, seed=1)) == 6


def test_prompt_carries_the_combination():
    model = ScriptedModel([text_reply("Where is my order?")])
    generate(model, [{"topic": "shipping", "persona": "annoyed", "phrasing": "casual"}])
    call = model.calls[0]
    assert call.system == GEN_SYSTEM
    assert call.tools == []
    assert call.messages[0].text == "Topic: shipping\nPersona: annoyed\nPhrasing: casual"


def test_strips_quotes_and_whitespace():
    model = ScriptedModel([text_reply('  "Where is my book?"\n')])
    cands, dropped = generate(model, [{"topic": "shipping", "persona": "polite", "phrasing": "casual"}])
    assert cands[0].text == "Where is my book?"
    assert dropped == {}


def test_empty_reply_counted_not_kept():
    model = ScriptedModel([text_reply('  ""  '), text_reply("Can I return this?")])
    combos = sample_combinations(DIMS, 2, seed=1)
    cands, dropped = generate(model, combos)
    assert [c.text for c in cands] == ["Can I return this?"]
    assert dropped == {"empty": 1}


def test_candidate_id_stable_for_same_dims():
    d = {"topic": "returns", "persona": "polite", "phrasing": "casual"}
    assert candidate_id(d) == candidate_id(dict(reversed(list(d.items()))))
    assert candidate_id(d).startswith("gen-") and len(candidate_id(d)) == 12
    model = ScriptedModel([text_reply("hi")])
    assert generate(model, [d])[0][0] == Candidate(candidate_id(d), "hi", d)


def test_generate_cli_writes_candidates(tmp_path, monkeypatch, capsys):
    from evally.llm.cache import CachedModel
    monkeypatch.setenv("EVALLY_CACHE_DIR", str(tmp_path / "cache"))
    dims = tmp_path / "dims.json"
    dims.write_text(json.dumps(DIMS))
    combos = sample_combinations(DIMS, 2, seed=3)
    rec = CachedModel(ScriptedModel([text_reply("one"), text_reply("")]), tmp_path / "cache" / "ollama-m", "record")
    generate(rec, combos)
    out = tmp_path / "c.jsonl"
    assert cli.main(["generate", "--dims", str(dims), "--n", "2", "--seed", "3", "--out", str(out),
                     "--provider", "ollama", "--model", "m"]) == 0
    assert "generated 1, dropped 1 (empty 1)" in capsys.readouterr().out
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    assert rows == [{"id": candidate_id(combos[0]), "text": "one", "dims": combos[0]}]


def test_generate_cli_replay_miss_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("EVALLY_CACHE_DIR", str(tmp_path / "cache"))
    dims = tmp_path / "dims.json"
    dims.write_text(json.dumps(DIMS))
    out = tmp_path / "c.jsonl"
    assert cli.main(["generate", "--dims", str(dims), "--n", "2", "--seed", "3", "--out", str(out),
                     "--provider", "ollama", "--model", "m"]) == 1
    assert "Re-run with --live" in capsys.readouterr().out
    assert not out.exists()
