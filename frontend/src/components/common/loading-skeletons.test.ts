import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

/**
 * The skeletons are the loaded layout's stand-ins, and this pins them to it.
 *
 * A skeleton that approximates its loaded counterpart shows the reader one
 * layout and delivers another -- the shimmer lands in the wrong places, the
 * content jumps on arrival. When Epic 122 pinned LoadingCardSkeleton to the
 * StatCard's anatomy (icon bar + label row, big-number bar, hint line), it
 * had to be by hand: nothing failed when the shape drifted. This suite is
 * that failure mode, turned into a gate:
 *
 * - every exported skeleton declares itself to assistive technology (role=status
 *   or aria-hidden) -- a shimmer nobody announced is not an answer, an unlabelled
 *   one is worse than silence;
 * - LoadingCardSkeleton renders the loaded card's own anatomy: CardHeader with
 *   the icon bar beside the label and the big-number bar, CardContent carrying
 *   the hint line;
 * - the metric grid's breakpoints match the dashboard's loaded grid, so the
 *   strip does not rewrap on arrival;
 * - the route-segment fallback imports only exported skeletons, so the fallback
 *   cannot drift from the module's public surface.
 */

const SKELETONS = readFileSync(
  fileURLToPath(new URL("./loading-skeletons.tsx", import.meta.url)),
  "utf-8"
);
const LOADING = readFileSync(
  fileURLToPath(new URL("../../app/(app)/loading.tsx", import.meta.url)),
  "utf-8"
);
const DASHBOARD = readFileSync(
  fileURLToPath(new URL("../../app/(app)/dashboard/page.tsx", import.meta.url)),
  "utf-8"
);

/** One exported function body per match, from its declaration to the next `export function`. */
function skeletonBodies(): Map<string, string> {
  const bodies = new Map<string, string>();
  const marks = [...SKELETONS.matchAll(/export function (Loading\w+Skeleton)/g)];
  for (let i = 0; i < marks.length; i++) {
    const end = marks[i + 1]?.index ?? SKELETONS.length;
    bodies.set(marks[i][1], SKELETONS.slice(marks[i].index, end));
  }
  return bodies;
}

describe("the loading skeletons hold the loaded shapes", () => {
  const bodies = skeletonBodies();

  it("exports every skeleton as a named Loading*Skeleton", () => {
    expect(bodies.size).toBeGreaterThanOrEqual(7);
    for (const name of bodies.keys()) {
      expect(name).toMatch(/^Loading[A-Z]/);
    }
  });

  it("declares itself to assistive technology, whatever shape it shimmers", () => {
    for (const [name, body] of bodies) {
      const announces = body.includes('role="status"') || body.includes("aria-hidden") || body.includes("aria-label");
      expect(announces, `${name} carries neither role="status" nor aria-hidden`).toBe(true);
    }
  });

  it("pins LoadingCardSkeleton to the loaded StatCard anatomy", () => {
    const card = bodies.get("LoadingCardSkeleton");
    expect(card).toBeDefined();
    // The loaded card is CardHeader (icon bar + label beside it, then the big
    // number) + CardContent (the hint line). The skeleton renders the same seams.
    expect(card).toContain("<CardHeader>");
    expect(card).toContain("<CardContent>");
    expect(card).toMatch(/<CardDescription[^>]*>\s*<Skeleton className="size-3\.5/);
    expect(card).toMatch(/<CardContent>/);
  });

  it("ships the metric grid's breakpoints from the dashboard's loaded strip", () => {
    expect(DASHBOARD).toContain("sm:grid-cols-2");
    expect(SKELETONS).toContain("grid gap-4 sm:grid-cols-2 xl:grid-cols-4");
  });

  it("keeps the route fallback behind the module's public surface", () => {
    const imported = [...LOADING.matchAll(/import \{ ([^}]+) \} from "@\/components\/common\/loading-skeletons"/g)]
      .flatMap((m) => m[1].split(",").map((s) => s.trim()));
    expect(imported.length).toBeGreaterThan(0);
    for (const name of imported) {
      expect(bodies.has(name), `${name} is imported by (app)/loading.tsx but not exported by loading-skeletons`).toBe(true);
    }
  });
});
