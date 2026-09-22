-- V2: Normalize salary values to the canonical unit (minor currency unit per year).
--
-- Background
-- ----------
-- `jobs.salary_min` / `jobs.salary_max` are documented (docs/architecture.md) and consumed by
-- the frontend formatter (frontend/src/lib/format.ts -> formatSalary) as an amount in the
-- currency's base unit per YEAR. For CNY that means 元/年: 380000 renders as "38万".
--
-- Early smoke-test rows were written before that convention was pinned down and stored the
-- value in 万/年 instead (e.g. 30 meaning "30万"), which the formatter turns into "0万" --
-- a visible data defect.
--
-- This migration repairs only rows that are unambiguously in the legacy unit, so it is safe
-- to apply to any database and is idempotent (a second run matches nothing).
--
-- Heuristic
-- ---------
-- A CNY annual salary below 10,000 元 is not a plausible real figure, and a legacy value
-- below 1,000 (万) is likewise implausible if it had already been stored in 元. So we only
-- scale values that are strictly between 1 (exclusive, zero/NULL untouched) and 10,000
-- (exclusive). Both bounds are applied per column; a column that does not satisfy the range
-- is left alone.

DO $$
DECLARE
    touched int;
BEGIN
    IF to_regclass('public.jobs') IS NULL THEN
        RAISE NOTICE 'jobs table absent; skipping salary normalization';
        RETURN;
    END IF;

    UPDATE jobs
       SET salary_min = CASE
               WHEN salary_min > 1 AND salary_min < 10000 THEN salary_min * 10000
               ELSE salary_min
           END,
           salary_max = CASE
               WHEN salary_max > 1 AND salary_max < 10000 THEN salary_max * 10000
               ELSE salary_max
           END
     WHERE COALESCE(salary_currency, 'CNY') IN ('CNY', 'RMB')
       AND (
            (salary_min > 1 AND salary_min < 10000)
         OR (salary_max > 1 AND salary_max < 10000)
       );

    GET DIAGNOSTICS touched = ROW_COUNT;
    RAISE NOTICE 'normalized % legacy salary row(s) to minor-unit-per-year', touched;
END $$;

-- Guard against a min/max inversion. PostgreSQL evaluates the right-hand side against the
-- pre-update row, so a single assignment swaps the two columns without losing either value.
UPDATE jobs
   SET salary_min = salary_max,
       salary_max = salary_min
 WHERE salary_min IS NOT NULL
   AND salary_max IS NOT NULL
   AND salary_min > salary_max;
