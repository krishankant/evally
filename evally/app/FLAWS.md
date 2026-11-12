# Planted flaws (spoiler file)

The bookstore assistant ships with deliberate weaknesses, so the course's evals have
real failures to find. The lessons don't link here until the capstone. If you're
following the course, try to find them with evals first.

| Id | Flaw | Where it lives | Week that should catch it |
| --- | --- | --- | --- |
| F1 | An out-of-date returns policy (60 days, store credit) sits next to the current one (30 days, original payment). Retrieval brings back both. | `docs/returns-2023.md` | 1 (code check), 9 (RAG checks) |
| F2 | The stock tool always times out for books in the north warehouse. | `tools.py`, `check_stock` | 1, 10 (agent checks) |
| F3 | The system prompt is thin: no refusal rules, nothing about conflicting documents, no length limit, nothing about privacy. | `assistant.py`, `SYSTEM_PROMPT` | 2, 11 (safety) |
| F4 | Nothing stops the assistant promising things policy doesn't allow, such as a price match. | `assistant.py` + `docs/price-match.md` | 1, 5 (LLM grader) |
| F5 | Replies run long. | `assistant.py` (no length rule) | 1 |
