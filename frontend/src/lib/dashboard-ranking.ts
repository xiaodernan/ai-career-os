import type { Job } from "@/lib/api/types";

/**
 * Which sentence the dashboard's "Where to focus" band is allowed to print.
 *
 * Measured on the running stack (2026-10-24, `demo+mvle37ja@careeros.test`): the band read
 * "Ranked by the matching agent against your resume." over five rows whose every
 * `matchOverall` was `null`. No agent had ranked anything; the band was describing a
 * decision that was never made.
 *
 * The rows come from `DashboardRepository.recommendedJobs`, which `LEFT JOIN LATERAL`s the
 * viewer's latest match and ends with `ORDER BY m.overall DESC NULLS LAST, j.posted_at DESC`.
 * When no job has a match for this user every `overall` is null, the first key collapses,
 * and the order is pure recency — the same list, in the same order, for whoever signs in.
 * The band decided its sentence by `recommendedJobs?.length`, so it asked "are there rows?"
 * and answered "did the agent rank them?", and rows are exactly what an unranked board
 * still supplies.
 *
 * Two shape choices carry the fix, and the module's own test holds both:
 *
 * - **`some`, not `every`.** `NULLS LAST` puts the scored rows at the head, so a list where
 *   three of five rows are unscored *was* ordered by the agent's numbers first; the head of
 *   it is the ranking. The case that must not claim a ranking is the one with no score at all.
 * - **`!= null`, not truthiness.** A match the agent scored zero is still an answer the agent
 *   gave, and `normalizeJob` keeps it: `pct(0)` is `0`, and `0 != null`.
 */

// The two keys are names in code and copy in the table; nothing type-checks the middle.
const RANKED = "dashboard.skillGapsHint";
const UNRANKED = "dashboard.straightFromTheBoard";

/** Both sentences the band can print — the values production returns, not a second list. */
export const RANKING_HINT_KEYS: readonly string[] = [RANKED, UNRANKED];

/** The band's description key: the agent's ranking when any row carries a score, the board's own order when none does. */
export function rankingHintKey(jobs: readonly Job[] | undefined): string {
  return jobs?.some((job) => job.latestMatch != null) ? RANKED : UNRANKED;
}
