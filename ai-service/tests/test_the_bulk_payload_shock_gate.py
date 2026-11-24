"""One oversized request, one oversized corpus — the bulk-shape of the stress brief.

The 200-caller gates answer concurrency; this one answers the other half of
"瞬间大数据量冲击": a single caller arriving with megabytes at once. The shipped
bounds are exercised, not replaced — a size check before parsing, and a context
budget before the model sees anything. Both must refuse or truncate HONESTLY:
no half-parsed rows, no invented content, no unbounded work. No DB, Redis,
Docker, LLM or socket is involved.
"""

from __future__ import annotations

import json
import time

import pytest

from app.core import context_budget as cb
from app.core.ai import evidence_block
from app.core.errors import RefusalError
from app.features import ingestion as I


def test_one_megabyte_board_is_refused_before_it_is_parsed() -> None:
    # One request, not a crowd: a board far larger than the shipped ceiling.
    rows = [{"title": f"role-{i}", "description": "x" * 100} for i in range(50_000)]
    board = json.dumps({"jobs": rows}, ensure_ascii=False)
    assert len(board) > I.MAX_FEED_BYTES  # the shock is real, not a token gesture

    started = time.perf_counter()
    with pytest.raises(RefusalError) as caught:
        I.parse_json_board(board)
    elapsed = time.perf_counter() - started

    refusal = caught.value.refusal
    assert refusal.code == "INGEST_BOARD_TOO_LARGE"
    # The refusal is a fixed, structured sentence: it names the kind of refusal
    # without inventing a size (the cap is a constant the code owns, not a claim
    # to restate per request). No partial parse escapes as a "successful" answer.
    assert refusal.message == "board payload exceeds the size cap"
    assert refusal.status == 400
    # The size check precedes json.loads, so the work is bounded by the ceiling,
    # not by the payload the caller chose to send.
    assert elapsed < 5.0


def test_huge_corpus_is_truncated_to_the_shipped_budget_with_honest_accounting() -> None:
    corpus = {"rows": [{"id": i, "text": f"candidate-{i}"} for i in range(60_000)]}

    started = time.perf_counter()
    fitted = cb.fit_json(corpus)
    elapsed = time.perf_counter() - started

    assert fitted.text
    assert len(fitted.text) <= fitted.cap <= cb.input_budget()
    assert fitted.dropped > 0 and fitted.truncated is True
    # The visible text is a verbatim prefix of the caller's own data — nothing
    # is synthesized to fill the gap the truncation left.
    assert fitted.text == json.dumps(corpus, ensure_ascii=False, default=str)[: fitted.kept]
    trace = fitted.as_trace()
    assert trace["input_kept"] == fitted.kept
    assert trace["input_dropped"] == fitted.dropped
    assert trace["input_truncated"] is True
    assert elapsed < 10.0


def test_huge_evidence_corpus_yields_a_bounded_block_of_real_rows() -> None:
    items = [
        {"chunk_id": str(i), "source": "s", "section": "x", "text": "a" * 200}
        for i in range(50_000)
    ]

    started = time.perf_counter()
    block = evidence_block(items, share=0.25)
    elapsed = time.perf_counter() - started

    assert len(block) <= int(cb.input_budget() * 0.25)
    assert "<<<BEGIN UNTRUSTED EVIDENCE>>>" in block
    # The first real chunk survives; an invented marker does not.
    assert "chunk_id=0" in block
    assert "chunk_id=not-a-row" not in block
    assert elapsed < 10.0
