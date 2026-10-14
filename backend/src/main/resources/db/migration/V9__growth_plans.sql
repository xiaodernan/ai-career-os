-- One stored growth plan per run: the report the 10.8 aggregate composed, kept so the
-- next run for the same (user, target_role) diffs against it server-side (roadmap 10.4)
-- instead of the browser carrying its last answer around. Rows are appended, never
-- updated — a run's report is an observation, and the diff is between observations.
CREATE TABLE growth_plans (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    target_role TEXT NOT NULL,
    coverage    DOUBLE PRECISION NOT NULL DEFAULT 0,
    report      JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The only read the feature has: the latest row for one (user, role) pair.
CREATE INDEX idx_growth_plans_user_role ON growth_plans (user_id, target_role, created_at DESC);
