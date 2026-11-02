-- The nightly sweep's content phase (roadmap 44.3) deletes documents retired more than the
-- window ago, and no index answers that question: idx_docs_user is keyed by owner, which the
-- sweep does not filter on, so every pass would scan the whole table to find the few rows past
-- the cutoff. Status is what narrows the work, because an install that rarely deletes keeps
-- almost no retired rows, so the index covers only that slice and stays small as the table
-- grows.
CREATE INDEX idx_docs_retired_age ON documents(updated_at) WHERE status = 'retired';
