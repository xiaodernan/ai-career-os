"""The networking tools (Epic 11.4) read and write only the caller's own contacts.

Four handlers plus one subagent whitelist. Each case below holds a claim that would be
a bug in production rather than a style preference:

* Every statement binds `user_id`. `contacts` is a per-user registry, so a lookup on an
  unscoped `id` is an IDOR, and a filter typed by the model must never reach SQL text.
* `get_follow_ups` reads `ORDER BY last_touch_at ASC` *because* it caps the read. The
  neglected people sit at the far end of that column; ordering the way the registry
  page does (newest first) and then cutting would discard exactly the contacts this
  tool exists to surface, and would report a clean inbox to a user whose network has
  gone cold.
* `draft_outreach` refuses before it calls the model. A purpose the schema does not
  offer and a contact that is not the caller's are both answered without spending a
  completion, and the handler's accepted set is the set the model is shown -- a schema
  that drifts from the validator is a tool the model cannot call correctly.
* Drafts are built from the record alone (the 11.2 no-fabrication rule): a contact with
  no company must not be addressed at one the record does not name.
* The whitelist is the security argument of AGENTS.md §2: `networking` may log a touch
  and draft a message, and physically cannot save a job or move an application.

The clock is pinned through `reminders._now` and every fixture date is written as an
offset from it, so the verdicts do not drift with the day the suite runs.
"""

from datetime import datetime, timedelta, timezone

import app.db.domain as domain_mod
import app.features.outreach as outreach_mod
import app.features.reminders as reminders_mod
from app.agents import tools as tools_mod
from app.agents.orchestrator import TRANSFER_SPEC
from app.agents.tools import (SUBAGENT_TOOLS, TOOL_INDEX, draft_outreach,
                              get_follow_ups, log_contact_touch, search_contacts)
from app.core import db
from app.features.outreach import PURPOSES

REF = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def _touched(days_ago):
    """An ISO stamp `days_ago` before the pinned clock; None means never touched."""
    if days_ago is None:
        return None
    return (REF - timedelta(days=days_ago)).isoformat()


def _row(name="Ada", relation="recruiter", company="Acme", ago=0):
    """A row shaped exactly like `_CONTACT_COLS`."""
    return {"id": f"c-{name}", "name": name, "role": "Talent lead", "company": company,
            "relation": relation, "email": None, "last_touch_at": _touched(ago)}


def _pin_clock(monkeypatch):
    monkeypatch.setattr(reminders_mod, "_now", lambda: REF)


def _patch_fetch(monkeypatch, rows):
    seen = {}

    async def fake_fetch(query, *args):
        seen["sql"] = query
        seen["args"] = args
        return rows

    monkeypatch.setattr(tools_mod.db, "fetch", fake_fetch)
    return seen


def _patch_fetchrow(monkeypatch, row):
    seen = {}

    async def fake_fetchrow(query, *args):
        seen["sql"] = query
        seen["args"] = args
        return row

    monkeypatch.setattr(tools_mod.db, "fetchrow", fake_fetchrow)
    return seen


# ---------------- search_contacts ----------------


async def test_search_contacts_binds_the_caller_and_never_splices_a_filter(monkeypatch):
    seen = _patch_fetch(monkeypatch, [_row()])
    out = await search_contacts("u-1", name="O'Brien", company="Acme!")

    assert "user_id = $1::uuid" in seen["sql"], (
        "a contact read that is not scoped to the caller reads other people's networks")
    assert seen["args"][0] == "u-1"
    assert seen["args"][1] == db.like_contains("O'Brien"), "the filter is bound as a pattern"
    assert seen["args"][2] == db.like_contains("Acme!")
    for term in ("O'Brien", "Acme!"):
        assert term.replace("!", "") not in seen["sql"], (
            f"{term!r} reached the SQL text instead of a placeholder")
    assert out["contacts"][0]["name"] == "Ada"


async def test_search_contacts_clamps_a_runaway_limit(monkeypatch):
    seen = _patch_fetch(monkeypatch, [])
    await search_contacts("u-1", limit=10_000)
    assert seen["args"][-1] == 25, "the cap the handler promises is the cap the tool ships"

    seen = _patch_fetch(monkeypatch, [])
    await search_contacts("u-1", limit=0)
    assert seen["args"][-1] == 1, "a zero limit answers with nothing and reads as an empty registry"


async def test_search_contacts_dates_are_serialisable_and_parseable(monkeypatch):
    """`last_touch_at` goes back as an ISO string, not a datetime repr.

    asyncpg hands a `TIMESTAMPTZ` column back as a datetime; `surface_stale` re-reads
    the same field, so a shape `_parse` cannot read would make every contact look
    never-touched and the tool would report the whole registry overdue.
    """
    from app.features.reminders import days_since

    seen = {}

    async def fake_fetch(query, *args):
        seen["rows"] = [{**_row(), "last_touch_at": REF}]
        return seen["rows"]

    monkeypatch.setattr(tools_mod.db, "fetch", fake_fetch)
    out = await search_contacts("u-1")

    stamped = out["contacts"][0]["last_touch_at"]
    assert isinstance(stamped, str) and stamped.startswith("2026-10-14")
    assert days_since(stamped, REF) == 0


