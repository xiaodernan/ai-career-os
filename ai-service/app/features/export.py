"""Portable export / re-import composition (forward Epic 13.1 / 13.2 / 13.3).

A personal job-search OS is only as trustworthy as the user's ability to leave
with their data. This module is the *composition* layer: it gathers everything
the ai-service can read (profile, resume versions, the knowledge base, pasted
JDs, interview sessions, and long-term memories) into one deterministic,
versioned bundle, and offers the helpers the import / delete paths need:

- ``content_hash`` is computed over the *data* only (never over ``generated_at``
  or the hash itself), so re-exporting unchanged data yields the same hash.
  That is what makes an idempotent re-import (13.2) and a backup snapshot
  detectable as "nothing changed".
- ``anonymize`` strips the PII fields a right-to-be-forgotten / portability
  export should not carry (13.3).
- ``diff_bundles`` turns two exports into an added / changed / removed report
  per section, which is exactly the input an idempotent upsert needs.

It is **internal-only** on purpose: like the other forward features it ships
ahead of its backend bridge (the backend owns the ``applications`` and
``growth_plans`` writes, so those sections are reserved in the schema and filled
in by the bridge later). No route is registered here, so it cannot collide with
the in-flight ``api/features.py`` / ``main.py`` work in this repo's concurrent
development.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

SCHEMA_VERSION = "1.2.0"
GENERATOR = "ai-career-os"

# Top-level profile keys stripped by ``anonymize`` unless the caller overrides.
DEFAULT_PII_FIELDS: tuple[str, ...] = ("email", "display_name", "phone", "address")

# The fields each section carries that name a person -- the reader, or
# somebody the reader knows -- or that are the reader's own words.
#
# The anonymized export blanks them: the shape of the bundle stays, the
# people go. A field is on this list because it carries an identity or a
# sentence the reader wrote; everything else is the substance of a job
# search, and an export that leaves nothing behind is not an export.
#
# It is read by ``anonymize`` and by the gate that holds it against the
# entities that own the columns, so the list cannot drift away from the
# shape of the data without the gate saying so.
ANONYMIZED_FIELDS: dict[str, tuple[str, ...]] = {
    # The reader's own id, and the links to their profiles.
    "profile": ("user_id", "links", "summary"),
    # The people they know: a name, an address, a relation and what they
    # wrote about the person.
    "contacts": ("name", "role", "company", "relation", "email", "notes"),
    # The notes they typed -- and the tags they chose for them.
    "notes": ("title", "content", "tags"),
    # The resume's own text -- a name, a phone number, a history -- and the
    # diff between two versions, which is made of the very same words.
    "resumes": ("user_id", "label", "resume_title", "plaintext", "structured", "diff"),
    # What they wrote about each application, why it was rejected, and what
    # they were offered.
    "applications": ("notes", "rejection_reason", "offer_compensation"),
    # The growth report and its coverage, both of which are made of the
    # reader's own material.
    "growth_plans": ("coverage", "report"),
    # The excerpt of their own material, its title, and the storage key --
    # which is a path into the reader's own bucket and begins with their id.
    "knowledge": ("user_id", "title", "text_excerpt", "file_key"),
    # The pasted posting is not the reader's own words, but the row still
    # says whose posting it is.
    "job_descriptions": ("user_id",),
    # The facts the assistant extracted about them.
    "memories": ("key", "content"),
    # The interview session's own id of the reader. The turns are a list
    # inside the session, so they are handled by the bag policy below.
    "interviews": ("user_id",),
}

# Fields that carry a **bag** -- a JSON object stored in one column -- whose
# *inside* holds the reader's words.
#
# A bag cannot be handled by the field-name list above: the name says
# nothing about what is in it. `meta` is the bag the ingester puts the
# reader's own text into, and its shape is owned by whoever writes it --
# so the keys that carry the text are named here, and the bag keeps the
# rest, which is its shape ("this is a note", not "this is a resume").
#
# The gate holds this list against the writer that owns the shape, so a
# bag that grows a new text-bearing key cannot be added quietly.
ANONYMIZED_NESTED_FIELDS: dict[str, dict[str, tuple[str, ...]]] = {
    "knowledge": {"meta": ("inline_text", "text_excerpt")},
    # The interview turns: a list of rows inside the session's row, and the
    # reader's own answers in it. The evaluation quotes the answer back, so
    # it is the reader's words wearing the assistant's clothes.
    "interviews": {"turns": ("user_id", "content", "evaluation")},
}

# The sections the ai-service reads for itself.
AI_SECTIONS: tuple[str, ...] = (
    "profile",
    "resumes",
    "knowledge",
    "job_descriptions",
    "interviews",
    "memories",
)

# The sections the BACKEND owns: it writes ``applications`` and ``growth_plans``,
# so the ai-service cannot read them and the bridge hands them over. Since
# 1.1.0 they travel in the bundle, which is what makes an export complete --
# a bundle without the pipeline a candidate actually worked is a bundle of
# their reading list and nothing else.
#
# Since 1.2.0 the backend's own ``notes`` and ``contacts`` travel too, and
# those are not a nicety: they are the reader's own words -- the notes they
# typed into their knowledge base and the people they know. "Your data"
# that leaves out the two tables the reader typed into is a bundle of
# everything the *product* knows about them.
BACKEND_SECTIONS: tuple[str, ...] = (
    "applications",
    "growth_plans",
    "notes",
    "contacts",
)

# Every section a 1.2.0 bundle carries.
SECTIONS: tuple[str, ...] = AI_SECTIONS + BACKEND_SECTIONS

# What a 1.0.0 bundle carried. A bundle written before the bridge has no
# backend sections, and it is still a valid bundle -- so the required set is
# read off the bundle's own schema version rather than assumed.
LEGACY_SECTIONS: tuple[str, ...] = AI_SECTIONS

# The schema version that introduced the backend sections. It is a rung of
# the ladder below rather than a constant of its own, because the ladder is
# what the required set is read from.
#
# The sections each schema version carries, oldest first.
#
# A bundle's required set is read off its OWN version, so an older backup
# stays a valid bundle: a 1.0.0 one predates the backend's sections, a
# 1.1.0 one predates the notes and the contacts. The map is the record of
# what grew when, and it is read by *parsed* version rather than by string
# comparison -- "1.10.0" is after "1.9.0", and a string comparison says
# otherwise.
SECTIONS_BY_VERSION: dict[str, tuple[str, ...]] = {
    "1.0.0": LEGACY_SECTIONS,
    "1.1.0": AI_SECTIONS + ("applications", "growth_plans"),
    "1.2.0": SECTIONS,
}


def _version_tuple(version: str) -> tuple[int, ...] | None:
    """A schema version as numbers, or None when it is not one."""
    parts = version.split(".")
    if not parts or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def required_sections(schema_version: str) -> tuple[str, ...]:
    """The sections a bundle of this schema version must carry.

    A 1.0.0 bundle predates the backend sections and is still valid; a 1.1.0
    one without them is a bundle that was truncated, and the import path has to
    know the difference. The same holds for the notes and the contacts: a
    1.1.0 bundle is not a bundle that was truncated for them, because it
    never carried them.

    An unknown version is held to the newest set. A bundle written by a
    future version carries at least what this one does, and a file that is
    not a version at all -- a typo, a hand-made file -- is held to the
    strictest reading rather than the loosest.
    """
    known = SECTIONS_BY_VERSION
    if schema_version in known:
        return known[schema_version]
    parsed = _version_tuple(schema_version)
    if parsed is None:
        return SECTIONS
    # The newest known version that is not after this one: a 1.1.5 bundle is
    # a 1.1.0 bundle as far as its sections go.
    earlier = [v for v in known if (_version_tuple(v) or ()) <= parsed]
    if not earlier:
        return known["1.0.0"]
    newest = max(earlier, key=lambda v: _version_tuple(v) or ())
    return known[newest]


# --------------------------------------------------------------------------- #
# Raw fetch (I/O) — every function is module-level and monkeypatchable so the
# pure composition below can be unit-tested with zero database access.
# --------------------------------------------------------------------------- #


async def fetch_profile(user_id: str) -> dict | None:
    from app.db import domain

    return await domain.get_profile(user_id)


async def fetch_resume_versions(user_id: str) -> list[dict]:
    from app.core import db

    rows = await db.fetch(
        """SELECT rv.*, r.title AS resume_title
             FROM resume_versions rv
             JOIN resumes r ON r.id = rv.resume_id
            WHERE rv.user_id=$1::uuid
            ORDER BY rv.created_at""",
        user_id,
    )
    return [dict(r) for r in rows]


async def fetch_documents(user_id: str) -> list[dict]:
    from app.core import db

    rows = await db.fetch(
        """SELECT id, user_id, source_id, file_key, media_type, title,
                  content_hash, status, meta, text_excerpt, created_at, updated_at
             FROM documents WHERE user_id=$1::uuid ORDER BY created_at""",
        user_id,
    )
    return [dict(r) for r in rows]


async def fetch_jds(user_id: str) -> list[dict]:
    from app.core import db

    rows = await db.fetch(
        "SELECT * FROM job_jds WHERE user_id=$1::uuid ORDER BY created_at", user_id
    )
    return [dict(r) for r in rows]


async def fetch_interview_sessions(user_id: str) -> list[dict]:
    from app.core import db

    rows = await db.fetch(
        """SELECT s.*, j.title AS job_title, c.name AS company_name
             FROM interview_sessions s
             LEFT JOIN jobs j ON j.id = s.job_id
             LEFT JOIN companies c ON c.id = j.company_id
            WHERE s.user_id=$1::uuid
            ORDER BY s.started_at""",
        user_id,
    )
    return [dict(r) for r in rows]


async def fetch_interview_turns(session_ids: list[str]) -> dict[str, list[dict]]:
    from app.core import db

    if not session_ids:
        return {}
    rows = await db.fetch(
        "SELECT * FROM interview_turns WHERE session_id = ANY($1::uuid[]) ORDER BY seq",
        session_ids,
    )
    out: dict[str, list[dict]] = {}
    for r in rows:
        d = dict(r)
        out.setdefault(str(d["session_id"]), []).append(d)
    return out


async def fetch_memories(user_id: str) -> list[dict]:
    from app.db import domain

    return await domain.list_memories(user_id, limit=1000)


async def gather_raw(user_id: str) -> dict:
    """Pull every readable record for a user into one raw dict (no post-processing).

    The shape is deliberately close to the wire shape so ``build_bundle`` is a thin,
    pure transform — the part worth unit-testing without a database.
    """
    sessions = await fetch_interview_sessions(user_id)
    turns_by_session = await fetch_interview_turns([str(s["id"]) for s in sessions])
    interviews = [
        {**s, "turns": turns_by_session.get(str(s["id"]), [])} for s in sessions
    ]
    return {
        "profile": await fetch_profile(user_id),
        "resumes": await fetch_resume_versions(user_id),
        "knowledge": await fetch_documents(user_id),
        "job_descriptions": await fetch_jds(user_id),
        "interviews": interviews,
        "memories": await fetch_memories(user_id),
    }


# --------------------------------------------------------------------------- #
# Pure composition (no I/O) — these are what the unit tests hold.
# --------------------------------------------------------------------------- #


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable(value: Any) -> str:
    """Serialize a value deterministically so equal data hashes equally.

    Datetimes become ISO strings; dict key order is sorted; sets/lists are sorted
    when their contents are comparable, otherwise left in order. The goal is
    stability across runs, not human prettiness.

    A UUID becomes its string form, because the rows come straight out of
    Postgres and asyncpg hands back a `uuid.UUID` for every id column -- the
    bundle's whole point is to carry those ids, and a serializer that refused
    them could not produce a bundle for any workspace with a row in it.
    """

    def default(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat() if isinstance(o, datetime) else str(o)
        if isinstance(o, UUID):
            return str(o)
        if hasattr(o, "isoformat"):
            return o.isoformat()
        raise TypeError(f"not serializable: {type(o).__name__}")

    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=default)


def canonical_json(data: Any) -> str:
    """The canonical byte string a content hash is computed over."""
    return _stable(data)


def content_hash(data: Any) -> str:
    """Deterministic sha256 over the data payload.

    Stable across re-exports of unchanged data — the primitive the idempotent
    re-import (13.2) and the backup snapshot rely on.
    """
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def section_counts(data: dict) -> dict[str, int]:
    """How many rows each section carries.

    Public because the manifest's counts are a contract of their own: the
    bundle says how much of itself it holds, and a section that is absent
    counts as zero rather than as "unknown". The redaction recomputes this
    over the data it left behind, because a count that still claims the
    dropped rows is a count the bundle's own document contradicts.
    """
    counts: dict[str, int] = {}
    for section in SECTIONS:
        item = data.get(section)
        if item is None:
            counts[section] = 0
        elif isinstance(item, list):
            counts[section] = len(item)
        else:
            counts[section] = 1
    return counts


def redacted_sections(bundle: dict) -> set[str]:
    """The sections the bundle's manifest records as withheld.

    A redacted section is one the reader asked to be gone before sharing.
    It is absent from ``data`` -- that is the whole claim -- and the
    manifest says so, so a reader of the bundle can tell the difference
    between a section that was withheld and one that was always empty.
    """
    if not isinstance(bundle, dict):
        return set()
    manifest = bundle.get("manifest")
    if not isinstance(manifest, dict):
        return set()
    recorded = manifest.get("redacted_sections")
    if not isinstance(recorded, list):
        return set()
    return {s for s in recorded if isinstance(s, str) and s in SECTIONS}


def _dict_obj(value: Any) -> dict:
    """A mapping value, else an empty dict -- a None or wrong-typed key can't crash."""
    return value if isinstance(value, dict) else {}


