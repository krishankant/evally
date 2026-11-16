"""MkDocs hook: links that leave the site open the file on GitHub.

The site holds README.md, COURSE_PLAN.md, lessons/ and concepts/. Lessons also link to
code and eval files (`../evally/cli.py`, `../evals/vibe-check.md`), which read fine on
github.com but don't exist in the built site. This hook rewrites those to GitHub URLs,
so a link works in both places and `mkdocs build --strict` stays clean.
"""

from __future__ import annotations

import posixpath
import re

REPO_URL = "https://github.com/krishankant/evally/blob/main/"
INSIDE = ("README.md", "COURSE_PLAN.md", "lessons/", "concepts/")
_LINK = re.compile(r"\]\(([^)\s]+)\)")


def _is_inside(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in INSIDE)


def rewrite_outside_links(markdown: str, page_src: str, repo_url: str) -> str:
    """Rewrite relative links from `page_src` (repo-relative) that resolve outside the site."""
    base = posixpath.dirname(page_src)

    def fix(m: re.Match) -> str:
        target = m.group(1)
        if target.startswith("#") or re.match(r"^[a-z][a-z0-9+.-]*:", target):
            return m.group(0)
        path, _, anchor = target.partition("#")
        resolved = posixpath.normpath(posixpath.join(base, path))
        if resolved.startswith("..") or _is_inside(resolved):
            return m.group(0)
        return "](" + repo_url + resolved + ("#" + anchor if anchor else "") + ")"

    return _LINK.sub(fix, markdown)


def on_page_markdown(markdown, page, config, files):  # MkDocs hook signature
    return rewrite_outside_links(markdown, page.file.src_uri, REPO_URL)
