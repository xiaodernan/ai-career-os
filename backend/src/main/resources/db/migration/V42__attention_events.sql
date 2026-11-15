-- Epic 267 — the attention spine: how the reader behaves, recorded.
--
-- The admin door answers how big the install is, who ever acted, where the readers fall,
-- which way the weeks trend — but nothing yet says where a reader *dwells*, which page
-- they skim, or which they left without a word. Those are the questions a real owner
-- asks about their own book before they rewrite it.
--
-- One row per recorded attention move — landed, read (kept the page open), acted. The
-- user id is optional: an unauthenticated landing still counts (anonymous reads), and
-- the only cross-row question is ever "of the people who landed, how many acted".
-- The column set is intentionally minimal: no fingerprint, no UA, no IP — the install
-- tracks its own behaviour, not the reader's identity beyond a nullable link.
CREATE TABLE attention_events (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NULL REFERENCES users(id) ON DELETE CASCADE,
    journey     varchar(64) NOT NULL,
    path        varchar(500) NOT NULL,
    event       varchar(32) NOT NULL,     -- land | dwell | act
    value       varchar(200) NULL,        -- e.g. the seconds read, the clicked tile
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_attention_user_time ON attention_events (user_id, created_at DESC);
CREATE INDEX idx_attention_path_time ON attention_events (path, created_at DESC);
CREATE INDEX idx_attention_event_time ON attention_events (event, created_at DESC);
