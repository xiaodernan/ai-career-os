"""One timeline over the whole loop (Epic 81).

The product stores resume versions, JD analyses, matches, tailored materials,
interview sessions, applications, notes, contacts, offers and digests, each with
its own screen and its own clock. A reader cannot see "what has happened in this
job search, in order" without walking multiple screens and comparing their clocks.
This engine reads rows that already exist and merges them into a single ordered
list the reader can scroll.

Pure and deterministic: no LLM, no clock of the call, no randomness. The same
events in any order answer the same timeline. Events are sorted by
`(at, kind, ref_id)` — `at` ISO-8601, `kind` a stable per-card-kind
tie-break, `ref_id` the row's own primary key, so the answer is a partition,
not a plan's mood.
"""
from __future__ import annotations

from datetime import datetime


def _parse(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _as_naive(value)
    text = str(value).replace("Z", "+00:00")
    try:
        return _as_naive(datetime.fromisoformat(text))
    except ValueError:
        return None


def _as_naive(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value
    return value.replace(tzinfo=None)


def build_timeline(events: list[dict]) -> dict:
    """Merge per-user events into the timeline shape.

    Every input event must carry at least `at` and `kind`; `title`,
    `refId` and `summary` are optional and default to empty. An unparseable
    `at` sorts before every event rather than crashing the page:
    a bad row is a data-point the timeline still shows, at the top.
    """
    out = []
    for event in events or []:
        raw_at = str(event.get("at") or "")
        parsed = _parse(raw_at)
        out.append({
            "at": raw_at,
            "kind": str(event.get("kind") or "unknown"),
            "title": str(event.get("title") or ""),
            "refId": str(event.get("refId") or event.get("ref_id") or ""),
            "summary": str(event.get("summary") or ""),
            "_sort": (parsed or datetime(1970, 1, 1),
                      str(event.get("kind") or ""),
                      str(event.get("refId") or event.get("ref_id") or "")),
        })
    out.sort(key=lambda item: item["_sort"])
    return {"timeline": [{"at": item["at"],
                          "kind": item["kind"],
                          "title": item["title"],
                          "refId": item["refId"],
                          "summary": item["summary"]} for item in out]}
