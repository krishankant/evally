"""evally's command line.

    evally run --suite week01           replay the recorded run: free, no key needed
    evally run --suite week01 --live    call the model and record anything new
    evally chat                         talk to the bookstore assistant (live)
    evally traces <run> [--case ID]     read saved conversations
    evally label <run>                  label each conversation pass/fail with a note
    evally label <run> --code           group the fail notes into categories
    evally label <run> --report         fails per category, most first
    evally generate --dims F --n N --seed S --out F [--live]   candidate cases from dimensions
    evally review <candidates.jsonl> [--report]                 keep/drop each candidate
    evally dataset build [--manifest F]  merge sources, split dev/test, write the lock file
    evally dataset stats bramble-v1      coverage per tag, dev vs test
    evally run --suite S --by category   pass rates per tag value after the table
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import anthropic
import openai

from evally import config as config_mod
from evally.app.assistant import Assistant
from evally.app.retrieval import Retriever
from evally.app.store import Store
from evally.evals_core.cases import load_cases
from evally.evals_core.runner import format_table, load_run, run_suite, save_run, slug
from evally.evals_core.labels import append_label, code_loop, format_report, label_loop, labels_path, load_labels
from evally.evals_core.traces import format_case_list, format_conversation, run_path
from evally.datasets.build import build
from evally.datasets.dimensions import DIMENSIONS
from evally.datasets.stats import coverage, format_by_tag, format_coverage
from evally.datasets.generate import generate, sample_combinations
from evally.datasets.review import decisions_path, load_candidates, load_decisions, review_loop, save_decision, survival_report
from evally.llm.cache import CachedModel, ReplayMiss
from evally.llm.factory import make_model
from evally.types import Message

CONNECTION_ERRORS = (openai.APIConnectionError, anthropic.APIConnectionError)


def _model(args, cfg) -> CachedModel:
    cache_dir = cfg.cache_dir / f"{args.provider}-{slug(args.model)}"
    if args.live:
        return CachedModel(make_model(args.provider, args.model), cache_dir, "record")
    return CachedModel(None, cache_dir, "replay")


def _suite_path(name: str, cfg) -> Path:
    p = Path(name)
    return p if p.suffix == ".jsonl" else cfg.suites_dir / f"{name}.jsonl"


def cmd_run(args, cfg) -> int:
    if args.by and args.by not in DIMENSIONS:
        print(f"unknown dimension {args.by!r} (known: {', '.join(DIMENSIONS)})")
        return 1
    model = _model(args, cfg)
    path = _suite_path(args.suite, cfg)
    cases = load_cases(path)
    result = run_suite(path.stem, cases, lambda: Assistant(model, Store.from_seed(), Retriever.from_dir()), model.name)
    print(format_table(result))
    if args.by:
        print("\n" + format_by_tag(result, args.by))
    print(f"\nsaved {save_run(result, cfg.runs_dir)}")
    return 0


def _summary(turn) -> str:
    docs = next((s.data["docs"] for s in turn.trace if s.kind == "retrieve"), [])
    return f"[docs: {', '.join(docs) or 'none'} | tools: {', '.join(turn.tools_called) or 'none'}]"


def cmd_chat(args, cfg) -> int:
    model = _model(args, cfg)
    assistant = Assistant(model, Store.from_seed(), Retriever.from_dir())
    print(f"Bramble Books support ({model.name}{'' if args.live else ', replay only'}). /quit to leave.")
    history: list[Message] = []
    while True:
        try:
            text = input("you> ").strip()
        except EOFError:
            return 0
        if text in ("/quit", "/exit"):
            return 0
        if not text:
            continue
        history.append(Message("user", text))
        turn, history = assistant.respond(history)
        print(f"bot> {turn.reply}\n     {_summary(turn)}")


def _load_run(name: str, cfg) -> dict | None:
    path = run_path(name, cfg.runs_dir)
    if not path.exists():
        print(f"no run named {name} in {cfg.runs_dir}")
        return None
    return load_run(path)


def cmd_traces(args, cfg) -> int:
    run = _load_run(args.run, cfg)
    if run is None:
        return 1
    if not args.case:
        print(format_case_list(run))
        return 0
    case = next((c for c in run["cases"] if c["id"] == args.case), None)
    if case is None:
        print(f"no case {args.case} in {args.run}")
        return 1
    print(format_conversation(case))
    return 0


def cmd_label(args, cfg) -> int:
    run = _load_run(args.run, cfg)
    if run is None:
        return 1
    name = run_path(args.run, cfg.runs_dir).stem
    path = labels_path(name, cfg.labels_dir)
    existing = load_labels(path)
    if args.report:
        print(format_report(name, existing, {c["id"] for c in run["cases"]}))
        return 0
    if args.code:
        code_loop(existing, input, print, lambda lab: append_label(path, lab), {c["id"] for c in run["cases"]})
        return 0
    print(f"labelling {name}: {len(existing)} of {len(run['cases'])} already labelled, saving to {path}\n")
    label_loop(run, name, existing, args.labeler, input, print, lambda lab: append_label(path, lab))
    return 0


def cmd_generate(args, cfg) -> int:
    dims = json.loads(Path(args.dims).read_text())
    combos = sample_combinations(dims, args.n, args.seed)
    try:
        candidates, dropped = generate(_model(args, cfg), combos)
    except ReplayMiss as e:
        print(e)
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps({"id": c.id, "text": c.text, "dims": c.dims}) + "\n" for c in candidates))
    reasons = ", ".join(f"{k} {v}" for k, v in sorted(dropped.items()))
    total = sum(dropped.values())
    print(f"generated {len(candidates)}, dropped {total}" + (f" ({reasons})" if reasons else "") + f"\nsaved {out}")
    return 0


def cmd_review(args, cfg) -> int:
    path = Path(args.candidates)
    if not path.exists():
        print(f"no candidates file {path}")
        return 1
    candidates = load_candidates(path)
    store = decisions_path(path)
    existing = load_decisions(store)
    if args.report:
        print(survival_report(path.stem, candidates, existing))
        return 0
    print(f"reviewing {path.stem}: {sum(c.id in existing for c in candidates)} of {len(candidates)} "
          f"already reviewed, saving to {store}\n")
    review_loop(candidates, existing, args.reviewer, input, print, lambda d: save_decision(store, d))
    return 0


def cmd_dataset(args, cfg) -> int:
    if args.action == "build":
        try:
            lock = build(Path(args.manifest), cfg.suites_dir, cfg.datasets_dir)
        except (ValueError, FileNotFoundError) as e:
            print(f"build failed: {e}")
            return 1
        d = json.loads(lock.read_text())
        stem = f"{d['name']}-v{d['version']}"
        moved = f", {len(d['moved'])} moved to balance categories" if d["moved"] else ""
        print(f"{stem}: {len(d['dev'])} dev, {len(d['test'])} test{moved}\n"
              f"suites {cfg.suites_dir}/{stem}-dev.jsonl, {cfg.suites_dir}/{stem}-test.jsonl\nlock {lock}")
        return 0
    lock = cfg.datasets_dir / f"{args.name}.lock.json"
    if not lock.exists():
        print(f"no dataset {args.name} (no {lock}); run evally dataset build")
        return 1
    dev = load_cases(cfg.suites_dir / f"{args.name}-dev.jsonl")
    test = load_cases(cfg.suites_dir / f"{args.name}-test.jsonl")
    print(format_coverage(args.name, coverage(dev, test), len(dev), len(test)))
    return 0


def main(argv: list[str] | None = None) -> int:
    cfg = config_mod.load()
    parser = argparse.ArgumentParser(prog="evally")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, live_default in (("run", False), ("chat", True), ("generate", False)):
        p = sub.add_parser(name)
        p.add_argument("--live", action="store_true", default=live_default,
                       help="call the model (and record new replies) instead of replaying recordings")
        p.add_argument("--replay", dest="live", action="store_false", help="use recordings only")
        p.add_argument("--provider", default=cfg.provider, choices=["ollama", "openai", "anthropic"])
        p.add_argument("--model", default=cfg.model)
        if name == "run":
            p.add_argument("--suite", required=True, help="suite name in evals/suites, or a .jsonl path")
            p.add_argument("--by", help="also print pass rates per value of this tag dimension (e.g. category)")
        if name == "generate":
            p.add_argument("--dims", required=True, help="JSON file: dimension -> list of values")
            p.add_argument("--n", type=int, required=True, help="how many combinations to sample")
            p.add_argument("--seed", type=int, default=0)
            p.add_argument("--out", required=True, help="candidates .jsonl to write")
    p = sub.add_parser("traces", help="read saved conversations from a run")
    p.add_argument("run", help="run name in evals/runs (like week01-qwen3.5-4b) or a .json path")
    p.add_argument("--case", help="show one conversation in full")
    p = sub.add_parser("label", help="label saved conversations (error analysis)")
    p.add_argument("run", help="run name in evals/runs or a .json path")
    p.add_argument("--labeler", default="human", help="who is labelling; recorded with every label")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--code", action="store_true", help="put each fail label in a category")
    mode.add_argument("--report", action="store_true", help="print fails per category, most first")
    p = sub.add_parser("review", help="keep or drop generated candidates")
    p.add_argument("candidates", help="candidates .jsonl from evally generate")
    p.add_argument("--reviewer", default="human", help="who is reviewing; recorded with every decision")
    p.add_argument("--report", action="store_true", help="print the survival rate and drop reasons")
    p = sub.add_parser("dataset", help="build and inspect versioned datasets")
    dsub = p.add_subparsers(dest="action", required=True)
    b = dsub.add_parser("build", help="merge sources, split dev/test, write the lock file")
    b.add_argument("--manifest", default=str(cfg.datasets_dir / "bramble.json"))
    st = dsub.add_parser("stats", help="coverage per tag dimension, dev vs test")
    st.add_argument("name", help="dataset name and version, like bramble-v1")
    args = parser.parse_args(argv)
    if args.cmd == "dataset":
        return cmd_dataset(args, cfg)
    if args.cmd == "review":
        return cmd_review(args, cfg)
    if args.cmd == "traces":
        return cmd_traces(args, cfg)
    if args.cmd == "label":
        return cmd_label(args, cfg)
    try:
        if args.cmd == "generate":
            return cmd_generate(args, cfg)
        return cmd_run(args, cfg) if args.cmd == "run" else cmd_chat(args, cfg)
    except CONNECTION_ERRORS:
        where = cfg.ollama_url if args.provider == "ollama" else args.provider
        print(f"Can't reach the model at {where}. Is Ollama running? (ollama serve)"
              if args.provider == "ollama" else f"Can't reach {where}. Check your network and API key.")
        return 1
