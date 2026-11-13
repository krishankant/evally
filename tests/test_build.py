import json

import pytest

from evally.datasets.build import build, split
from evally.evals_core.cases import Case, load_cases


def case(cid, category="none", **extra):
    return {"id": cid, "tags": [f"category:{category}", "source:hand"], "turns": ["hi"],
            "checks": [{"type": "max_words", "value": 50}], **extra}


def mk(cid, category="none"):
    return Case(cid, [f"category:{category}"], ["hi"], [])


def project(tmp_path, sources: dict[str, list[dict]], version=1):
    paths = []
    for name, rows in sources.items():
        p = tmp_path / "src" / f"{name}.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("".join(json.dumps(r) + "\n" for r in rows))
        paths.append(str(p))
    manifest = tmp_path / "bramble.json"
    manifest.write_text(json.dumps({"name": "bramble", "version": version, "sources": paths, "test_share": 0.4}))
    return manifest, tmp_path / "suites", tmp_path / "datasets"


def test_split_deterministic():
    cases = [mk(f"c{i}") for i in range(20)]
    assert split(cases, 0.4) == split(list(cases), 0.4)
    dev, test, _ = split(cases, 0.4)
    assert len(dev) + len(test) == 20 and dev and test
    assert [c.id for c in dev] == [c.id for c in cases if c in dev]  # source order kept


def test_split_share_is_close_over_many_ids():
    dev, test, moved = split([mk(f"case-{i}") for i in range(2000)], 0.4)
    assert abs(len(test) / 2000 - 0.4) < 0.03
    assert moved == []


def test_adding_a_case_moves_no_existing_case():
    cases = [mk(f"c{i}", "none") for i in range(30)]
    dev, test, moved = split(cases, 0.4)
    dev2, test2, moved2 = split(cases + [mk("new-one", "none")], 0.4)
    assert moved == moved2 == []
    assert {c.id for c in test} <= {c.id for c in test2}
    assert {c.id for c in dev} <= {c.id for c in dev2}


def test_each_category_with_two_cases_in_both_splits():
    cases = [mk(f"{cat}-{i}", cat) for cat in ("goes-beyond-policy", "unsupported-claims", "needless-escalation",
                                                "uses-outdated-policy") for i in range(2)]
    cases.append(mk("lonely", "cant-find-book-by-title"))
    dev, test, moved = split(cases, 0.4)
    for cat in ("goes-beyond-policy", "unsupported-claims", "needless-escalation", "uses-outdated-policy"):
        assert any(c.tags == [f"category:{cat}"] for c in dev), cat
        assert any(c.tags == [f"category:{cat}"] for c in test), cat
    assert moved and all(m in {c.id for c in cases} for m in moved)  # the rebalancing ran


def test_duplicate_id_across_sources_fails(tmp_path):
    m, suites, ds = project(tmp_path, {"hand": [case("a")], "traffic": [case("a")]})
    with pytest.raises(ValueError) as e:
        build(m, suites, ds)
    assert "hand.jsonl" in str(e.value) and "traffic.jsonl" in str(e.value) and "'a'" in str(e.value)
    assert not suites.exists() and not ds.exists()


def test_build_rejects_bad_tag(tmp_path):
    bad = case("b")
    bad["tags"] = ["topic:shippng"]
    m, suites, ds = project(tmp_path, {"hand": [case("a"), bad]})
    with pytest.raises(ValueError, match="hand.jsonl:2:.*shippng"):
        build(m, suites, ds)
    assert not suites.exists()


def test_lock_records_hashes_and_ids(tmp_path):
    m, suites, ds = project(tmp_path, {"hand": [case(f"h{i}") for i in range(6)]})
    lock_path = build(m, suites, ds)
    assert lock_path == ds / "bramble-v1.lock.json"
    lock = json.loads(lock_path.read_text())
    assert lock["name"] == "bramble" and lock["version"] == 1
    assert len(lock["sources"]) == 1 and len(next(iter(lock["sources"].values()))) == 64
    dev = load_cases(suites / "bramble-v1-dev.jsonl")
    test = load_cases(suites / "bramble-v1-test.jsonl")
    assert [c.id for c in dev] == lock["dev"] and [c.id for c in test] == lock["test"]
    assert sorted(lock["dev"] + lock["test"]) == [f"h{i}" for i in range(6)]
    assert dev[0].checks == [{"type": "max_words", "value": 50}]


