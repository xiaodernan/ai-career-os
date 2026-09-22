"""Unit tests for RRF fusion, compression, anti-fabrication verifier, pricing, taskbus."""

import asyncio

import pytest

from app.core.taskbus import finish, gc_old_tasks, is_done, new_task, publish, sse, state, subscribe
from app.features.cover_letter import style_directives
from app.features.tailor import verify_no_fabrication
from app.providers.pricing import estimate_cost
from app.rag.compress import compress
from app.rag.store import rrf_merge

# ---------------- rrf_merge ----------------


def test_rrf_fuses_lists_by_chunk_id():
    a = [{"id": "1", "t": "x"}, {"id": "2", "t": "y"}]
    b = [{"id": "2", "t": "y"}, {"id": "3", "t": "z"}]
    merged = rrf_merge([a, b])
    ids = [m["id"] for m in merged]
    assert ids[0] == "2"  # top-ranked in one list + second in another beats rank-1-only
    assert set(ids) == {"1", "2", "3"}
    assert all(m["rrf"] > 0 for m in merged)


def test_rrf_score_matches_formula_and_cap():
    k = 60
    merged = rrf_merge([[{"id": "1"}], [{"id": "1"}]])
    assert merged[0]["rrf"] == 2 * (1.0 / (k + 1))
    under_cap = [[{"id": str(i)}] for i in range(50)]  # 50 lists, one item each
    assert len(rrf_merge(under_cap, cap=60)) == 50
    flat = [{"id": str(i)} for i in range(100)]
    assert len(rrf_merge([flat], cap=40)) == 40


def test_rrf_empty_lists():
    assert rrf_merge([]) == []


# ---------------- compress ----------------


def test_compress_keeps_query_sentences_and_drops_rest():
    chunks = [{"id": "1", "text": "Used Kafka for streaming events. The team had lunch. "
                                 "Deployed Kafka weekly on AWS."}]
    out = compress(["kafka"], chunks)
    assert "Kafka for streaming" in out[0]["text"]
    assert "Deployed Kafka weekly" in out[0]["text"]
    assert "had lunch" not in out[0]["text"]
    assert out[0]["text_original"].startswith("Used Kafka")


def test_compress_fallback_keeps_first_sentence_when_no_overlap():
    chunks = [{"id": "1", "text": "Alpha one. Alpha two."}]
    out = compress(["zzz-unknown"], chunks)
    assert out[0]["text"] == "Alpha one."


def test_compress_floor_keeps_minimum_sentences():
    text = ". ".join(f"Unrelated sentence number {i}" for i in range(20)) + "."
    chunks = [{"id": "1", "text": text}]
    out = compress(["kafka"], chunks, min_keep=0.12)
    kept = len(out[0]["text"].split(".")) - 1
    assert kept >= 2  # floor of 12% of 20 sentences


# ---------------- verify_no_fabrication ----------------

BASE_RESUME = "Built order services in Java with Spring Boot and MySQL, cut p99 latency by 40%."


def test_verifier_accepts_rephrasing_of_existing_facts():
    after = "Cut p99 latency by 40% by building order services in Java with Spring Boot."
    assert verify_no_fabrication(BASE_RESUME, "", after) is None


def test_verifier_rejects_invented_skill():
    after = "Built order services in Java with Spring Boot, MySQL and Kafka."
    reason = verify_no_fabrication(BASE_RESUME, "", after)
    assert reason and "Kafka" in reason


def test_verifier_rejects_invented_numbers():
    after = "Built order services, cut p99 latency by 75%."
    reason = verify_no_fabrication(BASE_RESUME, "", after)
    assert reason and "75%" in reason


def test_verifier_allows_numbers_present_in_before():
    before = "Improved latency by 30%."
    after = "Cut p99 latency by 30% via tuning."
    # 30% exists in `before`; nothing new relative to resume+before
    reason = verify_no_fabrication(BASE_RESUME + " Improved latency by 30%.", before, after)
    assert reason is None


# ---------------- pricing ----------------


def test_estimate_cost_basic():
    assert estimate_cost("gpt-4o-mini", 1_000_000, 500_000) == pytest.approx(0.45)


def test_estimate_cost_with_cached_input():
    expected = (500 * 2.50 + 500 * 1.25) / 1_000_000
    assert estimate_cost("gpt-4o", 1000, 0, cached=500) == expected


def test_estimate_cost_unknown_model_is_zero():
    assert estimate_cost("some-local-model", 999, 999) == 0.0


# ---------------- taskbus ----------------


async def test_taskbus_replays_history_then_closes_on_done():
    tid = new_task("ingest", user_id="u1")
    publish(tid, "status", {"step": "chunking"})
    publish(tid, "status", {"step": "embedding"})
    finish(tid, True, {"chunks": 3})
    events = [e async for e in subscribe(tid, heartbeat_s=0.05)]
    assert [e["event"] for e in events] == ["status", "status", "done"]
    assert events[-1]["data"]["result"] == {"chunks": 3}
    assert is_done(tid)


async def test_taskbus_live_subscriber_sees_new_events():
    tid = new_task("agent")
    seen = []

    async def consume():
        async for e in subscribe(tid, heartbeat_s=0.05):
            seen.append(e["event"])
            if e["event"] == "done":
                break

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.01)
    publish(tid, "status", {"step": "reranking"})
    finish(tid, True, {"ok": 1})
    await asyncio.wait_for(task, timeout=2)
    assert seen == ["status", "done"]
    st = state(tid)
    assert st["done"] is True and st["events"] == 2 and st["last"]["event"] == "done"


async def test_taskbus_unknown_task_yields_error():
    events = [e async for e in subscribe("no-such-task", heartbeat_s=0.05)]
    assert events[0]["event"] == "error"


def test_taskbus_gc_only_removes_old_done_tasks():
    fresh = new_task("x")
    stale = new_task("y")
    finish(stale, True)
    import app.core.taskbus as tb
    tb._TASKS[stale]["created"] -= 7200
    gc_old_tasks(max_age_s=3600)
    assert state(stale) is None
    assert state(fresh) is not None


def test_sse_formats_event():
    line = sse({"event": "status", "data": {"步骤": "解析"}})
    assert line.startswith("event: status\ndata: ")
    assert '"步骤": "解析"' in line and line.endswith("\n\n")


def test_style_directives_empty_defaults_add_nothing():
    assert style_directives("", "") == []
    assert style_directives("balanced", "") == []
    # "balanced" tone maps to no directive, so only the length one survives
    assert len(style_directives("balanced", "standard")) == 1


def test_style_directives_maps_tone_and_length():
    d = style_directives("formal", "short")
    assert len(d) == 2
    assert any("formal" in s.lower() for s in d)
    assert any("180" in s for s in d)


def test_style_directives_case_insensitive_and_ignores_unknown():
    assert style_directives("  CONCISE ", "detailed") == style_directives("concise", "detailed")
    assert style_directives("unknown-tone", "unknown-len") == []