# ---------------- get_follow_ups ----------------


async def test_the_follow_up_read_is_ordered_so_the_cap_keeps_the_neglected(monkeypatch):
    _pin_clock(monkeypatch)
    seen = _patch_fetch(monkeypatch, [_row()])
    await get_follow_ups("u-1", limit=5)

    assert "ORDER BY last_touch_at ASC NULLS FIRST" in seen["sql"], (
        "the follow-up read is capped, so newest-first ordering would cut the stale "
        "contacts -- the only rows this tool exists to return")
    assert seen["args"] == ("u-1", 5)


async def test_follow_ups_reports_only_whoever_is_past_cadence(monkeypatch):
    _pin_clock(monkeypatch)
    rows = [_row(name="Fresh", relation="peer", ago=1),      # peer cadence 90
            _row(name="Cold", relation="recruiter", ago=43),  # recruiter 30 -> overdue
            _row(name="Soon", relation="peer", ago=74),       # 90 * 0.7 = 63 -> soon
            _row(name="Never", relation="peer", ago=None)]    # never -> overdue
    _patch_fetch(monkeypatch, rows)

    out = await get_follow_ups("u-1")
    by_name = {c["name"]: c for c in out["follow_ups"]}

    assert "Fresh" not in by_name, "a contact inside its cadence is not a follow-up"
    assert by_name["Cold"]["priority"] == "overdue"
    assert by_name["Cold"]["cadence_days"] == 30, "the cadence is the relation's own, not a default"
    assert by_name["Soon"]["priority"] == "soon"
    assert by_name["Never"]["priority"] == "overdue", "never touched is the most overdue"
    assert [c["name"] for c in out["follow_ups"]] == ["Never", "Cold", "Soon"], (
        "ranked by how long it has been, most neglected first")


async def test_every_follow_up_carries_a_draft_built_from_that_row_alone(monkeypatch):
    _pin_clock(monkeypatch)
    _patch_fetch(monkeypatch, [_row(name="Grace", relation="recruiter",
                                    company="Hopper Corp", ago=200)])
    top = (await get_follow_ups("u-1"))["follow_ups"][0]

    assert top["priority"] == "overdue"
    assert "Grace" in top["suggested_message"] and "Hopper Corp" in top["suggested_message"]


async def test_a_draft_never_invents_a_company_the_row_does_not_carry(monkeypatch):
    _pin_clock(monkeypatch)
    _patch_fetch(monkeypatch, [_row(name="Grace", company=None, ago=200)])
    draft = (await get_follow_ups("u-1"))["follow_ups"][0]["suggested_message"]

    assert "hope you've been well" in draft, (
        "a contact with no company must not be addressed at one the record does not name")


async def test_include_fresh_hands_back_the_whole_registry(monkeypatch):
    _pin_clock(monkeypatch)
    _patch_fetch(monkeypatch, [_row(name="Fresh", relation="peer", ago=1)])
    out = await get_follow_ups("u-1", include_fresh=True)

    assert [c["name"] for c in out["follow_ups"]] == ["Fresh"]
    assert out["follow_ups"][0]["priority"] == "fresh"


async def test_an_empty_registry_is_an_empty_list_not_an_error(monkeypatch):
    _pin_clock(monkeypatch)
    _patch_fetch(monkeypatch, [])
    assert await get_follow_ups("u-1") == {"follow_ups": []}


# ---------------- draft_outreach ----------------


def _patch_outreach(monkeypatch, captured):
    async def fake_draft(contact, purpose, structured, *, context="", user_id=None,
                         run_id=None):
        captured["call"] = (contact, purpose, structured, context)
        return {"purpose": purpose, "subject": "Hi", "body": "..."}

    monkeypatch.setattr(outreach_mod, "draft_message", fake_draft)


async def test_draft_outreach_refuses_an_unknown_purpose_before_reading_or_calling(monkeypatch):
    cap = {}
    _patch_outreach(monkeypatch, cap)
    seen = _patch_fetchrow(monkeypatch, {"name": "Ada", "role": None, "company": "Acme",
                                         "relation": "recruiter"})
    out = await draft_outreach("u-1", contact_id="c-1", purpose="ask_for_a_job")

    assert "error" in out and "referral" in out["error"]
    assert "call" not in cap, "a purpose the generator does not know must not spend a completion"
    assert not seen.get("sql"), "and must not even read the row"


