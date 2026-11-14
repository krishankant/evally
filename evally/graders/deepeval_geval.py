"""The same rubric, graded by DeepEval's G-Eval, through evally's own recorded model.

G-Eval (DeepEval 4.3.2) asks the model twice: first to turn the rubric into evaluation
steps, then to score the reply against those steps, from 0 to 10, which it scales to 0-1.
`CachedJudge` hands DeepEval our `CachedModel`, so its calls are recorded and replayed
like every other call in the course, and the steps it wrote can be shown.

DeepEval is an optional extra: everything here imports it inside `_deepeval_env`, which
turns telemetry off and supplies a placeholder OpenAI key for the duration.
"""

from __future__ import annotations

from evally.graders.deepeval_side import _deepeval_env
from evally.graders.judge import conversation_for_grader
from evally.graders.rubrics import Rubric
from evally.llm.base import Model
from evally.types import Message

THRESHOLD = 0.5


def make_cached_judge(model: Model):
    """A DeepEvalBaseLLM that calls `model`. Built inside the env guard, since it imports DeepEval."""
    with _deepeval_env():  # the first import of DeepEval must already have telemetry off
        from deepeval.models import DeepEvalBaseLLM

    class CachedJudge(DeepEvalBaseLLM):
        def __init__(self, inner: Model):
            self.inner = inner
            self.tokens = {"input": 0, "output": 0}
            super().__init__(inner.name)

        def load_model(self):
            return self.inner

        def generate(self, prompt: str, schema=None) -> str:
            # No structured output and no logprobs: G-Eval parses the JSON out of the text.
            resp = self.inner.complete([Message("user", prompt)], [], None)
            self.tokens["input"] += resp.usage.input_tokens
            self.tokens["output"] += resp.usage.output_tokens
            return resp.message.text

        async def a_generate(self, prompt: str, schema=None) -> str:
            return self.generate(prompt, schema)

        def get_model_name(self) -> str:
            return self.inner.name

    return CachedJudge(model)


def split_case(case: dict) -> tuple[str, str]:
    """(the conversation up to the last customer message, the last reply)."""
    *earlier, last = case["turns"]
    shown = {**case, "turns": earlier + [{**last, "reply": ""}]}
    text = conversation_for_grader(shown).rsplit("\nassistant:", 1)[0]
    return text, last["reply"]


def geval_case(model: Model, rubric: Rubric, case: dict, reference: str) -> dict:
    with _deepeval_env():
        from deepeval.metrics import GEval
        from deepeval.test_case import LLMTestCase, SingleTurnParams

        metric = GEval(
            name=rubric.name,
            criteria=rubric.text,
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.CONTEXT],
            model=(judge := make_cached_judge(model)),
            threshold=THRESHOLD,
            async_mode=False,
        )
        conversation, reply = split_case(case)
        metric.measure(LLMTestCase(input=conversation, actual_output=reply, context=[reference]))
        return {"score": metric.score, "reason": metric.reason, "passed": metric.is_successful(),
                "steps": list(metric.evaluation_steps or []), "tokens": judge.tokens}
