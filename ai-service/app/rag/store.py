"""Retrieval primitives over document_chunks (vector, FTS, metadata-filtered)."""

from typing import Any

from app.core import db


def _apply_scoping(where: list[str], args: list[Any], kinds: list[str] | None,
                   document_ids: list[str] | None) -> None:
    """Append the metadata restrictions to a channel's WHERE/args.

    Every retrieval channel must call this: RRF scores each list by rank alone, so one
    unfiltered channel injects out-of-scope chunks that outrank the tail of the
    filtered ones and get quoted as evidence.
    """
    if kinds:
        args.append(kinds)
        where.append(f"ks.kind = ANY(${len(args)}::text[])")
    if document_ids:
        args.append(document_ids)
        where.append(f"c.document_id = ANY(${len(args)}::uuid[])")


async def vector_search(user_id: str, query_vec: list[float], k: int = 25,
                        kinds: list[str] | None = None,
                        document_ids: list[str] | None = None,
                        skill: str | None = None) -> list[dict]:
    where = ["c.user_id = $2::uuid", "d.status = 'ready'"]
    args: list[Any] = [db.vec(query_vec), user_id]
    _apply_scoping(where, args, kinds, document_ids)
    if skill:
        args.append(f"%\"{skill}\"%")
        # The cast must wrap the -> result: `c.meta->'skills'::text` parses as
        # c.meta -> ('skills'::text) and leaves jsonb on the left of LIKE, which
        # Postgres rejects (operator does not exist: jsonb ~~ unknown).
        where.append(f"(c.meta->'skills')::text LIKE ${len(args)}")
    sql = f"""
        SELECT c.id, c.document_id, c.text, c.section_path, c.kind, c.meta,
               d.title AS doc_title, d.id AS doc_id, ks.kind AS source_kind,
               1 - (c.embedding <=> $1::vector) AS score
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        LEFT JOIN knowledge_sources ks ON ks.document_id = d.id
        WHERE {" AND ".join(where)} AND c.embedding IS NOT NULL
        ORDER BY c.embedding <=> $1::vector
        LIMIT {int(k)}"""
    rows = await db.fetch(sql, *args)
    return [dict(r) for r in rows]


async def keyword_search(user_id: str, query: str, k: int = 25,
                         kinds: list[str] | None = None,
                         document_ids: list[str] | None = None) -> list[dict]:
    where = ["c.user_id = $2::uuid", "d.status = 'ready'",
             "c.tsv @@ plainto_tsquery('simple', $1)"]
    args: list[Any] = [query, user_id]
    _apply_scoping(where, args, kinds, document_ids)
    sql = f"""
        SELECT c.id, c.document_id, c.text, c.section_path, c.kind, c.meta,
               d.title AS doc_title, d.id AS doc_id, ks.kind AS source_kind,
               ts_rank(c.tsv, plainto_tsquery('simple', $1)) AS score
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        LEFT JOIN knowledge_sources ks ON ks.document_id = d.id
        WHERE {" AND ".join(where)}
        ORDER BY score DESC
        LIMIT {int(k)}"""
    rows = await db.fetch(sql, *args)
    return [dict(r) for r in rows]


async def trigram_search(user_id: str, query: str, k: int = 15,
                         kinds: list[str] | None = None,
                         document_ids: list[str] | None = None) -> list[dict]:
    """Catch misspellings / rare exact tokens via pg_trgm on chunk text."""
    where = ["c.user_id = $1::uuid", "d.status='ready'",
             "similarity(c.text, $2) > 0.15"]
    args: list[Any] = [user_id, query]
    _apply_scoping(where, args, kinds, document_ids)
    rows = await db.fetch(
        f"""SELECT c.id, c.document_id, c.text, c.section_path, c.kind, c.meta,
                   d.title AS doc_title, d.id AS doc_id, ks.kind AS source_kind,
                   similarity(c.text, $2) AS score
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            LEFT JOIN knowledge_sources ks ON ks.document_id = d.id
            WHERE {" AND ".join(where)}
            ORDER BY score DESC LIMIT {int(k)}""",
        *args)
    return [dict(r) for r in rows]


async def get_chunks(chunk_ids: list[str], user_id: str | None = None) -> list[dict]:
    rows = await db.fetch(
        """SELECT c.id, c.document_id, c.user_id, c.text, c.section_path, c.meta,
                  d.title AS doc_title
           FROM document_chunks c JOIN documents d ON d.id = c.document_id
           WHERE c.id = ANY($1::uuid[]) AND ($2::uuid IS NULL OR c.user_id = $2::uuid)""",
        chunk_ids, user_id)
    return [dict(r) for r in rows]


def rrf_merge(lists: list[list[dict]], k: int = 60, cap: int = 40) -> list[dict]:
    """Reciprocal Rank Fusion across result lists keyed by chunk id."""
    scores: dict[str, float] = {}
    keep: dict[str, dict] = {}
    for lst in lists:
        for rank, item in enumerate(lst):
            cid = str(item["id"])
            scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
            keep.setdefault(cid, item)
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:cap]
    out = []
    for cid, sc in ordered:
        item = dict(keep[cid])
        item["rrf"] = sc
        out.append(item)
    return out
