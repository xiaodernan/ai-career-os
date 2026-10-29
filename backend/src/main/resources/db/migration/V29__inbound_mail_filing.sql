-- The reply meets the application it answers (roadmap 37.3). A filed letter points at the
-- board row whose company -- and, when the name repeats, whose role -- it matched. The link
-- is a pointer, not ownership: deleting the application clears it (ON DELETE SET NULL) so the
-- letter returns to the replies page as unmatched, rather than disappearing with a card that
-- happened to answer it. The letter is the reader's record of what a recruiter wrote.
--
-- `filed_at` is when the row was matched, whether automatically on arrival or by the reader
-- choosing an application on the replies page. It is null exactly when the letter is unfiled;
-- the two columns move together.
ALTER TABLE inbound_mails
    ADD COLUMN application_id UUID REFERENCES applications (id) ON DELETE SET NULL,
    ADD COLUMN filed_at       TIMESTAMPTZ;

-- The inbox reads one account's filed letters newest first; the replies page reads all of an
-- account's letters, which the established (user_id, received_at DESC) index already covers.
CREATE INDEX idx_inbound_mails_user_application ON inbound_mails (user_id, application_id);
