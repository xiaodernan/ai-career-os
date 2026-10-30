"""Unit tests for the import planner (Epic 13.2, apply half).

The planner's contract is a promise about the apply, so the pins here are of
two kinds. The id-matched sections (applications, growth runs, notes, contacts,
postings, interviews, chats) are held to create / update / skip / delete. The
sections the restore re-ingests (resumes, knowledge, memories) are held to the
opposite: they are found by content, never deleted, and a bundle that carries
two copies still restores both.
"""

import json
from decimal import Decimal

import pytest

from app.features import export as ex
from app.features import import_plan as pl


def _bundle_with(resumes=("r1",), memories=("m1",), applications=()) -> dict:
    raw = {
        "profile": {"id": "u1", "display_name": "Ada"},
        "resumes": [{"id": r, "resume_title": r, "version": 1, "plaintext": r}
                    for r in resumes],
        "knowledge": [],
        "job_descriptions": [],
        "interviews": [],
        "memories": [{"id": m, "kind": "preference", "key": f"k-{m}",
                      "content": m, "importance": 0.6, "source": "manual"}
                     for m in memories],
        "applications": [{"id": a, "title": a, "company_name": "Acme",
                          "status": "applied"} for a in applications],
    }
    return ex.build_bundle("u1", raw)


def _interview(**overrides) -> dict:
    """One session as the export carries it: the row, the turns, the report."""
    row = {
        "id": "s1", "user_id": "u1", "job_id": "j1", "jd_id": None,
        "resume_version_id": None, "job_title": "Backend Engineer",
        "company_name": "Acme", "position_title": "Backend", "mode": "mixed",
        "status": "completed", "difficulty": 0.5, "config": {"depth": 2},
        "started_at": "2026-10-01T09:00:00+00:00", "finished_at": None,
        "turns": [
            {"id": "t1", "session_id": "s1", "user_id": "u1", "seq": 1,
             "role": "interviewer", "content": "Why us?",
             "question_meta": {"topic": "motivation"}, "evaluation": None,
             "created_at": "2026-10-01T09:01:00+00:00"},
        ],
        "evaluation": {"dims": {"communication": 4},
                       "summary": {"well": ["clear"]}, "trajectory": []},
    }
    row.update(overrides)
    return row


def _bundle_with_interviews(*sessions: dict) -> dict:
    return ex.build_bundle("u1", {
        "profile": {"id": "u1", "display_name": "Ada"},
        "resumes": [], "knowledge": [], "job_descriptions": [],
        "interviews": list(sessions), "memories": [],
    })


def _chat(**overrides) -> dict:
    """One copilot chat as the export carries it: the row and its transcript."""
    row = {
        "id": "c1", "title": "Which resume fits a platform role?",
        "context": {"resumeId": "r1"},
        "created_at": "2026-10-01T09:00:00+00:00",
        "updated_at": "2026-10-01T09:05:00+00:00",
        "messages": [
            {"id": "m1", "role": "user", "content": "Which resume fits?",
             "artifacts": [], "sources": [], "actions": [],
             "created_at": "2026-10-01T09:00:00+00:00"},
            {"id": "m2", "role": "assistant", "content": "The platform one.",
             "artifacts": [{"kind": "resume", "version": 2}],
             "sources": [{"kind": "job", "id": "j1"}], "actions": [],
             "created_at": "2026-10-01T09:01:00+00:00"},
        ],
    }
    row.update(overrides)
    return row


def _bundle_with_chats(*chats: dict) -> dict:
    return ex.build_bundle("u1", {
        "profile": {"id": "u1", "display_name": "Ada"},
        "resumes": [], "knowledge": [], "job_descriptions": [],
        "interviews": [], "memories": [], "conversations": list(chats),
    })


def _edited(bundle: dict) -> dict:
    """A bundle whose data was changed by the test, re-sealed the honest way.

    ``validate_bundle`` refuses a payload whose manifest hash no longer matches,
    so a test that edits a row has to recompute the hash at the same time as it
    edits -- which is also what a real exporter does.
    """
    bundle["manifest"]["content_hash"] = ex.content_hash(bundle["data"])
    return bundle


def test_plan_all_creates_without_existing():
    out = pl.plan_import(_bundle_with())
    assert out["op_counts"]["delete"] == 0
    assert out["op_counts"]["create"] == out["op_counts"]["total"]
    # every op is a create
    for sec, ops in out["sections"].items():
        assert all(o["op"] == "create" for o in ops)


