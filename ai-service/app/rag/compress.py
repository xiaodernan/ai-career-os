"""Context compression: keep only query-relevant sentences from retrieved chunks.

Lexical first (cheap, deterministic); the LLM pass over full chunks is avoided by
design to reduce token cost (PRD §36).
"""

import re

_SENT = re.compile(r"(?<=[.!?。！？;；\n])\s+")
_STOP = set("""the a an and or of to in for with on at is are was be this that your you
的 了 是 在 和 与 有 for a""".split())


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[\w\u4e00-\u9fff+.#-]+", s.lower()) if t not in _STOP}


def compress(query_terms: list[str], chunks: list[dict], min_keep: float = 0.12) -> list[dict]:
    q = _tokens(" ".join(query_terms))
    out = []
    for c in chunks:
        sents = [s for s in _SENT.split(c["text"]) if s.strip()]
        if not sents:
            continue
        scored = []
        for i, s in enumerate(sents):
            overlap = len(q & _tokens(s))
            scored.append((overlap, i, s))
        best = sorted(scored, key=lambda x: (-x[0], x[1]))
        keep_idx = {i for ov, i, _ in best if ov > 0}
        if not keep_idx:
            keep_idx = {0}
        # always keep some sentences so context is not gutted
        floor = min(max(1, int(len(sents) * min_keep)), len(sents))
        for i in range(len(sents)):
            if len(keep_idx) >= floor:
                break
            keep_idx.add(i)
        kept = " ".join(s for _, i, s in sorted((x for x in scored if x[1] in keep_idx),
                                                 key=lambda x: x[1]))
        c = dict(c)
        c["text_original"] = c["text"]
        c["text"] = kept[:2400]
        out.append(c)
    return out
