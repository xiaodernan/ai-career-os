"""Job-ingestion connectors (forward Epic 14, internal-only).

The product's job corpus is currently seeded; Epic 14 opens it to real sources. The
half that lives in ai-service is the *deterministic* half -- everything that can be
computed without a model:

* 14.1 **connector contract** -- a tiny ``Connector`` protocol plus a
  ``normalize_posting`` step that maps whatever a source hands over into the canonical
  ``jobs`` field set (title / company / location / remote_type / ... / posted_at).
* 14.2 **first real connector, the parse half** -- ``parse_feed`` turns RSS 2.0 or
  Atom XML into raw postings using only the standard library, so it is offline-testable
  against a fixture string with no network. The fetch half (HTTP) stays in the backend.
* 14.3 **de-duplication + freshness** -- ``dedupe_postings`` collapses the same posting
  seen from multiple sources (or re-fetched) down to one survivor with the losers
  reported, and ``freshness_sweep`` partitions the corpus into still-fresh / stale
  (needs a re-check) / expired (past its age cap) so a sweep can close or refresh rows.

Everything here is pure and deterministic: the same input yields the same output, and
nothing is invented about a posting a source did not carry. A duplicate is an *exact*
match on a normalised (company, title, location) fingerprint -- conservative by design,
so a sweep never merges two genuinely different roles.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from app.ingestion.clean import clean

# canonical defaults, mirroring the jobs table
DEFAULT_REMOTE_TYPE = "onsite"
DEFAULT_EMPLOYMENT_TYPE = "full_time"
DEFAULT_CURRENCY = "CNY"

# feed inputs are capped so a hostile/broken feed cannot exhaust memory
MAX_FEED_BYTES = 5_000_000

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\u4e00-\u9fff]+")


def _norm_text(value) -> str:
    return _WS.sub(" ", clean(str(value))).strip().lower() if value is not None else ""


def _strip_punct(value: str) -> str:
    return _PUNCT.sub(" ", value).strip()


# ---------------- 14.1 connector contract ----------------


@runtime_checkable
class Connector(Protocol):
    """A job source. ``fetch`` returns raw posting dicts; the pipeline normalises them.

    Implementations live wherever the network access does (the backend). ai-service
    only ever sees the dicts, which keeps this module pure and offline-testable.
    """

    source: str

    def fetch(self) -> list[dict]:  # pragma: no cover - protocol declaration
        ...


def _to_int(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    m = re.search(r"-?\d[\d,]*", str(value))
    if not m:
        return None
    try:
        return int(m.group(0).replace(",", ""))
    except ValueError:
        return None


def normalize_posting(raw: dict, *, source: str = "seed") -> dict:
    """Map a raw connector payload onto the canonical ``jobs`` fields.

    Missing optional fields default rather than fail; ``title`` is the only field a
    posting cannot do without, so it is coerced to a string and may be empty (the
    caller decides whether to drop it). Company is read from ``company`` or
    ``company_name``. Nothing is inferred that the payload does not contain.
    """
    raw = raw or {}
    company = raw.get("company") or raw.get("company_name") or ""
    location = raw.get("location") or ""
    skills = raw.get("skills") or []
    if isinstance(skills, str):
        skills = [s for s in re.split(r"[,\u3001;]+", skills) if s.strip()]
    return {
        "title": _WS.sub(" ", clean(str(raw.get("title") or ""))).strip(),
        "company": _WS.sub(" ", clean(str(company))).strip(),
        "location": _WS.sub(" ", clean(str(location))).strip(),
        "remote_type": (raw.get("remote_type") or DEFAULT_REMOTE_TYPE),
        "employment_type": (raw.get("employment_type") or DEFAULT_EMPLOYMENT_TYPE),
        "salary_min": _to_int(raw.get("salary_min")),
        "salary_max": _to_int(raw.get("salary_max")),
        "salary_currency": (raw.get("salary_currency") or DEFAULT_CURRENCY).upper(),
        "description": clean(str(raw.get("description") or "")),
        "skills": [str(s).strip() for s in skills if str(s).strip()],
        "external_url": raw.get("external_url") or raw.get("link") or None,
        "posted_at": raw.get("posted_at") or raw.get("pubDate") or None,
        "source": raw.get("source") or source,
    }


# ---------------- 14.3 fingerprint / de-duplication ----------------


def posting_fingerprint(posting: dict) -> str:
    """Exact-match key: normalised company + title + location.

    Punctuation and case are stripped so "Backend Engineer" and "backend engineer!"
    collide, but the location is kept so the same title in two cities stays distinct.
    """
    company = _strip_punct(_norm_text(posting.get("company") or posting.get("company_name")))
    title = _strip_punct(_norm_text(posting.get("title")))
    location = _strip_punct(_norm_text(posting.get("location")))
    return f"{company}|{title}|{location}"


def _completeness(posting: dict) -> int:
    """A rough tie-break score so the richer record survives a duplicate cluster."""
    score = 0
    if posting.get("description"):
        score += 2
    if posting.get("salary_min") or posting.get("salary_max"):
        score += 1
    if posting.get("skills"):
        score += 1
    if posting.get("external_url"):
        score += 1
    return score


def _sort_key(posting: dict):
    ts = _parse_dt(posting.get("posted_at"))
    # newest first; unknown dates sink; then prefer the more complete record, then id
    return (ts is not None, ts.timestamp() if ts else 0.0, _completeness(posting),
            str(posting.get("id") or ""))


def dedupe_postings(postings: list[dict]) -> dict:
    """Collapse duplicates, keeping the newest / most complete record per fingerprint.

    Returns ``unique`` (the survivors, input order preserved), ``duplicates`` (each
    loser with the ``duplicateOf`` survivor id and the shared ``fingerprint``), and the
    counts. Postings with an empty fingerprint (no company *and* no title) are treated
    as distinct and never merged -- there is nothing to match on.
    """
    items = [p for p in (postings or []) if isinstance(p, dict)]
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for idx, p in enumerate(items):
        fp = posting_fingerprint(p)
        if not fp.strip("|"):
            # nothing to match on -> keep it distinct, keyed deterministically by position
            fp = f"__unkeyed__{idx}"
        if fp not in groups:
            groups[fp] = []
            order.append(fp)
        groups[fp].append(p)

    unique: list[dict] = []
    duplicates: list[dict] = []
    for fp in order:
        cluster = groups[fp]
        if len(cluster) == 1:
            unique.append(cluster[0])
            continue
        survivor = max(cluster, key=_sort_key)
        unique.append(survivor)
        for p in cluster:
            if p is survivor:
                continue
            duplicates.append({**p, "duplicateOf": survivor.get("id"),
                               "fingerprint": fp})
    return {
        "unique": unique,
        "duplicates": duplicates,
        "inputCount": len(items),
        "uniqueCount": len(unique),
        "duplicateCount": len(duplicates),
    }


# ---------------- 14.3 freshness sweep ----------------


def _parse_dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _age_days(value, now: datetime) -> float | None:
    dt = _parse_dt(value)
    if dt is None:
        return None
    ref = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    return max(0.0, (ref - dt).total_seconds() / 86400.0)


def freshness_sweep(postings: list[dict], *, now: datetime | None = None,
                    max_age_days: int = 60, stale_seen_days: int = 30) -> dict:
    """Partition postings by freshness.

    * ``expired`` -- posted longer than ``max_age_days`` ago -> the sweep should close it.
    * ``stale``   -- not expired, but ``last_seen`` is older than ``stale_seen_days``
      -> re-check the source before trusting it.
    * ``fresh``   -- everything else.

    Postings with no usable date are reported under ``undated`` rather than silently
    bucketed: a sweep must not claim a dateless row is fresh. ``last_seen`` is optional;
    without it a posting can be expired but never stale.
    """
    ref = now or datetime.now(timezone.utc)
    expired: list[dict] = []
    stale: list[dict] = []
    fresh: list[dict] = []
    undated: list[dict] = []

    for p in postings or []:
        if not isinstance(p, dict):
            continue
        age = _age_days(p.get("posted_at"), ref)
        if age is None:
            undated.append({"id": p.get("id"), "title": p.get("title")})
            continue
        if age > max_age_days:
            expired.append({"id": p.get("id"), "title": p.get("title"),
                            "ageDays": int(round(age))})
            continue
        seen_age = _age_days(p.get("last_seen"), ref)
        if seen_age is not None and seen_age > stale_seen_days:
            stale.append({"id": p.get("id"), "title": p.get("title"),
                          "daysSinceSeen": int(round(seen_age))})
            continue
        fresh.append({"id": p.get("id"), "title": p.get("title")})

    return {
        "fresh": fresh,
        "stale": stale,
        "expired": expired,
        "undated": undated,
        "counts": {"fresh": len(fresh), "stale": len(stale),
                   "expired": len(expired), "undated": len(undated)},
    }


# ---------------- 14.2 feed parsing (the first connector's deterministic half) ----------------


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _first_text(node: ET.Element, names: set[str]) -> str | None:
    for child in node:
        if _local(child.tag) in names and (child.text or "").strip():
            return child.text.strip()
    return None


def parse_feed(xml_text: str, *, source: str = "rss") -> list[dict]:
    """Parse RSS 2.0 or Atom XML into raw postings (no network, stdlib only).

    Returns one dict per item with ``title`` / ``link`` / ``description`` / ``pubDate``
    (RSS) or the Atom equivalents, plus ``company`` when the feed carries one. Malformed
    or oversized input raises ``ValueError`` -- a sweep should see a broken feed, not an
    empty success.
    """
    if xml_text is None:
        raise ValueError("feed is empty")
    if len(xml_text.encode("utf-8", "ignore")) > MAX_FEED_BYTES:
        raise ValueError("feed exceeds the size cap")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"invalid feed xml: {e}") from e

    items = [n for n in root.iter() if _local(n.tag) in ("item", "entry")]
    out: list[dict] = []
    for it in items:
        title = _first_text(it, {"title"})
        link = _first_text(it, {"link", "id"})
        if link is None:  # Atom <link href="..."/>
            for child in it:
                if _local(child.tag) == "link" and child.get("href"):
                    link = child.get("href")
                    break
        description = _first_text(it, {"description", "summary", "content"})
        pub = _first_text(it, {"pubdate", "published", "updated", "date"})
        company = _first_text(it, {"company", "author", "source", "creator"})
        out.append({
            "title": title,
            "link": link,
            "description": description,
            "pubDate": pub,
            "company": company,
            "source": source,
        })
    return out


BOARD_ARRAY_KEYS = ("jobs", "data", "results", "items", "postings")


def parse_json_board(text: str, *, source: str = "board") -> list[dict]:
    """Parse a board-API JSON payload into raw postings (no network, stdlib only).

    Accepts either a top-level array of posting objects or an object carrying the
    array under one of ``jobs`` / ``data`` / ``results`` / ``items`` / ``postings``
    -- the shapes real board APIs use. Non-JSON, an oversized payload, or an object
    with no recognised array raises ``ValueError`` rather than returning an empty
    success, so a broken board surfaces instead of silently ingesting nothing.
    """
    if text is None:
        raise ValueError("board payload is empty")
    if len(text.encode("utf-8", "ignore")) > MAX_FEED_BYTES:
        raise ValueError("board payload exceeds the size cap")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"invalid board json: {e}") from e

    if isinstance(data, dict):
        for key in BOARD_ARRAY_KEYS:
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            raise ValueError(
                f"no posting array found (looked for {', '.join(BOARD_ARRAY_KEYS)})")
    if not isinstance(data, list):
        raise ValueError("expected a JSON array of postings")

    out: list[dict] = []
    for item in data:
        row = dict(item) if isinstance(item, dict) else {"title": str(item)}
        row.setdefault("source", source)
        out.append(row)
    return out


# ---------------- composition: one call a backend sweep can act on ----------------


def plan_ingest(feed, *, source: str = "rss", existing: list[dict] | None = None,
                now: datetime | None = None, max_age_days: int = 60,
                stale_seen_days: int = 30) -> dict:
    """Compose parse -> normalize -> dedupe -> freshness into one actionable plan.

    ``feed`` is either raw RSS/Atom XML (a ``str``) or an already-parsed list of raw
    postings. ``existing`` is the corpus already in ``jobs``. The result is the three
    writes a backend sweep needs -- ``create`` (new), ``update`` (already known, carry
    the ``existingId`` so the row is refreshed), ``close`` (known, expired, and *not*
    re-seen this batch) -- plus the within-batch duplicates, never written twice.

    Pure and deterministic, and honest about its limits: a close is only proposed for a
    row that is expired *and* absent from this batch, so a still-live posting is never
    closed just because it did not reappear today.
    """
    raw = parse_feed(feed, source=source) if isinstance(feed, str) else list(feed or [])
    normalized = [normalize_posting(r, source=source) for r in raw]
    deduped = dedupe_postings(normalized)
    incoming = deduped["unique"]

    existing = [e for e in (existing or []) if isinstance(e, dict)]
    existing_by_fp: dict[str, dict] = {}
    for e in existing:
        existing_by_fp.setdefault(posting_fingerprint(e), e)

    incoming_fps: set[str] = set()
    create: list[dict] = []
    update: list[dict] = []
    for p in incoming:
        fp = posting_fingerprint(p)
        incoming_fps.add(fp)
        if fp in existing_by_fp:
            update.append({**p, "existingId": existing_by_fp[fp].get("id")})
        else:
            create.append(p)

    sweep = freshness_sweep(existing, now=now, max_age_days=max_age_days,
                            stale_seen_days=stale_seen_days)
    expired_ids = {x["id"] for x in sweep["expired"]}
    close = [{"id": e.get("id"), "title": e.get("title")} for e in existing
             if e.get("id") in expired_ids
             and posting_fingerprint(e) not in incoming_fps]

    return {
        "source": source,
        "create": create,
        "update": update,
        "close": close,
        "duplicates": deduped["duplicates"],
        "counts": {
            "incoming": len(incoming),
            "create": len(create),
            "update": len(update),
            "close": len(close),
            "duplicates": len(deduped["duplicates"]),
        },
    }
