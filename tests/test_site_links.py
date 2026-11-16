"""The site hook sends links that leave the site (code, eval files) to GitHub."""

from site_hooks import links

R = "https://github.com/krishankant/evally/blob/main/"


def test_rewrites_outside_link():
    out = links.rewrite_outside_links("[v](../evals/vibe-check.md)", "lessons/week01-baseline.md", R)
    assert out == "[v](" + R + "evals/vibe-check.md)"


def test_keeps_inside_link():
    md = "[p](../COURSE_PLAN.md) and [c](../concepts/06-testing-the-grader.md#2-kappa)"
    assert links.rewrite_outside_links(md, "lessons/week05-llm-graders.md", R) == md


def test_keeps_external_and_anchor():
    md = "[u](https://ollama.com) [a](#3-why) [m](mailto:x@example.com)"
    assert links.rewrite_outside_links(md, "README.md", R) == md


def test_code_file_link():
    out = links.rewrite_outside_links("[cli](../evally/cli.py)", "lessons/week04-code-graders.md", R)
    assert out == "[cli](" + R + "evally/cli.py)"


def test_root_page_outside_link_keeps_anchor():
    out = links.rewrite_outside_links("[r](evals/rubrics/x.md#fail)", "README.md", R)
    assert out == "[r](" + R + "evals/rubrics/x.md#fail)"
