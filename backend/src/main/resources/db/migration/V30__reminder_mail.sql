-- The reminder's own letter (roadmap 41.1). Until now a reminder came due in the app and rang
-- a browser, but a reader with no registration heard about it only in the next morning's signal
-- letter -- and a reminder's whole point is its moment. The minute clock now writes the letter
-- when the reminder comes due, and this column is the third dial on the mail settings page:
-- absence of a row still means all three are on, and turning this one off falls back to the
-- morning letter rather than to silence.
ALTER TABLE mail_preferences ADD COLUMN reminder_mail BOOLEAN NOT NULL DEFAULT TRUE;
