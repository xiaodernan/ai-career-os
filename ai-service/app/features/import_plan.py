"""Import planning (Epic 13.2, the "apply" half, internal-only).

``diff_bundles`` says *what changed* between two bundles. ``plan_import`` goes one
step further: given an import bundle (and, optionally, the user's current state as
an ``existing`` bundle) it emits the concrete, idempotent write operations a
backend would execute — ``create`` for new rows, ``update`` for a known row whose
content changed, ``skip`` for a known row whose content did not, and ``delete``
for rows the restore can name and the bundle no longer carries. Each op carries a
per-item ``content_hash``.

The plan is a promise about the apply, so it has to know what the apply does.
Two kinds of section, two matching rules:

- The sections the restore writes through an id it can find again (the profile,
  the applications, the growth runs, the notes, the contacts, the job
  descriptions, the interviews, the chats, the saved searches and the feeds) are
  matched by id, and an id the target has and the bundle does not is a
  ``delete`` — the restore can name the row, so it can retire it.
- The sections the restore *re-ingests* (the resumes, the knowledge documents,
  the memories) are matched by what the apply recognizes them by — their
  content, or their ``(kind, key)`` — because their restored rows get new ids
  (the ingestion pipeline mints them). Matching those by id would promise a
  delete the apply never performs and a create on every re-import of the file
  the workspace itself wrote.

Pure: no I/O and no DB, except ``current_state``, which reads through the same
export fetchers the route already trusts so the comparison's other half is the
bundle's own serialization.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from ..core.errors import IMPORT_BUNDLE_INVALID, raise_refusal
from app.features.export import (
    AI_SECTIONS,
    SECTIONS,
    content_hash,
    gather_raw,
    redacted_sections,
    validate_bundle,
)

# Sections that are lists of addressable items; ``profile`` is a single object.
_LIST_SECTIONS = tuple(s for s in SECTIONS if s != "profile")

# The fields of a row that a restore does not write: the key it matched on, the
# account that owns the row, and the two stamps the database sets.
#
# They are excluded from the "did this row change" comparison for a reason that
# is not cosmetic: the first apply stamps ``updated_at`` (and a restored row gets
# a fresh ``created_at``), so a comparison that read the stamps would find every
# row it had just written changed, write it again, and never once answer "skip".
# Excluding them makes the comparison cover exactly the fields the apply writes,
# which is what "unchanged" is supposed to mean.
_NOT_WRITTEN = ("id", "user_id", "created_at", "updated_at")

# The same bookkeeping on a child row (a turn, a report). The apply writes the
# child's owner and session from the session it is restoring, not from the
# bundle, so comparing them would make every cross-account re-import an update.
_CHILD_NOT_WRITTEN = ("id", "user_id", "session_id", "created_at", "updated_at")

# A row can carry a field the restore does not write after all, because only
# the target can decide it. Those are excluded per section, for the same
# reason the stamps are: the comparison covers what the apply writes.
_NOT_WRITTEN_BY_SECTION: dict[str, tuple[str, ...]] = {
    # The session's links to a job, a JD and a resume version are carried
    # when the target can hold them; they are not what the restore writes,
    # and comparing them would rewrite a session forever in an account that
    # lacks one of those rows.
    "interviews": ("job_id", "jd_id", "resume_version_id", "job_title"),
    # Same rule for a posting's link to the shared job corpus.
    "job_descriptions": ("job_id",),
    # A memory's weight is only written when the bundle carries one; the
    # apply's default is the row's, and the field is not the memory itself.
    "memories": ("last_used_at",),
}

# The sections the restore matches by id: the row it writes is the row the
# bundle names, so an id the target no longer has is retired.
_REPLACEABLE = ("applications", "growth_plans", "notes", "contacts",
                "job_descriptions", "interviews", "conversations",
                "saved_searches", "ingestion_feeds")

# The bookkeeping a conversation's messages do not carry: the restore mints a
# message id and stamps it, and the transcript's owner and parent are the
# conversation it is being written with.
_MESSAGE_NOT_WRITTEN = ("id", "user_id", "conversation_id", "created_at", "updated_at")

# The sections the restore re-ingests: a restored row is a new row with a new
# id, so identity is the content and the restore never retires.
_ADDITIVE = ("resumes", "knowledge", "memories")


def check_bundle(bundle: dict) -> None:
    """Refuse a bundle the contract rejects, before anything is read or written.

    The route calls this first: the file is the input, so a bad file is
    answered from the file alone -- not after a database round trip the answer
    did not need, and not after a run row that records a request the reader's
    own file got wrong.
    """
    errors = validate_bundle(bundle)
    if errors:
        raise raise_refusal(IMPORT_BUNDLE_INVALID.with_detail({"errors": errors}))


def _canonical(value: Any) -> Any:
    """The comparison's spelling of a value.

    Three differences are not content, and all three used to make a row look
    changed: a ``jsonb`` column arriving as its text (a bundle written before
    the export decoded them) and as the object it holds; a ``numeric`` column
    arriving as ``Decimal`` from the database and as a JSON number from the
    bundle; and a whole number spelled ``5`` or ``5.0``. They are removed
    here, so the comparison answers "did the content change" and not "did the
    two producers spell it the same".
    """
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    if isinstance(value, str):
        text = value.lstrip()
        if text.startswith(("{", "[")):
            try:
                return _canonical(json.loads(value))
            except (TypeError, ValueError):
                return value
        return value
    if isinstance(value, bool) or value is None:
        # bool is an int; it is a value, never a number to normalize.
        return value
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    return value


def _without(item: dict, names: tuple[str, ...]) -> dict:
    return {k: _canonical(v) for k, v in item.items() if k not in names}


def _identity_hash(item: dict, section: str) -> str:
    """The hash a skip is decided on: what the apply would write, nothing else."""
    stripped = _without(item, _NOT_WRITTEN + _NOT_WRITTEN_BY_SECTION.get(section, ()))
    if section == "interviews":
        # The transcript and the report are written as the bundle carries
        # them; their ids and owners are the restore's to mint, so they are
        # stripped at that depth too.
        if isinstance(stripped.get("turns"), list):
            stripped["turns"] = [
                _without(turn, _CHILD_NOT_WRITTEN) if isinstance(turn, dict)
                else _canonical(turn)
                for turn in stripped["turns"]
            ]
        if isinstance(stripped.get("evaluation"), dict):
            stripped["evaluation"] = _without(
                stripped["evaluation"], _CHILD_NOT_WRITTEN)
    if section == "conversations" and isinstance(stripped.get("messages"), list):
        # The transcript is replaced whole when the conversation changes,
        # and its rows get ids and stamps from the target -- comparing them
        # would make every restored chat look changed forever.
        stripped["messages"] = [
            _without(message, _MESSAGE_NOT_WRITTEN) if isinstance(message, dict)
            else _canonical(message)
            for message in stripped["messages"]
        ]
    if section == "saved_searches":
        # The apply trims a search's name, as the create form does. The
        # comparison trims too, or a name with a stray space would be
        # written again on every re-import of the file that wrote it.
        if isinstance(stripped.get("name"), str):
            stripped["name"] = stripped["name"].strip()
    if section == "ingestion_feeds":
        # The apply fills the defaults the subscribe form would have: a
        # provenance label and an enabled switch. A bundle that omits them
        # restores to exactly those, so it compares as those. It also trims
        # the name and the address it writes, so the comparison does too --
        # otherwise a row with a stray space would be rewritten on every
        # re-import of the file that wrote it.
        if isinstance(stripped.get("name"), str):
            stripped["name"] = stripped["name"].strip()
        if isinstance(stripped.get("url"), str):
            stripped["url"] = stripped["url"].strip()
        source = stripped.get("source")
        if not isinstance(source, str) or not source.strip():
            stripped["source"] = "feed"
        if stripped.get("enabled") is None:
            stripped["enabled"] = True
    return content_hash(stripped)


def _text(item: dict, *names: str) -> str | None:
    for name in names:
        value = item.get(name)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _content_key(section: str, item: dict) -> tuple:
    """What the apply recognizes an additive row by.

    A restored resume is a new row with a new id, created through the same
    service a new resume goes through; a restored document is re-ingested as
    a note; a memory is upserted on ``(kind, key)``. So the next plan can
    only find those rows by what the restore copied: the title and the text,
    or the key the upsert uses.
    """
    if section == "resumes":
        title = _text(item, "resume_title", "title")
        return ("resume", title.strip() if title else "", _text(item, "plaintext") or "")
    if section == "knowledge":
        return ("document", (_text(item, "title") or "").strip(),
                _text(item, "text_excerpt") or "")
    if section == "memories":
        return ("memory", _text(item, "kind") or "fact", _text(item, "key") or "")
    return ("row", item.get("id"))


def _object(item: dict, name: str) -> dict:
    """A JSON-object field as the object it holds, tolerating its text."""
    value = item.get(name)
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return {}
    return value if isinstance(value, dict) else {}


def _writable(section: str, item: dict) -> bool:
    """Whether the apply can write this row at all.

    The answer is the backend's own gate, restated: a row the apply would
    leave alone is not a row the plan can promise to create. Without this,
    every preview counted a create for a document whose excerpt the export
    never carried -- a count the apply then had nothing to do for.
    """
    if section == "resumes":
        return bool(_text(item, "resume_title", "title") and _text(item, "plaintext"))
    if section == "knowledge":
        return bool(_text(item, "title") and _text(item, "text_excerpt"))
    if section == "memories":
        return bool(_text(item, "content"))
    if section == "job_descriptions":
        return bool(_text(item, "raw_text"))
    if section == "notes":
        return bool(_text(item, "content"))
    if section == "contacts":
        return bool(_text(item, "name"))
    if section == "saved_searches":
        # A search with no criteria asks the board nothing: the creation
        # path refuses one, and the morning sweep skips it, so the restore
        # does not write one either.
        return bool(_text(item, "name")) and bool(_object(item, "criteria"))
    if section == "ingestion_feeds":
        return bool(_text(item, "name") and _text(item, "url"))
    return True


def _op(kind: str, item: dict) -> dict:
    return {"op": kind, "id": item.get("id"), "content_hash": content_hash(item)}


def _plan_replaceable(section: str, items: list[dict],
                      existing_items: list[dict]) -> list[dict]:
    """Id-matched ops: create, update, skip -- and a delete for what is gone."""
    ex_by_id = {it.get("id"): it for it in existing_items if it.get("id") is not None}
    ops: list[dict] = []
    present_ids: set = set()
    for it in items:
        iid = it.get("id")
        if iid is not None:
            present_ids.add(iid)
        known = ex_by_id.get(iid) if iid is not None else None
        if known is None:
            kind = "create"
        elif _identity_hash(it, section) == _identity_hash(known, section):
            # The row is already there, and the import would write the same
            # fields over it. "Unchanged rows are skipped" is the promise the
            # preview makes; this is the op that keeps it.
            kind = "skip"
        else:
            kind = "update"
        ops.append(_op(kind, it))
    for iid in ex_by_id:
        if iid not in present_ids:
            ops.append({"op": "delete", "id": iid, "content_hash": None})
    return ops


def _plan_additive(section: str, items: list[dict],
                   existing_items: list[dict]) -> list[dict]:
    """Content-matched ops: create, skip -- and update for a memory -- never delete.

    The matching is one-to-one: the target's rows are consumed as the bundle
    names them, so a bundle carrying two copies of the same resume restores
    the second one instead of skipping both against a single existing row.
    """
    remaining = list(existing_items)
    ops: list[dict] = []
    for it in items:
        key = _content_key(section, it)
        known = None
        for index, ex in enumerate(remaining):
            if _content_key(section, ex) == key:
                known = remaining.pop(index)
                break
        if known is None:
            kind = "create"
        elif section == "memories" and \
                _identity_hash(it, section) != _identity_hash(known, section):
            kind = "update"
        else:
            kind = "skip"
        ops.append(_op(kind, it))
    return ops


def plan_import(bundle: dict, existing: dict | None = None) -> dict:
    """Produce an idempotent write plan for importing ``bundle``.

    Returns a dict shaped::

        {
          "schema_version": str,
          "source_content_hash": str,
          "sections": { <section>: [ {"op","id","content_hash"}, ... ] },
          "op_counts": {"create": int, "update": int, "delete": int,
                        "skip": int, "total": int},
        }

    Raises ``ValueError`` if the bundle fails ``validate_bundle``.
    """
    check_bundle(bundle)

    data = bundle.get("data")
    data = data if isinstance(data, dict) else {}
    existing_data = {}
    if isinstance(existing, dict):
        ed = existing.get("data")
        existing_data = ed if isinstance(ed, dict) else {}

    # A section the sharer redacted is withheld, not empty. The bundle makes
    # no claim about it, so the plan must make none either -- and a plan
    # that read "no rows here" as "delete every row there" would destroy
    # the target's own data on the strength of a section the sharer chose
    # not to share. So the redacted sections get no ops at all.
    withheld = redacted_sections(bundle)

    plan: dict = {
        "schema_version": bundle["schema_version"],
        "source_content_hash": bundle["manifest"]["content_hash"],
        "sections": {},
    }

    for section in _LIST_SECTIONS:
        if section in withheld:
            continue
        items = [it for it in (data.get(section) or [])
                 if isinstance(it, dict) and _writable(section, it)]
        existing_items = [it for it in (existing_data.get(section) or [])
                          if isinstance(it, dict) and _writable(section, it)]
        if section in _ADDITIVE:
            plan["sections"][section] = _plan_additive(section, items, existing_items)
        else:
            plan["sections"][section] = _plan_replaceable(section, items, existing_items)

    # profile is a single object. A redacted profile is absent, so there is
    # nothing to plan for it -- the same rule as the list sections above,
    # reached by a different road.
    profile = data.get("profile")
    if isinstance(profile, dict) and profile:
        ex_profile = existing_data.get("profile")
        if not isinstance(ex_profile, dict) or not ex_profile:
            profile_op = "create"
        elif _identity_hash(profile, "profile") == _identity_hash(ex_profile, "profile"):
            profile_op = "skip"
        else:
            profile_op = "update"
        plan["sections"]["profile"] = [{
            "op": profile_op,
            "id": profile.get("id"),
            "content_hash": content_hash(profile),
        }]

    all_ops = [op for sec in plan["sections"].values() for op in sec]
    plan["op_counts"] = {
        "create": sum(1 for o in all_ops if o["op"] == "create"),
        "update": sum(1 for o in all_ops if o["op"] == "update"),
        "delete": sum(1 for o in all_ops if o["op"] == "delete"),
        "skip": sum(1 for o in all_ops if o["op"] == "skip"),
        "total": len(all_ops),
    }
    return plan


def with_current_state(existing: dict | None, gathered: dict) -> dict:
    """The caller's current state, with the sections this service reads itself.

    The bridge hands over the sections it writes and cannot read six of the
    ten; a plan that took that silence for an empty workspace would tell the
    reader every row was a new row -- and a preview that overstates is a
    preview the apply then contradicts. So a section the caller did not send
    is read here, through the same fetchers the export uses, which is what
    makes the two halves of the comparison the same serialization.

    A section the caller did send is theirs and is left alone: they are the
    authority on their own rows, and the profile is one of those rows.
    """
    data: dict = {}
    if isinstance(existing, dict) and isinstance(existing.get("data"), dict):
        data.update(existing["data"])
    for section in AI_SECTIONS:
        if data.get(section) is not None:
            continue
        if section == "profile":
            data["profile"] = gathered.get("profile")
        else:
            data[section] = list(gathered.get(section) or [])
    return {"data": data}


async def current_state(user_id: str, existing: dict | None = None) -> dict:
    """``existing`` plus the six sections this service reads for itself."""
    return with_current_state(existing, await gather_raw(user_id))
