-- Read/dismiss state for the inbox (roadmap 19.3). A notification is not stored: it is
-- synthesized from a signal the platform already wrote down -- an application whose reminder
-- has come due or that has gone quiet, a pull the sweep recorded. What persists is what the
-- reader did with it, keyed by the signal's own identity, so nothing has to be rewritten when
-- a signal changes, and a signal that ends leaves a harmless row behind.
--
-- The key names the episode, not just the row: `reminder:<applicationId>:<reminderAt>` and
-- `stale:<applicationId>:<updatedAt>` carry the moment the episode began, so dismissing a
-- stale nudge does not silence the next one -- a moved application that goes quiet again is a
-- new episode with a new key -- while `ingestion:<runId>` is already unique per pull.
CREATE TABLE notification_states (
    user_id      UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    signal_key   VARCHAR(160) NOT NULL,
    read_at      TIMESTAMPTZ,
    dismissed_at TIMESTAMPTZ,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, signal_key)
);

-- The only read is "every state this one user has", which the primary key already serves as a
-- prefix; no second index is needed.
