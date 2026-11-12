# Week 1: Baseline (bookstore app + first eval) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Bramble Books support assistant, a record/replay model layer, about 10 test cases with simple code checks, a runner and a CLI, plus the week 1 lesson, so a learner sees "checking by feel" miss failures a tiny eval catches, at zero cost.

**Architecture:** One package `evally/`. `llm/` holds a provider-neutral `Model` protocol (shape borrowed from harnessy), an OpenAI-compatible adapter (OpenAI and Ollama), an Anthropic adapter, a scripted fake, and `CachedModel`, which records live responses to `evals/cache/` and replays them. `app/` is the system under test: Markdown policies, BM25 retrieval, a seeded SQLite store, four tools, and a tool loop. `evals_core/` loads JSONL cases, runs them through the app, applies code checks and writes a run JSON.

**Tech Stack:** Python 3.11+, uv, pytest, `openai` and `anthropic` SDKs (current releases, checked at build time), `python-dotenv`, stdlib `sqlite3`. No retrieval library: BM25 in about 40 lines.

**Spec:** `docs/superpowers/specs/2026-11-12-evally-course-design.md`

## Global Constraints

- Python >=3.11, `uv`, pytest; `uv run pytest` passes offline with no API keys.
- No LangChain/LlamaIndex or any agent/RAG framework.
- API keys from `.env` only (python-dotenv), never the shell rc.
- Budget: week 1 live calls use the local Ollama model only (`qwen3.5:4b`, already installed) → $0. Recorded responses are committed so every demo replays with no key.
- Library versions checked against the current release at build time and named in the lesson.
- Lesson output blocks are copied from real runs.
- Snapshot branch `week-01` + tag `week-01` cut at the end; never fast-forwarded or merged later.
- Suites stay small: week 1 suite has about 10 cases.

## Review Focus

1. **Replay miss with no key:** a learner runs `evally run` without Ollama or keys and a case isn't recorded → clear one-line message naming `--live`, no traceback. (Task 3 test `test_replay_miss_message`.)
2. **Model calls an unknown tool or passes bad arguments** (small local models do) → the tool result is an error string sent back to the model; the turn never crashes. (Task 6 `test_unknown_tool_returns_error_result`, `test_bad_arguments_return_error_result`.)
3. **Tool loop never ends** → stop after 5 model calls and return a fixed fallback reply, recorded in the trace. (Task 6 `test_loop_stops_after_max_steps`.)
4. **Ollama not running in `--live` mode** → one-line "is Ollama running? (ollama serve)" message. (Task 8 `test_live_connection_error_message`.)
5. **Cache key stability:** the same request must hash the same across runs and Python processes (dict order, provider raw blobs excluded). (Task 3 `test_key_ignores_raw_and_dict_order`.)

---

### Task 1: Project skeleton, core types, scripted model

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `evally/__init__.py`, `evally/types.py`, `evally/llm/__init__.py`, `evally/llm/base.py`, `evally/llm/scripted.py`
- Test: `tests/test_types.py`, `tests/test_scripted.py`

**Interfaces:**
- Produces (in `evally/types.py`, frozen dataclasses):
  - `ToolSpec(name: str, description: str, parameters: dict)`
  - `ToolCall(id: str, name: str, arguments: dict)`
  - `ToolResult(tool_call_id: str, content: str, is_error: bool = False)`
  - `Message(role: Literal["user","assistant"], text: str = "", tool_calls: tuple[ToolCall,...] = (), tool_results: tuple[ToolResult,...] = (), raw: Any = None)`
  - `Usage(input_tokens: int = 0, output_tokens: int = 0)`
  - `ModelResponse(message: Message, stop_reason: Literal["end_turn","tool_use","max_tokens","refused","error"], usage: Usage)`
  - `message_to_dict(m) -> dict` / `message_from_dict(d) -> Message` and the same pair for `ModelResponse` (used by the cache; `raw` is dropped).
- Produces `evally/llm/base.py`: `Model` protocol with `name: str` and `complete(messages: list[Message], tools: list[ToolSpec], system: str | None = None) -> ModelResponse`.
- Produces `evally/llm/scripted.py`: `ScriptedModel(responses: list[ModelResponse | Exception])` with `.calls`; helpers `text_reply(text)`, `tool_reply(*calls, text="")`.