def test_plan_update_and_delete_with_existing():
    existing = _bundle_with(applications=("a1", "a2"))
    incoming = _bundle_with(applications=("a1", "a3"))
    # a1 is the same row in both bundles, so its own op is a skip; give it a
    # new status to keep this case about the update it is named for.
    incoming["data"]["applications"][0]["status"] = "interviewing"
    _edited(incoming)
    out = pl.plan_import(incoming, existing=existing)
    app_ops = {o["id"]: o["op"] for o in out["sections"]["applications"]}
    assert app_ops["a1"] == "update"
    assert app_ops["a3"] == "create"
    # a2 was in existing but not in incoming -> delete
    assert app_ops["a2"] == "delete"


def test_plan_invalid_bundle_raises():
    b = _bundle_with()
    b["manifest"]["content_hash"] = "tampered"
    with pytest.raises(ValueError) as exc:
        pl.plan_import(b)
    assert "content_hash" in str(exc.value)


def test_check_bundle_refuses_before_a_plan_exists():
    """The route validates from the file alone, before it reads any state."""
    with pytest.raises(ValueError) as exc:
        pl.check_bundle({"schema_version": "1.1.0"})
    assert "missing" in str(exc.value).lower()


def test_plan_profile_upsert():
    without = pl.plan_import(_bundle_with())
    assert without["sections"]["profile"][0]["op"] == "create"
    same = pl.plan_import(_bundle_with(), existing=_bundle_with())
    assert same["sections"]["profile"][0]["op"] == "skip", (
        "the same profile in and out is not a write"
    )
    changed = _bundle_with()
    changed["data"]["profile"]["display_name"] = "Ada Lovelace"
    _edited(changed)
    out = pl.plan_import(changed, existing=_bundle_with())
    assert out["sections"]["profile"][0]["op"] == "update"


def test_plan_an_identical_reimport_is_all_skips_and_writes_nothing():
    """The preview's promise: unchanged rows are skipped.

    Re-importing the bundle the workspace itself exported changes nothing,
    so every row of it is a skip -- not an update, which the backend would
    execute as a write. This is the assertion the copy in the product's own
    "Your data" panel depends on.
    """
    b = _bundle_with()
    out = pl.plan_import(b, existing=b)
    assert out["op_counts"]["delete"] == 0
    assert out["op_counts"]["create"] == 0
    assert out["op_counts"]["update"] == 0
    assert out["op_counts"]["skip"] == out["op_counts"]["total"] > 0
    assert all(o["op"] == "skip" for sec in out["sections"].values() for o in sec)


def test_plan_counts_the_skips_alongside_the_writes():
    existing = _bundle_with(resumes=("r1",), memories=("m1",),
                            applications=("a1", "a2"))
    incoming = _bundle_with(resumes=("r1",), memories=("m1",),
                            applications=("a1", "a3"))
    incoming["data"]["applications"][0]["status"] = "interviewing"
    incoming["data"]["profile"]["display_name"] = "Ada Lovelace"
    _edited(incoming)
    counts = pl.plan_import(incoming, existing=existing)["op_counts"]
    assert counts["create"] == 1          # application a3
    assert counts["update"] == 2          # application a1, profile
    assert counts["delete"] == 1          # application a2
    assert counts["skip"] == 2            # resume r1, memory m1
    assert counts["total"] == counts["create"] + counts["update"] + counts["delete"] + counts["skip"]


def test_plan_a_changed_row_is_an_update_not_a_skip():
    existing = _bundle_with(memories=("m1",))
    incoming = _bundle_with(memories=("m1",))
    incoming["data"]["memories"][0]["content"] = "now prefers on-site"
    _edited(incoming)
    op = pl.plan_import(incoming, existing=existing)["sections"]["memories"][0]
    assert op["op"] == "update", f"a changed row was not planned as a write: {op}"


def test_plan_the_stamps_a_restore_does_not_write_are_not_a_change():
    """``updated_at`` is stamped by the database, not by the bundle.

    The first apply bumps it, so comparing whole rows would make every row
    the import had just written look changed on the next run -- the plan
    would keep writing and "unchanged rows are skipped" would never hold.
    The comparison covers the fields the apply writes, and the stamps are
    not among them.
    """
    existing = _bundle_with(applications=("a1",))
    incoming = _bundle_with(applications=("a1",))
    for rows in (existing["data"]["applications"], incoming["data"]["applications"]):
        rows[0]["created_at"] = "2026-01-01T00:00:00Z"
        rows[0]["updated_at"] = "2026-01-02T00:00:00Z"
    incoming["data"]["applications"][0]["updated_at"] = "2026-10-27T09:00:00Z"
    _edited(incoming)
    ops = {o["id"]: o["op"] for o in
           pl.plan_import(incoming, existing=existing)["sections"]["applications"]}
    assert ops["a1"] == "skip"


