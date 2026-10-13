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

SCHEMA_VERSION = "1.0.0"
GENERATOR = "ai-career-os"

# Top-level profile keys stripped by ``anonymize`` unless the caller overrides.
DEFAULT_PII_FIELDS: tuple[str, ...] = ("email", "display_name", "phone", "address")

# Sections the ai-service composes today. ``applications`` / ``growth_plans`` are
# reserved for the backend bridge (it owns those writes) and stay absent until then.
SECTIONS: tuple[str, ...] = (
    "profile",
    "resumes",
    "knowledge",
    "job_descriptions",
    "interviews",
    "memories",
)


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
            ORDER BY s.created_at""",
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
    """

    def default(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat() if isinstance(o, datetime) else str(o)
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


def _section_counts(data: dict) -> dict[str, int]:
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


def build_bundle(user_id: str, raw: dict, *, anonymized: bool = False) -> dict:
    """Assemble a versioned, hashed export bundle from already-fetched raw data.

    Pure: takes the dict ``gather_raw`` would have produced and returns the bundle.
    ``generated_at`` and the hash are computed here, but the hash covers only
    ``data`` so it stays content-stable.
    """
    data = {section: raw.get(section) for section in SECTIONS}
    digest = content_hash(data)
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "generated_at": _iso_now(),
        "user": {"id": user_id, "anonymized": anonymized},
        "manifest": {
            "schema_version": SCHEMA_VERSION,
            "generator": GENERATOR,
            "counts": _section_counts(data),
            "content_hash": digest,
            "anonymized": anonymized,
        },
        "data": data,
    }
    return bundle


def anonymize(bundle: dict, drop: tuple[str, ...] = DEFAULT_PII_FIELDS) -> dict:
    """Return a copy of the bundle with PII fields stripped from the profile.

    Supports the right-to-be-forgotten / portability export (13.3). Matching is
    case-insensitive and only touches the top-level ``profile`` object, because
    that is the only section that carries direct identifiers today.
    """
    lowered = {d.lower() for d in drop}
    out = json.loads(_stable(bundle))  # deep copy via round-trip
    profile = out.get("data", {}).get("profile")
    if isinstance(profile, dict):
        for key in list(profile.keys()):
            if key.lower() in lowered:
                profile[key] = None
    out["user"] = {**out.get("user", {}), "anonymized": True}
    out["manifest"] = {**out.get("manifest", {}), "anonymized": True}
    # Re-stamp the hash now the profile changed.
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
    data = bundle.get("data", {})
    manifest = bundle.get("manifest", {})
    counts = manifest.get("counts", _section_counts(data))
    user = bundle.get("user", {})
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
    if profile:
        lines.append("## 个人档案")
        for k in ("display_name", "email", "headline", "summary"):
            if profile.get(k):
                lines.append(f"- **{k}**: {clip(profile[k], 400)}")
        lines.append("")

    resumes = data.get("resumes") or []
    if resumes:
        lines.append(f"## 简历版本（{len(resumes)}）")
        for r in resumes:
            lines.append(f"- {r.get('resume_title') or r.get('title')} "
                         f"· v{r.get('version', '?')} · {clip(r.get('plaintext'), 160)}")
        lines.append("")

    knowledge = data.get("knowledge") or []
    if knowledge:
        lines.append(f"## 知识库（{len(knowledge)} 篇）")
        for d in knowledge:
            lines.append(f"- {d.get('title')} · {d.get('media_type')} "
                         f"· {d.get('status')}")
        lines.append("")

    jds = data.get("job_descriptions") or []
    if jds:
        lines.append(f"## 职位描述（{len(jds)}）")
        for j in jds:
            lines.append(f"- {j.get('title') or j.get('role')} "
                         f"@ {j.get('company') or ''} · {clip(j.get('raw_text') or j.get('text'), 160)}")
        lines.append("")

    interviews = data.get("interviews") or []
    if interviews:
        lines.append(f"## 模拟面试（{len(interviews)} 场）")
        for s in interviews:
            turns = s.get("turns") or []
            lines.append(f"- {s.get('job_title') or '面试'} · {len(turns)} 轮 · "
                         f"{s.get('status') or ''}")
        lines.append("")

    memories = data.get("memories") or []
    if memories:
        lines.append(f"## 长期记忆（{len(memories)}）")
        for m in memories:
            lines.append(f"- [{m.get('kind')}] {clip(m.get('content'), 200)}")
        lines.append("")

    lines.append("---")
    lines.append(f"统计: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Async driver
# --------------------------------------------------------------------------- #


async def export_bundle(user_id: str, *, anonymized: bool = False) -> dict:
    """Fetch raw records and build the bundle in one call (the public entrypoint)."""
    raw = await gather_raw(user_id)
    return build_bundle(user_id, raw, anonymized=anonymized)