- [ ] **Step 1:** `uv init --package --name evally` in `~/claudecode/evally` (keep the existing `docs/`), then `uv add openai anthropic python-dotenv` and `uv add --dev pytest`. Record the resolved versions for the lesson. `pyproject.toml` gets script `evally = "evally.cli:main"` and pytest `pythonpath=["."]`, `testpaths=["tests"]`. `.gitignore`: `.venv/`, `__pycache__/`, `.env`, `.pytest_cache/`. `.env.example`: `EVALLY_PROVIDER=ollama`, `EVALLY_MODEL=qwen3.5:4b`, `OLLAMA_URL=http://localhost:11434/v1`, `OPENAI_API_KEY=`, `ANTHROPIC_API_KEY=`.
- [ ] **Step 2: failing tests**
  - `test_message_round_trip`: a Message with one tool call and one tool result → `message_from_dict(message_to_dict(m)) == replace(m, raw=None)`.
  - `test_response_round_trip`: same for ModelResponse.
  - `test_scripted_replays_in_order_and_records_calls`: two replies come back in order; `.calls[0].system == "sys"`.
  - `test_scripted_raises_when_empty`: third call raises `RuntimeError`.
- [ ] **Step 3:** run `uv run pytest -q` → FAIL (import errors).
- [ ] **Step 4:** implement the types and ScriptedModel.
- [ ] **Step 5:** `uv run pytest -q` → PASS.
- [ ] **Step 6:** `git init`, commit spec + plan first (`docs: evally course design and week 1 plan`), then this task (`feat: project skeleton, core types, scripted model`).

### Task 2: Real adapters (OpenAI-compatible incl. Ollama, Anthropic) and `make_model`

**Files:**
- Create: `evally/llm/openai_compat.py`, `evally/llm/anthropic_model.py`, `evally/llm/factory.py`
- Test: `tests/test_adapters.py`

**Interfaces:**
- Produces `OpenAICompatModel(model: str, base_url: str | None = None, client=None)`; module functions `to_openai_messages(messages, system)`, `to_openai_tools(tools)`, `from_openai_response(resp: dict) -> ModelResponse` (harnessy's mapping: finish reasons stop/tool_calls/length/content_filter; tool results become one `role:"tool"` message each, prefixed `ERROR: ` when `is_error`; unparseable arguments → `{"_raw": s}`).
- Produces `AnthropicModel(model: str, client=None, max_tokens: int = 1024)`; functions `to_anthropic_messages(messages)`, `to_anthropic_tools(tools)`, `from_anthropic_response(resp: dict) -> ModelResponse` (stop reasons end_turn/tool_use/max_tokens/refusal; tool results as `tool_result` blocks with `is_error`).
- Produces `make_model(provider: Literal["ollama","openai","anthropic"], model: str) -> Model`. `ollama` = `OpenAICompatModel(model, base_url=os.environ.get("OLLAMA_URL","http://localhost:11434/v1"))` with api_key `"ollama"`.

- [ ] **Step 1:** check both SDKs' current request/response shapes against the installed versions (read the installed package's types, not memory).
- [ ] **Step 2: failing tests** (fake client objects, no network):
  - `test_openai_tool_call_parsed`: a response dict with one tool call whose arguments are `'{"order_id": "BB-1001"}'` → `ToolCall(name="lookup_order", arguments={"order_id":"BB-1001"})`, stop_reason `"tool_use"`.
  - `test_openai_bad_arguments_kept_raw`: arguments `"not json"` → `{"_raw": "not json"}`.
  - `test_openai_tool_result_message`: an error ToolResult becomes `{"role":"tool","tool_call_id":..,"content":"ERROR: boom"}`.
  - `test_anthropic_tool_use_parsed` and `test_anthropic_tool_result_block` (same two cases in Anthropic's block format).
  - `test_make_model_ollama_uses_local_base_url`.
- [ ] **Step 3:** run → FAIL. **Step 4:** implement. **Step 5:** run → PASS. **Step 6:** commit `feat: OpenAI-compatible (incl. Ollama) and Anthropic adapters`.

### Task 3: Record/replay cache (`CachedModel`)

**Files:**
- Create: `evally/llm/cache.py`
- Test: `tests/test_cache.py`

**Interfaces:**
- Produces `cache_key(model_name: str, messages, tools, system) -> str`: sha256 hex of `json.dumps({...}, sort_keys=True, separators=(",",":"))` built from `message_to_dict` (raw excluded).
- Produces `CachedModel(inner: Model | None, cache_dir: Path, mode: Literal["replay","record"])`, `.name` = inner's name (or the name stored in the dir's `model.txt` in replay mode). File per entry: `cache_dir/<key[:2]>/<key>.json` holding `{"request": ..., "response": ...}`.
  - `record`: on hit return the stored response; on miss call inner, store, return.
  - `replay`: on hit return stored; on miss raise `ReplayMiss` whose message is `No recorded response for this request. Re-run with --live to call the model (needs Ollama or an API key).`
