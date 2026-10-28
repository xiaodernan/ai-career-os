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
* 19.8 **real board payloads** -- the two public board APIs carry the same facts under
  their own names: Greenhouse's ``absolute_url`` / ``first_published`` / HTML
  ``content`` and a ``{"name": ...}`` location, Lever's ``text`` / ``hostedUrl`` /
  ``createdAt`` (epoch milliseconds) / ``categories`` and HTML ``description`` next to
  its plain twin. ``normalize_posting`` reads those aliases, so the sweep and a hand
  paste of the same JSON take the identical road, and a board that never names its
  company in a row gets the board's own name from the caller.

Everything here is pure and deterministic: the same input yields the same output, and
nothing is invented about a posting a source did not carry. A duplicate is an *exact*
match on a normalised (company, title, location) fingerprint -- conservative by design,
so a sweep never merges two genuinely different roles.
"""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from app.ingestion.clean import clean

from ..core.errors import (
    INGEST_FEED_EMPTY,
    INGEST_FEED_TOO_LARGE,
    INGEST_FEED_INVALID,
    INGEST_BOARD_EMPTY,
    INGEST_BOARD_TOO_LARGE,
    INGEST_BOARD_INVALID,
    INGEST_BOARD_NO_ARRAY,
    INGEST_BOARD_NOT_ARRAY,
    INGEST_FORMAT_UNKNOWN,
    raise_refusal,
)

# canonical defaults, mirroring the jobs table
DEFAULT_REMOTE_TYPE = "onsite"
DEFAULT_EMPLOYMENT_TYPE = "full_time"
DEFAULT_CURRENCY = "CNY"

# feed inputs are capped so a hostile/broken feed cannot exhaust memory
MAX_FEED_BYTES = 5_000_000

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\u4e00-\u9fff]+")
_TAG = re.compile(r"<[^>]+>")
# Epoch stamps at or above this are milliseconds; below it they are seconds.
_EPOCH_MS = 100_000_000_000
# Lever's `categories.commitment` in the product's own four employment types.
_COMMITMENTS = {
    "full-time": "full_time", "full time": "full_time", "fulltime": "full_time",
    "full_time": "full_time", "internship": "internship", "contract": "contract",
    "contractor": "contract", "new grad": "new_grad", "new_grad": "new_grad",
}
# Lever's `workplaceType` in the jobs table's three remote types.
_WORKPLACES = {"remote": "remote", "hybrid": "hybrid", "on-site": "onsite",
               "onsite": "onsite"}


def _norm_text(value) -> str:
    return _WS.sub(" ", clean(str(value))).strip().lower() if value is not None else ""


def _strip_punct(value: str) -> str:
    return _PUNCT.sub(" ", value).strip()


# ---------------- 19.8 board payload shapes ----------------


def _board_text(value) -> str | None:
    """A board field that carries HTML, as text. Greenhouse escapes its HTML once more."""
    if value is None or value == "":
        return None
    return clean(_TAG.sub("\n", html.unescape(str(value))))


def _board_location(value) -> str:
    """A board's location is a name string (Lever) or ``{"name": ...}`` (Greenhouse)."""
    if isinstance(value, dict):
        return value.get("name") or value.get("city") or ""
    return value if isinstance(value, str) else ""


