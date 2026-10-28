-- A run stops being only a proposal. Until now every pull stored the
-- engine's create/update/close plan and nothing ever wrote it to the board: the jobs
-- table had no writer in the backend at all, so the nightly sweep could only report what
-- it saw. Applying a plan is the write, and these two columns are its receipt.
--
-- `applied_at` is what makes an apply idempotent: the endpoint refuses a run that already
-- carries one, so a reader who presses the button twice gets the same answer, not a second
-- copy of every posting. `applied_counts` is the three numbers the apply actually wrote
-- (created / updated / closed), kept beside the plan's proposal rather than derived from
-- it -- a posting the plan proposed and the board already had is not a create.
ALTER TABLE ingestion_runs
    ADD COLUMN applied_at     TIMESTAMPTZ,
    ADD COLUMN applied_counts JSONB;

-- The apply reads the run by owner and locks the row; the existing (user_id, started_at)
-- index serves the history and this lookup alike, so no second index is added here.
