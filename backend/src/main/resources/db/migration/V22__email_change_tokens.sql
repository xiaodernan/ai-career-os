-- Moving the account's login address is two acts: the owner asks with the password,
-- and the new mailbox answers the letter. A row is that unanswered letter, stored as a
-- hash so a database leak cannot let anyone else finish the move.
CREATE TABLE email_change_tokens (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  text NOT NULL UNIQUE,
  new_email   citext NOT NULL,
  expires_at  timestamptz NOT NULL,
  used_at     timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_email_change_user ON email_change_tokens(user_id);
