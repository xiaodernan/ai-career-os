"""Unit tests for follow-up reminder logic (forward Epic 11.3).

Pure functions, no I/O. The contract this file holds: cadence by relation,
deterministic stale/soon/fresh priority, stable ranking, and an evidence-bound
draft that never fabricates a shared history.
"""

from datetime import datetime, timezone

from app.features import reminders as rm

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def _contact(**kw) -> dict:
    base = {"name": "Ada Lovelace", "company": "Acme", "relation": "recruiter",
            "last_touch": None}
    base.update(kw)
    return base


# ---------------- days_since ----------------


def test_days_since_none_when_never_touched():
    assert rm.days_since(None, NOW) is None
    assert rm.days_since("", NOW) is None


def test_days_since_positive_and_clamped_at_zero():
    assert rm.days_since("2026-10-10", NOW) == 4
    assert rm.days_since("2026-10-20", NOW) == 0  # future clamps to 0


def test_days_since_accepts_iso_with_timezone():
    assert rm.days_since("2026-09-14T08:00:00+00:00", NOW) == 30


# ---------------- cadence ----------------


def test_cadence_known_relation():
    assert rm.suggest_cadence("recruiter") == 30
    assert rm.suggest_cadence("mentor") == 60


def test_cadence_unknown_or_none_defaults():
    assert rm.suggest_cadence("wizard") == rm.DEFAULT_CADENCE_DAYS
    assert rm.suggest_cadence(None) == rm.DEFAULT_CADENCE_DAYS


# ---------------- priority ----------------


def test_priority_never_touched_is_overdue():
    assert rm.priority_for({"last_touch": None}, NOW) == "overdue"


def test_priority_past_cadence_is_overdue():
    recruiter = {"relation": "recruiter", "last_touch": "2026-09-01"}  # 43d > 30
    assert rm.priority_for(recruiter, NOW) == "overdue"


def test_priority_within_soon_window():
    # 22 days since, cadence 30 -> 22 >= 0.7*30 (21) -> soon
    recruiter = {"relation": "recruiter", "last_touch": "2026-09-22"}
    assert rm.priority_for(recruiter, NOW) == "soon"


def test_priority_fresh():
    recruiter = {"relation": "recruiter", "last_touch": "2026-10-12"}  # 2d
    assert rm.priority_for(recruiter, NOW) == "fresh"


# ---------------- surface_stale ----------------


def test_surface_stale_omits_fresh_and_ranks():
    contacts = [
        _contact(name="Fresh", relation="peer", last_touch="2026-10-13"),       # 1d fresh
        _contact(name="Old", relation="peer", last_touch="2026-01-01"),          # ~286d overdue
        _contact(name="Soon", relation="peer", last_touch="2026-08-01"),         # ~74d soon
        _contact(name="Never", relation="peer", last_touch=None),                # overdue
    ]
    out = rm.surface_stale(contacts, NOW)
    names = [c["name"] for c in out]
    assert "Fresh" not in names
    # most-neglected first: Never (None sorts last/largest) then Old then Soon
    assert names[0] == "Never"
    assert names == ["Never", "Old", "Soon"]


def test_surface_stale_include_fresh():
    contacts = [_contact(name="Fresh", relation="peer", last_touch="2026-10-13")]
    assert rm.surface_stale(contacts, NOW) == []
    assert len(rm.surface_stale(contacts, NOW, include_fresh=True)) == 1


def test_surface_stale_annotates_each_row():
    out = rm.surface_stale([_contact(last_touch=None, relation=None)], NOW)
    row = out[0]
    assert row["priority"] == "overdue"
    assert row["cadence_days"] == 90
    assert row["days_since"] is None


# ---------------- draft_followup (evidence-bound) ----------------


def test_draft_uses_name_and_company_only():
    text = rm.draft_followup(_contact(name="Ada Lovelace", company="Acme",
                                     relation="recruiter"))
    assert "Ada" in text and "Acme" in text


def test_draft_without_company_is_generic():
    text = rm.draft_followup({"name": "Grace Hopper", "relation": "peer"})
    assert "Grace" in text
    assert "Acme" not in text  # no company -> no company named


def test_draft_recruiter_body_differs_from_peer():
    rec = rm.draft_followup(_contact(relation="recruiter"))
    peer = rm.draft_followup(_contact(relation="peer"))
    assert rec != peer
    assert "openings" in rec


def test_draft_does_not_fabricate_shared_history():
    # A bare contact record must not produce a claim of a shared project/status.
    text = rm.draft_followup(_contact(name="Ada", company="Acme", relation="peer"))
    lower = text.lower()
    assert "worked on" not in lower
    assert "our project" not in lower
    assert "offer" not in lower
