-- Epic 123/126 -- "the plate is warm before the request arrives".
--
-- A backend that boots cold pays its first queries at every page: the planner's
-- histogram statistics are as stale as the last autovacuum, and the composite
-- indexes Epics 121 and 126 added are on disk, not in shared buffers. This
-- script warms both, idempotently, in about the time of a handful of scans of
-- the hot indexes (tens of MB, not the tables).
--
-- Run as the database owner against the target database:
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/prewarm-hot.sql
--
-- Section A (ANALYZE) refreshes the planner's statistics for the hot
-- user-scoped relations; it needs only table ownership and is always safe.
--
-- Section B (pg_prewarm) loads the hot composite indexes into shared buffers so
-- the first reads do not stall on random disk I/O. pg_prewarm is a trusted
-- extension in PostgreSQL 13+, so a database owner may install it; on a
-- managed service where the extension is unavailable, comment out Section B and
-- keep Section A. Never run this in the middle of a migration.
--
-- The relations/indexes below are exactly the composites the hot-path migrations
-- create (V36__search_lookup_indexes.sql, V37__matches_digest_indexes.sql); a
-- contract test (ai-service/tests/test_the_prewarm_script_covers_the_composite_indexes.py)
-- fails when this script and those migrations drift apart.

-- ---------------- Section A -- statistics the planner uses ----------------
ANALYZE resumes;
ANALYZE user_notes;
ANALYZE conversations;
ANALYZE applications;
ANALYZE application_letters;
ANALYZE job_matches;

-- ---------------- Section B -- buffers the reader uses ----------------
CREATE EXTENSION IF NOT EXISTS pg_prewarm;
SELECT pg_prewarm('idx_resumes_user_updated') AS resumes_blocks;
SELECT pg_prewarm('idx_notes_user_updated') AS notes_blocks;
SELECT pg_prewarm('idx_conversations_user_updated') AS conversations_blocks;
SELECT pg_prewarm('idx_applications_user_updated') AS applications_blocks;
SELECT pg_prewarm('idx_application_letters_user_updated') AS application_letters_blocks;
SELECT pg_prewarm('idx_match_job_user_created') AS matches_latest_blocks;
SELECT pg_prewarm('idx_matches_user_job_created') AS matches_digest_blocks;
