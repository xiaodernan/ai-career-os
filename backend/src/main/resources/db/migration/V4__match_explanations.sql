-- V4: Give each derived match row the two explanations the job panel already renders.
--
-- Background
-- ----------
-- `MatchResponse`/`MatchSummary` are projected to the browser with `whyMatch` and `preparation`
-- keys, `lib/api/normalize.ts` reads both back, and `components/jobs/match-panel.tsx` renders them
-- ("Your resume covers …" bullets, and the "Recommended preparation" card whose heading promises
-- the items are "Ordered by how much match score each item is worth"). Nothing produced them: the
-- match feature computed the five scores, the skill lists and the evidence, and stopped. So both
-- panels were permanently empty for every job in the product, and the only text the UI could put
-- under that promise was the LLM's free-form narrative.
--
-- ai-service now builds both deterministically from the same arithmetic that produced the scores
-- (app/features/match.py: `_why_match`, `_preparation`), so this migration only widens the row
-- that holds them. The columns are jsonb rather than text arrays because `preparation` items are
-- objects ({title,reason,priority}) and `why_match` is an ordered list of sentences.
--
-- Safety
-- ------
-- `IF NOT EXISTS` makes a repeat run a no-op, and the defaults are `[]` rather than NULL so the
-- JPA entity's `List<Object>` fields never have to handle null. There is deliberately no backfill:
-- an explanation has to be computed against the resume version and JD that produced the score, so
-- inventing text here would put words in a match the service never made. Rows written before this
-- migration read as empty lists, which both panels already treat as "show nothing" — they are
-- filled in the next time that resume/job pair is re-matched.

DO $$
BEGIN
    IF to_regclass('public.job_matches') IS NULL THEN
        RAISE NOTICE 'job_matches absent; skipping match-explanation columns';
        RETURN;
    END IF;

    ALTER TABLE job_matches
      ADD COLUMN IF NOT EXISTS why_match    jsonb NOT NULL DEFAULT '[]',
      ADD COLUMN IF NOT EXISTS preparation  jsonb NOT NULL DEFAULT '[]';

    RAISE NOTICE 'added job_matches.why_match and job_matches.preparation';
END $$;
