import type { AgentTraceEvent } from "@/components/ai/agent-timeline";

/**
 * A bounded agent-trace timeline for the live task stream (useTaskStream).
 *
 * HONEST BOUNDARY. As of this epic the `trace` SSE channel has no producer:
 * the pipelines publish `status` / `progress` / `done` / `error` and an idle
 * transport frame, while `trace` (like `token` and `artifact`) is declared in
 * the transport with nobody writing it yet, so today's timeline stays empty.
 * Nothing is OOMing. This module puts a hard ceiling on a render path that is
 * already wired -- useTaskStream folds frames into state and AgentTimeline
 * mounts one <li> per row -- so that when a producer does land, or a caller
 * hands it a long list, the state and the mounted DOM stay O(cap) instead of
 * growing with the run's length.
 *
 * ZERO DRIFT. With the cap not reached, foldTrace is the old reducer verbatim:
 * a same-id frame merges in place, a new frame settles the running rows, and
 * append order is untouched. settleTraceFold is the old `onDone` map. A
 * source-contract test pins the hook to these functions so a later edit cannot
 * quietly route around the bound.
 *
 * WHAT THE CAP COSTS. The oldest rows leave the visible window and are counted
 * in `omitted`; the surface reports that count rather than truncating in
 * silence. The just-appended (possibly running) row sits at the tail and always
 * survives a tail slice, so an in-flight step is never the one that rolls off.
 * A late frame for an id that already rolled off is treated as a new row (it
 * re-enters at the tail): the fold is a window over *frames*, not a permanent
 * per-id store, and `omitted` only falls when the stream resets.
 *
 * COMPLEXITY. Per frame O(cap) (settle + bounded filter); memory O(cap).
 * Before this module both were O(frames seen) and unbounded in run time.
 */

export interface TraceFold {
  /** Rows currently in the timeline, oldest first. */
  events: AgentTraceEvent[];
  /** Frames the window folded away since this stream (re)started. */
  omitted: number;
}

/**
 * Ceiling on mounted timeline rows. Chosen as a conservative bound, not a
 * measured P99 (there is no producer to measure yet): real runs are expected
 * well under it, and it only bites on a runaway or externally-supplied stream.
 */
export const TRACE_ROW_CAP = 200;

/** A fresh, empty fold. A factory, not a shared constant, so React sees a new reference on reset. */
export function emptyTraceFold(): TraceFold {
  return { events: [], omitted: 0 };
}

/**
 * A cap must be a positive, finite integer. A bad value degrades to the most
 * conservative window (one row) rather than removing the bound altogether.
 */
function bound(cap: number): number {
  return Number.isFinite(cap) && cap >= 1 ? Math.floor(cap) : 1;
}

/**
 * Fold one trace frame into a bounded timeline.
 *
 * Same-id merge and new-id append are the pre-cap reducer unchanged. Only when
 * the append would pass `cap` do the oldest rows leave, via one tail slice; the
 * fold always ends at <= cap. The new-id branch settles the previous running
 * rows before appending, so `next` is the only row that can still be running
 * when the slice runs, and it is at the tail — dropping the front can never
 * evict an in-flight step. `cap` is injected so the bound is testable small.
 */
export function foldTrace(
  fold: TraceFold,
  next: AgentTraceEvent,
  cap: number = TRACE_ROW_CAP
): TraceFold {
  const ceiling = bound(cap);
  const { events, omitted } = fold;
  const idx = events.findIndex((t) => t.id === next.id);
  if (idx >= 0) {
    // Same id: merge in place. Length is unchanged, so the cap never fires --
    // this is the pre-cap reducer verbatim.
    const merged = events.slice();
    merged[idx] = { ...merged[idx], ...next, status: next.status ?? "ok" };
    return { events: merged, omitted };
  }
  // New id: settle the in-flight rows, then append. Also the pre-cap reducer.
  const settled = events.map((t) => (t.status === "running" ? { ...t, status: "ok" as const } : t));
  const grown = [...settled, next];
  if (grown.length <= ceiling) return { events: grown, omitted };

  // Over the bound: drop the oldest `drop` rows off the front, keep the newest
  // `ceiling`. The settle above turned every earlier running row ok, so `next`
  // is the only possible running row and it is last — a front slice cannot
  // evict it. One bounded slice keeps the fold O(cap) and the order intact.
  const drop = grown.length - ceiling;
  return { events: grown.slice(drop), omitted: omitted + drop };
}

/** The terminal settle the stream runs on its `done` frame, wrapped for the fold. */
export function settleTraceFold(fold: TraceFold): TraceFold {
  return {
    events: fold.events.map((t) => (t.status === "running" ? { ...t, status: "ok" as const } : t)),
    omitted: fold.omitted,
  };
}
