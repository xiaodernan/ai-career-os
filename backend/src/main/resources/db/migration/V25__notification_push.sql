-- The morning ring (roadmap 33.3). The mail's latch (V19) says "this episode was carried out by
-- letter"; a browser being woken is a different door out of the app, with its own consent (the
-- browser registration, V24) and its own failures. One latch cannot serve both: a reader who
-- turned the signals letter off still asked to be woken, and a push the push service refused is
-- not a letter that was delivered. This column is the fifth thing the reader's state remembers,
-- per episode, so a second morning cannot ring twice for the same signal while a new episode
-- arrives as a fresh row with no latch.
ALTER TABLE notification_states ADD COLUMN pushed_at TIMESTAMPTZ;
