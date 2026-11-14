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
    evally refusals <run>                which replies the refusal detector flags
    evally deepeval <run> --suite S --case ID   the same checks in DeepEval, side by side
    evally dataset build [--manifest F]  merge sources, split dev/test, write the lock file
    evally dataset stats bramble-v1      coverage per tag, dev vs test
    evally run --suite S --by category   pass rates per tag value after the table (--by check: per check type)
    evally grade <run> [--rubric R] [--scale binary|1-5] [--case ID]   LLM grader, one verdict per rubric
    evally pad <run>                     a copy of the run with one sentence of filler on each last reply
    evally bias <run-a> <run-b>          which reply is better, asked in both orders (grader biases)
"""

from __future__ import annotations

import argparse
import json
import os
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
from evally.graders.judge import format_case_verdicts, format_grades, grade_run, policy_reference, save_grades
from evally.graders.pairwise import bias_test, format_bias, pad_run
from evally.graders.refusal import refusal_match
from evally.graders.rubrics import load_rubrics
from evally.datasets.stats import coverage, format_by_check, format_by_tag, format_coverage
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


KEY_VARS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}


def _missing_key(provider: str) -> str | None:
    var = KEY_VARS.get(provider)
    if var and not os.environ.get(var, "").strip():
        return f"{var} isn't set: add it to .env"
    return None


def _grader_model(args, cfg) -> CachedModel:
    """The grader: set apart from the app model, recorded and replayed the same way."""
    cache_dir = cfg.cache_dir / f"{args.grader_provider}-{slug(args.grader_model)}"
    if args.live:
        return CachedModel(make_model(args.grader_provider, args.grader_model), cache_dir, "record")
    return CachedModel(None, cache_dir, "replay")


def _suite_path(name: str, cfg) -> Path:
    p = Path(name)
    return p if p.suffix == ".jsonl" else cfg.suites_dir / f"{name}.jsonl"


def cmd_run(args, cfg) -> int:
    if args.by and args.by not in (*DIMENSIONS, "check"):
        print(f"unknown dimension {args.by!r} (known: {', '.join(DIMENSIONS)}, check)")
        return 1
    model = _model(args, cfg)
    path = _suite_path(args.suite, cfg)
    try:
        cases = load_cases(path)
    except ValueError as e:
        print(e)
        return 1
    result = run_suite(path.stem, cases, lambda: Assistant(model, Store.from_seed(), Retriever.from_dir()), model.name)
    print(format_table(result))
    if args.by:
        print("\n" + (format_by_check(result) if args.by == "check" else format_by_tag(result, args.by)))
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
        candidates, dropped = generate(_model(args, cfg), combos, args.skip_unrecorded)
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


def cmd_refusals(args, cfg) -> int:
    run = _load_run(args.run, cfg)
    if run is None:
        return 1
    w = max([len(c["id"]) for c in run["cases"]] + [2])
    flagged = 0
    for case in run["cases"]:
        last = case["replies"][-1] if case.get("replies") else ""
        m = refusal_match(last)
        flagged += m is not None
        print(f"{case['id']:<{w}}  REFUSES  \"{m}\"" if m else f"{case['id']:<{w}}  -")
    print(f"{flagged} of {len(run['cases'])} replies flagged")
    return 0


def cmd_deepeval(args, cfg) -> int:
    from evally.graders.deepeval_side import _deepeval_env, compare, format_compare
    with _deepeval_env():  # even the "is it installed?" import runs with telemetry off
        try:
            import deepeval  # noqa: F401  (optional extra)
        except ImportError:
            print("DeepEval isn't installed: uv sync --extra deepeval")
            return 1
    run = _load_run(args.run, cfg)
    if run is None:
        return 1
    suite_path = _suite_path(args.suite, cfg)
    if run.get("suite") != suite_path.stem:
        print(f"run {args.run} came from suite {run.get('suite')}, not {suite_path.stem}")
        return 1
    try:
        cases = {c.id: c for c in load_cases(suite_path)}
    except (ValueError, FileNotFoundError) as e:
        print(e)
        return 1
    recorded = next((c for c in run["cases"] if c["id"] == args.case), None)
    if recorded is None or args.case not in cases:
        print(f"no case {args.case} in both {args.run} and {args.suite}")
        return 1
    try:
        rows = compare(cases[args.case], recorded)
    except ValueError as e:
        print(e)
        return 1
    print(format_compare(args.case, rows))
    return 0


def cmd_grade(args, cfg) -> int:
    run = _load_run(args.run, cfg)
    if run is None:
        return 1
    name = run_path(args.run, cfg.runs_dir).stem
    try:
        rubrics = load_rubrics()
    except ValueError as e:
        print(e)
        return 1
    chosen = args.rubric or list(rubrics)
    unknown = [r for r in chosen if r not in rubrics]
    if unknown:
        print(f"unknown rubric {unknown[0]!r} (known: {', '.join(rubrics)})")
        return 1
    cases = [c for c in run["cases"] if not args.case or c["id"] == args.case]
    if not cases:
        print(f"no case {args.case} in {args.run}")
        return 1
    if args.live and (msg := _missing_key(args.grader_provider)):
        print(msg)
        return 1
    model = _grader_model(args, cfg)
    try:  # every verdict is collected before anything is saved, so a miss writes nothing
        verdicts = grade_run(model, {**run, "cases": cases}, [rubrics[r] for r in chosen],
                             policy_reference(), args.scale)
    except ReplayMiss as e:
        print(e)
        return 1
    if args.case:  # one case is a look, not a result: it never overwrites the run's grades
        print(format_case_verdicts(args.case, verdicts))
        return 0
    print(format_grades(name, args.grader_model, args.scale, verdicts))
    print(f"\nsaved {save_grades(cfg.grades_dir, name, args.grader_model, args.scale, [rubrics[r] for r in chosen], verdicts)}")
    return 0


def cmd_pad(args, cfg) -> int:
    run = _load_run(args.run, cfg)
    if run is None:
        return 1
    out = Path(cfg.runs_dir) / f"{run_path(args.run, cfg.runs_dir).stem}-padded.json"
    out.write_text(json.dumps(pad_run(run), indent=2) + "\n")
    print(f"saved {out}")
    return 0


def cmd_bias(args, cfg) -> int:
    run_a, run_b = _load_run(args.run_a, cfg), _load_run(args.run_b, cfg)
    if run_a is None or run_b is None:
        return 1
    if run_a.get("suite") != run_b.get("suite"):
        print(f"runs came from different suites: {run_a.get('suite')}, {run_b.get('suite')}")
        return 1
    if args.live and (msg := _missing_key(args.grader_provider)):
        print(msg)
        return 1
    try:
        pairs, summary = bias_test(_grader_model(args, cfg), run_a, run_b, policy_reference())
    except ReplayMiss as e:
        print(e)
        return 1
    names = [run_path(n, cfg.runs_dir).stem for n in (args.run_a, args.run_b)]
    print(format_bias(names[0], names[1], args.grader_model, pairs, summary))
    return 0


def _add_grader_args(p, cfg) -> None:
    p.add_argument("--live", action="store_true", help="call the grader (and record new replies)")
    p.add_argument("--grader-provider", default=cfg.grader_provider, choices=["ollama", "openai", "anthropic"])
    p.add_argument("--grader-model", default=cfg.grader_model)


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
    try:
        dev = load_cases(cfg.suites_dir / f"{args.name}-dev.jsonl")
        test = load_cases(cfg.suites_dir / f"{args.name}-test.jsonl")
    except ValueError as e:
        print(e)
        return 1
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
            p.add_argument("--by", help="also print pass rates per tag value (e.g. category), or per check type (check)")
        if name == "generate":
            p.add_argument("--dims", required=True, help="JSON file: dimension -> list of values")
            p.add_argument("--n", type=int, required=True, help="how many combinations to sample")
            p.add_argument("--seed", type=int, default=0)
            p.add_argument("--out", required=True, help="candidates .jsonl to write")
            p.add_argument("--skip-unrecorded", action="store_true",
                           help="replay: skip combinations with no recording (counted) instead of stopping")
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
    p = sub.add_parser("refusals", help="list which saved replies the refusal detector flags")
    p.add_argument("run", help="run name in evals/runs or a .json path")
    p = sub.add_parser("deepeval", help="run a saved case's checks in DeepEval too, side by side")
    p.add_argument("run", help="run name in evals/runs or a .json path")
    p.add_argument("--suite", required=True, help="the suite the run came from (for the checks)")
    p.add_argument("--case", required=True)
    p = sub.add_parser("grade", help="grade a saved run with an LLM grader, one verdict per rubric")
    p.add_argument("run", help="run name in evals/runs or a .json path")
    p.add_argument("--rubric", action="append", help="a rubric in evals/rubrics (repeatable; default: all)")
    p.add_argument("--scale", choices=["binary", "1-5"], default="binary")
    p.add_argument("--case", help="grade one case and show every reason (saves nothing)")
    _add_grader_args(p, cfg)
    p = sub.add_parser("pad", help="copy a run with one sentence of filler added to each last reply")
    p.add_argument("run", help="run name in evals/runs or a .json path")
    p = sub.add_parser("bias", help="which reply is better, asked in both orders")
    p.add_argument("run_a", help="run A (name in evals/runs or a .json path)")
    p.add_argument("run_b", help="run B, from the same suite")
    _add_grader_args(p, cfg)
    p = sub.add_parser("dataset", help="build and inspect versioned datasets")
    dsub = p.add_subparsers(dest="action", required=True)
    b = dsub.add_parser("build", help="merge sources, split dev/test, write the lock file")
    b.add_argument("--manifest", default=str(cfg.datasets_dir / "bramble.json"))
    st = dsub.add_parser("stats", help="coverage per tag dimension, dev vs test")
    st.add_argument("name", help="dataset name and version, like bramble-v1")
    args = parser.parse_args(argv)
    if args.cmd == "dataset":
        return cmd_dataset(args, cfg)
    if args.cmd == "pad":
        return cmd_pad(args, cfg)
    if args.cmd == "refusals":
        return cmd_refusals(args, cfg)
    if args.cmd == "deepeval":
        return cmd_deepeval(args, cfg)
    if args.cmd == "review":
        return cmd_review(args, cfg)
    if args.cmd == "traces":
        return cmd_traces(args, cfg)
    if args.cmd == "label":
        return cmd_label(args, cfg)
    try:
        if args.cmd == "generate":
            return cmd_generate(args, cfg)
        if args.cmd == "grade":
            return cmd_grade(args, cfg)
        if args.cmd == "bias":
            return cmd_bias(args, cfg)
        return cmd_run(args, cfg) if args.cmd == "run" else cmd_chat(args, cfg)
    except CONNECTION_ERRORS:
        provider = getattr(args, "grader_provider", None) or args.provider
        where = cfg.ollama_url if provider == "ollama" else provider
        print(f"Can't reach the model at {where}. Is Ollama running? (ollama serve)"
              if provider == "ollama" else f"Can't reach {where}. Check your network and API key.")
        return 1
