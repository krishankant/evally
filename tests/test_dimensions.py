import json
from pathlib import Path

import pytest

from evally.datasets.dimensions import DIMENSIONS, parse_tag, tag_value, validate_tags
from evally.evals_core.cases import load_cases

ROOT = Path(__file__).resolve().parent.parent


def write_case(tmp_path, tags):
    p = tmp_path / "cases.jsonl"
    p.write_text("// header\n" + json.dumps({"id": "c1", "tags": tags, "turns": ["hi"], "checks": []}) + "\n")
    return p


def test_parse_dim_tag():
    assert parse_tag("topic:returns") == ("topic", "returns")
    assert parse_tag("policy") is None
    assert tag_value(["policy", "difficulty:hard"], "difficulty") == "hard"
    assert tag_value(["policy"], "difficulty") is None


def test_free_tags_without_colon_allowed(tmp_path):
    cases = load_cases(write_case(tmp_path, ["policy", "topic:returns"]))
    assert cases[0].tags == ["policy", "topic:returns"]


def test_unknown_dimension_value_rejected(tmp_path):
    p = write_case(tmp_path, ["topic:shippng"])
    with pytest.raises(ValueError) as e:
        load_cases(p)
    msg = str(e.value)
    assert f"{p}:2:" in msg
    assert "shippng" in msg and "shipping" in msg


def test_unknown_dimension_rejected(tmp_path):
    with pytest.raises(ValueError, match="mood"):
        load_cases(write_case(tmp_path, ["mood:sad"]))
    assert validate_tags(["mood:sad"])


def test_two_values_for_one_dimension_rejected(tmp_path):
    assert validate_tags(["difficulty:easy", "difficulty:hard"])
    with pytest.raises(ValueError, match="difficulty"):
        load_cases(write_case(tmp_path, ["difficulty:easy", "difficulty:hard"]))


def test_week01_suite_still_loads():
    assert len(load_cases(ROOT / "evals/suites/week01.jsonl")) == 10


def test_category_values_are_week2_taxonomy():
    assert set(DIMENSIONS["category"]) == {
        "none", "cant-find-book-by-title", "goes-beyond-policy", "misses-the-relevant-policy",
        "unsupported-claims", "needless-escalation", "uses-outdated-policy",
    }
