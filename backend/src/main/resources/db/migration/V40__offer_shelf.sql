-- Epic 185: the offer shelf. The salary actions (12.x) answer questions about offers
-- the reader pastes each time; this table is the reader's own record of the offers
-- they actually hold, so the compare view reads rows instead of re-entering numbers
-- and the deadline chip knows when an offer lapses. Equity is stored annualized: the
-- compare action already does the vest arithmetic, and the shelf keeps the result —
-- one number, no vest schedule to re-enter on every look.
CREATE TABLE offers (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  label       text NOT NULL,
  base        int  NOT NULL,
  bonus       int  NOT NULL DEFAULT 0,
  equity      int  NOT NULL DEFAULT 0,
  currency    varchar(3) NOT NULL DEFAULT 'USD',
  remote_type text NOT NULL DEFAULT 'onsite',   -- onsite|hybrid|remote (the jobs vocabulary)
  deadline    timestamptz,
  notes       text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_offers_user ON offers(user_id, created_at DESC);
