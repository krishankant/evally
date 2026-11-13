from evally import cli
from evally.datasets.dimensions import DIMENSIONS
from evally.datasets.stats import coverage, format_by_tag, format_coverage
from evally.evals_core.cases import Case
from evally.evals_core.runner import CaseResult, RunResult


def c(cid, *tags):
    return Case(cid, list(tags), ["hi"], [])


def test_coverage_counts_and_zero_rows():
    dev = [c("a", "topic:returns", "difficulty:easy"), c("b", "topic:returns"), c("x", "topic:stock")]
    test = [c("d", "topic:returns")]
    cov = coverage(dev, test)
    assert list(cov) == list(DIMENSIONS)
    topic = cov["topic"]
    assert [v for v, _, _ in topic] == list(DIMENSIONS["topic"])
    assert ("returns", 2, 1) in topic and ("stock", 1, 0) in topic and ("privacy", 0, 0) in topic


def test_format_marks_missing_in_test():
    dev = [c("a", "topic:returns"), c("b", "topic:stock")]
    test = [c("d", "topic:returns")]
    text = format_coverage("bramble-v1", coverage(dev, test), len(dev), len(test))
    assert text.splitlines()[0] == "coverage of bramble-v1 (dev 2 · test 1)"
    stock = next(l for l in text.splitlines() if l.strip().startswith("stock"))
    assert stock.endswith("← not in test")
    returns = next(l for l in text.splitlines() if l.strip().startswith("returns"))
    assert "not in test" not in returns
    assert "  missing: shipping, international, orders, membership, gift-cards, damaged, preorders, " \
           "privacy, account, off-topic" in text
    assert "privacy " not in text.replace("missing:", "")  # zero-zero values are not rows


def r(cid, status, *tags):
    return CaseResult(cid, list(tags), status)


def run(*cases):
    return RunResult("s", "m", list(cases), {})


def test_by_tag_rates_and_order():
    text = format_by_tag(run(r("a", "PASS", "category:none"), r("b", "PASS", "category:none"),
                             r("c", "FAIL", "category:goes-beyond-policy"),
                             r("d", "PASS", "category:goes-beyond-policy"),
                             r("e", "ERROR", "category:uses-outdated-policy"),
                             r("f", "UNCHECKED", "category:none")), "category")
    lines = text.splitlines()
    assert lines[0] == "by category"
    body = [l.split() for l in lines[2:]]
    assert body == [["uses-outdated-policy", "0/1", "0%"], ["goes-beyond-policy", "1/2", "50%"],
                    ["none", "2/2", "100%"]]


def test_by_tag_untagged_bucket():
    text = format_by_tag(run(r("a", "FAIL", "topic:returns"), r("b", "PASS")), "topic")
    assert text.splitlines()[-1].split() == ["(untagged)", "1/1", "100%"]


def test_run_by_unknown_dimension_message(tmp_path, monkeypatch, capsys):
    suite = tmp_path / "s.jsonl"
    suite.write_text('{"id": "a", "turns": ["hi"], "checks": []}\n')
    assert cli.main(["run", "--suite", str(suite), "--by", "mood"]) == 1
    out = capsys.readouterr().out.strip()
    assert out == "unknown dimension 'mood' (known: topic, difficulty, category, source)"


def test_dataset_stats_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "evals/suites").mkdir(parents=True)
    (tmp_path / "evals/datasets").mkdir(parents=True)
    assert cli.main(["dataset", "stats", "bramble-v1"]) == 1
    assert "no dataset bramble-v1" in capsys.readouterr().out
    (tmp_path / "evals/datasets/bramble-v1.lock.json").write_text("{}")
    (tmp_path / "evals/suites/bramble-v1-dev.jsonl").write_text('{"id": "a", "tags": ["topic:returns"], "turns": ["x"]}\n')
    (tmp_path / "evals/suites/bramble-v1-test.jsonl").write_text("")
    assert cli.main(["dataset", "stats", "bramble-v1"]) == 0
    assert "returns" in capsys.readouterr().out
