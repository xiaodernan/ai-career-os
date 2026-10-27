"""Ingest the eval corpus through the shipped ingest path.

``python -m app.ops.seed_eval_corpus --user-id <uuid> --corpus ../scripts/eval-corpus.json``
registers the golden document for the eval user and runs the pipeline the
``/internal/ingest/text`` endpoint runs -- this script CALLS that handler instead of
re-writing its registration steps, so what the nightly ingests is byte-for-byte what
the product ingests. The eval user is this script's own persona: no backend boots in
the nightly, so nobody registers the account both harnesses FK against, and the
script creates it (no known password, so it authenticates against nothing). It then
polls documents.status until ``ready``: an eval run against a corpus that never
landed reads ``0 of N cases scored -- nothing was measured`` (the runner refuses
that, but only after the run); this step catches the absence where it happens.

The corpus file carries kind=resume because the golden set's cases filter
kinds=["resume"] -- a note-kind ingest lands chunks the eval is scoped out of.

Exit codes: ``0`` the document is ready; ``1`` the ingest failed or did not finish
in time; ``2`` the CLI/file contract is broken (missing or malformed corpus file,
or the ingest refused the payload, e.g. blank text).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import asyncpg
from fastapi import HTTPException

from app.core import db
from app.db import documents as docs_repo

POLL_INTERVAL_S = 0.5


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="seed-eval-corpus",
        description="Ingest the eval corpus for a user through the shipped ingest path.")
    p.add_argument("--user-id", required=True, help="the user the corpus belongs to (uuid)")
    p.add_argument("--corpus", required=True, help="path to the corpus JSON ({kind,title,text})")
    p.add_argument("--timeout", type=float, default=90.0,
                   help="seconds to wait for the document to reach ready")
    return p


async def _ensure_eval_user(user_id: str) -> bool:
    """Create the synthetic eval account when it does not exist, return whether it was.

    The eval user is a persona this script owns: no backend boots in the nightly,
    so nobody registers it, and both harnesses FK against users. The password is a
    fresh random uuid, hashed by pgcrypto's bcrypt and discarded -- a valid digest
    of a secret nobody has ever known, so the account authenticates against nothing.
    """
    created = await db.fetchrow(
        """INSERT INTO users (id, email, password_hash, display_name)
           VALUES ($1::uuid, $2, crypt(gen_random_uuid()::text, gen_salt('bf', 10)),
                   'Eval Corpus')
           ON CONFLICT (id) DO NOTHING
           RETURNING id""",
        user_id, f"eval-{user_id}@careeros.local")
    return created is not None


async def seed(user_id: str, corpus_path: str, timeout: float) -> int:
    # Imported here so the CLI contract errors (exit 2) do not require a database
    # to be reachable: only the ingest path does.
    from app.api.ingest import ingest_text
    from app.core.deps import Ctx

    raw = Path(corpus_path).read_text(encoding="utf-8")
    body = json.loads(raw)
    text = (body.get("text") or "").strip()
    if not text:
        print("seed-eval-corpus: the corpus file carries no text", file=sys.stderr)
        return 2

    await db.init_db()
    try:
        try:
            # A second copy of the same document would not fail anything: ground
            # truth is a set, but the duplicate chunk eats a top_k slot and quietly
            # degrades the measured metrics. One ready copy per exact text.
            same = await db.fetchrow(
                """SELECT d.id FROM documents d
                   WHERE d.user_id=$1::uuid AND d.content_hash=$2 AND d.status='ready'""",
                user_id, docs_repo.sha256(text.encode()))
            if same:
                print(f"seed-eval-corpus: the corpus is already seeded ({same['id']})")
                return 0
            if await _ensure_eval_user(user_id):
                print(f"seed-eval-corpus: created the eval user {user_id}")
            result = await ingest_text(
                {"kind": body.get("kind", "resume"), "title": body.get("title", "Untitled"),
                 "text": text},
                Ctx(user_id=user_id))
        except HTTPException as e:
            detail = e.detail
            print(f"seed-eval-corpus: the ingest refused the payload: {detail}", file=sys.stderr)
            return 2
        except asyncpg.PostgresError as e:
            print(f"seed-eval-corpus: the database refused the ingest: "
                  f"{type(e).__name__}: {e}", file=sys.stderr)
            return 1
        doc_id = result["document_id"]

        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            doc = await docs_repo.get_document(doc_id)
            if doc and doc.get("status") == "ready":
                print(f"seed-eval-corpus: document {doc_id} is ready "
                      f"(source {result.get('source_id')}, provider {result.get('embedding_provider')})")
                return 0
            if doc and doc.get("status") == "failed":
                print(f"seed-eval-corpus: the ingest failed: {doc.get('error')}", file=sys.stderr)
                return 1
            if asyncio.get_event_loop().time() >= deadline:
                status = (doc or {}).get("status") or "missing"
                print(f"seed-eval-corpus: the document did not reach ready within {timeout}s "
                      f"(last status: {status})", file=sys.stderr)
                return 1
            await asyncio.sleep(POLL_INTERVAL_S)
    finally:
        await db.close_db()


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as e:
        return int(e.code or 2)
    try:
        return asyncio.run(seed(args.user_id, args.corpus, args.timeout))
    except (OSError, json.JSONDecodeError) as e:
        print(f"seed-eval-corpus: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