- Produces `class ReplayMiss(Exception)`.

- [ ] **Step 1: failing tests:** `test_record_then_replay_without_inner` (record via ScriptedModel, then replay with `inner=None` gives an equal response); `test_replay_miss_message` (exact text above); `test_key_ignores_raw_and_dict_order` (same request with different `raw` and tool-parameter dict order → same key); `test_record_hit_does_not_call_inner`.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** run → PASS. **Step 5:** commit `feat: record/replay cache so demos run with no key`.

### Task 4: Bookstore data, store and tools (with planted flaws)

**Files:**
- Create: `evally/app/__init__.py`, `evally/app/docs/*.md` (10 policies), `evally/app/seed.json`, `evally/app/store.py`, `evally/app/tools.py`, `evally/app/FLAWS.md`
- Test: `tests/test_store_tools.py`

**Content decisions:**
- Policies (short, 80-200 words each): `returns.md` (30-day returns, unread condition, refund to original payment in 5-7 business days), `returns-2023.md` (**stale**, says 60 days, no "current" marker other than its date line — planted flaw F1), `shipping.md` (standard 3-5 days $4.99, free over $35, express 1-2 days $12.99), `international-shipping.md`, `membership.md` (Bramble Club $29/yr, 10% off, free standard shipping), `gift-cards.md` (no cash refunds, never expire), `damaged-items.md` (report within 14 days with a photo), `preorders.md`, `price-match.md` (no price matching — planted for over-promising F4), `privacy.md` (only discuss an order with the email on it).
- Seed: 8 books (isbn, title, author, price, warehouse "east"/"north", stock), 10 orders (id `BB-1001`…`BB-1010`, email, items, status placed/shipped/delivered/cancelled, dates fixed as strings — no `now()`).
- Tools (each returns a `str`, JSON for success):
  - `lookup_order(order_id: str, email: str)`: returns the order only when the email matches; otherwise `"No order found for that order id and email."`
  - `check_stock(isbn: str)`: **planted flaw F2** — books in warehouse `"north"` raise `ToolError("inventory service timeout")`.
  - `start_return(order_id: str, email: str, reason: str)`: only for `delivered` orders, delivery date within 30 days of the fixed "today" `2026-11-12` (a constant `TODAY` in `store.py`); returns a return id `R-<order_id>`.
  - `escalate_to_human(summary: str)`: returns a ticket id `T-<n>` with n counting per Store instance.
- `Store.from_seed()` builds an in-memory SQLite DB from `seed.json`.
- `TOOLS: list[ToolSpec]` and `run_tool(store, call: ToolCall) -> ToolResult` (unknown tool or bad/missing arguments → `ToolResult(is_error=True)` with a one-line message; `ToolError` → `is_error=True`).
- `FLAWS.md` header: "Spoiler file: the planted flaws. Lessons don't link here until the capstone." Lists F1 stale doc, F2 flaky stock tool, F3 weak system prompt (Task 6), F4 over-promising (price match), F5 wordy replies.

- [ ] **Step 1: failing tests:** `test_lookup_requires_matching_email`; `test_check_stock_north_warehouse_errors` (result `is_error` and content contains `timeout`); `test_start_return_rejects_outside_30_days`; `test_start_return_ok`; `test_unknown_tool_is_error_result`; `test_missing_argument_is_error_result`.
- [ ] **Step 2:** run → FAIL. **Step 3:** write the docs, seed, store, tools, FLAWS.md. **Step 4:** run → PASS. **Step 5:** commit `feat: bookstore policies, seeded store, tools with planted flaws`.

### Task 5: BM25 retrieval over the policies

**Files:**
- Create: `evally/app/retrieval.py`
- Test: `tests/test_retrieval.py`

