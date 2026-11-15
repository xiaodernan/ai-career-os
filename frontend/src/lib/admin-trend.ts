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
