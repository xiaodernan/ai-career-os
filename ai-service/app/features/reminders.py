"""Follow-up reminder logic (forward Epic 11.3, internal-only).

Networking only pays off if stale contacts resurface before they go cold. This
module is the *pure* half of 11.3: given a contact record (name / role / company
/ relation / last_touch_at) it decides what is overdue, suggests a cadence by
relation, ranks who to touch next, and drafts an evidence-bound follow-up. Its first
reader is the agent tool `get_follow_ups`, which hands it the rows the contacts
registry (`11.1`) actually stores -- so the key it reads is that column's own name,
`last_touch_at`, not a spelling invented here.

Evidence-bound, like every other feature here: the follow-up draft uses ONLY the
fields the contact record actually carries (name, company, relation). It never
invents a status, a shared project, or a skill — a fabricated "great working with
you on X" is exactly the kind of line this product refuses to generate.
"""

from __future__ import annotations

from datetime import datetime, timezone

# Recommended maximum gap (days) between touches, by relation. Contacts past this
# since their last touch are "overdue"; past 70% of it they are "soon".
RELATION_CADENCE_DAYS: dict[str, int] = {
    "recruiter": 30,
    "hiring_manager": 30,
    "mentor": 60,
    "peer": 90,
    "referral": 45,
    "alumni": 120,
}

DEFAULT_CADENCE_DAYS = 90
_SOON_RATIO = 0.7

# Ranking weights used by `surface_stale`: the bucket decides first, days within it second.
_PRIORITY_ORDER = {"overdue": 0, "soon": 1, "fresh": 2}
# A contact with no recorded touch sorts at the head of its bucket: it is the most
# neglected thing in the registry, not the least datable one.
_NEVER_TOUCHED = 10 ** 9


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(dt: str | None) -> datetime | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt
    # Accept ISO strings (with or without timezone); fall back to date-only.
    s = str(dt).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass
    try:
        # date-only "2026-01-02"
        return datetime.fromisoformat(s + "T00:00:00+00:00")
    except ValueError:
        # Unparseable last_touch_at is treated as "never touched".
        return None


def days_since(last_touch: str | None, now: datetime | None = None) -> int | None:
    """Whole days since the last touch. ``None`` if never touched or unparseable."""
    parsed = _parse(last_touch)
    if parsed is None:
        return None
    ref = now or _now()
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0, (ref - parsed).days)


def suggest_cadence(relation: str | None) -> int:
    """Recommended max days between touches for a relation (default 90)."""
    if relation:
        return RELATION_CADENCE_DAYS.get(relation.lower(), DEFAULT_CADENCE_DAYS)
    return DEFAULT_CADENCE_DAYS


def priority_for(contact: dict, now: datetime | None = None) -> str:
    """Return ``overdue`` / ``soon`` / ``fresh`` for one contact.

    Overdue when never touched or past the relation's cadence; soon when past
    70% of it; fresh otherwise.
    """
    cadence = suggest_cadence(contact.get("relation"))
    since = days_since(contact.get("last_touch_at"), now)
    if since is None:
        return "overdue"
    if since >= cadence:
        return "overdue"
    if since >= cadence * _SOON_RATIO:
        return "soon"
    return "fresh"


def surface_stale(contacts: list[dict], now: datetime | None = None,
                  include_fresh: bool = False) -> list[dict]:
    """Rank contacts needing attention.

    Returns a list of dicts with the contact plus ``priority``, ``days_since`` and
    ``cadence_days``, sorted overdue first, then soon, then fresh, and inside a bucket
    by ``days_since`` descending (most neglected first). ``include_fresh`` keeps
    everyone; otherwise only ``soon`` / ``overdue``.

    The bucket comes first because cadence is per relation: a 74-day peer is only "soon"
    on its 90-day cadence, while a 43-day recruiter is already "overdue" on a cadence
    one-third as long. A sort on raw days would tell a user to write the contact who is
    not yet due before the one who is.
    """
    ref = now or _now()
    out: list[dict] = []
    for c in contacts:
        since = days_since(c.get("last_touch_at"), ref)
        cadence = suggest_cadence(c.get("relation"))
        priority = priority_for(c, ref)
        if not include_fresh and priority == "fresh":
            continue
        out.append({
            **c,
            "priority": priority,
            "days_since": since,
            "cadence_days": cadence,
        })
    out.sort(key=lambda x: (_PRIORITY_ORDER[x["priority"]],
                            -(x["days_since"] if x["days_since"] is not None
                              else _NEVER_TOUCHED)))
    return out


def draft_followup(contact: dict, *, relation: str | None = None) -> str:
    """Draft an evidence-bound follow-up.

    Uses only the contact's own fields. Never claims a shared history, a project,
    or a status the record does not contain — if there is nothing concrete to
    reference, the draft stays generic and the user fills the blank.
    """
    name = (contact.get("name") or "there").split()[0]
    company = contact.get("company")
    rel = relation or contact.get("relation")

    if company:
        opener = f"Hi {name}, hope things are going well at {company}."
    else:
        opener = f"Hi {name}, hope you've been well."

    if rel == "recruiter":
        body = ("I wanted to stay on your radar for upcoming roles that fit my "
                "background. Are there any openings worth a conversation?")
    elif rel == "mentor":
        body = ("I've been applying what we discussed and wanted to share a quick "
                "update and thank you for the guidance.")
    elif rel == "referral":
        body = "Just circling back to thank you again for the referral — much appreciated."
    elif rel == "peer":
        body = "It's been a while — would love to catch up on what you've been working on."
    else:
        body = "It's been a little while since we last spoke — wanted to reconnect."

    return f"{opener} {body}"
