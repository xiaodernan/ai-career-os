"""Repository for documents & chunks (the evidence layer)."""

import hashlib

from app.core import db


async def get_document(doc_id: str) -> dict | None:
    row = await db.fetchrow("SELECT * FROM documents WHERE id=$1::uuid", doc_id)
    return dict(row) if row else None


async def create_document(user_id: str, source_id: str | None, file_key: str | None,
                          media_type: str, title: str, content_hash: str,
                          meta: dict, text_excerpt: str = "") -> str:
    row = await db.fetchrow(
        """INSERT INTO documents(user_id, source_id, file_key, media_type, title,
               content_hash, text_excerpt, meta)
           VALUES ($1::uuid,$2::uuid,$3,$4,$5,$6,$7,$8::jsonb) RETURNING id""",
        user_id, source_id, file_key, media_type, title, content_hash, text_excerpt[:2000],
        db.jsonb(meta))
    return str(row["id"])


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def set_status(doc_id: str, status: str, error: str | None = None,
                     text_excerpt: str | None = None) -> None:
    if text_excerpt is not None:
        await db.execute(
            "UPDATE documents SET status=$2, error=$3, text_excerpt=$4 WHERE id=$1::uuid",
            doc_id, status, error, text_excerpt[:2000])
    else:
        await db.execute("UPDATE documents SET status=$2, error=$3 WHERE id=$1::uuid",
                         doc_id, status, error)


async def replace_chunks(doc_id: str, user_id: str, chunks: list[dict]) -> int:
    await db.execute("DELETE FROM document_chunks WHERE document_id=$1::uuid", doc_id)
    if not chunks:
        return 0
    async with db.get_pool().acquire() as conn:
        await conn.executemany(
            """INSERT INTO document_chunks(id, document_id, user_id, ordinal, text, token_count,
                   section_path, kind, meta, embedding)
               VALUES (gen_random_uuid(), $1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8::jsonb,
                       $9::vector)""",
            [(doc_id, user_id, c["ordinal"], c["text"], c["token_count"], c["section_path"],
              c["kind"], db.jsonb(c.get("meta", {})), db.vec(c["embedding"]))
             for c in chunks])
    return len(chunks)


async def mark_source_ready(source_id: str | None, doc_id: str) -> None:
    if not source_id:
        return
    await db.execute(
        """UPDATE knowledge_sources SET status='ready', document_id=$2::uuid, error=NULL
           WHERE id=$1::uuid""", source_id, doc_id)


async def mark_source_failed(source_id: str | None, error: str) -> None:
    if not source_id:
        return
    await db.execute("UPDATE knowledge_sources SET status='failed', error=$2 WHERE id=$1::uuid",
                     source_id, error[:1000])