def _dicts(rows: Any) -> list:
    """The dict rows of a list, tolerating None and non-dict / non-list input.

    A bundle section can be null or carry a junk entry; iterating it raw would
    render (or crash on) a non-dict, so every consumer funnels its list through
    here first."""
    return [r for r in (rows or []) if isinstance(r, dict)]


def build_bundle(user_id: str, raw: dict, *, anonymized: bool = False,
                 extra: dict | None = None) -> dict:
    """Assemble a versioned, hashed export bundle from already-fetched raw data.

    Pure: takes the dict ``gather_raw`` would have produced and returns the bundle.
    ``generated_at`` and the hash are computed here, but the hash covers only
    ``data`` so it stays content-stable.

    ``extra`` carries the sections the BACKEND owns -- ``applications`` and
    ``growth_plans``. The bridge reads those rows (it writes them) and hands
    them over, and the hash is computed here so there is one hashing rule for
    the whole bundle rather than one per producer. A section the bridge did not
    send is absent rather than null: "the user has no applications" and "the
    bridge did not ask" are different facts, and the import path has to know
    which one it is looking at.
    """
    data = {section: raw.get(section) for section in SECTIONS}
    for section, value in (extra or {}).items():
        if section in BACKEND_SECTIONS:
            data[section] = value
    digest = content_hash(data)
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "generated_at": _iso_now(),
        "user": {"id": user_id, "anonymized": anonymized},
        "manifest": {
            "schema_version": SCHEMA_VERSION,
            "generator": GENERATOR,
            "counts": section_counts(data),
            "content_hash": digest,
            "anonymized": anonymized,
        },
        "data": data,
    }
    if anonymized:
        # The flag has to *mean* something. It used to set the two
        # ``anonymized`` markers and nothing else, so the file said it was
        # anonymized -- in the manifest, and in the printable document, which
        # prints "（已匿名）" beside the reader's id -- while carrying the
        # reader's uuid, the links to their profiles, their resume's
        # plaintext, every answer they gave an interviewer, and the notes
        # they typed. The strip is here, so the flag and the file agree.
        bundle = anonymize(bundle)
    return bundle


