-- The reader can say stop (roadmap 23.1). Until now every account that had an application or a
-- feed was mailed: the Monday letter and the morning signals had no opt-out, no footer and no
-- List-Unsubscribe header, so a reader who wanted the mail to end could only ignore it.
--
-- One row per account that has ever changed a switch; absence means both letters are on, which
-- keeps signup free of a row and makes "never asked" and "asked for both" the same dial. The
-- columns are the two letters by the names the unsubscribe page shows, not the classes that
-- compose them, so a renamed scheduler cannot silently swap what a reader turned off.
CREATE TABLE mail_preferences (
    user_id       UUID PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    weekly_digest BOOLEAN     NOT NULL DEFAULT TRUE,
    signal_mail   BOOLEAN     NOT NULL DEFAULT TRUE,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
