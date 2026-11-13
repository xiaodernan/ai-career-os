-- Epic 184: the activity heatmap reads four tables' daily counts for one user over
-- up to half a year. Each union arm filters by (user_id, its own clock) and groups
-- by that clock's day, so every arm wants the same composite shape: user first, time
-- second. ai_usage_events already carries idx_usage_user_time(user_id, created_at)
-- from V1, and inbound_mails carries idx_inbound_mails_user_received (user_id,
-- received_at DESC) from V27; these two give the remaining arms the same plan
-- instead of a per-row filter. The interview arm groups by started_at -- a session's
-- clock is when it began, and the table has no created_at.
CREATE INDEX IF NOT EXISTS idx_apps_user_created ON applications(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_iv_user_started ON interview_sessions(user_id, started_at);