def _redact_bag(value: Any, inner_keys: tuple[str, ...]) -> Any:
    """Take the reader's words out of a bag, and keep the bag's shape.

    A bag is a JSON object in one column. The field name says nothing about
    what is inside it, so the keys that carry the reader's words are named
    by the policy and only those go: the bag still says *what kind* of thing
    it was, which is the shape of the export.

    A bag that does not parse is not a bag we can read, and it might be
    anything -- so it goes whole. Half of an anonymization is worse than
    none: it looks like the file was cleaned.
    """
    if isinstance(value, dict):
        return {k: (None if k in inner_keys else v) for k, v in value.items()}
    if isinstance(value, list):
        # A list of rows -- the interview turns are a list inside a row.
        return [_redact_bag(item, inner_keys) for item in value]
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return json.dumps(
        {k: (None if k in inner_keys else v) for k, v in parsed.items()},
        ensure_ascii=False,
        sort_keys=True,
    )


def anonymize(bundle: dict, drop: tuple[str, ...] = DEFAULT_PII_FIELDS) -> dict:
    """Return a copy of the bundle with the people taken out of it.

    The reader has two ways to leave with their data: the **redaction** drops
    whole sections, and the **anonymized export** keeps the shape and takes
    the people out of it. This is the second one, and it is the surface the
    docs call "the right-to-be-forgotten surface" -- so it has to actually
    forget.

    It used to forget nothing. It blanked four field names on the profile
    (``email``, ``display_name``, ``phone``, ``address``) and the profile has
    carried none of them for as long as the export has existed: its columns
    are ``headline``, ``summary``, ``location``, ``links``,
    ``work_authorization``, ``preferences`` and ``user_id``. So the button
    called "Export anonymized" exported everything -- the reader's own uuid,
    the links to their profiles, their resume's plaintext and every answer
    they gave an interviewer. The unit test passed because its fixture was
    shaped like the *old* profile rather than the real one.

    Since 1.2.0 the bundle also carries the notes the reader typed and the
    people they know, which is worse: an "anonymized" file that names every
    contact in the reader's address book, with their email.

    So the policy is one list, per section, read by the code that does the
    stripping. A field is on it because it names a person -- the reader or
    somebody the reader knows -- or because it is the reader's own words.
    Everything else is the substance of a job search, and an export that
    leaves nothing behind is not an export.
    """
    lowered = {d.lower() for d in drop if isinstance(d, str)}
    out = json.loads(_stable(bundle)) if isinstance(bundle, dict) else {}
    if not isinstance(out, dict):
        out = {}
    data = out.get("data")
    if not isinstance(data, dict):
        data = {}
        out["data"] = data
    profile = data.get("profile")
    if isinstance(profile, dict):
        for key in list(profile.keys()):
            if key.lower() in lowered:
                profile[key] = None
    for section, fields in ANONYMIZED_FIELDS.items():
        rows = data.get(section)
        if isinstance(rows, dict):
            # The profile is the one section that is a single object.
            rows = [rows]
        elif not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            for field in fields:
                if field in row:
                    row[field] = None
    # The bags: the text inside them goes, the shape of them stays.
    for section, fields in ANONYMIZED_NESTED_FIELDS.items():
        rows = data.get(section)
        if isinstance(rows, dict):
            rows = [rows]
        elif not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            for field, inner in fields.items():
                if field in row:
                    row[field] = _redact_bag(row[field], inner)
    # The reader's own id, in the envelope and in the rows that carry it.
    user = _dict_obj(out.get("user"))
    if "id" in user:
        user["id"] = None
    out["user"] = {**user, "anonymized": True}
    out["manifest"] = {**_dict_obj(out.get("manifest")), "anonymized": True}
    # Re-stamp the hash now the bundle changed.
    out["manifest"]["content_hash"] = content_hash(out["data"])
    return out


