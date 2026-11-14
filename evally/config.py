"""Settings, read from .env and the environment. Defaults use the free local Ollama model."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    provider: str
    model: str
    ollama_url: str
    cache_dir: Path
    runs_dir: Path
    suites_dir: Path
    labels_dir: Path
    datasets_dir: Path
    grader_provider: str = "ollama"
    grader_model: str = "qwen3.5:4b"
    grades_dir: Path = Path("evals/grades")


def load() -> Config:
    load_dotenv()  # keys live in .env, never the shell rc file
    return Config(
        provider=os.environ.get("EVALLY_PROVIDER") or "ollama",
        model=os.environ.get("EVALLY_MODEL") or "qwen3.5:4b",
        ollama_url=os.environ.get("OLLAMA_URL") or "http://localhost:11434/v1",
        cache_dir=Path(os.environ.get("EVALLY_CACHE_DIR") or "evals/cache"),
        runs_dir=Path(os.environ.get("EVALLY_RUNS_DIR") or "evals/runs"),
        suites_dir=Path("evals/suites"),
        labels_dir=Path(os.environ.get("EVALLY_LABELS_DIR") or "evals/labels"),
        datasets_dir=Path("evals/datasets"),
        # The grader is set apart from the app: a different model can judge the app's replies.
        grader_provider=os.environ.get("EVALLY_GRADER_PROVIDER") or "ollama",
        grader_model=os.environ.get("EVALLY_GRADER_MODEL") or "qwen3.5:4b",
        grades_dir=Path(os.environ.get("EVALLY_GRADES_DIR") or "evals/grades"),
    )
