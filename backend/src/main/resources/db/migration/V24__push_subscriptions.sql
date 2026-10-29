-- The bell outside the tab (roadmap 33.1). The bell count and the morning letter both need
-- something already looking -- a tab holding a session, or a mailbox being read. A Web Push
-- subscription is the browser's promise that its installed worker can be woken, and this table
-- is that promise kept per browser.
--
-- The endpoint is unique across the table, not per account: a subscription belongs to a browser
-- registration, not to a reader. When another reader signs in on the same browser and opts in,
-- the row moves to them instead of a second row pointing at the same registration, which would
-- wake that browser twice for one morning. The two keys are what a push service needs to encrypt
-- a payload; today the push carries none, but the browser hands them over at subscribe time and
-- re-registering refreshes them.
CREATE TABLE push_subscriptions (
    id         UUID PRIMARY KEY,
    user_id    UUID         NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    endpoint   TEXT         NOT NULL UNIQUE,
    p256dh     VARCHAR(160) NOT NULL,
    auth       VARCHAR(64)  NOT NULL,
    label      VARCHAR(120),
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Every read is "this account's devices"; the unique index on the endpoint serves the write path.
CREATE INDEX idx_push_subscriptions_user ON push_subscriptions (user_id);