def _board_date(value) -> str | None:
    """An epoch stamp (Lever's ``createdAt``) as ISO 8601, or None when it is not one.

    Lever sends milliseconds; a seconds-scale stamp is read as seconds rather than as a
    date in 1970. A boolean or a non-number is not a date at all.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return None
    seconds = value / 1000.0 if value >= _EPOCH_MS else float(value)
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _board_employment(value) -> str | None:
    if not isinstance(value, str):
        return None
    return _COMMITMENTS.get(_WS.sub(" ", value).strip().lower())


def _board_remote(value) -> str | None:
    if not isinstance(value, str):
        return None
    return _WORKPLACES.get(value.strip().lower())


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


def normalize_posting(raw: dict, *, source: str = "seed",
                      default_company: str | None = None) -> dict:
    """Map a raw connector payload onto the canonical ``jobs`` fields.

    Missing optional fields default rather than fail; ``title`` is the only field a
    posting cannot do without, so it is coerced to a string and may be empty (the
    caller decides whether to drop it). Company is read from ``company`` or
    ``company_name``, then from ``default_company`` -- the board's own name, the one
    place a Greenhouse or Lever row could get it, since neither names the company in a
    posting. Nothing is inferred that the payload does not contain.

    The remaining aliases are the public board APIs' own field names (19.8): Lever's
    ``text`` / ``hostedUrl`` / ``categories`` / ``createdAt`` and Greenhouse's
    ``absolute_url`` / ``first_published`` / HTML ``content``. A field the payload does
    not carry -- an unlisted commitment, a missing date -- keeps the canonical default
    rather than being guessed from another field.
    """
    # a connector/paste may hand over a non-dict (a bare string, None); default rather
    # than raise -- the caller decides whether a title-less posting is worth keeping
    raw = raw if isinstance(raw, dict) else {}
    categories = raw.get("categories")
    categories = categories if isinstance(categories, dict) else {}
    company = raw.get("company") or raw.get("company_name") or default_company or ""
    location = _board_location(raw.get("location")) or categories.get("location") or ""
    skills = raw.get("skills") or []
    if isinstance(skills, str):
        skills = [s for s in re.split(r"[,\u3001;]+", skills) if s.strip()]
    title = raw.get("title") or raw.get("text") or ""  # Lever names the title `text`
    description = (raw.get("descriptionPlain") or raw.get("description")
                   or _board_text(raw.get("content")) or "")
    return {
        "title": _WS.sub(" ", clean(str(title))).strip(),
        "company": _WS.sub(" ", clean(str(company))).strip(),
        "location": _WS.sub(" ", clean(str(location))).strip(),
        "remote_type": (raw.get("remote_type") or _board_remote(raw.get("workplaceType"))
                        or DEFAULT_REMOTE_TYPE),
        "employment_type": (raw.get("employment_type")
                            or _board_employment(categories.get("commitment"))
                            or DEFAULT_EMPLOYMENT_TYPE),
        "salary_min": _to_int(raw.get("salary_min")),
        "salary_max": _to_int(raw.get("salary_max")),
        "salary_currency": (raw.get("salary_currency") or DEFAULT_CURRENCY).upper(),
        "description": clean(str(description)),
        "skills": [str(s).strip() for s in skills if str(s).strip()],
        "external_url": (raw.get("external_url") or raw.get("link")
                         or raw.get("absolute_url") or raw.get("hostedUrl") or None),
        "posted_at": (raw.get("posted_at") or raw.get("pubDate")
                      or raw.get("first_published") or _board_date(raw.get("createdAt"))
                      or None),
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


def detect_format(text: str) -> str:
    """``"rss"`` for an XML feed, ``"board"`` for a board-API JSON payload.

    The product's own page says it accepts both ("RSS 2.0 / Atom XML, or a
    board-API JSON payload"), so the reader is not asked to say which one
    they pasted -- and a feed that begins with ``<`` is XML whatever the
    caller labelled it. This is the one place the decision is made, and the
    operator-facing ``app.ops.ingest_plan`` reads it too.
    """
    if not isinstance(text, str):
        return "board"
    return "rss" if text.lstrip()[:1] == "<" else "board"


def parse_any(text: str, *, source: str = "rss") -> list[dict]:
    """Parse a feed of either shape into raw postings.

    A broken feed raises ``ValueError`` -- from whichever parser the shape
    selected -- so a sweep sees a broken feed, not an empty success.
    """
    if detect_format(text) == "rss":
        return parse_feed(text, source=source)
    return parse_json_board(text, source=source)


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
    if not isinstance(xml_text, str) or not xml_text.strip():
        raise raise_refusal(INGEST_FEED_EMPTY)
    if len(xml_text.encode("utf-8", "ignore")) > MAX_FEED_BYTES:
        raise raise_refusal(INGEST_FEED_TOO_LARGE)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise raise_refusal(INGEST_FEED_INVALID) from e

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
    if not isinstance(text, str) or not text.strip():
        raise raise_refusal(INGEST_BOARD_EMPTY)
    if len(text.encode("utf-8", "ignore")) > MAX_FEED_BYTES:
        raise raise_refusal(INGEST_BOARD_TOO_LARGE)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        raise raise_refusal(INGEST_BOARD_INVALID) from e

    if isinstance(data, dict):
        for key in BOARD_ARRAY_KEYS:
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            raise raise_refusal(INGEST_BOARD_NO_ARRAY)
    if not isinstance(data, list):
        raise raise_refusal(INGEST_BOARD_NOT_ARRAY)

    out: list[dict] = []
    for item in data:
        row = dict(item) if isinstance(item, dict) else {"title": str(item)}
        row.setdefault("source", source)
        out.append(row)
    return out


# ---------------- composition: one call a backend sweep can act on ----------------


def plan_ingest(feed, *, source: str = "rss", existing: list[dict] | None = None,
                now: datetime | None = None, max_age_days: int = 60,
                stale_seen_days: int = 30, default_company: str | None = None) -> dict:
    """Compose parse -> normalize -> dedupe -> freshness into one actionable plan.

    ``feed`` is either raw RSS/Atom XML (a ``str``) or an already-parsed list of raw
    postings. ``existing`` is the corpus already in ``jobs``. ``default_company`` is
    the company a board's rows belong to, for the sources whose payload never names
    it. The result is the three writes a backend sweep needs -- ``create`` (new),
    ``update`` (already known, carry the ``existingId`` so the row is refreshed),
    ``close`` (known, expired, and *not* re-seen this batch) -- plus the within-batch
    duplicates, never written twice.

    Pure and deterministic, and honest about its limits: a close is only proposed for a
    row that is expired *and* absent from this batch, so a still-live posting is never
    closed just because it did not reappear today.
    """
    if feed is None:
        raw = []
    elif isinstance(feed, str):
        # The same detection the parse route uses, so a plan over a
        # board-API payload is not a plan over a broken XML document.
        raw = parse_any(feed, source=source)
    elif isinstance(feed, (list, tuple)):
        # ignore non-dict entries rather than letting one bad row abort the whole sweep
        raw = [r for r in feed if isinstance(r, dict)]
    else:
        raise raise_refusal(INGEST_FORMAT_UNKNOWN)
    normalized = [normalize_posting(r, source=source, default_company=default_company)
                  for r in raw]
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
