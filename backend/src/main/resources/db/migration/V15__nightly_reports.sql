-- Queryable history for the nightly verification run (roadmap 20.1). The nightly job's
-- backend-IT, eval-harness and export-check results used to end with the runner: the logs
-- expire with the workflow and the eval reports land in a git-ignored directory, so
-- "did last Tuesday's night pass, and what did the RAG eval score?" had no answer after the
-- fact. One row per night, written by the night itself through the backend's internal token,
-- read back by the monitoring page.
--
-- `summary` is the job's own account of its steps -- names, statuses and the few numbers each
-- step measured -- stored as it arrived rather than flattened into columns that the next
-- harness change would invalidate. The spine (when, which commit, did it pass) is typed,
-- because that is what the page sorts and colors by.
CREATE TABLE nightly_reports (
    id          UUID PRIMARY KEY,
    source      VARCHAR(40)  NOT NULL DEFAULT 'nightly',
    status      VARCHAR(20)  NOT NULL,
    commit_sha  VARCHAR(64),
    run_url     VARCHAR(512),
    started_at  TIMESTAMPTZ  NOT NULL,
    finished_at TIMESTAMPTZ  NOT NULL,
    summary     JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT nightly_reports_status_ck CHECK (status IN ('passed', 'failed')),
    CONSTRAINT nightly_reports_span_ck CHECK (finished_at >= started_at)
);

-- The only read is "newest first"; `id` is the tiebreak because a manual dispatch can start
-- in the same second as the scheduled run, and the same page must answer the same order.
CREATE INDEX idx_nightly_reports_started ON nightly_reports (started_at DESC, id DESC);