def test_plan_per_item_content_hash_is_stable():
    b = _bundle_with()
    out = pl.plan_import(b)
    h1 = next(o["content_hash"] for o in out["sections"]["resumes"] if o["id"] == "r1")
    out2 = pl.plan_import(b)
    h2 = next(o["content_hash"] for o in out2["sections"]["resumes"] if o["id"] == "r1")
    assert h1 == h2 and h1 is not None


# ---------------- the sections the restore re-ingests ----------------


def test_a_restored_row_is_found_by_content_not_by_the_id_it_lost():
    """A restored resume is a new row with a new id.

    The apply creates it through the resume service, which mints the id the
    ingestion hangs the copy off. So the next plan can never match it by the
    bundle's id -- matching by id would say "create" on every re-import of the
    file the workspace itself wrote, and the panel would promise writes that
    it makes happen again each time.
    """
    existing = _bundle_with(resumes=("r1",))
    existing["data"]["resumes"][0]["id"] = "minted-by-the-restore"
    _edited(existing)
    out = pl.plan_import(_bundle_with(resumes=("r1",)), existing=existing)
    assert [o["op"] for o in out["sections"]["resumes"]] == ["skip"]
    assert out["op_counts"]["delete"] == 0


def test_a_row_the_apply_never_retires_is_never_planned_for_delete():
    existing = _bundle_with(resumes=("r1", "r2"))
    incoming = _bundle_with(resumes=("r1",))
    out = pl.plan_import(incoming, existing=existing)
    assert all(o["op"] != "delete" for o in out["sections"]["resumes"])
    assert out["op_counts"]["delete"] == 0, (
        "the restore cannot name a resume it would bring back as a different one"
    )


def test_two_identical_rows_in_the_bundle_are_two_restores():
    """The match is one-to-one: an existing row is consumed once.

    The apply writes every non-skip row, so a bundle with two copies of a
    resume and a target with one must plan one skip and one create -- not two
    skips against a single existing row, which would leave the second copy
    un-restored while the preview claimed it had landed.
    """
    existing = _bundle_with(resumes=("r1",))
    incoming = _bundle_with(resumes=("r1", "r1-copy"))
    incoming["data"]["resumes"][1]["id"] = "r1-copy"
    incoming["data"]["resumes"][1]["resume_title"] = "r1"
    incoming["data"]["resumes"][0]["id"] = "r1"
    _edited(incoming)
    ops = pl.plan_import(incoming, existing=existing)["sections"]["resumes"]
    assert sorted(o["op"] for o in ops) == ["create", "skip"]


def test_a_memory_is_matched_by_the_key_the_upsert_uses():
    """The restore upserts a memory on ``(kind, key)``; so does the plan.

    The id in the bundle is the source's, and the target's row has its own --
    a memory the two sides agree on is a skip whatever ids they carry.
    """
    existing = _bundle_with(memories=("m1",))
    incoming = _bundle_with(memories=("m1",))
    incoming["data"]["memories"][0]["id"] = "the-sources-id"
    _edited(incoming)
    op = pl.plan_import(incoming, existing=existing)["sections"]["memories"][0]
    assert op["op"] == "skip"

    incoming["data"]["memories"][0]["content"] = "now prefers on-site"
    _edited(incoming)
    op = pl.plan_import(incoming, existing=existing)["sections"]["memories"][0]
    assert op["op"] == "update", "the upsert would write the new sentence"


def test_the_plan_never_deletes_a_memory():
    existing = _bundle_with(memories=("m1", "m2"))
    incoming = _bundle_with(memories=("m1",))
    out = pl.plan_import(incoming, existing=existing)
    assert all(o["op"] != "delete" for o in out["sections"]["memories"])


# ---------------- the interviews: the row, the transcript, the report ----------------