def test_rebuild_same_sources_ok(tmp_path):
    m, suites, ds = project(tmp_path, {"hand": [case("a"), case("b")]})
    lock = build(m, suites, ds)
    before = lock.stat().st_mtime_ns
    assert build(m, suites, ds) == lock
    assert lock.stat().st_mtime_ns == before


def test_changed_sources_need_new_version(tmp_path):
    m, suites, ds = project(tmp_path, {"hand": [case("a"), case("b")]})
    build(m, suites, ds)
    project(tmp_path, {"hand": [case("a"), case("b"), case("c")]})
    with pytest.raises(ValueError, match='bramble v1 already built from different sources; bump "version"'):
        build(m, suites, ds)
    project(tmp_path, {"hand": [case("a"), case("b"), case("c")]}, version=2)
    assert build(m, suites, ds).name == "bramble-v2.lock.json"
    assert (suites / "bramble-v1-dev.jsonl").exists()


def test_dataset_build_cli(tmp_path, monkeypatch, capsys):
    from evally import cli
    m, _, _ = project(tmp_path, {"hand": [case("a"), case("b")], "traffic": [case("a")]})
    monkeypatch.chdir(tmp_path)
    assert cli.main(["dataset", "build", "--manifest", str(m)]) == 1
    assert "build failed: case id 'a' is in both" in capsys.readouterr().out
    project(tmp_path, {"hand": [case("a"), case("b")], "traffic": [case("c")]})
    assert cli.main(["dataset", "build", "--manifest", str(m)]) == 0
    assert "bramble-v1: " in capsys.readouterr().out
    assert (tmp_path / "evals/suites/bramble-v1-dev.jsonl").exists()


def test_bad_tag_reported_before_version_check(tmp_path):
    m, suites, ds = project(tmp_path, {"hand": [case("a"), case("b")]})
    build(m, suites, ds)
    bad = case("c")
    bad["tags"] = ["topic:shippng"]
    project(tmp_path, {"hand": [case("a"), case("b"), bad]})
    with pytest.raises(ValueError, match="shippng"):
        build(m, suites, ds)


def test_pinned_cases_never_move_even_when_rebalancing():
    cases = [mk(f"{cat}-{i}", cat) for cat in ("goes-beyond-policy", "unsupported-claims", "needless-escalation",
                                                "uses-outdated-policy") for i in range(2)]
    dev, test, moved = split(cases, 0.4)
    assert moved  # v1 needed rebalancing
    pinned = {c.id: "dev" for c in dev} | {c.id: "test" for c in test}
    more = cases + [mk(f"{cat}-new{j}", cat) for cat in ("goes-beyond-policy", "unsupported-claims",
                                                         "needless-escalation", "uses-outdated-policy")
                    for j in range(3)]
    dev2, test2, moved2 = split(more, 0.4, pinned)
    assert {c.id for c in dev} <= {c.id for c in dev2}
    assert {c.id for c in test} <= {c.id for c in test2}
    assert all(m not in pinned for m in moved2)


def test_new_version_keeps_every_old_case_in_its_half(tmp_path):
    v1 = [case(f"cant-{i}", "cant-find-book-by-title") for i in range(2)] + \
         [case(f"miss-{i}", "misses-the-relevant-policy") for i in range(2)] + [case(f"n{i}") for i in range(6)]
    m, suites, ds = project(tmp_path, {"hand": v1})
    lock1 = json.loads(build(m, suites, ds).read_text())
    added = [case(f"cant-new{i}", "cant-find-book-by-title") for i in range(4)] + \
            [case(f"miss-new{i}", "misses-the-relevant-policy") for i in range(4)]
    project(tmp_path, {"hand": v1 + added}, version=2)
    lock2 = json.loads(build(m, suites, ds).read_text())
    assert set(lock1["dev"]) <= set(lock2["dev"]) and set(lock1["test"]) <= set(lock2["test"])
    assert lock2["pinned_from"] == 1
    assert not set(lock2["moved"]) & set(lock1["dev"] + lock1["test"])
