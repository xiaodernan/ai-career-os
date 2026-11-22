/**
 * The ledger's own analyst (Epic 379).
 *
 * The LLM analyst is an optional second voice. When the provider is dark — a
 * closed account, an exhausted quota, a network that cannot reach the relay —
 * the operator still needs the two things the brief asks for: a trend forecast
 * and the next measures. Both are arithmetic over the numbers the page already
 * fetched, so they need no model, no network and no invented prose.
 *
 * Every measure below is a function of its input. A rule that cannot see its
 * series stays silent; silence reads as "not measured", never as "all is well".
 */

export type Direction = "up" | "down" | "flat";

export interface Forecast {
  /** Projected values for the next `horizon` buckets, clamped at zero. */
  next: number[];
  /** Sum of the projected buckets. */
  nextTotal: number;
  /** Least-squares slope per bucket. */
  slope: number;
  /** R² of the fit over the measured window, 0..1. */
  r2: number;
  direction: Direction;
}

const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const clamp0 = (v: number): number => Math.max(0, v);

/**
 * Least-squares straight-line projection over a measured window.
 *
 * `flat` is a real answer, not a failure: a window whose slope is tiny next to
 * its own mean is a window that is not moving, and drawing an arrow on it would
 * be the kind of confident lie this page exists to avoid.
 */
export function forecast(values: number[] | undefined, horizon = 4): Forecast | null {
  const series = (values ?? []).filter(isNum);
  if (series.length < 3 || horizon < 1) return null;
  const n = series.length;
  const xMean = (n - 1) / 2;
  const yMean = series.reduce((sum, v) => sum + v, 0) / n;
  let sxy = 0;
  let sxx = 0;
  let sst = 0;
  for (let i = 0; i < n; i += 1) {
    const dx = i - xMean;
    sxy += dx * (series[i] - yMean);
    sxx += dx * dx;
    sst += (series[i] - yMean) ** 2;
  }
  const slope = sxx === 0 ? 0 : sxy / sxx;
  const intercept = yMean - slope * xMean;
  const r2 = sst === 0 ? 0 : Math.max(0, Math.min(1, 1 - (sst - (sxy * sxy) / (sxx || 1)) / sst));
  const next = Array.from({ length: horizon }, (_, i) => clamp0(intercept + slope * (n + i)));
  // A slope smaller than 2% of the window's own mean is noise, not a direction.
  const threshold = Math.max(0.05, Math.abs(yMean) * 0.02);
  const direction: Direction = slope > threshold ? "up" : slope < -threshold ? "down" : "flat";
  return {
    next,
    nextTotal: next.reduce((sum, v) => sum + v, 0),
    slope,
    r2,
    direction,
  };
}

export interface Anomaly {
  key: string;
  last: number;
  mean: number;
  /** Standard deviations from the prior mean; positive is a spike. */
  z: number;
  direction: "spike" | "drop";
}

/**
 * The newest bucket against everything before it. Two and a half standard
 * deviations is a deliberately conservative bar: a weekly count is a noisy
 * thing, and flagging every wobble teaches the operator to ignore the flag.
 */
export function detectAnomalies(
  series: Record<string, number[] | undefined>,
  threshold = 2.5,
): Anomaly[] {
  const out: Anomaly[] = [];
  for (const [key, raw] of Object.entries(series)) {
    const values = (raw ?? []).filter(isNum);
    if (values.length < 4) continue;
    const prior = values.slice(0, -1);
    const last = values[values.length - 1];
    const mean = prior.reduce((sum, v) => sum + v, 0) / prior.length;
    const variance = prior.reduce((sum, v) => sum + (v - mean) ** 2, 0) / prior.length;
    const sd = Math.sqrt(variance);
    if (sd <= 0 || mean <= 0) continue;
    const z = (last - mean) / sd;
    if (Math.abs(z) < threshold) continue;
    out.push({ key, last, mean, z, direction: z > 0 ? "spike" : "drop" });
  }
  return out.sort((a, b) => Math.abs(b.z) - Math.abs(a.z));
}

export interface LocalMeasureAttention {
  days?: number;
  landings?: number;
  bounces?: number;
  bounceRatePct?: number;
  aimless?: number;
  /** 372: searches the product could not answer, and the words readers used. */
  searchMiss?: number;
  searchMissWords?: Array<{ word?: string; misses?: number }>;
}

export interface LocalMeasureInput {
  trends?: { series?: Record<string, number[] | undefined>; weeks?: string[] } | null;
  cache?: {
    totals?: { calls?: number; hit_pct?: number | null };
  } | null;
  attention?: LocalMeasureAttention | null;
}