def test_an_interview_is_compared_by_what_the_restore_writes():
    """The child rows are the pipeline's, not the bundle's.

    The restore mints the turns' ids, their session id and their stamps, and
    it does not write the session's links to a job, a JD or a resume version.
    Comparing any of those would make a re-import into the same account an
    update on every run -- and the apply would replace the transcript each
    time it was asked whether anything had changed.
    """
    incoming = _bundle_with_interviews(_interview())
    existing = _bundle_with_interviews(_interview(
        job_id="j2", job_title="Backend Engineer (renamed)", jd_id="jd-1"))
    existing["data"]["interviews"][0]["turns"] = [{
        "id": "a-different-turn-id", "session_id": "s1", "user_id": "u1",
        "seq": 1, "role": "interviewer", "content": "Why us?",
        "question_meta": {"topic": "motivation"}, "evaluation": None,
        "created_at": "2026-10-02T08:00:00+00:00",
    }]
    _edited(existing)
    op = pl.plan_import(incoming, existing=existing)["sections"]["interviews"][0]
    assert op["op"] == "skip", f"the same interview was planned as a write: {op}"


def test_a_changed_answer_is_an_interview_update():
    incoming = _bundle_with_interviews(_interview())
    existing = _bundle_with_interviews(_interview())
    existing["data"]["interviews"][0]["turns"][0]["content"] = "Because I like the team."
    _edited(existing)
    op = pl.plan_import(incoming, existing=existing)["sections"]["interviews"][0]
    assert op["op"] == "update"


def test_a_session_the_bundle_no_longer_carries_is_retired():
    incoming = _bundle_with_interviews(_interview())
    existing = _bundle_with_interviews(_interview(), _interview(id="s2"))
    ops = {o["id"]: o["op"]
           for o in pl.plan_import(incoming, existing=existing)["sections"]["interviews"]}
    assert ops["s1"] == "skip"
    assert ops["s2"] == "delete"


def test_a_changed_report_is_an_interview_update():
    incoming = _bundle_with_interviews(_interview())
    existing = _bundle_with_interviews(_interview())
    existing["data"]["interviews"][0]["evaluation"]["dims"] = {"communication": 2}
    _edited(existing)
    op = pl.plan_import(incoming, existing=existing)["sections"]["interviews"][0]
    assert op["op"] == "update", "the report is about the answers and travels with them"


# ---------------- the chats: the row and its transcript ----------------


def test_a_chat_is_compared_by_what_the_restore_writes():
    """The message ids and stamps are the target's, not the bundle's.

    The restore mints each message's id and stamps and ignores the transcript's
    user and conversation columns -- they are the parent's, and the parent is
    the row matched by id. Comparing any of them would make every re-import an
    update, and the apply would delete and rewrite every transcript just to be
    told nothing had changed.
    """
    incoming = _bundle_with_chats(_chat())
    existing = _bundle_with_chats(_chat())
    message = existing["data"]["conversations"][0]["messages"][1]
    message["id"] = "a-fresh-message-id"
    message["conversation_id"] = "c1"
    message["user_id"] = "u1"
    message["created_at"] = "2026-10-02T08:00:00+00:00"
    _edited(existing)
    op = pl.plan_import(incoming, existing=existing)["sections"]["conversations"][0]
    assert op["op"] == "skip", f"the same chat was planned as a write: {op}"


def test_a_changed_answer_is_a_chat_update():
    incoming = _bundle_with_chats(_chat())
    existing = _bundle_with_chats(_chat())
    existing["data"]["conversations"][0]["messages"][1]["content"] = (
        "The platform one, because the posting leads with scale.")
    _edited(existing)
    op = pl.plan_import(incoming, existing=existing)["sections"]["conversations"][0]
    assert op["op"] == "update"


def test_a_chat_the_bundle_no_longer_carries_is_retired():
    incoming = _bundle_with_chats(_chat())
    existing = _bundle_with_chats(_chat(), _chat(id="c2", title="Another chat"))
    ops = {o["id"]: o["op"]
           for o in pl.plan_import(incoming, existing=existing)["sections"]["conversations"]}
    assert ops["c1"] == "skip"
    assert ops["c2"] == "delete"


# ---------------- the standing choices: saved searches and feeds ----------------


def _bundle_with_choices(searches=(), feeds=()) -> dict:
    raw = {
        "profile": {"id": "u1", "display_name": "Ada"},
        "resumes": [], "knowledge": [], "job_descriptions": [],
        "interviews": [], "memories": [],
        "saved_searches": [
            {"id": s, "name": f"Search {s}", "criteria": {"city": "Hangzhou"}}
            for s in searches],
        "ingestion_feeds": [
            {"id": f, "name": f"Feed {f}", "url": f"https://{f}.example/feed.xml",
             "source": "rss", "enabled": True}
            for f in feeds],
    }
    return ex.build_bundle("u1", raw)


