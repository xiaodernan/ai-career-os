import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import type { AgentTraceEvent } from "@/components/ai/agent-timeline";
import {
  TRACE_ROW_CAP,
  emptyTraceFold,
  foldTrace,
  settleTraceFold,
  type TraceFold,
} from "@/lib/trace-fold";

function ev(id: string, over: Partial<AgentTraceEvent> = {}): AgentTraceEvent {
  return { id, kind: "step_start", label: id, status: "running", ...over };
}

function feed(frames: AgentTraceEvent[], cap: number): TraceFold {
  return frames.reduce<TraceFold>((fold, next) => foldTrace(fold, next, cap), emptyTraceFold());
}

/**
 * The pre-cap reducer, copied verbatim from useTaskStream's `onTrace`. It is the
 * zero-drift oracle: for any stream shorter than the cap, foldTrace must produce
 * exactly the array this function did, with `omitted` still zero.
 */
function legacyTraceReducer(prev: AgentTraceEvent[], next: AgentTraceEvent): AgentTraceEvent[] {
  const idx = prev.findIndex((t) => t.id === next.id);
  if (idx >= 0) {
    const merged = [...prev];
    merged[idx] = { ...merged[idx], ...next, status: next.status ?? "ok" };
    return merged;
  }
  // a new step means the previous running one is done
  const settled = prev.map((t) => (t.status === "running" ? { ...t, status: "ok" as const } : t));
  return [...settled, next];
}

/** The pre-cap `onDone` settle, copied verbatim. */
function legacyOnDone(prev: AgentTraceEvent[]): AgentTraceEvent[] {
  return prev.map((t) => (t.status === "running" ? { ...t, status: "ok" } : t));
}

/** A mixed wire sequence: new ids, same-id merges, settles and an error flip. */
const WIRE: AgentTraceEvent[] = [
  ev("a", { label: "extract" }),
  ev("a", { label: "extract", status: "ok", durationMs: 12 }),
  ev("b", { kind: "retrieval" }),
  ev("b", { kind: "retrieval", status: "error", durationMs: 3 }),
  ev("c", { kind: "tool_call", payload: { tool: "web" } }),
  ev("c", { status: "ok", durationMs: 40 }),
  ev("d", { status: "ok" }),
  ev("d", { status: "ok", durationMs: 5 }),
];

describe("foldTrace — zero drift while the cap is not reached", () => {
  it("matches the old reducer frame for frame, and never counts a fold", () => {
    let legacy: AgentTraceEvent[] = [];
    let fold = emptyTraceFold();
    // A cap larger than the stream must be indistinguishable from the old code.
    const roomyCap = WIRE.length + 10;
    for (const next of WIRE) {
      legacy = legacyTraceReducer(legacy, next);
      fold = foldTrace(fold, next, roomyCap);
      expect(fold.events).toEqual(legacy);
      expect(fold.omitted).toBe(0);
    }
  });

  it("merges a repeated id in place without appending or settling its siblings", () => {
    const start = feed(WIRE.slice(0, 3), 100); // a(ok), b(running)
    const merged = foldTrace(start, ev("a", { status: "ok", durationMs: 99 }), 100);
    expect(merged.events).toHaveLength(start.events.length);
    expect(merged.events.find((t) => t.id === "a")?.durationMs).toBe(99);
    expect(merged.events.find((t) => t.id === "b")?.status).toBe("running");
    expect(merged.omitted).toBe(0);
  });

  it("settles the previous running row when a genuinely new step lands", () => {
    const fold = feed([ev("a"), ev("b")], 100);
    expect(fold.events.map((t) => t.status)).toEqual(["ok", "running"]);
  });
});

