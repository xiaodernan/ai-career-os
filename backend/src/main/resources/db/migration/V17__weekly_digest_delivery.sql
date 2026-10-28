-- The letter's delivery (roadmap 21.2): the Monday sweep hands each composed letter to the mail
-- transport and keeps what happened, so a week that never reached its mailbox is a row a reader
-- can see rather than a silence.
--
-- delivered_at is the latch, not only a receipt: composing a week again (a re-run after a crash,
-- a manual POST /digests/run) must not put a second copy in the mailbox, so the sweep skips any
-- letter that already carries a moment here. delivery_error holds the last refusal and is cleared
-- by a later success; delivery_attempts counts every hand-off tried, so "never tried" (0) and
-- "tried and refused" (1 with an error) are different readings of the same row.
ALTER TABLE weekly_digests
    ADD COLUMN delivered_at      TIMESTAMPTZ,
    ADD COLUMN delivery_error    VARCHAR(500),
    ADD COLUMN delivery_attempts INTEGER NOT NULL DEFAULT 0;
