-- The contacts registry (roadmap 11.1): the people a search actually touches, kept so the
-- outreach generator (11.2) has a real name to draft for and the follow-up cadence (11.3)
-- has a last-touched date to go stale against. User-scoped like every table in this schema.
CREATE TABLE contacts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    role          TEXT,
    company       TEXT,
    -- How the user knows this person: referrer, mentor, peer, recruiter, ... Free text,
    -- because the honest taxonomy belongs to the user, not to this schema.
    relation      TEXT,
    email         TEXT,
    notes         TEXT,
    last_touch_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The list the registry page renders: this user's people, most recently touched first.
CREATE INDEX idx_contacts_user ON contacts (user_id, updated_at DESC);
