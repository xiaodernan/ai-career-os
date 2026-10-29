-- The account's second door (roadmap 36.1). A TOTP seed and the recovery codes that stand in
-- for the authenticator when the phone is lost. Every row hangs off users(id) with ON DELETE
-- CASCADE, like every user-scoped table since V1, so erasure (24.2) empties this one with the
-- account row.
--
-- The seed is stored sealed, not as the base32 the authenticator was given: a database dump is
-- the one copy an attacker most often gets, and a plain seed there is every future second factor
-- for that account. The key lives in `app.security.mfa-secret`, which a production boot refuses
-- while it is still the value this repository publishes (ProductionGuard).
--
-- `active` separates an enrollment the reader started (a seed exists, no code has proven it yet)
-- from one that is in force. A pending row may be replaced by re-enrolling; an active one may not,
-- or a stolen session could hand itself a fresh seed and silently retire the reader's phone.
-- `last_used_step` is the replay guard: a code that verified once cannot verify again, though its
-- 30-second step is still inside the accepted window.
CREATE TABLE user_mfa (
    user_id           UUID PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    secret_ciphertext TEXT        NOT NULL,
    active            BOOLEAN     NOT NULL DEFAULT FALSE,
    last_used_step    BIGINT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at      TIMESTAMPTZ
);

-- Each recovery code is a single-use password of its own, stored only as a hash. `used_at` is
-- what makes it single-use; the plaintext leaves the service exactly once, in the activation
-- answer, and is never recoverable afterwards -- the reader prints it then or enrolls again.
CREATE TABLE user_mfa_recovery_codes (
    id         UUID PRIMARY KEY,
    user_id    UUID         NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    code_hash  VARCHAR(100) NOT NULL,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- The sign-in path loads one account's unused codes, and activation replaces them wholesale;
-- both walk this index. A code is matched by hash, so there is no lookup by value.
CREATE INDEX idx_user_mfa_recovery_codes_user ON user_mfa_recovery_codes (user_id);
