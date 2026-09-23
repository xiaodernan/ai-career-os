-- V3: Backfill each agent run's token/cost rollup from its own usage events.
--
-- Background
-- ----------
-- `agent_runs.input_tokens / output_tokens / cached_tokens / cost_usd` are a rollup that the
-- dashboard (DashboardService) and the activity page (ActivityController) read directly. They
-- were only ever written when the caller of finish_run happened to pass usage figures, and the
-- most expensive path in the product — the copilot agent turn, up to eight model calls — passed
-- a latency and nothing else. Every one of those tokens *was* recorded, per call, in
-- ai_usage_events by core/ai.ask; the rollup just never picked them up, so both surfaces showed
-- a clean zero for runs that had spent thousands of tokens.
--
-- The code now derives the rollup from the ledger at finish time (ai-service
-- app/db/observability.py, finish_run). This migration repairs the history that predates it.
--
-- Safety
-- ------
-- Only rows whose rollup is entirely empty AND that have at least one recorded event are
-- touched, so a run that was finished with real figures by a caller is left alone, and a second
-- run of this migration matches nothing (idempotent). Latency is not inferred: it is not in the
-- ledger's sums and must not be invented here.

DO $$
DECLARE
    touched int;
BEGIN
    IF to_regclass('public.agent_runs') IS NULL OR to_regclass('public.ai_usage_events') IS NULL THEN
        RAISE NOTICE 'agent_runs or ai_usage_events absent; skipping run-usage backfill';
        RETURN;
    END IF;

    WITH ledger AS (
        SELECT u.run_id                       AS id,
               sum(u.input_tokens)            AS in_tok,
               sum(u.output_tokens)           AS out_tok,
               sum(u.cached_tokens)           AS cached_tok,
               sum(u.cost_usd)                AS cost
          FROM ai_usage_events u
          JOIN agent_runs a ON a.id = u.run_id
         WHERE a.input_tokens = 0
           AND a.output_tokens = 0
           AND a.cached_tokens = 0
           AND a.cost_usd = 0
         GROUP BY u.run_id
    )
    UPDATE agent_runs a
       SET input_tokens  = coalesce(l.in_tok, 0),
           output_tokens = coalesce(l.out_tok, 0),
           cached_tokens = coalesce(l.cached_tok, 0),
           cost_usd      = coalesce(l.cost, 0)
      FROM ledger l
     WHERE a.id = l.id;

    GET DIAGNOSTICS touched = ROW_COUNT;
    RAISE NOTICE 'backfilled usage rollup for % agent run(s) from ai_usage_events', touched;
END $$;
