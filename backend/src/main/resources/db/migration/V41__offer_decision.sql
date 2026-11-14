-- Epic 194: the offer shelf remembers the reader's mind.
-- The shelf shows the offers a reader actually holds — but holding is not a state of
-- the mind. The reader can mark one accepted and the rest declined without erasing a
-- row: an offer that expires next week is still a row in the record of the search
-- that produced it. Numbers stay the reader's; the decision is the reader's.
--
-- VARCHAR with an app-level vocabulary — "pending"|"accepted"|"declined"; no check
-- constraint vocabulary, because a CHECK would need a migration every time a state
-- were added and the column has a documented default for old rows.
ALTER TABLE offers ADD COLUMN IF NOT EXISTS decision varchar(24) NOT NULL DEFAULT 'pending';
