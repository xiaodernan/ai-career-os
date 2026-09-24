"""Operational jobs (PRD §4.1).

`embed_jobs` backfills `jobs.embedding` so vector job search has vectors to
search; the raw-SQL counterparts (`vector_index.sql`) live in `ai-service/ops/`.

    python -m app.ops.embed_jobs [--limit N] [--force] [--dry-run]
"""
