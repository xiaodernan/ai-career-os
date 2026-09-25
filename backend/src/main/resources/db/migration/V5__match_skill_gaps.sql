-- V5: Give a stored match the skill gaps it computed, so the job panel keeps them after a reload.
--
-- Background
-- ----------
-- `compute_match` has always returned `skillGaps` — one row per required skill the resume does not
-- evidence — and `normalizeMatch` reads it back, but `persist_match` never stored it. So the only
-- copy of the list lived in the POST /jobs/{id}/match response body: reload the page, and the
-- "Skill gaps" card falls back to `normalizeSkillGaps(jdBody)`, which drills `skillGaps` out of the
-- JD analysis (a map that carries `requiredSkills`, never `skillGaps`) and therefore yields nothing.
-- Measured on 2026-09-26, the card was empty on every path, not just after a reload: the job page
-- read `data.skillGaps`, which comes from the *job detail* payload, and `JobDetail` has no such
-- component — the value the service produced sat on `data.match.skillGaps`, which nothing read.
--
-- `interviewTopics` was surveyed with it and deliberately left out: it is a property of the job
-- description, not of this resume/job pair, it is already stored with the analysis in
-- `job_jds.parsed`, and the panel's fallback for it (`jdParsed.interviewTopics`) does resolve.
-- Copying it onto the match row would put the same list under two owners with different refresh
-- times, which is a drift to maintain rather than a bug to fix.
--
-- Safety
-- ------
-- `IF NOT EXISTS` makes a repeat run a no-op and the `[]` default keeps the JPA `List<Object>`
-- field from ever being null. There is no backfill: which skills were gaps is a claim about the
-- resume version that produced the score, and rows written before this migration simply show an
-- empty list until that pair is re-matched — the same treatment `why_match` and `preparation` got
-- in V4.

DO $$
BEGIN
    IF to_regclass('public.job_matches') IS NULL THEN
        RAISE NOTICE 'job_matches absent; skipping skill_gaps column';
        RETURN;
    END IF;

    ALTER TABLE job_matches
      ADD COLUMN IF NOT EXISTS skill_gaps jsonb NOT NULL DEFAULT '[]';

    RAISE NOTICE 'added job_matches.skill_gaps';
END $$;
