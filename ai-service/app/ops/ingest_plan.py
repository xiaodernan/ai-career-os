"""Ingest-plan CLI (forward Epic 14, offline).

``python -m app.ops.ingest_plan feed.xml`` (or ``feed.json``) reads a job feed from a
file, parses it, and prints the sweep plan the backend would run -- ``create`` /
``update`` / ``close`` plus within-batch duplicates -- **without touching a database**.
It is the operator-facing companion to :mod:`app.ops.restore_plan`: dry-run the write
before it happens.

Format is auto-detected (XML -> RSS/Atom, JSON -> board API) and can be forced with
``--format``. ``--existing corpus.json`` diffs against a current corpus (an array of
postings, or an object wrapping one) so already-known postings plan as ``update`` and
expired, absent ones plan as ``close``. ``--now`` pins the clock so a dry run is
reproducible.

Exit codes: ``0`` a plan was produced; ``2`` the file is missing, the feed is malformed,
or an option is invalid (the message says which).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from app.features import ingestion


def detect_format(text: str) -> str:
    """``board`` for a JSON payload, ``rss`` otherwise (XML feeds)."""
    return "board" if text.lstrip()[:1] in ("[", "{") else "rss"


def parse_feed_text(text: str, fmt: str = "auto") -> list[dict]:
    fmt = (fmt or "auto").lower()
    if fmt == "auto":
        fmt = detect_format(text)
    if fmt == "board":
        return ingestion.parse_json_board(text, source="board")
    if fmt == "rss":
        return ingestion.parse_feed(text, source="rss")
    raise ValueError(f"unknown format {fmt!r} (expected auto, rss, board)")


def _parse_now(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(f"--now is not an ISO datetime: {value!r}") from e


def build_plan(text: str, *, fmt: str = "auto", existing: list[dict] | None = None,
               now: datetime | None = None, max_age_days: int = 60,
               stale_seen_days: int = 30) -> dict:
    """Parse ``text`` then plan the ingest (pure; no I/O)."""
    postings = parse_feed_text(text, fmt)
    source = "board" if (fmt == "board" or (fmt == "auto" and detect_format(text) == "board")) else "rss"
    return ingestion.plan_ingest(
        postings, source=source, existing=existing, now=now,
        max_age_days=max_age_days, stale_seen_days=stale_seen_days)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="app.ops.ingest_plan",
        description="Print the create/update/close plan for a job feed (dry run).")
    p.add_argument("feed", help="path to an RSS/Atom XML or board-API JSON feed")
    p.add_argument("--format", choices=["auto", "rss", "board"], default="auto")
    p.add_argument("--existing", default=None,
                   help="optional current corpus JSON (array, or an object wrapping one)")
    p.add_argument("--now", default=None, help="ISO datetime to pin the freshness clock")
    p.add_argument("--max-age-days", type=int, default=60)
    p.add_argument("--stale-seen-days", type=int, default=30)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        with open(args.feed, encoding="utf-8") as fh:
            text = fh.read()
        existing = None
        if args.existing:
            with open(args.existing, encoding="utf-8") as fh:
                existing = ingestion.parse_json_board(fh.read(), source="existing")
        plan = build_plan(text, fmt=args.format, existing=existing,
                          now=_parse_now(args.now),
                          max_age_days=args.max_age_days,
                          stale_seen_days=args.stale_seen_days)
    except (OSError, ValueError) as e:
        print(f"ingest-plan: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    c = plan.get("counts", {})
    print(f"ingest-plan: {c.get('create', 0)} create, {c.get('update', 0)} update, "
          f"{c.get('close', 0)} close, {c.get('duplicates', 0)} duplicate(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
