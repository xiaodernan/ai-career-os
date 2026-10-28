-- A saved search is the question the board was asked, kept under a name -- what an
-- alert is about (roadmap 19.1). The criteria are the board's own filter names in
-- one jsonb object, written by the service as a canonical map (blank keys absent),
-- so the nightly sweep (19.2) and the alert matcher (19.3) read one shape rather
-- than each remembering which synonyms the browser used.
CREATE TABLE saved_searches (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name        VARCHAR(80) NOT NULL,
    criteria    JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT saved_searches_name_not_blank CHECK (length(btrim(name)) > 0)
);

-- The only read the feature has: one user's saved searches, newest first.
CREATE INDEX idx_saved_searches_user_created ON saved_searches (user_id, created_at DESC);
