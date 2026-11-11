# Target-install verification: `EXPLAIN (ANALYZE, BUFFERS)` for the hot reads

**Status: pending, by environment.** The migrations that ship the hot composites (V36
`search_lookup_indexes`, V37 `matches_digest_indexes`) were applied and verified offline on
this host (Flyway naming gate, prewarm contract gate, `*IT`-free suite). What this host
cannot produce is a query plan against a populated production-like corpus — no Docker here,
and a plan from an empty database would prove nothing. This file is the runbook for the
first target install, and its output is the ledger entry that closes the last "not run
here" notes in `docs/plans/PERFORMANCE_HORIZON.md` (Epics 121, 126).

Do **not** paste plans into this file from a dev database with a seeded handful of rows:
the shape that matters is the `Index Scan` vs `Seq Scan` decision on a table with real
cardinality, plus the buffer hits for the five user-scoped reads.

## Preconditions

- A target install where Flyway has applied V36 and V37 (`SELECT version FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 2;` shows `V37` and `V36`).
- A database whose largest hot table has ≥ 100k rows (the point of the exercise; below that PG's planner is right to prefer a sequential scan).
- `psql` with read access to the query text the backend actually runs.

## The statements to measure

Settings recommendation (best-of-3 per statement, discard the first as cold):

```sql
\set ON_ERROR_STOP on
SET jit = off;            -- JIT noise in short plans; not what is being measured
```

### 1. The global-search reads (V36), one per surface

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT text)
SELECT id, title, status, updated_at
  FROM resumes
 WHERE user_id = '<a real user id>' AND title ILIKE '%spring%'
 ORDER BY updated_at DESC, id ASC
 LIMIT 20;

EXPLAIN (ANALYZE, BUFFERS, FORMAT text)
SELECT id, title, left(content, 180), updated_at
  FROM user_notes
 WHERE user_id = '<a real user id>' AND (title ILIKE '%spring%' OR content ILIKE '%spring%')
 ORDER BY updated_at DESC, id ASC
 LIMIT 20;

EXPLAIN (ANALYZE, BUFFERS, FORMAT text)
SELECT cv.id, cv.title, cv.updated_at
  FROM conversations cv
 WHERE cv.user_id = '<a real user id>'
   AND (cv.title ILIKE '%spring%' OR EXISTS (SELECT 1 FROM messages m
          WHERE m.conversation_id = cv.id AND m.content ILIKE '%spring%'))
 ORDER BY cv.updated_at DESC, cv.id ASC
 LIMIT 20;

EXPLAIN (ANALYZE, BUFFERS, FORMAT text)
SELECT id, title, company_name, status, updated_at
  FROM applications
 WHERE user_id = '<a real user id>'
   AND (title ILIKE '%spring%' OR COALESCE(company_name, '') ILIKE '%spring%')
 ORDER BY updated_at DESC, id ASC
 LIMIT 20;

EXPLAIN (ANALYZE, BUFFERS, FORMAT text)
SELECT l.id, l.application_id, l.updated_at
  FROM application_letters l
  JOIN applications a ON a.id = l.application_id
 WHERE l.user_id = '<a real user id>'
   AND (l.body ILIKE '%spring%' OR COALESCE(a.title, '') ILIKE '%spring%')
 ORDER BY l.updated_at DESC, l.id ASC
 LIMIT 20;
```

Expected shape per statement: one `Index Scan` (or `Index Only Scan`) on the composite
`idx_resumes_user_updated` / `idx_notes_user_updated` / `idx_conversations_user_updated` /
`idx_applications_user_updated` / `idx_application_letters_user_updated`, no external sort,
`Limit` node.

Note on the letters query: the ORDER BY column is `l.updated_at` with `l.id` as tiebreaker —
identical key order to the index.

### 2. The matches digest (V37)

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT text)
SELECT avg(latest.overall) FROM (
      SELECT DISTINCT ON (jm.job_id) jm.job_id, jm.overall
        FROM job_matches jm
       WHERE jm.user_id = '<a real user id>'
       ORDER BY jm.job_id, jm.created_at DESC, jm.id DESC
) latest;

EXPLAIN (ANALYZE, BUFFERS, FORMAT text)
SELECT jm.overall, jm.id, jm.created_at
  FROM job_matches jm
 WHERE jm.job_id = '<a real job id>' AND jm.user_id = '<a real user id>'
 ORDER BY jm.created_at DESC
 LIMIT 1;
```

Expected: the first plan is an `Index Scan` on `idx_matches_user_job_created` (index-ordered,
no `Sort` above the `Distinct`); the second a `Index Scan` on `idx_match_job_user_created`
with `Limit 1` and no sort.

### 3. The applications board and the needs-attention predicate (V36)

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT text)
SELECT count(*) FROM applications
 WHERE user_id = '<a real user id>'
   AND status NOT IN ('offer', 'rejected')
   AND (updated_at < now() - make_interval(days => 14)
        OR (reminder_at IS NOT NULL AND reminder_at <= now()));
```

Expected: `Index Scan` on `idx_applications_user_updated` for the `user_id` prefix. The
`updated_at <` predicate is a range scan inside the index once `user_id` is fixed.

## Recording the result

In the same commit that closes the ledger note, paste the three shapes into
`docs/plans/PERFORMANCE_HORIZON.md` beside the Epics 121 and 126 entries (plan node names only,
not buffer counts), and update the "target-install EXPLAIN remains the follow-up" sentences to
name the environment and date. If any statement shows a `Seq Scan` where an index scan was
expected, the honest entry is the plan that says so — plus whichever new index removes it,
as its own epic.

## What would invalidate this runbook

- The tables were `ANALYZE`d after migration but before testing (do this — the planner is only as honest as its histograms: `ANALYZE resumes, user_notes, conversations, applications, application_letters, job_matches;` — exactly what `scripts/prewarm-hot.sql` does).
- The user id picked was an empty account (zero rows proves nothing).
- The run happened against a replica with stale stats.
