"""Embed seeded/imported jobs so vector job search works (PRD §4.1 remainder).

    cd ai-service && python -m app.ops.embed_jobs [--limit 200] [--force] [--dry-run]

Why this exists
---------------
Ingestion embeds `document_chunks` (resumes, notes, JDs), but nothing embedded
`jobs` — the seed data deliberately ships `jobs.embedding = NULL`, so the vector
half of job retrieval had no vectors to search and only keyword/skill search
worked. This fills that gap, idempotently: by default it only touches rows whose
embedding is still NULL, so it is safe to re-run after new jobs land.

Order of operations matters: run this *before* `ops/vector_index.sql`. That script
types the column and builds the HNSW index, which is only worth doing once real
vectors exist. Re-running it after switching embedding providers requires
re-embedding with `--force`.

Offline note: with `EMBEDDING_PROVIDER=hash` the vectors are deterministic
pseudo-embeddings. They exercise the whole path (dimension, cast, index) but carry
no semantics, so retrieval quality is meaningless — point it at a real provider
for that, exactly like the RAG eval.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Mapping
from typing import Any

from app.core import db
from app.core.config import get_settings

log = logging.getLogger("ops.embed_jobs")

# Kept in one place so the CLI, the report and the tests agree on the batch size.
DEFAULT_BATCH = 64

# How often the service sweeps up jobs that landed without a vector. Polling rather
# than a trigger because every writer -- the backend's create/import routes and the
# agent's own inserts alike -- writes this one table, and only the table sees them all.
EMBED_LOOP_INTERVAL = 60.0


def _clean(value: Any) -> str:
    """Flatten a scalar-or-array column into one line of text."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    return str(value).strip()


def job_embedding_text(job: Mapping[str, Any]) -> str:
    """Build the text that represents a job to the embedding model.

    Labelled sections rather than a raw concatenation: a bare join of "Beijing",
    "Java", "Remote" gives the model no way to tell a location from a skill. The
    labels are the same vocabulary the JD parser emits, so a job vector and a
    resume chunk land in comparable regions of the space.

    Company, salary and posting age are deliberately excluded — they are filters,
    not semantics, and including them makes similar roles at different employers
    look unrelated.
    """
    sections: list[tuple[str, str]] = [
        ("Title", _clean(job.get("title"))),
        ("Location", _clean(job.get("location"))),
        ("Work type", " ".join(
            p for p in (_clean(job.get("remote_type")), _clean(job.get("employment_type"))) if p
        )),
        ("Skills", _clean(job.get("skills"))),
        ("Description", _clean(job.get("description"))),
        ("Requirements", _clean(job.get("requirements"))),
        ("Nice to have", _clean(job.get("nice_to_have"))),
        ("Responsibilities", _clean(job.get("responsibilities"))),
    ]
    return "\n".join(f"{label}: {text}" for label, text in sections if text)


async def _pending_jobs(limit: int | None, force: bool) -> list[Mapping[str, Any]]:
    where = "" if force else "WHERE j.embedding IS NULL"
    tail = "" if limit is None else "LIMIT $1"
    sql = f"""
        SELECT j.id, j.title, j.location, j.remote_type, j.employment_type,
               j.description, j.requirements, j.nice_to_have, j.responsibilities, j.skills
        FROM jobs j
        {where}
        ORDER BY j.posted_at DESC NULLS LAST
        {tail}
    """
    args = () if limit is None else (limit,)
    return await db.fetch(sql, *args)


async def embed_jobs(limit: int | None = None, force: bool = False, batch: int = DEFAULT_BATCH,
                     dry_run: bool = False) -> dict[str, Any]:
    """Embed every job that needs it. Returns a summary dict (also used by tests)."""
    settings = get_settings()
    jobs = await _pending_jobs(limit, force)
    report: dict[str, Any] = {
        "provider": settings.embedding_provider,
        "candidates": len(jobs),
        "embedded": 0,
        "skipped_empty": 0,
        "dim": None,
        "dry_run": dry_run,
    }
    if not jobs:
        return report

    # Jobs with no usable text would embed to a vector of noise; skip and count them.
    usable: list[tuple[str, str]] = []
    for job in jobs:
        text = job_embedding_text(job)
        if not text:
            report["skipped_empty"] += 1
            continue
        usable.append((str(job["id"]), text))

    if dry_run or not usable:
        report["candidates"] = len(usable)
        return report

    from app.providers.registry import get_embeddings

    embedder = get_embeddings(settings)
    for i in range(0, len(usable), batch):
        window = usable[i:i + batch]
        vectors = await embedder.embed([text for _, text in window])
        if len(vectors) != len(window):
            raise RuntimeError(
                f"embedding provider returned {len(vectors)} vectors for {len(window)} texts")
        for (job_id, _), vector in zip(window, vectors):
            if report["dim"] is None:
                report["dim"] = len(vector)
            elif len(vector) != report["dim"]:
                raise RuntimeError(
                    f"inconsistent embedding dim: {len(vector)} != {report['dim']}")
            await db.execute("UPDATE jobs SET embedding = $2::vector WHERE id = $1::uuid",
                             job_id, db.vec(vector))
            report["embedded"] += 1

    report["candidates"] = len(usable)
    return report


async def embed_loop(interval: float = EMBED_LOOP_INTERVAL,
                     stop: asyncio.Event | None = None) -> None:
    """Keep `jobs.embedding` fresh while the service runs.

    A role created after the backfill used to stay invisible to vector recall until
    someone re-ran the CLI, which is exactly the state this whole module was written
    to end: so the first pass runs immediately (it *is* the startup backfill) and
    repeats every `interval` seconds, touching only rows whose embedding is still
    NULL. A pass that fails -- provider unset, provider down, a column typed by a
    different provider -- is logged and retried on the next tick: a stuck embedder
    costs recall, it must never take the service down. `stop` lets a test end the
    loop cleanly; in the app it runs until the task is cancelled at shutdown.
    """
    while True:
        try:
            await embed_jobs()
        except Exception:
            log.warning("job embedding pass failed; retrying in %ss", interval, exc_info=True)
        if stop is None:
            await asyncio.sleep(interval)
            continue
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
        return


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Embed jobs that have no vector yet.")
    p.add_argument("--limit", type=int, default=None, help="max jobs to process")
    p.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="embedding batch size")
    p.add_argument("--force", action="store_true", help="re-embed even rows that already have one")
    p.add_argument("--dry-run", action="store_true", help="report what would be embedded, write nothing")
    return p.parse_args(argv)


async def _main(args: argparse.Namespace) -> int:
    await db.init_db()
    try:
        report = await embed_jobs(limit=args.limit, force=args.force, batch=args.batch,
                                  dry_run=args.dry_run)
    finally:
        await db.close_db()

    print(f"provider      : {report['provider']}")
    print(f"candidates    : {report['candidates']}")
    print(f"embedded      : {report['embedded']}")
    print(f"skipped empty : {report['skipped_empty']}")
    print(f"dimension     : {report['dim']}")
    if report["dry_run"]:
        print("(dry run — nothing written)")
    elif report["embedded"]:
        print("\nNext: apply the vector index, then vector job search is live:")
        print("  psql -v dim=<dimension> -f ops/vector_index.sql")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(_parse_args())))
