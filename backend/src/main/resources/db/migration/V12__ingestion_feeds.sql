-- A feed is a job source the user subscribed to, swept on the backend's clock instead
-- of being pasted each morning (roadmap 19.2). The URL is user input fetched by the
-- server, so the fetcher refuses non-HTTP schemes and private/loopback addresses; the
-- source is the label its postings carry (the parser still detects XML vs JSON from the
-- body, so a wrong label cannot change how the feed is read).
CREATE TABLE ingestion_feeds (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name        VARCHAR(120) NOT NULL,
    url         VARCHAR(2048) NOT NULL,
    source      VARCHAR(40) NOT NULL DEFAULT 'feed',
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ingestion_feeds_name_not_blank CHECK (length(btrim(name)) > 0),
    CONSTRAINT ingestion_feeds_url_not_blank CHECK (length(btrim(url)) > 0)
);

-- The only read the feature has: one user's feeds, newest first.
CREATE INDEX idx_ingestion_feeds_user_created ON ingestion_feeds (user_id, created_at DESC);
-- The nightly sweep's read: every enabled feed, across users, oldest first.
CREATE INDEX idx_ingestion_feeds_enabled ON ingestion_feeds (created_at ASC) WHERE enabled;

-- One pull of one feed -- completed with the plan the engine proposed, or failed with
-- the sentence that says why. A failed pull is a row here rather than a silent night:
-- the row is written when the pull ends, so there is no `running` status to go stale
-- if the process dies mid-fetch.
CREATE TABLE ingestion_runs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    feed_id     UUID NOT NULL REFERENCES ingestion_feeds (id) ON DELETE CASCADE,
    status      VARCHAR(20) NOT NULL,
    error       TEXT,
    plan        JSONB,
    counts      JSONB,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    CONSTRAINT ingestion_runs_status_known CHECK (status IN ('completed', 'failed'))
);

-- The run list is scoped to the caller; the per-feed badge is the newest run of one feed.
CREATE INDEX idx_ingestion_runs_user_started ON ingestion_runs (user_id, started_at DESC);
CREATE INDEX idx_ingestion_runs_feed_started ON ingestion_runs (feed_id, started_at DESC);