def _item_key(item: Any) -> str:
    """A stable per-item key for diffing: prefer an ``id``, else hash the item."""
    if isinstance(item, dict):
        iid = item.get("id") or item.get("session_id")
        if iid is not None:
            return str(iid)
    return content_hash(item)


def diff_bundles(old: dict, new: dict) -> dict:
    """Compare two bundles per section.

    Returns, for each section, ``added`` / ``removed`` / ``changed`` lists of
    item keys. The input an idempotent re-import (13.2) needs: the bridge only
    has to upsert the ``added`` + ``changed`` keys and delete the ``removed``.
    """
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "sections": {}}
    old_data = old.get("data", {})
    new_data = new.get("data", {})
    for section in SECTIONS:
        old_items = old_data.get(section) or []
        new_items = new_data.get(section) or []
        if not isinstance(old_items, list):
            old_items = [old_items]
        if not isinstance(new_items, list):
            new_items = [new_items]
        old_map = {_item_key(i): i for i in old_items}
        new_map = {_item_key(i): i for i in new_items}
        added = [k for k in new_map if k not in old_map]
        removed = [k for k in old_map if k not in new_map]
        changed = [
            k
            for k in new_map
            if k in old_map and content_hash(new_map[k]) != content_hash(old_map[k])
        ]
        report["sections"][section] = {
            "added": added,
            "removed": removed,
            "changed": changed,
        }
    return report