async def test_draft_outreach_answers_another_users_contact_as_not_found(monkeypatch):
    cap = {}
    _patch_outreach(monkeypatch, cap)
    seen = _patch_fetchrow(monkeypatch, None)
    out = await draft_outreach("u-1", contact_id="someone-elses-id")

    assert out == {"error": "contact not found"}
    assert "id=$1::uuid AND user_id=$2::uuid" in seen["sql"], (
        "the scoping is what makes another user's id a not-found rather than a read")
    assert "call" not in cap


async def test_draft_outreach_hands_the_saved_contact_and_current_resume_over(monkeypatch):
    cap = {}
    _patch_outreach(monkeypatch, cap)
    _patch_fetchrow(monkeypatch, {"name": "Ada", "role": "Talent lead",
                                  "company": "Acme", "relation": "recruiter"})

    async def fake_current(user_id):
        return {"id": "rv-1", "structured": '{"skills": [{"name": "Kubernetes"}]}'}

    monkeypatch.setattr(domain_mod, "get_current_resume_version", fake_current)
    out = await draft_outreach("u-1", contact_id="c-1", purpose="intro",
                               context="met at a talk")

    contact, purpose, structured, context = cap["call"]
    assert purpose == "intro" and context == "met at a talk"
    assert contact["company"] == "Acme"
    cited = {"skills": [{"name": "Kubernetes"}]}
    assert structured == cited, (
        "the jsonb text column arrives as a string; unparsed, the generator cites nothing")
    assert out["message"]["purpose"] == "intro"
    assert out["contact"]["name"] == "Ada"


async def test_draft_outreach_works_with_no_resume_at_all(monkeypatch):
    cap = {}
    _patch_outreach(monkeypatch, cap)
    _patch_fetchrow(monkeypatch, {"name": "Ada", "role": None, "company": None,
                                  "relation": None})

    async def no_resume(user_id):
        return None

    monkeypatch.setattr(domain_mod, "get_current_resume_version", no_resume)
    out = await draft_outreach("u-1", contact_id="c-1")

    assert cap["call"][2] == {}, "no resume is a shorter citation list, not an error"
    assert "error" not in out


# ---------------- log_contact_touch ----------------


async def test_a_touch_is_written_only_to_the_callers_row(monkeypatch):
    seen = _patch_fetchrow(monkeypatch, _row(ago=0))
    out = await log_contact_touch("u-1", contact_id="c-9", note="replied on LinkedIn")

    assert "id = $1::uuid AND user_id = $2::uuid" in seen["sql"]
    assert seen["args"] == ("c-9", "u-1", "replied on LinkedIn")
    assert out["logged"] is True
    assert "replied on LinkedIn" not in seen["sql"], (
        "the note is user text; spliced, it is injection and it leaks into SQL")


async def test_a_touch_of_an_unknown_contact_reports_failure_not_a_silent_log(monkeypatch):
    _patch_fetchrow(monkeypatch, None)
    out = await log_contact_touch("u-1", contact_id="c-9")

    assert out == {"error": "contact not found"}, (
        "an updated-row count of zero is the only signal the agent gets that nothing happened")


async def test_an_empty_note_leaves_the_notes_column_alone(monkeypatch):
    seen = _patch_fetchrow(monkeypatch, _row(ago=0))
    await log_contact_touch("u-1", contact_id="c-9")

    assert "WHEN $3 = '' THEN notes" in seen["sql"], (
        "logging a touch without a note must not blank the notes the user wrote")
    assert seen["args"][-1] == ""


async def test_a_note_is_appended_below_the_previous_one(monkeypatch):
    seen = _patch_fetchrow(monkeypatch, _row(ago=0))
    await log_contact_touch("u-1", contact_id="c-9", note="called")

    assert "notes || chr(10) || $3" in seen["sql"], (
        "overwriting notes would delete what the user typed into the registry")


# ---------------- the whitelist ----------------


def test_networking_is_one_of_the_agents_the_orchestrator_can_hand_off_to():
    assert "networking" in SUBAGENT_TOOLS
    assert "networking" in TRANSFER_SPEC.parameters["properties"]["agent"]["enum"], (
        "a subagent the orchestrator cannot name is a subagent that does not exist")


def test_the_networking_surface_holds_the_contact_tools_and_no_writes_elsewhere():
    granted = SUBAGENT_TOOLS["networking"]
    assert all(name in TOOL_INDEX for name in granted), "the whitelist names a deleted tool"
    for forbidden in ("save_job", "update_application_status", "create_interview",
                      "generate_resume", "generate_cover_letter", "calculate_match"):
        assert forbidden not in granted, (
            f"networking may call {forbidden}: the scoped-surface argument in AGENTS.md §2 "
            f"is only true if each agent holds just its own")


def test_the_purpose_enum_the_model_is_shown_is_the_one_the_handler_accepts():
    offered = TOOL_INDEX["draft_outreach"].parameters["properties"]["purpose"]["enum"]
    assert offered == sorted(PURPOSES), (
        f"schema offers {offered}, the generator knows {sorted(PURPOSES)} -- a purpose "
        f"outside this list is refused by the handler, so the model must not guess it")
