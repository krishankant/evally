"""BM25 keyword search over the policy documents.

Each policy is short, so each file is one searchable document. BM25 scores a document
higher when it contains the query's words, especially rare ones, without rewarding
long documents just for being long.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DOCS_DIR = Path(__file__).with_name("docs")
STOPWORDS = set("a an the and or of to in on for is are be do does i my me we you your it can how what when "
                "with this that have has at by from as if not will there about any get".split())


def tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]


@dataclass(frozen=True)
class DocHit:
    name: str
    text: str
    score: float


class Retriever:
    def __init__(self, docs: dict[str, str], k1: float = 1.5, b: float = 0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.tf = {n: Counter(tokenize(t)) for n, t in docs.items()}
        self.len = {n: sum(c.values()) for n, c in self.tf.items()}
        self.avg = sum(self.len.values()) / max(len(docs), 1)
        df = Counter(w for c in self.tf.values() for w in c)
        n = len(docs)
        self.idf = {w: math.log(1 + (n - d + 0.5) / (d + 0.5)) for w, d in df.items()}

    @classmethod
    def from_dir(cls, path: Path = DOCS_DIR) -> "Retriever":
        return cls({p.name: p.read_text() for p in sorted(Path(path).glob("*.md"))})

    def score(self, name: str, terms: list[str]) -> float:
        tf, length, s = self.tf[name], self.len[name], 0.0
        for w in terms:
            f = tf.get(w, 0)
            if f:
                s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self.avg))
        return s

    def search(self, query: str, k: int = 3) -> list[DocHit]:
        terms = tokenize(query)
        if not terms:
            return []
        scored = sorted(((self.score(n, terms), n) for n in self.docs), key=lambda x: (-x[0], x[1]))
        return [DocHit(n, self.docs[n], round(s, 4)) for s, n in scored[:k] if s > 0]
