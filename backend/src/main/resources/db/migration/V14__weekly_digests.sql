-- The week's letter (roadmap 19.4): the 15.3 digest composed on the backend's clock and kept,
-- so a week's signals do not require opening the app on the day they were true.
--
-- One row per user per week. The payload is the engine's answer stored as it came back -- the
-- totals, the stage mix, the rates, the stalled rows and the engine's own signals -- so the
-- letter reads the same after the week ends, and an email can be assembled from it without
-- asking the engine again. Re-composing the same week refreshes this row rather than appending
-- a second one: a letter is the week as it stands, not a log of attempts.
CREATE TABLE weekly_digests (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    week_start   DATE NOT NULL,
    window_days  SMALLINT NOT NULL,
    payload      JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT weekly_digests_week_is_monday CHECK (EXTRACT(ISODOW FROM week_start) = 1),
    CONSTRAINT weekly_digests_window_positive CHECK (window_days > 0),
    UNIQUE (user_id, week_start)
);

-- No second index: the unique key's (user_id, week_start) prefix answers the one read -- a
-- user's newest letters -- in reverse.
