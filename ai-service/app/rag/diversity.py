"""Maximal Marginal Relevance for the reranked top-N.

The fusion stage can surface three near-identical chunks from the same
document when one posting repeats boilerplate ten times. The reader's prompt
then carries the same sentence three times, the reranker scores them all high
(correctly, genuinely relevant) and nothing but the insertion order decides
which survives the context budget. MMR spends a little novelty budget per slot
and buys coverage: each next evidence is scored `lambda * rel - (1-lambda) *
max_jaccard_sim_to_selected`, greedy, deterministic, ties broken by the
incoming order (the fusion's own rank), never dropping a row — the list is a
reordering, not a filter.
"""

from __future__ import annotations

import re
from typing import Any, Callable

_LATIN = re.compile(r"[a-z0-9]+")
_CJK_RUN = re.compile(
    r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]+")

DEFAULT_LAMBDA = 0.7
_TOKEN_CAP = 800  # evidence chunks are capped far below this; the bound keeps pathological inputs cheap


def tokens(text: str) -> set[str]:
    """Latin runs become lowercased words; CJK runs become overlapping bigrams."""
    if not isinstance(text, str) or not text:
        return set()
    out: set[str] = set()
    for m in _LATIN.finditer(text.lower()):
        tok = m.group(0)
        if tok:
            out.add(tok)
        if len(out) >= _TOKEN_CAP:
            return out
    for m in _CJK_RUN.finditer(text):
        run = m.group(0)
        if len(run) == 1:
            out.add(run)
        else:
            for i in range(len(run) - 1):
                out.add(run[i:i + 2])
        if len(out) >= _TOKEN_CAP:
            return out
    return out


def _jaccard(a: set[str], b: Any) -> float:
    if not a or not isinstance(b, set) or not b:
        return 0.0
    inter = len(a & b)
    return inter / float(len(a | b))


def mmr_reorder(
    rows: list[dict],
    *,
    rel: Callable[[dict], float],
    text_of: Callable[[dict], str],
    lambda_: float = DEFAULT_LAMBDA,
) -> list[dict]:
    """Greedy MMR over rows, preserving length: a reordering, never a filter.

    `rel` must return a finite float in any consistent scale — the only use is
    comparison within this call. `lambda_` 0.0-1.0; values outside clamp.
    Ties go to the row earlier in the incoming order, so a caller that passes
    fused-ranked input gets fusion order on exact ties — determinism over cleverness.
    """
    if not rows:
        return []
    lam = max(0.0, min(1.0, float(lambda_)))

    remaining = list(enumerate(rows))
    selected: list[tuple[int, dict]] = []
    selected_tokens: list[set[str]] = []
    rels = {i: float(rel(row)) for i, row in remaining}

    while remaining:
        best_idx = 0
        best_val: float | None = None
        for j, (i, row) in enumerate(remaining):
            toks = tokens(text_of(row))
            sim = 0.0
            for other in selected_tokens:
                s = _jaccard(toks, other)
                if s > sim:
                    sim = s
            val = lam * rels[i] - (1.0 - lam) * sim
            if best_val is None or val > best_val:
                best_val = val
                best_idx = j
        orig_i, chosen = remaining.pop(best_idx)
        selected.append((orig_i, chosen))
        selected_tokens.append(tokens(text_of(chosen)))

    # Incoming order for exact ties is preserved inside the greedy pass by val
    # comparison strictly with '>'; remaining.pop(best_idx) picks first max.
    return [row for _, row in selected]