describe("foldTrace — the bound and its honest count", () => {
  it("keeps the newest `cap` rows in order and counts every row it drops", () => {
    const fold = feed([ev("a"), ev("b"), ev("c"), ev("d"), ev("e")], 3);
    expect(fold.events.map((t) => t.id)).toEqual(["c", "d", "e"]);
    expect(fold.omitted).toBe(2);
  });

  it("holds a cap of one and still reports the two folds", () => {
    const fold = feed([ev("a"), ev("b"), ev("c")], 1);
    expect(fold.events.map((t) => t.id)).toEqual(["c"]);
    expect(fold.omitted).toBe(2);
  });

  it("does not touch `omitted` on a same-id merge even when the window is full", () => {
    const full = feed([ev("a"), ev("b"), ev("c")], 2); // kept b,c, omitted 1
    const merged = foldTrace(full, ev("c", { status: "ok", durationMs: 7 }), 2);
    expect(merged.events).toHaveLength(2);
    expect(merged.events.find((t) => t.id === "c")?.durationMs).toBe(7);
    expect(merged.omitted).toBe(1); // unchanged: a merge is not a new frame
  });

  it("never evicts the in-flight step: an append settles older running rows, and the new tail survives a fold", () => {
    // A new step first marks the previous running rows ok (zero-drift reducer),
    // so by the time the cap slices, `next` is the only running row and it is
    // last. Dropping from the front can therefore never evict an in-flight step.
    const base: TraceFold = {
      events: [ev("a", { status: "ok" }), ev("b", { status: "running" })],
      omitted: 0,
    };
    const grown = foldTrace(base, ev("c", { status: "running" }), 2);
    expect(grown.events.map((t) => t.id)).toEqual(["b", "c"]);
    expect(grown.events.map((t) => t.status)).toEqual(["ok", "running"]);
    expect(grown.omitted).toBe(1);
  });

  it("treats a late frame for a rolled-off id as a new tail row, without lying about the count", () => {
    const rolled = feed([ev("a"), ev("b"), ev("c")], 2); // kept b,c, omitted 1
    const late = foldTrace(rolled, ev("a", { status: "ok" }), 2);
    expect(late.events.map((t) => t.id)).toEqual(["c", "a"]);
    expect(late.omitted).toBe(2); // a rolled off once; the late frame pushes b out
  });

  it("degrades a non-positive or non-finite cap to one row instead of removing the bound", () => {
    for (const bad of [0, -3, Number.NaN, Number.POSITIVE_INFINITY]) {
      const fold = feed([ev("a"), ev("b"), ev("c")], bad);
      expect(fold.events).toHaveLength(1);
      expect(fold.omitted).toBe(2);
    }
  });

  it("stays bounded over a long run: 1000 frames at the default cap", () => {
    const frames = Array.from({ length: 1000 }, (_, i) => ev(`step-${i}`, { status: "ok" }));
    let fold = emptyTraceFold();
    let peak = 0;
    for (const next of frames) {
      fold = foldTrace(fold, next); // default TRACE_ROW_CAP
      peak = Math.max(peak, fold.events.length);
      expect(fold.events.length).toBeLessThanOrEqual(TRACE_ROW_CAP);
    }
    expect(peak).toBe(TRACE_ROW_CAP);
    expect(fold.events).toHaveLength(TRACE_ROW_CAP);
    expect(fold.events[0].id).toBe(`step-${1000 - TRACE_ROW_CAP}`);
    expect(fold.events.at(-1)?.id).toBe("step-999");
    expect(fold.omitted).toBe(1000 - TRACE_ROW_CAP);
  });

  it("never mutates the fold it is given", () => {
    const fold: TraceFold = { events: [ev("a"), ev("b")], omitted: 0 };
    const snapshot = structuredClone(fold);
    foldTrace(fold, ev("c", { status: "ok" }), 2);
    foldTrace(fold, ev("a", { status: "ok" }), 2);
    expect(fold).toEqual(snapshot);
  });
});

describe("settleTraceFold — the terminal `done` settle", () => {
  it("turns running rows ok, leaves the rest, and preserves the honest count", () => {
    const fold: TraceFold = {
      events: [ev("a", { status: "ok" }), ev("b", { status: "running" }), ev("c", { status: "error" })],
      omitted: 4,
    };
    const settled = settleTraceFold(fold);
    expect(settled.events).toEqual(legacyOnDone(fold.events));
    expect(settled.omitted).toBe(4);
  });

  it("does not change the window or the fold's identity of rows", () => {
    const fold = feed([ev("a"), ev("b"), ev("c")], 2); // b,c, omitted 1
    const settled = settleTraceFold(fold);
    expect(settled.events.map((t) => t.id)).toEqual(["b", "c"]);
    expect(settled.omitted).toBe(1);
  });
});

/** The hook is the only thing that can grow the fold; pin it to the pure functions. */
describe("the live stream stays wired to the bound", () => {
  const source = readFileSync(
    new URL("../components/ai/task-stream.tsx", import.meta.url),
    "utf8"
  );
  const copy = readFileSync(new URL("./i18n/translations.ts", import.meta.url), "utf8");

  it("folds every trace frame through foldTrace, not a bare state append", () => {
    expect(source).toContain("foldTrace(prev, next)");
    expect(source).not.toMatch(/setTraces\s*\(/);
    expect(source).not.toContain("return [...settled, next];");
  });

  it("settles the window through settleTraceFold on `done`", () => {
    expect(source).toContain("settleTraceFold");
  });

  it("exposes the honest count on the stream state", () => {
    expect(source).toContain("tracesOmitted: fold.omitted");
  });

  it("reports the folded count to the reader instead of hiding it", () => {
    expect(source).toMatch(/tracesOmitted\s*>\s*0/);
    expect(source).toContain('t("ai.taskStream.foldedSteps"');
    // Both halves of the translation table answer the new key.
    expect(copy.match(/foldedSteps:/g) ?? []).toHaveLength(2);
  });
});