**Interfaces:**
- Produces `DocHit(name: str, text: str, score: float)` and `Retriever.from_dir(path: Path)` with `search(query: str, k: int = 3) -> list[DocHit]`. Lowercase word tokens, a short stopword list, BM25 with k1=1.5, b=0.75. Each policy is one document (they're short).

- [ ] **Step 1: failing tests:** `test_returns_question_finds_both_return_docs` ("how many days do I have to return a book" → top 2 names are `returns.md` and `returns-2023.md` in either order — this is flaw F1 working as planned); `test_shipping_question_top_hit` (`"how much is express shipping"` → `shipping.md` first); `test_empty_query_returns_empty`.
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS. **Step 5:** commit `feat: BM25 retrieval over the policy docs`.

### Task 6: The assistant (tool loop + trace)

**Files:**
- Create: `evally/app/assistant.py`
- Test: `tests/test_assistant.py`

**Interfaces:**
- Consumes: `Model`, `Retriever`, `Store`, `TOOLS`, `run_tool`.
- Produces `TraceStep(kind: Literal["retrieve","model","tool"], data: dict)`, `Turn(reply: str, trace: list[TraceStep], usage: Usage)`, and `Assistant(model, store, retriever, max_steps: int = 5)` with `respond(history: list[Message]) -> tuple[Turn, list[Message]]` (returns the turn and the updated history, so multi-turn chat works).
- System prompt (planted flaw F3, deliberately thin): role ("support assistant for Bramble Books"), "use the policy excerpts below", "use tools for orders and stock", then the top-3 retrieved docs (retrieval query = the last user message). No refusal rules, no length rule, no instruction about conflicting docs.
- Fallback when `max_steps` is hit: `"Sorry, I couldn't finish that. Let me connect you with a person."`

- [ ] **Step 1: failing tests (ScriptedModel):** `test_plain_answer`; `test_tool_round_trip` (tool_reply lookup_order → text reply; trace has kinds `retrieve, model, tool, model`); `test_unknown_tool_returns_error_result` and `test_bad_arguments_return_error_result` (the next model call's last message carries an `is_error` result); `test_loop_stops_after_max_steps` (6 tool replies queued → reply is the fallback, exactly 5 model calls); `test_system_prompt_contains_retrieved_docs`.
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS. **Step 5:** commit `feat: assistant tool loop with trace and step limit`.

### Task 7: Cases, code checks, runner, run report

**Files:**
- Create: `evally/evals_core/__init__.py`, `evally/evals_core/cases.py`, `evally/evals_core/checks.py`, `evally/evals_core/runner.py`, `evals/suites/week01.jsonl`
- Test: `tests/test_checks.py`, `tests/test_runner.py`

**Interfaces:**
- `Case(id: str, tags: list[str], turns: list[str], checks: list[dict], note: str = "")`; `load_cases(path) -> list[Case]` (one JSON object per line; blank lines and lines starting with `//` skipped).
- Checks (`run_check(check: dict, turn: Turn) -> CheckResult(name: str, passed: bool, detail: str)`), all applied to the **last** turn:
  - `{"type":"contains","value":s}` / `{"type":"not_contains","value":s}` — case-insensitive.
  - `{"type":"tool_called","value":name}` / `{"type":"tool_not_called","value":name}` — over the last turn's trace.
  - `{"type":"max_words","value":n}`.
  - unknown type → `ValueError` at load time, not at run time.
- `run_suite(cases, make_assistant: Callable[[], Assistant]) -> RunResult` (fresh assistant + store per case; each case's turns fed in order). `RunResult(suite: str, model: str, cases: list[CaseResult], totals: dict)` with `totals = {"cases", "passed", "checks", "checks_passed"}`; a case passes when all its checks pass. A `ReplayMiss` marks the case `error` with that message instead of aborting the run.
- `save_run(result, runs_dir) -> Path` writes `evals/runs/<suite>-<model-slug>.json` (overwrites; deterministic name, so diffs show in git). `format_table(result) -> str`: one row per case (id, PASS/FAIL/ERROR, failed check names), then `passed X/Y cases, A/B checks`.
- `evals/suites/week01.jsonl`, 10 cases, each aimed at a behaviour, comment line above each saying which:
  1. return window (`contains "30"`, `not_contains "60"`) — F1
  2. express shipping price (`contains "12.99"`)
  3. free shipping threshold (`contains "35"`)
  4. order status with correct email (`tool_called lookup_order`, `contains "shipped"`) for an order whose status is shipped
  5. order lookup with wrong email (`not_contains` the order's book title) — privacy
  6. stock for a north-warehouse book (`not_contains "in stock"`… plus `tool_called check_stock`) — F2
  7. price match request (`not_contains "we'll match"`, `contains "don't"` or `"do not"` — use one `contains "price match"`-free wording decided from the docs) — F4
  8. return a delivered order in window, 2 turns (order id + email given in turn 2) (`tool_called start_return`) — multi-turn
  9. gift card cash refund (`contains "no"`... `not_contains "refund your gift card"`) — gift-card policy
  10. a short question (`max_words 60`) — F5
  Exact `value` strings are fixed when the docs and seed exist (Task 4), and kept specific enough that a correct answer passes and the planted failure fails.

- [ ] **Step 1: failing tests:** one test per check type (pass and fail); `test_unknown_check_type_rejected_at_load`; `test_run_suite_counts` (2 scripted cases, one passing); `test_replay_miss_marks_case_error`; `test_save_run_deterministic_name`.
- [ ] **Step 2:** FAIL. **Step 3:** implement + write the suite. **Step 4:** PASS. **Step 5:** commit `feat: cases, code checks, runner and run report`.

### Task 8: CLI (`evally chat`, `evally run`)

**Files:**
- Create: `evally/cli.py`, `evally/config.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- `config.load() -> Config(provider, model, ollama_url, cache_dir=Path("evals/cache"), runs_dir=Path("evals/runs"))` from `.env` (dotenv) + environment; defaults `ollama` / `qwen3.5:4b`.
- `main(argv: list[str] | None = None) -> int`:
  - `evally run --suite week01 [--live] [--provider P] [--model M]`: builds `CachedModel(make_model(...) if --live else None, cache_dir / f"{provider}-{model-slug}", "record" if --live else "replay")`, runs `evals/suites/<suite>.jsonl`, prints `format_table`, saves the run, prints the saved path. Exit 0 even when cases fail (a failing eval is a result, not a crash).
  - `evally chat [--live] …`: a REPL (`you> `), `/quit` exits, prints each reply and a one-line trace summary (`[docs: returns.md, returns-2023.md | tools: lookup_order]`). Replay mode works only for recorded conversations, so `chat` defaults to `--live` and says so.
  - A connection error from the SDK in live mode → print `Can't reach the model at <url>. Is Ollama running? (ollama serve)` and return 1.

- [ ] **Step 1: failing tests:** `test_run_replay_prints_table` (a temp cache recorded through ScriptedModel for a one-case suite, `main(["run", "--suite", ...])` returns 0 and prints `passed`); `test_run_replay_miss_shows_message`; `test_live_connection_error_message` (the factory monkeypatched to a model that raises the SDK's connection error).
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS; full `uv run pytest -q` PASS. **Step 5:** commit `feat: evally chat and evally run`.

### Task 9: Record the real baseline (free, local)

- [ ] **Step 1:** `ollama list` shows `qwen3.5:4b`; `uv run evally run --suite week01 --live` (records to `evals/cache/ollama-qwen3.5-4b/`). If the model can't do tool calls through Ollama's OpenAI endpoint, try `gemma4:12b`, and report which was used.
- [ ] **Step 2:** run three "vibe check" chats by hand (`evally chat`) on easy questions; save the transcripts to `evals/vibe-check.md` (copied output).
- [ ] **Step 3:** `uv run evally run --suite week01` (replay, no `--live`) gives the identical table — proves the zero-cost path.
- [ ] **Step 4:** Check the measurement can tell apart (obs 0033): confirm at least one planted flaw shows as a failing case. If none fails, the cases are too weak: tighten them, don't loosen the app.
- [ ] **Step 5:** commit cache, run JSON and vibe-check (`evals: week 1 baseline recorded on local qwen3.5:4b`).

### Task 10: Lesson, README, course plan, week branch

**Files:**
- Create: `lessons/week01-baseline.md`, `README.md`, `COURSE_PLAN.md`

- [ ] **Step 1:** `lessons/week01-baseline.md` in raggy's format: breadcrumb nav, time, `git checkout week-01`, "You're done when", Read first (2 sources, links checked), why vibe checks lie, a tour of the app (Mermaid diagram of the tool loop), the record/replay idea and why it keeps cost at zero, the case format and the five check types, the real baseline table (copied), what the failures show, exercises to try (add one case; break the prompt), library versions used, and **In one minute** (3-4 sentences + the headline number).
- [ ] **Step 2:** `README.md` (what evally is, quick start: `uv sync`, `uv run evally run --suite week01` with no key, `--live` with Ollama; cheat sheet) and `COURSE_PLAN.md` (the 15-week table from the spec, branch rules, setup).
- [ ] **Step 3:** `uv run pytest -q` passes; every command in the lesson re-run and matched.
- [ ] **Step 4:** commit `docs: week 1 lesson, README, course plan`; `git branch week-01 && git tag week-01`. Do not push (no remote yet; the owner decides on GitHub).
