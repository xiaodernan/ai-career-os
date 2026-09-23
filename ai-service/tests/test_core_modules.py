"""Unit tests for RRF fusion, compression, anti-fabrication verifier, pricing, taskbus."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.core.ai import _coerce_json
from app.core.taskbus import finish, gc_old_tasks, is_done, new_task, publish, sse, state, subscribe
from app.features.cover_letter import _build_prompt, style_directives
from app.features.interview import (_trajectory_detail, advance, decide_next,
                                    evaluate_answer, finalize)
from app.features.jd_analyze import _backfill_skills, suggest_resume_improvements
from app.features.tailor import _apply_changes, verify_no_fabrication
from app.providers.pricing import estimate_cost
from app.rag import rerank as rerank_mod
from app.rag.compress import compress
from app.rag.pipeline import to_evidence
from app.rag import rewrite as rewrite_mod
from app.rag.rerank import rerank
from app.rag.rewrite import _INTENTS, understand
from app.rag.store import rrf_merge

# ---------------- to_evidence (RAG citation shaping) ----------------


def test_to_evidence_numbers_refs_from_one_and_maps_fields():
    chunks = [
        {"id": "c1", "document_id": "d1", "doc_title": "Resume", "source_kind": "resume",
         "section_path": "Experience/Acme", "text": "Built services.", "rerank": 0.9, "rrf": 0.02},
        {"id": "c2", "document_id": "d2", "doc_title": "Project", "source_kind": "project",
         "section_path": "README", "text": "Shipped X.", "rrf": 0.03},
    ]
    ev = to_evidence(chunks)
    assert [e["ref"] for e in ev] == [1, 2]  # 1-based, stable ordering
    assert ev[0]["chunk_id"] == "c1" and ev[0]["document_id"] == "d1"
    assert ev[0]["section"] == "Experience/Acme"  # section_path renamed to section
    assert ev[0]["source_kind"] == "resume"


def test_to_evidence_score_is_best_of_rerank_and_rrf():
    assert to_evidence([{"id": "a", "document_id": "d", "text": "t",
                         "rerank": 0.75, "rrf": 0.9}])[0]["score"] == 0.9
    assert to_evidence([{"id": "a", "document_id": "d", "text": "t",
                         "rerank": 0.9, "rrf": 0.75}])[0]["score"] == 0.9
    # rerank_mode="none": chunks carry only rrf -> rrf is surfaced, not zeroed out
    assert to_evidence([{"id": "a", "document_id": "d", "text": "t",
                         "rrf": 0.0312}])[0]["score"] == 0.0312


def test_to_evidence_treats_missing_and_zero_scores_as_zero():
    s = to_evidence([{"id": "a", "document_id": "d", "text": "t"}])[0]["score"]
    assert s == 0  # neither rerank nor rrf present
    # rerank explicitly 0.0 must not crash the `or 0` guard and stays 0
    assert to_evidence([{"id": "a", "document_id": "d", "text": "t", "rerank": 0.0,
                         "rrf": 0.0}])[0]["score"] == 0


def test_to_evidence_caps_quote_and_handles_null_text():
    long_text = "x" * 1000
    e = to_evidence([{"id": "a", "document_id": "d", "text": long_text}])[0]
    assert len(e["quote"]) == 600
    assert to_evidence([{"id": "a", "document_id": "d", "text": None}])[0]["quote"] == ""


def test_to_evidence_rounds_score_to_four_places():
    e = to_evidence([{"id": "a", "document_id": "d", "text": "t", "rrf": 0.123456789}])[0]
    assert e["score"] == 0.1235


def test_to_evidence_empty_input():
    assert to_evidence([]) == []

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


def test_compress_preserves_original_sentence_order():
    # Regression: reconstruction must join kept sentences in DOCUMENT order, not by
    # query-overlap score. Here sentence 0 has overlap 2 and sentence 1 overlap 1; the
    # buggy default-tuple sort ordered them by ascending overlap, reversing the text.
    chunks = [{"id": "1", "text": "The Kafka AWS broker runs. Just Kafka here."}]
    out = compress(["kafka", "aws"], chunks)
    assert out[0]["text"] == "The Kafka AWS broker runs. Just Kafka here."


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


# ---------------- _apply_changes ----------------


def test_apply_changes_replaces_bullet_by_text_match_and_leaves_source_intact():
    structured = {"experience": [{"company": "A", "bullets": ["Built X", "Led Y"]}]}
    changes = [{"section": "experience", "index": 0, "before": "Built X",
                "after": "Built X with Java"}]
    t = _apply_changes(structured, changes, {}, "resume text")
    assert t["experience"][0]["bullets"] == ["Built X with Java", "Led Y"]
    # deep copy: the caller's structured resume must not be mutated
    assert structured["experience"][0]["bullets"] == ["Built X", "Led Y"]


def test_apply_changes_ignores_non_bullet_sections_and_bad_index():
    structured = {"experience": [{"bullets": ["a"]}]}
    for ch in ([{"section": "summary", "index": 0, "before": "a", "after": "b"}],
               [{"section": "experience", "index": 5, "before": "a", "after": "b"}]):
        t = _apply_changes(structured, ch, {}, "x")
        assert t["experience"][0]["bullets"] == ["a"]


def test_apply_changes_fallback_reuses_item_index_as_bullet_index():
    # Documents current best-effort: `index` selects the experience ITEM, but when
    # `before` is not found among that item's bullets the same `index` is reused to
    # position the replacement, overwriting a DIFFERENT bullet (here bullets[0] "one"
    # is destroyed even though `after` was meant for a non-existent bullet).
    # Pinned deliberately (not asserted "correct") so tailor application can't shift
    # silently without a test noticing.
    structured = {"experience": [{"bullets": ["one", "two", "three"]}]}
    changes = [{"section": "experience", "index": 0, "before": "NOTPRESENT",
                "after": "rewritten"}]
    t = _apply_changes(structured, changes, {}, "x")
    assert t["experience"][0]["bullets"] == ["rewritten", "two", "three"]


def test_apply_changes_sets_summary_only_when_it_passes_the_verifier():
    dirty = _apply_changes({"profile": {}}, [], {"summary": "Expert in Kafka"},
                           "Java and Spring Boot engineer")
    assert "summary" not in dirty.get("profile", {})
    clean = _apply_changes({"profile": {}}, [], {"summary": "Java engineer"},
                           "Java and Spring Boot engineer")
    assert clean["profile"]["summary"] == "Java engineer"


def test_apply_changes_reorders_skills_by_relevance_unranked_last():
    structured = {"skills": [{"name": "MySQL"}, {"name": "Java"}, {"name": "Redis"}]}
    t = _apply_changes(structured, [], {"skillOrder": ["Redis", "Java"]},
                       "resume mentions Redis and Java and MySQL")
    assert [s["name"] for s in t["skills"]] == ["Redis", "Java", "MySQL"]


def test_apply_changes_drops_skill_order_entries_not_on_the_resume():
    # "Kafka" is neither a resume skill nor a resume_text token -> not eligible,
    # so it must not inject a phantom ordering entry.
    structured = {"skills": [{"name": "Java"}, {"name": "MySQL"}]}
    t = _apply_changes(structured, [], {"skillOrder": ["Kafka", "MySQL"]},
                       "Java resume")
    assert [s["name"] for s in t["skills"]] == ["MySQL", "Java"]


def test_apply_changes_summary_survives_null_profile_from_storage():
    # Regression: `structured` is loaded straight from the resume_versions.structured
    # jsonb (Java-owned), so `profile` can be an explicit null. The old
    # t.setdefault("profile", {})["summary"]=... returned None for a present-null key
    # and then crashed on None["summary"]. Must coerce to a dict and set summary.
    t = _apply_changes({"profile": None}, [], {"summary": "Java engineer"},
                       "Java and Spring Boot engineer")
    assert t["profile"]["summary"] == "Java engineer"


def test_apply_changes_summary_creates_profile_when_key_absent():
    t = _apply_changes({}, [], {"summary": "Java engineer"},
                       "Java and Spring Boot engineer")
    assert t["profile"] == {"summary": "Java engineer"}


# ---------------- pricing ----------------


def test_estimate_cost_basic():
    assert estimate_cost("gpt-4o-mini", 1_000_000, 500_000) == pytest.approx(0.45)


def test_estimate_cost_with_cached_input():
    expected = (500 * 2.50 + 500 * 1.25) / 1_000_000
    assert estimate_cost("gpt-4o", 1000, 0, cached=500) == expected


def test_estimate_cost_unknown_model_is_zero():
    assert estimate_cost("some-local-model", 999, 999) == 0.0


# ---------------- rerank (graceful-degradation ordering) ----------------


def _chunks(n):
    # rrf decreases with rank so RRF order is c0, c1, c2, ... (highest first)
    return [{"id": f"c{i}", "text": f"snippet {i} " + "x" * 700, "source_kind": "resume",
             "section_path": "S", "rrf": 1.0 / (i + 1)} for i in range(n)]


def _patch_mode(monkeypatch, mode):
    monkeypatch.setattr(rerank_mod, "get_settings",
                        lambda: SimpleNamespace(rerank_mode=mode))


async def test_rerank_none_mode_returns_prefix_untouched(monkeypatch):
    _patch_mode(monkeypatch, "none")
    out = await rerank("q", _chunks(30), top_n=8)
    assert [c["id"] for c in out] == [f"c{i}" for i in range(8)]
    assert all("rerank" not in c for c in out)  # no LLM pass, no score injected


async def test_rerank_returns_early_when_within_top_n(monkeypatch):
    # even with the reranker on, <= top_n candidates must be returned without an LLM call
    async def boom(*a, **k):  # would fail the test if invoked
        raise AssertionError("LLM must not run when candidates fit within top_n")
    _patch_mode(monkeypatch, "llm")
    monkeypatch.setattr(rerank_mod, "ask_json", boom)
    out = await rerank("q", _chunks(5), top_n=8)
    assert [c["id"] for c in out] == [f"c{i}" for i in range(5)]


async def test_rerank_falls_back_to_rrf_prefix_when_llm_errors(monkeypatch):
    async def explode(*a, **k):
        raise RuntimeError("provider down")
    _patch_mode(monkeypatch, "llm")
    monkeypatch.setattr(rerank_mod, "ask_json", explode)
    out = await rerank("q", _chunks(30), top_n=8)
    assert [c["id"] for c in out] == [f"c{i}" for i in range(8)]  # candidates[:top_n]


async def test_rerank_orders_by_score_and_keeps_unscored_at_tail(monkeypatch):
    async def scores_out(req, **k):
        # c2 best, c0 weak; c1/c3/c4 left unscored -> should sink below c0 (RRF-stable)
        return {"scores": {"2": 0.9, "0": 0.1}}
    _patch_mode(monkeypatch, "llm")
    monkeypatch.setattr(rerank_mod, "ask_json", scores_out)
    out = await rerank("q", _chunks(6), top_n=5)
    assert [c["id"] for c in out] == ["c2", "c0", "c1", "c3", "c4"]
    assert out[0]["rerank"] == 0.9 and out[1]["rerank"] == 0.1
    assert out[2]["rerank"] == 0.0  # unscored explicitly zeroed, not dropped


async def test_rerank_scores_out_of_range_key_are_ignored(monkeypatch):
    async def weird(req, **k):
        return {"scores": {"99": 1.0, "1": 0.7}}  # index 99 has no candidate
    _patch_mode(monkeypatch, "llm")
    monkeypatch.setattr(rerank_mod, "ask_json", weird)
    out = await rerank("q", _chunks(5), top_n=4)
    assert out[0]["id"] == "c1"  # only real candidate index scored high
    assert out[0]["rerank"] == 0.7


# ---------------- understand (query-understanding sanitizer) ----------------


def _patch_ask(monkeypatch, payload=None, raises=False):
    async def fake(req, **k):
        if raises:
            raise RuntimeError("provider down")
        return payload or {}
    monkeypatch.setattr(rewrite_mod, "ask_json", fake)


async def test_understand_falls_back_to_raw_query_on_llm_error(monkeypatch):
    _patch_ask(monkeypatch, raises=True)
    u = await understand("best backend jobs near me")
    assert u["rewritten"] == "best backend jobs near me"  # uses the original query
    assert u["original"] == "best backend jobs near me"
    assert u["intent"] == "other"
    assert u["expansions"] == [] and u["keywords"] == []
    assert u["filters"] == {}
    assert u["needs_personal_evidence"] is True  # defaults to true when unknown


async def test_understand_uses_clean_llm_output(monkeypatch):
    _patch_ask(monkeypatch, {
        "rewritten": "senior backend engineer jobs",
        "expansions": ["distributed systems", "api design"],
        "intent": "job_search",
        "keywords": ["java", "spring", "kafka"],
        "needs_personal_evidence": False,
        "filters": {"kinds": ["resume"]}})
    u = await understand("find senior roles")
    assert u["rewritten"] == "senior backend engineer jobs"
    assert u["intent"] == "job_search"
    assert u["expansions"] == ["distributed systems", "api design"]
    assert u["keywords"] == ["java", "spring", "kafka"]
    assert u["needs_personal_evidence"] is False
    assert u["filters"] == {"kinds": ["resume"]}


async def test_understand_rejects_off_whitelist_intent(monkeypatch):
    _patch_ask(monkeypatch, {"intent": "make_me_a_sandwich"})
    u = await understand("q")
    assert u["intent"] == "other"
    # every advertised intent is accepted verbatim
    for intent in _INTENTS:
        _patch_ask(monkeypatch, {"intent": intent})
        assert (await understand("q"))["intent"] == intent


async def test_understand_drops_non_string_and_caps_list_fields(monkeypatch):
    _patch_ask(monkeypatch, {
        "expansions": ["ok", 42, None, "two", "three", "four"],
        "keywords": ["k1", 7, "k2", "k3", "k4", "k5", "k6", "k7", "k8", "k9"]})
    u = await understand("q")
    assert u["expansions"] == ["ok", "two", "three"]  # non-str dropped, capped at 3
    assert u["keywords"] == ["k1", "k2", "k3", "k4", "k5", "k6", "k7", "k8"]  # capped at 8


async def test_understand_defaults_empty_rewritten_to_query_and_guards_filters(monkeypatch):
    _patch_ask(monkeypatch, {"rewritten": "", "filters": ["not", "a", "dict"]})
    u = await understand("original question text")
    assert u["rewritten"] == "original question text"  # empty string -> falsy -> query
    assert u["filters"] == {}  # non-dict filters rejected, never leaks list downstream


# ---------------- cover_letter._build_prompt (prompt assembly) ----------------


JD = {"title": "Backend Engineer", "company": "Acme Inc",
      "requiredSkills": [{"name": "Java"}, {"name": "Spring"}, {"name": "Kafka"}]}
RESUME = {"profile": {"name": "Lee", "headline": "Senior Dev"}}


def _bp(**over):
    args = dict(resume_structured=RESUME, jd=JD, company=None, goal="",
                context_block="EV", tone="", length="", mode="generate", previous="")
    args.update(over)
    return _build_prompt(**args)


def test_build_prompt_includes_core_facts_and_evidence():
    p = _bp()
    assert "ROLE: Backend Engineer" in p
    assert "COMPANY: Acme Inc" in p  # company None -> jd company fallback
    assert "COMPANY OVERVIEW" not in p  # no company -> overview line dropped
    assert "CANDIDATE: Lee - Senior Dev" in p
    assert "EVIDENCE:\nEV" in p
    assert "Java" in p and "Kafka" in p
    assert "CAREER GOAL" not in p  # empty goal line dropped


def test_build_prompt_uses_company_when_present():
    p = _bp(company={"name": "BigCorp", "overview": "Leader in X"}, goal="switch domains")
    assert "COMPANY: BigCorp" in p
    assert "COMPANY OVERVIEW" in p
    assert "CAREER GOAL: switch domains" in p


def test_build_prompt_appends_style_only_when_directives_present():
    assert "STYLE:" not in _bp()  # tone/length empty -> no style
    assert "STYLE:" not in _bp(tone="balanced", length="")  # balanced maps to ""
    p = _bp(tone="formal", length="short")
    assert "STYLE:" in p and "formal" in p.lower() and "180 words" in p


def test_build_prompt_previous_block_requires_previous_and_variant_mode():
    # no previous -> never a PREVIOUS VERSION block regardless of mode
    assert "PREVIOUS VERSION" not in _bp(mode="shorten", previous="")
    # previous but a plain (non-variant) mode -> still no block
    assert "PREVIOUS VERSION" not in _bp(mode="generate", previous="old letter")
    # previous + known variant -> block with that variant's instruction
    p = _bp(mode="shorten", previous="old letter")
    assert "PREVIOUS VERSION:\nold letter" in p and "INSTRUCTION:" in p
    assert "180 words" in p  # shorten directive text from VARIANTS


def test_build_prompt_customize_mode_uses_jd_customization_with_fallback():
    p = _bp(mode="customize", previous="draft", jd={**JD, "customization": "warmer tone"})
    assert "warmer tone" in p
    p2 = _bp(mode="customize", previous="draft")  # no customization key -> default
    assert "make it better" in p2


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

# ---------------- interview decide_next (pure next-move contract) ----------------


_CT = {"role": "candidate"}  # last turn answered -> budget may force finish
_IV = {"role": "interviewer"}


def test_decide_next_whitelists_action_and_strips_question():
    r = decide_next({"action": "ramble", "question": "  hi  ", "topic": "sys",
                     "reasoning": "x"}, difficulty=0.5, qnum=1, max_q=8, turns=[])
    assert r["action"] == "next_topic"          # unknown coerced to default
    assert r["question"] == "hi"                # whitespace trimmed
    assert r["topic"] == "sys" and r["reasoning"] == "x"
    for a in ("followup", "next_topic", "finish"):
        assert decide_next({"action": a}, difficulty=0.5, qnum=1, max_q=8,
                           turns=[])["action"] == a


def test_decide_next_defaults_missing_fields():
    r = decide_next({}, difficulty=0.5, qnum=1, max_q=8, turns=[])
    assert r == {"action": "next_topic", "question": "", "topic": "",
                 "difficulty": 0.5, "reasoning": ""}


def test_decide_next_forces_finish_only_at_budget_on_answered_turn():
    # at budget + last turn is the candidate's answer -> wrap up
    r = decide_next({"action": "next_topic"}, difficulty=0.5, qnum=8, max_q=8,
                    turns=[_CT])
    assert r["action"] == "finish"
    # at budget but last turn is still the interviewer's -> keep going
    assert decide_next({"action": "next_topic"}, difficulty=0.5, qnum=8, max_q=8,
                       turns=[_IV])["action"] == "next_topic"
    # below budget -> never force
    assert decide_next({"action": "next_topic"}, difficulty=0.5, qnum=3, max_q=8,
                       turns=[_CT])["action"] == "next_topic"
    # explicit finish is preserved regardless of budget
    assert decide_next({"action": "finish"}, difficulty=0.5, qnum=1, max_q=8,
                       turns=[])["action"] == "finish"


def test_decide_next_clamps_difficulty_band_and_falls_back_on_bad_value():
    assert decide_next({"difficulty": 5.0}, difficulty=0.5, qnum=1, max_q=8,
                       turns=[])["difficulty"] == 0.95   # high clamp
    assert decide_next({"difficulty": -3}, difficulty=0.5, qnum=1, max_q=8,
                       turns=[])["difficulty"] == 0.1    # low clamp
    assert decide_next({"difficulty": 0.7}, difficulty=0.5, qnum=1, max_q=8,
                       turns=[])["difficulty"] == 0.7    # in-band preserved
    # non-numeric -> keep the incoming difficulty (clamped)
    assert decide_next({"difficulty": "hard"}, difficulty=0.5, qnum=1, max_q=8,
                       turns=[])["difficulty"] == 0.5
    # incoming difficulty above the band is still clamped when used as fallback
    assert decide_next({"difficulty": "x"}, difficulty=0.99, qnum=1, max_q=8,
                       turns=[])["difficulty"] == 0.95


# ---------------- interview _trajectory_detail (report trajectory builder) ----------------


def test_trajectory_detail_maps_seq_role_topic_depth_score():
    turns = [
        {"seq": 1, "role": "interviewer", "content": "Q",
         "question_meta": {"topic": "concurrency", "depth_level": 2}},
        {"seq": 2, "role": "candidate", "content": "A",
         "evaluation": {"score": 0.7}},
    ]
    traj = _trajectory_detail(turns)
    assert traj[0] == {"seq": 1, "role": "interviewer", "topic": "concurrency",
                       "depth": 2, "score": None}
    assert traj[1] == {"seq": 2, "role": "candidate", "topic": None,
                       "depth": None, "score": 0.7}


def test_trajectory_detail_tolerates_missing_meta_and_evaluation():
    traj = _trajectory_detail([{"seq": 0, "role": "interviewer"}])
    assert traj == [{"seq": 0, "role": "interviewer", "topic": None,
                     "depth": None, "score": None}]


def test_trajectory_detail_handles_null_submaps_and_empty_turns():
    # question_meta / evaluation explicitly None must not crash the .get chain
    traj = _trajectory_detail([{"seq": 3, "role": "candidate",
                                "question_meta": None, "evaluation": None}])
    assert traj[0]["topic"] is None and traj[0]["score"] is None
    assert _trajectory_detail([]) == []


def test_trajectory_detail_omits_absent_seq_as_none():
    traj = _trajectory_detail([{"role": "interviewer"}])
    assert traj[0]["seq"] is None


# ------------- interview LLM-failure graceful fallbacks (the report must survive) -------------


async def test_evaluate_answer_falls_back_to_neutral_score_when_llm_fails(monkeypatch):
    async def fake(*a, **k):
        raise RuntimeError("provider down")
    monkeypatch.setattr("app.features.interview.ask_json", fake)
    ev = await evaluate_answer(mode="technical", question="q", answer="a", resume_ctx="ctx")
    assert ev == {"score": 0.5, "question_was_answered": True}


async def test_evaluate_answer_passes_through_model_output_on_success(monkeypatch):
    async def fake(*a, **k):
        return {"score": 0.8, "strengths": ["x"]}
    monkeypatch.setattr("app.features.interview.ask_json", fake)
    ev = await evaluate_answer(mode="technical", question="q", answer="a", resume_ctx="ctx")
    assert ev["score"] == 0.8


async def test_finalize_defaults_dims_and_overall_and_still_builds_trajectory_when_llm_fails(monkeypatch):
    async def fake(*a, **k):
        raise RuntimeError("provider down")
    monkeypatch.setattr("app.features.interview.ask_json", fake)
    turns = [{"seq": 0, "role": "interviewer", "content": "q"},
             {"seq": 1, "role": "candidate", "content": "a"}]
    out = await finalize(mode="mixed", turns=turns, resume_ctx="ctx")
    assert out["dims"] == {}
    assert out["overall"] == 0.5
    assert out["trajectory_detail"] == _trajectory_detail(turns)


async def test_finalize_keeps_model_dims_and_only_fills_absent_overall(monkeypatch):
    async def fake(*a, **k):
        return {"dims": {"technical_accuracy": 0.7}, "overall": 0.65}
    monkeypatch.setattr("app.features.interview.ask_json", fake)
    out = await finalize(mode="mixed", turns=[], resume_ctx="")
    assert out["dims"] == {"technical_accuracy": 0.7}
    assert out["overall"] == 0.65
    assert out["trajectory_detail"] == []


async def test_advance_falls_back_to_a_usable_next_topic_question_when_llm_fails(monkeypatch):
    async def fake(*a, **k):
        raise RuntimeError("provider down")
    monkeypatch.setattr("app.features.interview.ask_json", fake)
    out = await advance(mode="mixed", turns=[{"role": "candidate", "content": "a"}],
                        difficulty=0.4, qnum=2, max_q=8, resume_ctx="", jd_topics=[])
    assert out["action"] == "next_topic"
    assert out["question"]  # non-empty so the session can keep going
    assert out["difficulty"] == 0.4

# ---------------- jd_analyze suggest_resume_improvements (rule engine) ----------------


def _types(sugs):
    return [s["type"] for s in sugs]


def test_suggestions_flag_missing_required_skill():
    jd = {"requiredSkills": [{"name": "Go"}, {"name": "Python"}]}
    resume = {"skills": [{"name": "Python"}], "experience": [{"bullets": ["wrote code"]}],
              "projects": [{"name": "p"}]}
    sugs = suggest_resume_improvements(jd, resume)
    missing = [s for s in sugs if s["type"] == "missing_required"]
    assert [s["skill"] for s in missing] == ["Go"]        # Python already present
    assert "Go" in missing[0]["advice"]


def test_suggestions_treat_skill_mentioned_in_bullets_as_present():
    jd = {"requiredSkills": [{"name": "Kubernetes"}]}
    resume = {"skills": [], "experience": [{"bullets": ["Scaled services on Kubernetes"]}],
              "projects": [{"name": "p"}]}
    sugs = suggest_resume_improvements(jd, resume)
    assert not any(s["type"] == "missing_required" for s in sugs)


def test_suggestions_add_structure_and_impact_prompts_only_when_warranted():
    # no projects + zero quantified bullets -> both nudges fire
    sugs = suggest_resume_improvements({"requiredSkills": []},
                                       {"skills": [], "experience": [{"bullets": ["did work"]}],
                                        "projects": []})
    assert _types(sugs) == ["structure", "impact"]
    # projects present + 2+ quantified bullets -> neither nudge
    clean = {"skills": [], "experience": [{"bullets": ["cut p99 by 40%", "served 3M users"]}],
             "projects": [{"name": "p"}]}
    assert suggest_resume_improvements({"requiredSkills": []}, clean) == []


def test_suggestions_handle_plain_string_required_skills():
    # analyze_jd's requiredSkills are normally dicts; the else str() branch must still work
    sugs = suggest_resume_improvements({"requiredSkills": ["Rust"]},
                                       {"skills": [], "experience": [], "projects": [{"n": 1}]})
    assert sugs[0]["type"] == "missing_required" and sugs[0]["skill"] == "Rust"


# ---------------- jd_analyze _backfill_skills (deterministic skill capture) ----------------


def test_backfill_appends_missed_dict_skill_as_preferred():
    out = {"requiredSkills": [{"name": "Python", "priority": "must"}]}
    result = _backfill_skills(out, "Team uses Kubernetes and Docker daily.")
    preferred = {s["name"]: s for s in result["preferredSkills"]}
    assert "Kubernetes" in preferred
    assert preferred["Kubernetes"]["priority"] == "nice"
    assert preferred["Kubernetes"]["evidence_phrase"] == ""


def test_backfill_does_not_duplicate_skill_model_already_captured():
    out = {"requiredSkills": [{"name": "Kubernetes", "priority": "must"}],
           "preferredSkills": []}
    result = _backfill_skills(out, "Kubernetes experience required.")
    names = ([s["name"] for s in result["requiredSkills"]]
             + [s["name"] for s in result["preferredSkills"]])
    assert names.count("Kubernetes") == 1


def test_backfill_normalizes_aliases_and_existing_names():
    out = {"requiredSkills": [{"name": "react.js"}], "preferredSkills": [{"name": "ts"}]}
    result = _backfill_skills(out, "Need k8s and postgres.")
    req = {s["name"] for s in result["requiredSkills"]}
    pref = {s["name"] for s in result["preferredSkills"]}
    assert "React" in req and "TypeScript" in pref
    assert "Kubernetes" in pref and "PostgreSQL" in pref


def test_backfill_skips_non_dict_skill_entries_and_sets_length():
    out = {"requiredSkills": ["Go"], "preferredSkills": None}
    result = _backfill_skills(out, "Python.")
    assert result["requiredSkills"] == ["Go"]        # untouched string entry
    assert result["rawTextLength"] == len("Python.")
    assert any(s["name"] == "Python" for s in result["preferredSkills"])


def test_backfill_creates_preferred_list_when_absent():
    result = _backfill_skills({}, "Requires Kafka.")
    assert [s["name"] for s in result["preferredSkills"]] == ["Kafka"]


# ---------------- core.ai _coerce_json (LLM JSON reply tolerance) ----------------


def test_coerce_json_parses_clean_object():
    assert _coerce_json('{"a": 1}') == {"a": 1}
    assert _coerce_json('  {"a": 1}\n') == {"a": 1}


def test_coerce_json_strips_code_fence():
    assert _coerce_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _coerce_json('```\n{"a": 1}\n```') == {"a": 1}


def test_coerce_json_survives_trailing_prose_in_fence():
    # regression: the old repair path used text.strip("`") then text[find("{"):]
    # which left the closing fence + "Hope this helps!" and raised JSONDecodeError
    messy = '```json\n{"a": 1, "b": {"c": 2}}\n```\nHope this helps!'
    assert _coerce_json(messy) == {"a": 1, "b": {"c": 2}}


def test_coerce_json_survives_leading_prose():
    assert _coerce_json('Sure thing! {"x": [1, 2, 3]} enjoy') == {"x": [1, 2, 3]}


def test_coerce_json_extracts_outermost_object_with_nested_braces():
    assert _coerce_json('{"a": {"b": {"c": 3}}}') == {"a": {"b": {"c": 3}}}


def test_coerce_json_raises_when_no_object_found():
    with pytest.raises(json.JSONDecodeError):
        _coerce_json("this is not json at all")

