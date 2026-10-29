-- The reply has a door home (roadmap 37.1). A provider forwards an answer to the address
-- generated for one account, and the backend keeps the letter so the tracker can show it
-- beside the application it answers. Every row hangs off users(id) with ON DELETE CASCADE,
-- like every user-scoped table since V1, so erasure (24.2) takes the letters with the account.
--
-- `message_key` is the provider's MessageID, or a SHA-256 of the four fields when the payload
-- carries none. The unique pair is what makes a provider retry answer the same letter instead
-- of a second row. `received_at` is the letter's own date (the provider's), not the row's
-- creation time: a mail relayed late still belongs where it was written.
--
-- The intent and the application it files on arrive in the next two units; this table holds
-- only what the webhook itself measured, so a column here is never a promise the code has
-- not made yet.
CREATE TABLE inbound_mails (
    id           UUID         PRIMARY KEY,
    user_id      UUID         NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    message_key  VARCHAR(256) NOT NULL,
    from_address VARCHAR(320) NOT NULL,
    subject      VARCHAR(500) NOT NULL,
    body_text    TEXT         NOT NULL,
    received_at  TIMESTAMPTZ  NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_inbound_mails_user_message UNIQUE (user_id, message_key)
);

-- The replies page reads one account's letters newest first; the unique pair above covers
-- the webhook's lookup, and this index covers the screen's.
CREATE INDEX idx_inbound_mails_user_received ON inbound_mails (user_id, received_at DESC);
