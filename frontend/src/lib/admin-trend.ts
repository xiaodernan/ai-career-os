/**
 * The trend cards' own arithmetic (Epic 251).
 *
 * Pure SVG polyline math for the overseer's ledger — no chart library, no locale, no copy.
 * Every coordinate derives from the numbers the caller hands in, baseline zero, oldest point
 * on the left.
 */

export interface Sparkline {
  /** `x,y` pairs for a `<polyline>`, oldest first. */
  points: string;
  /** The x/y of the final (newest) point — where the dot is drawn. */
  last: { x: number; y: number };
  /** Index of the largest value (first of a tie), or -1 for empty input. */
  peak: number;
}

export function sparkline(values: number[], width = 120, height = 36, pad = 3): Sparkline | null {
  if (values.length === 0) {
    return null;
  }
  const max = Math.max(...values, 0);
  const spanX = width - pad * 2;
  const step = values.length === 1 ? 0 : spanX / (values.length - 1);
  // Counts can't go negative; if a broken caller hands us one anyway, it clamps to the axis
  // rather than drawing below the box.
  const yFor = (value: number) =>
    max === 0 ? height - pad : height - pad - Math.max(value, 0) * ((height - pad * 2) / max);

  const coords = values.map((value, index) => {
    const x = pad + step * index;
    const y = yFor(value);
    return { x: Number(x.toFixed(2)), y: Number(y.toFixed(2)) };
  });

  let peak = 0;
  for (let i = 1; i < values.length; i++) {
    if (values[i] > values[peak]) {
      peak = i;
    }
  }

  return {
    points: coords.map((c) => `${c.x},${c.y}`).join(" "),
    last: coords[coords.length - 1],
    peak: max === 0 ? -1 : peak,
  };
}

export function seriesTotal(values: number[]): number {
  return values.reduce((sum, value) => sum + value, 0);
}

export interface TrendProjection {
  /** Solid polyline: the measured weeks, oldest leftmost, same math as `sparkline`. */
  points: string;
  /** Dashed polyline: last measured point plus `ahead` straight-line projections. */
  projectionPoints: string;
  /** Where the newest measured point sits — the seam between solid and dashed. */
  last: { x: number; y: number };
  /** Least-squares slope per week. Negative means the window sloped downward. */
  slope: number;
  /** R² of the fit on the measured window, 0..1 (0 for a perfectly flat line). */
  r2: number;
  /** Index of the largest measured value (first of a tie), or -1 for empty input. */
  peak: number;
}

/**
 * A straight line through the window — the projection the operator asked for, and nothing
 * more than it claims to be.
 *
 * Least squares, baseline zero on the projection side only (measured weeks keep their real
 * y). The projected week count defaults to four; falling windows clamp at zero rather than
 * grow negative inventions. The caller is expected to label this as a straight-line read,
 * not a forecast — the number is arithmetic, not a promise.
 */
export function projectedSparkline(
  values: number[],
  ahead = 4,
  width = 120,
  height = 36,
  pad = 3,
): TrendProjection | null {
  if (values.length === 0 || ahead < 1) {
    return null;
  }
  const n = values.length;
  const xMean = (n - 1) / 2;
  const yMean = seriesTotal(values) / n;
  let sxy = 0;
  let sxx = 0;
  let sst = 0;
  for (let i = 0; i < n; i++) {
    const dx = i - xMean;
    sxy += dx * (values[i] - yMean);
    sxx += dx * dx;
    sst += (values[i] - yMean) ** 2;
  }
  const slope = sxx === 0 ? 0 : sxy / sxx;
  const intercept = yMean - slope * xMean;
  const r2 = sst === 0 ? 0 : Math.max(0, Math.min(1, 1 - (sst - (sxy * sxy) / (sxx || 1)) / sst));

  const maxMeasured = Math.max(...values, 0);
  const maxProjected = Math.max(0, ...Array.from({ length: ahead }, (_, i) => intercept + slope * (n + i)));
  const max = Math.max(maxMeasured, maxProjected);
  const spanX = width - pad * 2;
  const slots = n + ahead;
  const step = slots === 1 ? 0 : spanX / (slots - 1);
  const yFor = (value: number) => (max === 0 ? height - pad : height - pad - Math.max(value, 0) * ((height - pad * 2) / max));

  const xAt = (i: number) => Number((pad + step * i).toFixed(2));
  const solid: string[] = [];
  for (let i = 0; i < n; i++) {
    solid.push(`${xAt(i)},${Number(yFor(values[i]).toFixed(2))}`);
  }
  // The dashed half starts from the last measured point, so the two segments share a seam.
  const dashed: string[] = [solid[solid.length - 1]];
  for (let i = 0; i < ahead; i++) {
    const projected = Math.max(0, intercept + slope * (n + i));
    dashed.push(`${xAt(n + i)},${Number(yFor(projected).toFixed(2))}`);
  }

  let peak = 0;
  for (let i = 1; i < n; i++) {
    if (values[i] > values[peak]) {
      peak = i;
    }
  }

  return {
    points: solid.join(" "),
    projectionPoints: dashed.join(" "),
    last: (() => {
      const [x, y] = solid[solid.length - 1].split(",").map(Number);
      return { x, y };
    })(),
    slope,
    r2,
    peak: maxMeasured === 0 ? -1 : peak,
  };
}
