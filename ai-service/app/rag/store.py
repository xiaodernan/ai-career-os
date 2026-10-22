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
        args.append(db.like_contains(f'"{skill}"'))
        # The cast must wrap the -> result: `c.meta->'skills'::text` parses as
        # c.meta -> ('skills'::text) and leaves jsonb on the left of LIKE, which
        # Postgres rejects (operator does not exist: jsonb ~~ unknown). The quotes are
        # JSON syntax, so the skill name still needs its own wildcards neutralised
        # ("ci_cd" must not select a chunk tagged "ci/cd").
        where.append(f"(c.meta->'skills')::text LIKE ${len(args)} ESCAPE '!'")
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


async def get_chunks(chunk_ids: list[str], user_id: str) -> list[dict]:
    """Fetch chunks by id for the given viewer.

    ``user_id`` is required, not optional: callers hand this a list of ids taken straight
    from a request body, so the tenant predicate is the only thing keeping an enumerating
    caller out of other users' documents. A default of None used to compile the filter
    away (``$2 IS NULL OR ...``) and return the row.
    """
    rows = await db.fetch(
        """SELECT c.id, c.document_id, c.user_id, c.text, c.section_path, c.meta,
                  d.title AS doc_title
           FROM document_chunks c JOIN documents d ON d.id = c.document_id
           WHERE c.id = ANY($1::uuid[]) AND c.user_id = $2::uuid""",
        chunk_ids, user_id)
    return [dict(r) for r in rows]


def _chunk_id(item: Any) -> str | None:
    """The chunk id regardless of whether the row is a dict or a DB Record.

    `db.fetch` returns asyncpg Records, which support ``item["id"]``; cached or
    hand-built rows are dicts. A malformed (non-dict, non-record, None) entry has
    no id and is skipped rather than raising ``TypeError``/``KeyError`` mid-fusion.
    """
    if isinstance(item, dict):
        cid = item.get("id")
    else:
        cid = getattr(item, "id", None)
    return str(cid) if cid is not None else None


def rrf_merge(lists: list[list[dict]] | None, k: int = 60, cap: int = 40) -> list[dict]:
    """Reciprocal Rank Fusion across result lists keyed by chunk id."""
    scores: dict[str, float] = {}
    keep: dict[str, dict] = {}
    # `None` (or any non-list) here means "no retrieval ran" -- fuse to empty
    # rather than raising on iteration. A real provider/peer handing a wrong shape
    # must degrade to "no evidence", never crash the answer path.
    for lst in (lists or []):
        for rank, item in enumerate(lst):
            cid = _chunk_id(item)
            if cid is None:
                continue
            scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
            keep.setdefault(cid, item)
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:cap]
    out = []
    for cid, sc in ordered:
        item = keep[cid]
        # A real asyncpg Record converts via dict(); a hostile non-record,
        # non-dict entry degrades to a minimal {id} row instead of raising on the
        # dict() call -- it still carries the fusion score so ranking is intact.
        try:
            item = dict(item)
        except (TypeError, ValueError):
            item = {"id": cid}
        item["rrf"] = sc
        out.append(item)
    return out
