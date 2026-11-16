/**
 * The counsel the overseer's ledger gives its own reader (Epic 280).
 *
 * The "what to do next" section used to be five hardcoded sentences — useful
 * once, stale forever, and never a function of what the wires actually
 * returned. This module derives every item from the seven payloads the page
 * already fetches, and nothing else. Rules are deliberately plain arithmetic;
 * a rule that cannot see its input stays silent, which is the honest
 * behaviour: silence reads as "nothing measured", never as "all is well".
 *
 * No model call, no generated prose, no invented confidence. Every item names
 * the numbers that fired it in its body, in the reader's locale via the keys
 * the page hands it to. The page owns rendering, fetch, and the stage-label
 * lookup (`labelForStage`) — this file owns the arithmetic and the order.
 */

export interface CounselStats {
  users?: number;
  applications?: number;
  interviewsPracticed?: number;
  agentRuns?: number;
  aiUsageEvents?: number;
}

export interface CounselTrends {
  weeks?: string[];
  series?: Record<string, number[] | undefined>;
}

export interface CounselFunnel {
  stages?: Array<{ id: string; readers: number }>;
}

export interface CounselCohort {
  cohort?: Array<{ week: string; registered: number; active: number }>;
}

export interface CounselAttention {
  landings?: number;
  dwells?: number;
  acts?: number;
  signedLandings?: number;
  anonymousLandings?: number;
  dwellPerLandingMs?: number;
}

export interface CounselInput {
  stats?: CounselStats | null;
  trends?: CounselTrends | null;
  funnel?: CounselFunnel | null;
  cohort?: CounselCohort | null;
  attention?: CounselAttention | null;
}

export interface CounselOptions {
  /** Stage id → localized stage name. Absent stages fall back to the raw id. */
  labelForStage?: (id: string) => string;
}

export interface CounselItem {
  id: string;
  titleKey: string;
  bodyKey: string;
  vars: Record<string, string | number>;
}

const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const pct = (part: number, whole: number): number =>
  whole <= 0 ? 0 : Math.round((part / whole) * 1000) / 10;

function funnelCliff(funnel: CounselFunnel | null | undefined, labelForStage?: (id: string) => string): CounselItem | null {
  const stages = funnel?.stages ?? [];
  if (stages.length < 2) return null;
  let worst: { from: string; to: string; fromCount: number; toCount: number; drop: number } | null = null;
  for (let i = 0; i + 1 < stages.length; i += 1) {
    const from = stages[i];
    const to = stages[i + 1];
    if (!isNum(from.readers) || !isNum(to.readers) || from.readers <= 0) continue;
    const drop = 1 - to.readers / from.readers;
    if (drop < 0.5) continue;
    if (!worst || drop > worst.drop) {
      worst = { from: from.id, to: to.id, fromCount: from.readers, toCount: to.readers, drop };
    }
  }
  if (!worst) return null;
  const label = labelForStage ?? ((id: string) => id);
  return {
    id: "funnel-cliff",
    titleKey: "admin.counselFunnelTitle",
    bodyKey: "admin.counselFunnelBody",
    vars: {
      from: label(worst.from),
      to: label(worst.to),
      fromCount: worst.fromCount,
      toCount: worst.toCount,
      dropPct: Math.round(worst.drop * 100),
    },
  };
}

function cohortCliff(cohort: CounselCohort | null | undefined): CounselItem | null {
  const rows = (cohort?.cohort ?? []).filter(
    (r) => isNum(r.registered) && isNum(r.active) && r.registered > 0
  );
  if (rows.length === 0) return null;
  const newest = rows.slice(-4);
  const registered = newest.reduce((sum, r) => sum + r.registered, 0);
  const active = newest.reduce((sum, r) => sum + r.active, 0);
  if (registered <= 0) return null;
  const retention = (active / registered) * 100;
  if (retention >= 50) return null;
  return {
    id: "cohort-cliff",
    titleKey: "admin.counselCohortTitle",
    bodyKey: "admin.counselCohortBody",
    vars: {
      retentionPct: Math.round(retention * 10) / 10,
      weeks: newest.length,
      active,
      registered,
    },
  };
}

