import { describe, expect, it } from "vitest";

import {
  applyStatusEvent,
  progressDetail,
  statusFromEvent,
  type ProcessingStep,
  type StatusEvent,
} from "@/components/ai/processing-steps";
import { INGEST_SEED } from "@/components/resumes/upload-dropzone";

/**
 * The run stream's step fold, verified against the frames the ingestion pipeline
 * actually publishes. `ai-service/app/ingestion/pipeline.py` is the producer and
 * the backend relay renames nothing, so this list is the wire contract.
 */
type Frame = [event: string, data: StatusEvent];

const INGEST_WIRE: Frame[] = [
  ["status", { step: "extracting", state: "active" }],
  ["status", { step: "extracting", state: "done" }],
  ["status", { step: "cleaning", state: "active" }],
  ["status", { step: "cleaning", state: "done" }],
  ["status", { step: "chunking", state: "active" }],
  ["status", { step: "chunking", state: "done", count: 150 }],
  ["status", { step: "embedding", state: "active" }],
  ["progress", { step: "embedding", done: 64, total: 150 }],
  ["progress", { step: "embedding", done: 128, total: 150 }],
  ["progress", { step: "embedding", done: 150, total: 150 }],
  ["status", { step: "embedding", state: "done" }],
  ["status", { step: "indexing", state: "active" }],
  ["status", { step: "indexing", state: "done" }],
];

/** useTaskStream seeds row 0 active and the rest pending. */
function seeded(): ProcessingStep[] {
  return INGEST_SEED.map((s, i): ProcessingStep => ({ ...s, status: i === 0 ? "active" : "pending" }));
}

function fold(frames: Frame[]): ProcessingStep[] {
  return frames.reduce<ProcessingStep[]>((prev, [, data]) => applyStatusEvent(prev, data), seeded());
}

describe("statusFromEvent", () => {
  it("reads the state the pipelines send", () => {
    expect(statusFromEvent({ step: "chunking", state: "active" })).toBe("active");
    expect(statusFromEvent({ step: "chunking", state: "done" })).toBe("done");
    expect(statusFromEvent({ step: "chunking", state: "error" })).toBe("error");
  });

  it("still honours the older status/progress spellings", () => {
    expect(statusFromEvent({ step: "a", status: "done" })).toBe("done");
    expect(statusFromEvent({ step: "a", status: "error" })).toBe("error");
    expect(statusFromEvent({ step: "a", progress: 100 })).toBe("done");
  });

  it("treats a frame that only names a step as in flight", () => {
    // The agent orchestrator emits {"agent","step"} sentences with no state at all.
    expect(statusFromEvent({ step: "Thinking" })).toBe("active");
  });
});

describe("progressDetail", () => {
  it("formats a counted frame", () => {
    expect(progressDetail({ step: "embedding", done: 64, total: 150 })).toBe("64 / 150");
  });

  it("needs both numbers", () => {
    expect(progressDetail({ step: "embedding", done: 64 })).toBeUndefined();
    expect(progressDetail({ step: "embedding", total: 150 })).toBeUndefined();
    expect(progressDetail({ step: "chunking", state: "done", count: 150 })).toBeUndefined();
  });
});

describe("applyStatusEvent over the ingestion publish sequence", () => {
  it("lands on exactly the seeded rows, all done", () => {
    const steps = fold(INGEST_WIRE);
    expect(steps.map((s) => s.id)).toEqual([
      "extracting",
      "cleaning",
      "chunking",
      "embedding",
      "indexing",
    ]);
    expect(steps.every((s) => s.status === "done")).toBe(true);
    expect(steps.map((s) => s.label)).toEqual(INGEST_SEED.map((s) => s.label));
  });

  it("keys each frame onto its seeded row instead of appending a raw-id duplicate", () => {
    expect(INGEST_WIRE.filter(([, d]) => !INGEST_SEED.some((s) => s.id === d.step))).toEqual([]);
  });

  it("reports embedding counts on the running row without ending it", () => {
    const steps = fold(INGEST_WIRE.slice(0, 9)); // through done:128
    const embedding = steps.find((s) => s.id === "embedding");
    expect(embedding?.status).toBe("active");
    expect(embedding?.detail).toBe("128 / 150");
    // …and a progress frame never grew the checklist.
    expect(steps).toHaveLength(INGEST_SEED.length);
  });

  it("leaves later stages pending while an earlier one runs", () => {
    const steps = fold(INGEST_WIRE.slice(0, 7)); // extracting..chunking done, embedding active
    expect(steps.map((s) => s.status)).toEqual(["done", "done", "done", "active", "pending"]);
  });

  it("keeps an unknown step appending instead of vanishing", () => {
    // The agent orchestrator / RAG pipeline publish steps no seed names, so the
    // aligning the ingest seed must not cost us the ability to show a new one.
    let steps: ProcessingStep[] = [];
    steps = applyStatusEvent(steps, { agent: "career", step: "Thinking" });
    steps = applyStatusEvent(steps, { agent: "career", step: "Calling get_profile" });
    expect(steps.map((s) => s.status)).toEqual(["done", "active"]);
    expect(steps.map((s) => s.label)).toEqual(["Thinking", "Calling get_profile"]);
  });

  it("ignores a frame with no step rather than clearing the list", () => {
    const before = seeded();
    expect(applyStatusEvent(before, { state: "done" })).toBe(before);
  });
});

describe("the seed matches the producer", () => {
  it("lists every published ingestion step, in publish order", () => {
    const published: string[] = [];
    for (const [, data] of INGEST_WIRE) {
      const step = String(data.step);
      if (published[published.length - 1] !== step) published.push(step);
    }
    expect(INGEST_SEED.map((s) => s.id)).toEqual(published);
  });

  it("names rows for people, not for the pipeline", () => {
    for (const row of INGEST_SEED) expect(row.label).not.toMatch(/_/);
  });
});