def to_markdown(bundle: dict) -> str:
    """Render the bundle as a human-readable Markdown document.

    The PDF half of 13.1 is a downstream concern; this is the readable source
    that the PDF generator would flow. Large free-text fields are clipped so the
    document stays scannable.
    """
    bundle = bundle if isinstance(bundle, dict) else {}
    data = _dict_obj(bundle.get("data"))
    manifest = _dict_obj(bundle.get("manifest"))
    _counts = manifest.get("counts")
    counts = _counts if isinstance(_counts, dict) else section_counts(data)
    user = _dict_obj(bundle.get("user"))
    lines: list[str] = []
    lines.append("# AI Career OS — 数据导出")
    lines.append("")
    lines.append(f"- 生成时间: {bundle.get('generated_at', 'n/a')}")
    lines.append(f"- 用户 ID: {user.get('id', 'n/a')}"
                 + ("（已匿名）" if user.get("anonymized") else ""))
    lines.append(f"- Schema: {manifest.get('schema_version', SCHEMA_VERSION)}")
    lines.append(f"- 内容哈希: `{manifest.get('content_hash', 'n/a')}`")
    lines.append("")

    def clip(text: Any, n: int = 240) -> str:
        if text is None:
            return "—"
        s = str(text).replace("\n", " ")
        return s if len(s) <= n else s[:n] + "…"

    profile = data.get("profile")
    if not isinstance(profile, dict):
        profile = None
    if profile:
        lines.append("## 个人档案")
        for k in ("display_name", "email", "headline", "summary"):
            if profile.get(k):
                lines.append(f"- **{k}**: {clip(profile[k], 400)}")
        lines.append("")

    resumes = _dicts(data.get("resumes"))
    if resumes:
        lines.append(f"## 简历版本（{len(resumes)}）")
        for r in resumes:
            lines.append(f"- {r.get('resume_title') or r.get('title')} "
                         f"· v{r.get('version', '?')} · {clip(r.get('plaintext'), 160)}")
        lines.append("")

    knowledge = _dicts(data.get("knowledge"))
    if knowledge:
        lines.append(f"## 知识库（{len(knowledge)} 篇）")
        for d in knowledge:
            lines.append(f"- {d.get('title')} · {d.get('media_type')} "
                         f"· {d.get('status')}")
        lines.append("")

    jds = _dicts(data.get("job_descriptions"))
    if jds:
        lines.append(f"## 职位描述（{len(jds)}）")
        for j in jds:
            lines.append(f"- {j.get('title') or j.get('role')} "
                         f"@ {j.get('company') or ''} · {clip(j.get('raw_text') or j.get('text'), 160)}")
        lines.append("")

    interviews = _dicts(data.get("interviews"))
    if interviews:
        lines.append(f"## 模拟面试（{len(interviews)} 场）")
        for s in interviews:
            _turns = s.get("turns")
            turns = _turns if isinstance(_turns, list) else []
            lines.append(f"- {s.get('job_title') or '面试'} · {len(turns)} 轮 · "
                         f"{s.get('status') or ''}")
        lines.append("")

    memories = _dicts(data.get("memories"))
    if memories:
        lines.append(f"## 长期记忆（{len(memories)}）")
        for m in memories:
            lines.append(f"- [{m.get('kind')}] {clip(m.get('content'), 200)}")
        lines.append("")

    lines.append("---")
    lines.append(f"统计: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Serialization & validation (the JSON half of 13.1 + the import contract)
# --------------------------------------------------------------------------- #


def serialize_bundle(bundle: dict) -> str:
    """Deterministic JSON text for the bundle (stable key order, UTF-8)."""
    return canonical_json(bundle)


def parse_bundle(text: str) -> dict:
    """Parse bundle JSON back into a dict. Raises ``json.JSONDecodeError`` on bad input."""
    return json.loads(text)


def validate_bundle(bundle: dict) -> list[str]:
    """Return a list of contract violations (empty list == valid).

    Held so the import path (13.2) can reject a malformed or tampered bundle
    before any upsert: every required top-level / manifest key must be present
    and ``manifest.content_hash`` must still match the ``data`` payload.

    A non-object (``null`` is legal JSON, so a backup file can decode to ``None``) is a
    contract violation, not an exception: returning it here lets the caller report a
    clean "invalid bundle" instead of a ``TypeError`` traceback from ``key not in None``.
    """
    if not isinstance(bundle, dict):
        return ["bundle is not a JSON object"]
    errors: list[str] = []
    for key in ("schema_version", "generator", "generated_at", "user", "manifest", "data"):
        if key not in bundle:
            errors.append(f"missing top-level key: {key}")
    if "manifest" in bundle:
        m = bundle["manifest"]
        for k in ("schema_version", "generator", "counts", "content_hash", "anonymized"):
            if k not in m:
                errors.append(f"missing manifest key: {k}")
    if "data" in bundle:
        # The required set is read off the bundle's OWN schema version: a 1.0.0
        # bundle predates the backend sections and is still valid, while a
        # 1.1.0 one without them was truncated. Assuming the current set for
        # both would reject every backup the user already has.
        version = bundle.get("schema_version")
        wanted = required_sections(version) if isinstance(version, str) else SECTIONS
        # A section the manifest records as redacted was withheld on purpose,
        # and a withheld section is not a truncated one. Without this rule a
        # redacted bundle -- the file a reader deliberately made shareable --
        # is rejected by the very path that exists to restore it, and the
        # redaction turns a backup into a document nobody can use.
        withheld = redacted_sections(bundle)
        for s in wanted:
            if s in withheld:
                continue
            if s not in bundle["data"]:
                errors.append(f"missing data section: {s}")
    if (
        "manifest" in bundle
        and "data" in bundle
        and isinstance(bundle.get("manifest"), dict)
        and "content_hash" in bundle["manifest"]
    ):
        if bundle["manifest"]["content_hash"] != content_hash(bundle["data"]):
            errors.append("content_hash does not match data payload")
    return errors


def write_bundle(bundle: dict, path: str) -> None:
    """Persist the bundle as a ``.json`` file (the one-click export target)."""
    from pathlib import Path

    Path(path).write_text(serialize_bundle(bundle), encoding="utf-8")


def read_bundle(path: str) -> dict:
    """Load a bundle previously written by :func:`write_bundle`."""
    from pathlib import Path

    return parse_bundle(Path(path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Async driver
# --------------------------------------------------------------------------- #


async def export_bundle(user_id: str, *, anonymized: bool = False,
                       extra: dict | None = None) -> dict:
    """Fetch raw records and build the bundle in one call (the public entrypoint).

    ``extra`` carries the sections the backend owns — it reads those rows itself
    and hands them over, so the bundle is complete and the hash is still
    computed in one place.
    """
    raw = await gather_raw(user_id)
    return build_bundle(user_id, raw, anonymized=anonymized, extra=extra)
