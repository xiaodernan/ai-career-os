"""Vector ANN indexes, created lazily against the live dimension (forward §36).

The ``embedding`` columns are deliberately dimension-less in V1: the deployment picks
its provider (OpenAI's 1536, Ollama's 768, ...), and a ``vector(1536)`` column would
refuse a legal 768-dimension provider before a single row existed. The cost of that
freedom is that pgvector refuses an HNSW index on a column with no declared dimension,
so the index cannot ship in a migration either — it can only be created once the
deployment has actually chosen its dimension and inserted vectors.

This module is that deferred step, as a pure decision over a rows-and-dimensions
snapshot so it is unit-testable offline: read the distinct vector dimension actually
present per table, and either

* one dimension, rows exist  -> ``ALTER TYPE vector(n)`` + ``CREATE INDEX ... hnsw``,
* no rows yet                -> report "nothing to index yet" (exit 0; rerun after the
  first ingestion),
* mixed dimensions           -> report the conflict (exit 1; a provider switch mid-life
  without a re-embed is exactly the drift this must not paper over),
* index already present      -> report it and skip (idempotent, safe to schedule).

``python -m app.ops.vector_index`` runs it against the live database. The SQL is
executed through a single injected ``runner(sql) -> None`` / ``fetcher(sql) -> rows``
pair, so the unit tests never touch a database.
"""

from __future__ import annotations

from dataclasses import dataclass

TABLES = {
    # table -> the queries that scan it by cosine distance (the readers this index serves).
    "document_chunks": "ai-service app/rag/store.py -- the retriever's cosine scan",
    "jobs": "JobSearchRepository -- the hybrid job board's vector pass",
    "job_jds": "the JD vector pass on pasted postings",
}


@dataclass(frozen=True)
class Outcome:
    ok: bool
    detail: str


def plan(dimensions: dict[str, set[int]], existing: dict[str, set[str]]) -> list[tuple[str, Outcome]]:
    """The per-table decision, pure: dimensions seen, index names already present."""
    out: list[tuple[str, Outcome]] = []
    for table in TABLES:
        if table in existing and any(
            name.startswith(f"idx_{table}_embedding") for name in existing.get(table, set())
        ):
            out.append((table, Outcome(True, "HNSW index already present; nothing to do")))
            continue
        dims = dimensions.get(table, set())
        if not dims:
            out.append((table, Outcome(True, "no vectors yet; rerun after the first ingestion")))
            continue
        if len(dims) > 1:
            out.append((table, Outcome(False, f"mixed dimensions {sorted(dims)}: re-embed before indexing")))
            continue
        # Copy before reading: dims is the caller's live set, and a pop here would empty
        # it behind their back -- the run loop reads it again to expand the DDL.
        n = next(iter(dims))
        out.append((table, Outcome(True, f"declare vector({n}) + HNSW (cosine)")))
    return out


def statements(table: str, dimension: int) -> list[str]:
    """The DDL one table's decision expands to: fix the type, then index it."""
    return [
        f"ALTER TABLE {table} ALTER COLUMN embedding TYPE vector({dimension})",
        f"CREATE INDEX idx_{table}_embedding ON {table} "
        f"USING hnsw (embedding vector_cosine_ops)",
    ]


async def run(fetch, execute) -> int:
    """Against the live database (``app.core.db.fetch`` / ``.execute``). Exit code only."""
    dims: dict[str, set[int]] = {}
    existing: dict[str, set[str]] = {}
    for table in TABLES:
        rows = await fetch(
            f"SELECT vector_dims(embedding) AS d FROM {table} "
            f"WHERE embedding IS NOT NULL GROUP BY 1"
        )
        dims[table] = {int(r["d"]) for r in rows}
        existing[table] = {
            r["indexname"]
            for r in await fetch(
                "SELECT indexname FROM pg_indexes WHERE tablename = $1", table
            )
        }

    failed = False
    for table, outcome in plan(dims, existing):
        print(f"{table}: {outcome.detail}")
        if not outcome.ok:
            failed = True
            continue
        if outcome.detail.startswith(("no vectors", "HNSW index")):
            continue
        dim = next(iter(dims.get(table, set())))
        for sql in statements(table, dim):
            print(f"  {sql}")
            await execute(sql)
    return 1 if failed else 0


async def main() -> int:
    from app.core import db

    return await run(db.fetch, db.execute)


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