export interface LocalMeasure {
  id: string;
  titleKey: string;
  bodyKey: string;
  vars: Record<string, string | number>;
  href?: string;
  /** Higher is more urgent; the page renders the list in this order. */
  severity: number;
}

function measured(values: number[] | undefined): number[] {
  return (values ?? []).filter(isNum);
}

/**
 * The measures the arithmetic can defend, most urgent first, at most four.
 * The same copy keys the model analyst's measures use where the meaning is the
 * same; nothing here is model-authored.
 */
export function deriveLocalMeasures(input: LocalMeasureInput): LocalMeasure[] {
  const series = input.trends?.series ?? {};
  const out: LocalMeasure[] = [];

  const falling = (
    key: string,
    titleKey: string,
    bodyKey: string,
    href: string,
    severity: number,
  ) => {
    const values = measured(series[key]);
    const fc = forecast(values);
    if (!fc || fc.direction !== "down") return;
    const last = values[values.length - 1];
    const first = values[0];
    if (first <= 0 && last <= 0) return; // a flat zero window is not a falling tide
    out.push({
      id: `local-${key}-falling`,
      titleKey,
      bodyKey,
      vars: { first, last, weeks: values.length, next: Math.round(fc.nextTotal) },
      href,
      severity,
    });
  };

  falling(
    "applications",
    "admin.localApplicationsFallingTitle",
    "admin.localApplicationsFallingBody",
    "/jobs",
    90,
  );
  falling(
    "attentionLands",
    "admin.localAttentionFallingTitle",
    "admin.localAttentionFallingBody",
    "/",
    85,
  );
  falling(
    "interviewsPracticed",
    "admin.localInterviewFallingTitle",
    "admin.localInterviewFallingBody",
    "/interviews",
    80,
  );

  const calls = input.cache?.totals?.calls;
  const hit = input.cache?.totals?.hit_pct;
  if (isNum(calls) && calls >= 10 && isNum(hit) && hit < 50) {
    out.push({
      id: "local-cache-cold",
      titleKey: "admin.localCacheColdTitle",
      bodyKey: "admin.localCacheColdBody",
      vars: { calls, hit: Math.round(hit * 10) / 10 },
      href: "/monitoring",
      severity: 70,
    });
  }

  // Epic 413 — the attention ledger already holds the three behaviours the brief
  // names (an impatient close, a lost click, a search with no answer). They were
  // read only as counters; these rules turn the ones that cross a bar into
  // measures with a door, and stay silent under it, because a small sample is
  // not a finding.
  const attention = input.attention;
  if (attention) {
    const days = isNum(attention.days) && attention.days > 0 ? Math.round(attention.days) : 30;
    const landings = isNum(attention.landings) ? attention.landings : 0;
    const bounces = isNum(attention.bounces) ? attention.bounces : 0;
    const rate = isNum(attention.bounceRatePct)
      ? attention.bounceRatePct
      : landings > 0
        ? (100 * bounces) / landings
        : 0;
    if (landings >= 50 && rate >= 35) {
      out.push({
        id: "local-attention-bounce",
        titleKey: "admin.localBounceTitle",
        bodyKey: "admin.localBounceBody",
        vars: { days, landings, bounces, rate: Math.round(rate * 10) / 10 },
        href: "/",
        severity: 92,
      });
    }

    const misses = isNum(attention.searchMiss) ? attention.searchMiss : 0;
    const word = (attention.searchMissWords ?? []).find(
      (candidate) =>
        typeof candidate.word === "string" &&
        candidate.word.trim() !== "" &&
        isNum(candidate.misses) &&
        candidate.misses > 0
    );
    if (misses >= 10 && word) {
      out.push({
        id: "local-attention-search-miss",
        titleKey: "admin.localSearchMissTitle",
        bodyKey: "admin.localSearchMissBody",
        vars: { days, misses, word: word.word!.trim(), wordMisses: word.misses! },
        href: "/jobs",
        severity: 86,
      });
    }

    const aimless = isNum(attention.aimless) ? attention.aimless : 0;
    if (aimless >= 20 && landings >= 50) {
      out.push({
        id: "local-attention-aimless",
        titleKey: "admin.localAimlessTitle",
        bodyKey: "admin.localAimlessBody",
        vars: { days, aimless, landings },
        href: "/playbook",
        severity: 74,
      });
    }
  }

  return out.sort((a, b) => b.severity - a.severity).slice(0, 4);
}
