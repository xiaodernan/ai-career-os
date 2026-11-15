/**
 * Reading the funnel the install drew for itself (Epic 259).
 *
 * Templated arithmetic, deliberately not generative: the product never writes a sentence a
 * human must interpret on faith — it names the steepest single-stage loss it can measure,
 * with the percentage that produced it, and nothing else.
 */

export interface FunnelStage {
  id: string;
  readers: number;
}

export interface FunnelReading {
  /** The stage AFTER the steepest single-stage loss (i.e. the leaky one), or null for a degenerate line. */
  bottleneckStageId: string | null;
  /** Share of the previous stage that survived, percent, or null when the previous stage is zero. */
  bottleneckPercent: number | null;
  /** Matched readers as a share of the registration cohort, percent, or null. */
  matchedSharePercent: number | null;
}

export function funnelReading(
  stages: FunnelStage[],
  matchedReaders: number | undefined,
): FunnelReading {
  let bottleneckStageId: string | null = null;
  let bottleneckPercent: number | null = null;
  for (let i = 1; i < stages.length; i++) {
    const previous = stages[i - 1].readers;
    const current = stages[i].readers;
    if (previous <= 0) {
      continue;
    }
    const share = Math.round((current / previous) * 100);
    if (bottleneckPercent === null || share < bottleneckPercent) {
      bottleneckPercent = share;
      bottleneckStageId = stages[i].id;
    }
  }
  const registered = stages[0]?.readers ?? 0;
  const matchedSharePercent =
    registered > 0 && typeof matchedReaders === "number"
      ? Math.min(100, Math.round((matchedReaders / registered) * 100))
      : null;
  return { bottleneckStageId, bottleneckPercent, matchedSharePercent };
}
