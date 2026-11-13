from evally.evals_core.labels import Label, append_label, label_loop, labels_path, load_labels


def _case(i):
    return {"id": f"c{i}", "status": "UNCHECKED",
            "turns": [{"user": f"question {i}", "reply": f"answer {i}", "trace": []}]}


RUN = {"suite": "t", "model": "m", "cases": [_case(1), _case(2), _case(3)]}


def drive(answers, existing=None, labeler="human"):
    answers, shown, saved = list(answers), [], []

    def ask(prompt):
        if not answers:
            raise EOFError
        a = answers.pop(0)
        if isinstance(a, BaseException):
            raise a
        return a

    n = label_loop(RUN, "t-m", existing or {}, labeler, ask, shown.append, saved.append)
    return n, shown, saved


def test_labels_pass_and_fail_with_notes():
    n, _, saved = drive(["p", "", "f", "invented a URL", "q"])
    assert n == 2
    assert [(l.case_id, l.verdict, l.note) for l in saved] == [("c1", "pass", ""), ("c2", "fail", "invented a URL")]
    assert saved[0].run == "t-m"


def test_fail_needs_a_note():
    _, _, saved = drive(["f", "", "  ", "too long", "q"])
    assert [l.note for l in saved] == ["too long"]


def test_bad_verdict_reprompts():
    n, _, saved = drive(["x", "", "p", "", "q"])
    assert n == 1 and saved[0].verdict == "pass"


def test_skip_writes_nothing():
    _, shown, saved = drive(["s", "p", "", "q"])
    assert [l.case_id for l in saved] == ["c2"]
    assert "question 1" in shown[0]


def test_quit_keeps_earlier_labels():
    _, _, saved = drive(["p", "", "q"])
    assert len(saved) == 1


def test_eof_ends_cleanly():
    n, shown, saved = drive(["f", "wrong"])
    assert n == 1 and shown[-1] == "labelled 1, 2 left"


def test_ctrl_c_ends_cleanly():
    n, _, _ = drive(["p", "", KeyboardInterrupt()])
    assert n == 1


def test_resume_skips_labelled():
    existing = {"c1": Label("t-m", "c1", "pass", "")}
    _, shown, saved = drive(["p", "", "q"], existing=existing)
    assert "question 2" in shown[0]
    assert saved[0].case_id == "c2"


def test_labeler_recorded():
    _, _, saved = drive(["p", "", "q"], labeler="course-author (AI)")
    assert saved[0].labeler == "course-author (AI)"


def test_append_then_load_round_trip(tmp_path):
    path = labels_path("t-m", tmp_path / "labels")
    assert path == tmp_path / "labels" / "t-m.jsonl"
    label = Label("t-m", "c1", "fail", "quoted 60 days", "stale-policy", "me")
    append_label(path, label)
    assert load_labels(path) == {"c1": label}


def test_last_line_wins(tmp_path):
    path = tmp_path / "l.jsonl"
    append_label(path, Label("t-m", "c1", "fail", "x"))
    append_label(path, Label("t-m", "c1", "fail", "x", "invents-facts"))
    assert load_labels(path)["c1"].category == "invents-facts"


def test_load_missing_file_is_empty(tmp_path):
    assert load_labels(tmp_path / "none.jsonl") == {}
