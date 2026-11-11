"""Okapi BM25, the lexical ranker for short-document corpora.

Pure Python, no dependency, same formula the IR literature uses:

    score(d, q) = sum over q_i of IDF(q_i) * f(q_i, d) * (k1 + 1) / (f(q_i, d) + k1 * (1 - b + b * |d| / avgdl))

with IDF(q) = log(1 + (N - n(q) + 0.5) / (n(q) + 0.5)) so a term absent from
every document contributes nothing and a stopword-ish universal term
contributes ~0 without ever going negative.

The corpus is whatever the caller passes as token lists (or raw strings,
which this module tokenizes on whitespace/lowercase). `fit` builds the
postings and statistics; `score`/`top_k` read them.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _as_tokens(document: Iterable[str] | str) -> list[str]:
    if isinstance(document, str):
        return tokenize(document)
    return list(document)


class Bm25:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be positive")
        if not 0.0 <= b <= 1.0:
            raise ValueError("b must be inside [0, 1]")
        self.k1 = k1
        self.b = b
        self._doc_tokens: list[list[str]] = []
        self._doc_len: list[int] = []
        self._avgdl = 0.0
        self._df: Counter[str] = Counter()  # documents each term appears in
        self._postings: list[Counter[str]] = []  # per-document term frequencies

    def fit(self, documents: Iterable[list[str] | str]) -> "Bm25":
        docs = [_as_tokens(d) for d in documents]
        self._doc_tokens = docs
        self._doc_len = [len(d) for d in docs]
        total = sum(self._doc_len)
        self._avgdl = total / len(docs) if docs else 0.0
        self._df = Counter()
        self._postings = []
        for tokens in docs:
            freq = Counter(tokens)
            self._postings.append(freq)
            for term in freq:
                self._df[term] += 1
        return self

    def idf(self, term: str) -> float:
        n = len(self._doc_tokens)
        n_q = self._df.get(term, 0)
        return math.log(1 + (n - n_q + 0.5) / (n_q + 0.5))

    def score(self, query: Iterable[str] | str, index: int) -> float:
        tokens = _as_tokens(query)
        if not tokens or not self._doc_tokens:
            return 0.0
        if not 0 <= index < len(self._doc_tokens):
            raise IndexError(index)
        doc_len = self._doc_len[index]
        freq = self._postings[index]
        numerator_scale = self.k1 + 1
        length_norm = self.k1 * (1 - self.b + self.b * (doc_len / self._avgdl if self._avgdl else 0.0))
        total = 0.0
        for term in set(tokens):
            tf = freq.get(term, 0)
            if tf == 0:
                continue
            total += self.idf(term) * (tf * numerator_scale) / (tf + length_norm)
        return total

    def scores(self, query: Iterable[str] | str) -> list[float]:
        tokens = _as_tokens(query)
        return [self.score(tokens, i) for i in range(len(self._doc_tokens))]

    def top_k(self, query: Iterable[str] | str, k: int) -> list[tuple[int, float]]:
        """The k highest-scoring documents, best first (ties by earlier index)."""
        if k < 0:
            raise ValueError("k must be >= 0")
        scored = [(index, score) for index, score in enumerate(self.scores(query))]
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:k]
