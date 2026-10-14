import { describe, expect, it } from "vitest";

import { pickResumeId, pickTaskId } from "@/lib/resume-upload";

/**
 * The seam where "the upload answered" meets "the stream starts". The ai-service's
 * ingest answer nests the task under `ingest` and the upload route's own resolve
 * returns it top-level; both spellings exist on both the camel and the snake side
 * of the relay. A reader that stops recognizing one of the four shapes loses the
 * live progress panel *silently* — the upload still succeeds — so every spelling
 * is pinned here rather than discovered in a browser.
 */

describe("pickTaskId", () => {
  it("reads the top-level task id in both spellings", () => {
    expect(pickTaskId({ taskId: "t-1" })).toBe("t-1");
    expect(pickTaskId({ task_id: "t-2" })).toBe("t-2");
  });

  it("reads the nested ingest answer both spellings too", () => {
    expect(pickTaskId({ ingest: { taskId: "t-3" } })).toBe("t-3");
    expect(pickTaskId({ ingest: { task_id: "t-4" } })).toBe("t-4");
  });

  it("has nothing for an answer that carries neither", () => {
    expect(pickTaskId({})).toBeNull();
    expect(pickTaskId({ ingest: {} })).toBeNull();
    expect(pickTaskId(null)).toBeNull();
    expect(pickTaskId(undefined)).toBeNull();
    // A non-string id is not an id — `str` refuses it rather than coercing.
    expect(pickTaskId({ taskId: { id: 7 } })).toBeNull();
  });
});

describe("pickResumeId", () => {
  it("reads the top-level resume id in both spellings", () => {
    expect(pickResumeId({ resumeId: "r-1" })).toBe("r-1");
    expect(pickResumeId({ resume_id: "r-2" })).toBe("r-2");
  });

  it("falls back to a nested resume object's id", () => {
    expect(pickResumeId({ resume: { id: "r-3" } })).toBe("r-3");
  });

  it("has nothing for an answer that carries neither", () => {
    expect(pickResumeId({})).toBeNull();
    expect(pickResumeId({ resume: {} })).toBeNull();
    expect(pickResumeId(null)).toBeNull();
  });
});