function attentionSignals(attention: CounselAttention | null | undefined): CounselItem[] {
  const landings = attention?.landings;
  if (!isNum(landings) || landings < 20) return [];
  const items: CounselItem[] = [];
  const acts = attention?.acts;
  if (isNum(acts) && acts === 0) {
    items.push({
      id: "act-rate-zero",
      titleKey: "admin.counselActTitle",
      bodyKey: "admin.counselActBody",
      vars: { landings },
    });
  }
  const dwells = attention?.dwells;
  if (isNum(dwells) && pct(dwells, landings) < 10) {
    items.push({
      id: "dwell-rare",
      titleKey: "admin.counselDwellTitle",
      bodyKey: "admin.counselDwellBody",
      vars: { pct: pct(dwells, landings), dwells, landings },
    });
  }
  const signed = attention?.signedLandings;
  const anonymous = attention?.anonymousLandings;
  if (isNum(signed) && isNum(anonymous) && signed === 0 && anonymous >= 20) {
    items.push({
      id: "all-anonymous",
      titleKey: "admin.counselAnonymousTitle",
      bodyKey: "admin.counselAnonymousBody",
      vars: { landings: anonymous },
    });
  }
  return items;
}

function applicationsSlope(values: number[] | undefined): number | null {
  if (!values || values.length < 8) return null;
  const n = values.length;
  let sumX = 0;
  let sumY = 0;
  let sumXX = 0;
  let sumXY = 0;
  for (let i = 0; i < n; i += 1) {
    sumX += i;
    sumY += values[i];
    sumXX += i * i;
    sumXY += i * values[i];
  }
  const denom = n * sumXX - sumX * sumX;
  if (denom === 0) return null;
  return (n * sumXY - sumX * sumY) / denom;
}

function trendFalling(trends: CounselTrends | null | undefined): CounselItem | null {
  const apps = trends?.series?.applications;
  const slope = applicationsSlope(apps);
  if (slope === null || slope >= 0) return null;
  const first = apps![0];
  const last = apps![apps!.length - 1];
  if (first === 0 && last === 0) return null; // a flat zero window is not a falling tide
  return {
    id: "trend-falling",
    titleKey: "admin.counselTrendTitle",
    bodyKey: "admin.counselTrendBody",
    vars: { first, last, weeks: apps!.length },
  };
}

function stuckJourney(stats: CounselStats | null | undefined): CounselItem | null {
  const users = stats?.users;
  const applications = stats?.applications;
  if (!isNum(users) || !isNum(applications)) return null;
  if (users > 0 && applications === 0) {
    return {
      id: "stuck-journey",
      titleKey: "admin.counselStuckTitle",
      bodyKey: "admin.counselStuckBody",
      vars: { users },
    };
  }
  return null;
}

function seriesMean(values: number[]): number {
  return values.reduce((sum, v) => sum + v, 0) / Math.max(values.length, 1);
}

function attentionSoften(trends: CounselTrends | null | undefined): CounselItem | null {
  const lands = trends?.series?.attentionLands;
  if (!lands || lands.length < 8) return null;
  const half = Math.floor(lands.length / 2);
  const firstHalf = lands.slice(0, half);
  const secondHalf = lands.slice(half);
  const firstMean = seriesMean(firstHalf);
  const secondMean = seriesMean(secondHalf);
  if (firstMean < 1) return null; // a quiet window is not a softer one
  if (secondMean >= 0.6 * firstMean) return null;
  return {
    id: "attention-soften",
    titleKey: "admin.counselAttentionSoftenTitle",
    bodyKey: "admin.counselAttentionSoftenBody",
    vars: { recent: Math.round(secondMean), base: Math.round(firstMean) },
  };
}

function attentionCollapse(trends: CounselTrends | null | undefined): CounselItem | null {
  const lands = trends?.series?.attentionLands;
  if (!lands || lands.length < 4) return null;
  const last = lands[lands.length - 1];
  const prior = lands.slice(0, lands.length - 1);
  const priorMean = seriesMean(prior);
  if (priorMean < 1) return null;
  if (last >= 0.3 * priorMean) return null;
  return {
    id: "attention-collapse",
    titleKey: "admin.counselAttentionCollapseTitle",
    bodyKey: "admin.counselAttentionCollapseBody",
    vars: { last, base: Math.round(priorMean) },
  };
}

/**
 * Every counsel item the wires can honestly produce, most urgent first.
 * Wires that failed or have nothing to say are silent by construction.
 */
export function deriveCounsel(input: CounselInput, options: CounselOptions = {}): CounselItem[] {
  const out: CounselItem[] = [];
  const funnel = funnelCliff(input.funnel, options.labelForStage);
  if (funnel) out.push(funnel);
  const cohort = cohortCliff(input.cohort);
  if (cohort) out.push(cohort);
  out.push(...attentionSignals(input.attention));
  const collapse = attentionCollapse(input.trends);
  if (collapse) out.push(collapse);
  const soften = attentionSoften(input.trends);
  if (soften) out.push(soften);
  const trend = trendFalling(input.trends);
  if (trend) out.push(trend);
  const stuck = stuckJourney(input.stats);
  if (stuck) out.push(stuck);
  return out;
}
