-- Epic 184: the activity heatmap reads four tables' daily counts for one user over
-- up to half a year. Each union arm filters by (user_id, <its clock>) and groups by
-- that clock's day, so every arm wants the same composite shape: user first, time
-- second. ai_usage_events already carries idx_usage_user_time(user_id, created_at)
-- from V1; these three give the other arms the same plan instead of a per-row filter.
CREATE INDEX IF NOT EXISTS idx_apps_user_created ON applications(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_iv_user_created ON interview_sessions(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_inbound_user_received ON inbound_mails(user_id, received_at);
