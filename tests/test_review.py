from evally.datasets.generate import Candidate
from evally.datasets.review import Decision, load_decisions, review_loop, save_decision, survival_report

CANDS = [Candidate(f"gen-{i:08x}", f"message {i}", {"topic": "returns", "persona": "polite", "phrasing": "casual"})
         for i in range(3)]


def drive(answers, existing=None):
    it = iter(answers)
    saved, said = [], []

    def ask(prompt):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    n = review_loop(CANDS, existing or {}, "tester", ask, said.append, saved.append)
    return n, saved, said


def test_keep_and_drop_with_reason():
    n, saved, said = drive(["k", "", "d", "not a real request", "k", "nice"])
    assert n == 3
    assert saved == [Decision(CANDS[0].id, True, "", "tester"),
                     Decision(CANDS[1].id, False, "not a real request", "tester"),
                     Decision(CANDS[2].id, True, "nice", "tester")]
    assert any("message 0" in s and "topic: returns" in s for s in said)
    assert said[-1] == "reviewed 3, 0 left"


def test_drop_needs_reason():
    _, saved, _ = drive(["d", "", "  ", "duplicate"])
    assert saved[0] == Decision(CANDS[0].id, False, "duplicate", "tester")


def test_bad_answer_reprompts():
    _, saved, _ = drive(["x", "keep", "k", ""])
    assert saved[0].keep is True


def test_quit_keeps_earlier_decisions():
    n, saved, said = drive(["k", "", "q"])
    assert n == 1 and len(saved) == 1
    assert said[-1] == "reviewed 1, 2 left"
    n, saved, _ = drive(["d", "q"])  # q at the reason prompt quits without saving
    assert n == 0 and saved == []


def test_resume_skips_decided():
    existing = {CANDS[0].id: Decision(CANDS[0].id, True, "", "tester")}
    _, saved, said = drive(["d", "vague"], existing)
    assert saved[0].candidate_id == CANDS[1].id
    assert not any("message 0" in s for s in said)


def test_decisions_round_trip_last_line_wins(tmp_path):
    p = tmp_path / "c.review.jsonl"
    save_decision(p, Decision("a", True, "", "x"))
    save_decision(p, Decision("a", False, "vague", "x"))
    assert load_decisions(p) == {"a": Decision("a", False, "vague", "x")}
    assert load_decisions(tmp_path / "missing.jsonl") == {}


def test_report_layout():
    cands = [Candidate(f"c{i}", "t", {}) for i in range(12)]
    decisions = {f"c{i}": Decision(f"c{i}", True, "", "course-author (AI)") for i in range(8)}
    decisions.update({"c8": Decision("c8", False, "Not a real request", "course-author (AI)"),
                      "c9": Decision("c9", False, "not a  real request", "course-author (AI)"),
                      "c10": Decision("c10", False, "duplicate", "course-author (AI)"),
                      "c11": Decision("c11", False, "vague", "course-author (AI)")})
    assert survival_report("week03-generated", cands, decisions) == (
        "review of week03-generated (reviewer: course-author (AI))\n"
        "\n"
        "  12 generated · 8 kept · 4 dropped (67% kept)\n"
        "\n"
        "  drop reason         count\n"
        "  not-a-real-request      2\n"
        "  duplicate               1\n"
        "  vague                   1"
    )


def test_report_counts_unreviewed_and_ignores_stale():
    decisions = {CANDS[0].id: Decision(CANDS[0].id, True, "", "x"),
                 "gen-gone": Decision("gen-gone", False, "vague", "x")}
    report = survival_report("w", CANDS, decisions)
    assert "  3 generated · 1 kept · 0 dropped (100% kept)" in report
    assert "  2 not reviewed yet" in report
    assert "  1 stale decision ignored (candidate not in this file)" in report
    assert "vague" not in report


def test_review_cli_report(tmp_path, capsys):
    import json
    from evally import cli
    p = tmp_path / "w.jsonl"
    p.write_text(json.dumps({"id": "a", "text": "hi", "dims": {}}) + "\n")
    save_decision(tmp_path / "w.review.jsonl", Decision("a", True, "", "x"))
    assert cli.main(["review", str(p), "--report"]) == 0
    assert "1 generated · 1 kept · 0 dropped (100% kept)" in capsys.readouterr().out
    assert cli.main(["review", str(tmp_path / "nope.jsonl")]) == 1