def test_a_saved_search_the_bundle_no_longer_carries_is_retired():
    incoming = _bundle_with_choices(searches=("s1",))
    existing = _bundle_with_choices(searches=("s1", "s2"))
    ops = {o["id"]: o["op"] for o in
           pl.plan_import(incoming, existing=existing)["sections"]["saved_searches"]}
    assert ops["s1"] == "skip"
    assert ops["s2"] == "delete"


def test_a_changed_criteria_is_a_saved_search_update():
    incoming = _bundle_with_choices(searches=("s1",))
    existing = _bundle_with_choices(searches=("s1",))
    existing["data"]["saved_searches"][0]["criteria"] = {"city": "Shanghai"}
    _edited(existing)
    op = pl.plan_import(incoming, existing=existing)["sections"]["saved_searches"][0]
    assert op["op"] == "update"


def test_a_feed_is_skipped_when_the_switch_and_the_address_are_the_same():
    """The stamps the database sets are not the feed's content.

    The feed's switch and its address are; a re-import that sees them the
    same must not rewrite the row just because the first apply stamped it.
    """
    incoming = _bundle_with_choices(feeds=("f1",))
    existing = _bundle_with_choices(feeds=("f1",))
    for row in existing["data"]["ingestion_feeds"]:
        row["created_at"] = "2026-10-01T00:00:00+00:00"
        row["updated_at"] = "2026-10-02T00:00:00+00:00"
    _edited(existing)
    out = pl.plan_import(incoming, existing=existing)
    assert [o["op"] for o in out["sections"]["ingestion_feeds"]] == ["skip"]
    assert out["op_counts"]["delete"] == 0


def test_a_feed_the_bundle_flips_off_is_an_update():
    incoming = _bundle_with_choices(feeds=("f1",))
    incoming["data"]["ingestion_feeds"][0]["enabled"] = False
    _edited(incoming)
    existing = _bundle_with_choices(feeds=("f1",))
    op = pl.plan_import(incoming, existing=existing)["sections"]["ingestion_feeds"][0]
    assert op["op"] == "update", "the reader's switch is content"


def test_a_saved_search_carried_as_text_is_the_map_it_holds():
    incoming = _bundle_with_choices(searches=("s1",))
    existing = _bundle_with_choices(searches=("s1",))
    existing["data"]["saved_searches"][0]["criteria"] = json.dumps(
        existing["data"]["saved_searches"][0]["criteria"])
    _edited(existing)
    op = pl.plan_import(incoming, existing=existing)["sections"]["saved_searches"][0]
    assert op["op"] == "skip"


def test_the_applies_transformations_are_not_changes():
    """The apply trims names and addresses and fills a feed's defaults.

    A comparison that did not mirror those would call the row it had just
    written changed on the next run -- the plan would keep writing and
    "unchanged rows are skipped" would never hold for these two sections.
    """
    incoming = _bundle_with_choices(searches=("s1",), feeds=("f1",))
    existing = _bundle_with_choices(searches=("s1",), feeds=("f1",))
    incoming["data"]["saved_searches"][0]["name"] = " Search s1 "
    incoming["data"]["ingestion_feeds"][0]["name"] = " Feed f1 "
    incoming["data"]["ingestion_feeds"][0]["url"] = " https://f1.example/feed.xml "
    del incoming["data"]["ingestion_feeds"][0]["source"]
    del incoming["data"]["ingestion_feeds"][0]["enabled"]
    existing["data"]["ingestion_feeds"][0]["source"] = "feed"
    existing["data"]["ingestion_feeds"][0]["enabled"] = True
    _edited(incoming)
    _edited(existing)

    out = pl.plan_import(incoming, existing=existing)
    assert [o["op"] for o in out["sections"]["saved_searches"]] == ["skip"]
    assert [o["op"] for o in out["sections"]["ingestion_feeds"]] == ["skip"]


def test_a_row_the_apply_cannot_write_is_not_promised_or_retired():
    """The creation paths refuse these rows, so the plan does not promise them.

    A saved search with no criteria asks the board nothing and a feed with no
    address points at nothing: the services refuse both at creation. A
    restore that planned them would count creates the apply skips -- and
    their existing counterparts must not be retired over the bundle's
    silence either.
    """
    raw = {
        "profile": {"id": "u1"},
        "resumes": [], "knowledge": [], "job_descriptions": [],
        "interviews": [], "memories": [],
        "saved_searches": [{"id": "s1", "name": "Empty", "criteria": {}}],
        "ingestion_feeds": [{"id": "f1", "name": "No address", "url": ""}],
    }
    bundle = ex.build_bundle("u1", raw)
    out = pl.plan_import(bundle, existing=bundle)
    assert out["sections"]["saved_searches"] == []
    assert out["sections"]["ingestion_feeds"] == []
    assert out["op_counts"]["delete"] == 0


