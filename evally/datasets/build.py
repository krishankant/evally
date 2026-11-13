"""Build a versioned dataset: merge the sources, split dev/test, write a lock file.

The split is decided per case by a hash of its id. Then every category with two or more cases gets
at least one in each half (the case nearest the hash threshold is moved, and the move is recorded).
A new version pins every case the previous version had to its old half, and only new cases are
hashed or moved, so adding cases never moves an existing one. The lock file pins the sources' content
hashes: a version is built once, and changed sources need a new version number.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evally.datasets.dimensions import tag_value
from evally.evals_core.cases import Case, load_cases


def _hash(case_id: str) -> float:
    return int(hashlib.sha256(case_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def split(cases: list[Case], test_share: float,
          pinned: dict[str, str] | None = None) -> tuple[list[Case], list[Case], list[str]]:
    """Returns (dev, test, moved ids). Order within each half is the input order.

    `pinned` maps case ids to "dev" or "test" (the previous version's split): those cases keep
    their half, and rebalancing may move only cases that aren't pinned.
    """
    pinned = pinned or {}
    in_test = {c.id: pinned[c.id] == "test" if c.id in pinned else _hash(c.id) < test_share for c in cases}
    moved: list[str] = []
    by_cat: dict[str, list[Case]] = {}
    for c in cases:
        by_cat.setdefault(tag_value(c.tags, "category") or "none", []).append(c)
    for group in by_cat.values():
        free = [c for c in group if c.id not in pinned]
        if len(group) < 2 or not free:
            continue
        if not any(in_test[c.id] for c in group):  # nothing in test: move the dev case nearest the line
            pick = min(free, key=lambda c: _hash(c.id))
        elif all(in_test[c.id] for c in group):  # nothing in dev: move the test case nearest the line
            pick = max(free, key=lambda c: _hash(c.id))
        else:
            continue
        in_test[pick.id] = not in_test[pick.id]
        moved.append(pick.id)
    return [c for c in cases if not in_test[c.id]], [c for c in cases if in_test[c.id]], moved


def _previous_lock(datasets_dir: Path, name: str, version: int) -> dict | None:
    for v in range(version - 1, 0, -1):
        p = Path(datasets_dir) / f"{name}-v{v}.lock.json"
        if p.exists():
            return json.loads(p.read_text())
    return None


def _case_line(c: Case) -> str:
    d = {"id": c.id, "tags": c.tags, "turns": c.turns, "checks": c.checks}
    if c.note:
        d["note"] = c.note
    return json.dumps(d, ensure_ascii=False) + "\n"


def build(manifest_path: Path, suites_dir: Path, datasets_dir: Path) -> Path:
    manifest = json.loads(Path(manifest_path).read_text())
    name, version = manifest["name"], manifest["version"]
    stem = f"{name}-v{version}"
    sources = {src: hashlib.sha256(Path(src).read_bytes()).hexdigest() for src in manifest["sources"]}
    cases: list[Case] = []
    seen: dict[str, str] = {}
    for src in manifest["sources"]:
        for c in load_cases(Path(src)):  # bad tags or checks raise here, naming file:line
            if c.id in seen:
                raise ValueError(f"case id {c.id!r} is in both {seen[c.id]} and {src}")
            seen[c.id] = src
            cases.append(c)

    lock_path = Path(datasets_dir) / f"{stem}.lock.json"
    if lock_path.exists():
        if json.loads(lock_path.read_text())["sources"] == sources:
            return lock_path
        raise ValueError(f'{name} v{version} already built from different sources; '
                         f'bump "version" in {manifest_path}')

    prev = _previous_lock(datasets_dir, name, version)
    pinned = {i: "dev" for i in prev["dev"]} | {i: "test" for i in prev["test"]} if prev else {}
    dev, test, moved = split(cases, manifest["test_share"], pinned)
    suites_dir, datasets_dir = Path(suites_dir), Path(datasets_dir)
    suites_dir.mkdir(parents=True, exist_ok=True)
    datasets_dir.mkdir(parents=True, exist_ok=True)
    for half, rows in (("dev", dev), ("test", test)):
        header = f"// {name} v{version} {half}: built by `evally dataset build` from {manifest_path}. Do not edit.\n"
        (suites_dir / f"{stem}-{half}.jsonl").write_text(header + "".join(_case_line(c) for c in rows))
    lock = {"name": name, "version": version, "sources": sources,
            "dev": [c.id for c in dev], "test": [c.id for c in test], "moved": moved,
            "pinned_from": prev["version"] if prev else None}
    lock_path.write_text(json.dumps(lock, indent=1) + "\n")
    return lock_path
