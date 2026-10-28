-- The morning signal mail (roadmap 22.1). A notification is still not a row; this column is
-- the fourth thing the reader's state remembers: the moment a mail carrying this episode was
-- accepted by the transport. NULL means the item has never been handed to the reader outside
-- the app, so a later sweep may carry it; read_at and dismissed_at describe the app, not the
-- mailbox, and do not clear it. A new episode arrives under a new key and therefore a fresh
-- row with no latch.
ALTER TABLE notification_states ADD COLUMN notified_at TIMESTAMPTZ;