# ---------------- two spellings of the same value ----------------


def test_a_json_column_written_as_text_is_the_object_it_holds():
    """A bundle written before the export decoded its jsonb columns.

    The two files carry the same posting, one as an object and one as the
    string asyncpg handed back. They are the same content, so the plan says
    skip -- otherwise the first re-import of an older backup would rewrite
    every posting, the session config and every answer's evaluation.
    """
    incoming = _bundle_with_interviews(_interview())
    existing = _bundle_with_interviews(_interview())
    row = existing["data"]["interviews"][0]
    row["config"] = json.dumps(row["config"])
    row["turns"][0]["question_meta"] = json.dumps(row["turns"][0]["question_meta"])
    _edited(existing)
    op = pl.plan_import(incoming, existing=existing)["sections"]["interviews"][0]
    assert op["op"] == "skip"


def test_a_number_is_the_number_it_means():
    """``numeric`` from the database and JSON from the bundle are one value.

    asyncpg hands back ``Decimal`` and the bundle carries the JSON number, so
    an exact comparison would call an untouched profile changed -- and the
    apply would rewrite it on every re-import.
    """
    incoming = _bundle_with()
    incoming["data"]["profile"]["years_experience"] = Decimal("5.0")
    _edited(incoming)
    existing = _bundle_with()
    existing["data"]["profile"]["years_experience"] = 5
    _edited(existing)
    op = pl.plan_import(incoming, existing=existing)["sections"]["profile"][0]
    assert op["op"] == "skip"


# ---------------- a row the apply cannot write ----------------


def test_a_row_the_apply_cannot_write_is_not_a_promise():
    """A document with no excerpt is metadata the apply has to leave alone.

    The restore re-ingests a document from its excerpt; one the export could
    not carry is not a row the plan may promise to create -- and an existing
    row of that shape is not a row a bundle's silence may retire, because the
    apply cannot tell it apart from a row it would keep.
    """
    raw = {
        "profile": {"id": "u1"},
        "resumes": [], "job_descriptions": [], "interviews": [], "memories": [],
        "knowledge": [{"id": "d1", "title": "Notes", "text_excerpt": ""}],
    }
    bundle = ex.build_bundle("u1", raw)
    out = pl.plan_import(bundle, existing=bundle)
    assert out["sections"]["knowledge"] == []
    assert out["op_counts"]["delete"] == 0


# ---------------- the other half of the comparison ----------------


def test_the_current_state_fills_only_what_the_caller_left_out():
    """The bridge sends the sections it owns; the rest are read here.

    A caller that sends a section is the authority on it -- the profile is
    one of those rows. A section the caller does not send is filled from the
    service's own read, not left absent: an absent section reads as "the
    target has none", and every row of it would be a create.
    """
    existing = {"data": {"notes": [{"id": "n1"}], "profile": {"id": "p1"}}}
    gathered = {
        "profile": {"id": "someone-else"},
        "resumes": [{"id": "r1"}],
        "knowledge": [],
        "job_descriptions": [],
        "interviews": [],
        "memories": [{"id": "m1"}],
    }
    state = pl.with_current_state(existing, gathered)
    assert state["data"]["notes"] == [{"id": "n1"}]
    assert state["data"]["profile"] == {"id": "p1"}, (
        "the caller's profile is the caller's row"
    )
    assert state["data"]["resumes"] == [{"id": "r1"}]
    assert state["data"]["memories"] == [{"id": "m1"}]


async def test_current_state_reads_through_the_export(monkeypatch):
    async def fake_gather(user_id):
        assert user_id == "u1"
        return {
            "profile": {"id": "p1"}, "resumes": [{"id": "r1"}],
            "knowledge": [], "job_descriptions": [], "interviews": [],
            "memories": [],
        }

    monkeypatch.setattr(pl, "gather_raw", fake_gather)
    state = await pl.current_state("u1")
    assert state["data"]["profile"] == {"id": "p1"}
    assert state["data"]["resumes"] == [{"id": "r1"}]
