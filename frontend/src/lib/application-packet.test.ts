import { describe, expect, it } from "vitest";

import { packetCompleteness } from "./application-packet";
import type { Application } from "@/lib/api/types";

const app = (ids: Partial<Application>): Application => ({
  id: "app-1",
  title: "Staff Backend Engineer",
  status: "applied",
  ...ids,
});

describe("packetCompleteness", () => {
  it("counts the three links and names the missing ones in display order", () => {
    expect(packetCompleteness(app({ resumeVersionId: "rv", matchId: "m" }))).toEqual({
      linked: 2,
      total: 3,
      missing: ["jd"],
    });
  });

  it("reports an untouched application as three missing, not as a broken packet", () => {
    expect(packetCompleteness(app({})).missing).toEqual(["resume", "jd", "match"]);
  });

  it("is complete only when every link is present", () => {
    const full = packetCompleteness(app({ resumeVersionId: "rv", jdId: "jd", matchId: "m" }));
    expect(full.linked).toBe(3);
    expect(full.missing).toEqual([]);
  });
});
