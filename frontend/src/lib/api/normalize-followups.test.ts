import { describe, expect, it } from "vitest";

import { normalizeDashboard } from "@/lib/api/normalize";

/**
 * The dashboard's follow-up tile (11.3), read through the whole payload.
 *
 * The tile is the one place the copilot and the screen have to agree about
 * *who* is overdue: the agent's `get_follow_ups` tool and this row list both
 * come from the same ranked contacts, so a change to one that does not reach
 * the other is a change nobody sees.
 *
 * What this holds is the shape the card renders: the row carries a name, a
 * priority and the draft the engine wrote, and a payload with no rows leaves
 * the tile absent rather than rendering an empty list of nothing.
 */

const BASE = {
  kanban: { statusCounts: {}, total: 0, offers: 0 },
  interviews: 0,
  avgMatch: null,
  needsAttention: 0,
  attention: [],
  currentResume: null,
  skillGaps: null,
  recommendedJobs: [],
  recentRuns: [],
  recentActivity: [],
};

describe("the dashboard's follow-up tile", () => {
  it("carries the engine's ranked row and its own draft", () => {
    const dashboard = normalizeDashboard({
      ...BASE,
      followUps: [
        {
          id: "c1",
          name: "Alex Chen",
          company: "FakeCorp",
          relation: "recruiter",
          priority: "overdue",
          daysSince: 45,
          cadenceDays: 30,
          suggestedMessage: "Hi Alex — hope you've been well.",
        },
      ],
    });
    expect(dashboard?.followUps).toHaveLength(1);
    const row = dashboard!.followUps![0];
    expect(row.name).toBe("Alex Chen");
    expect(row.priority).toBe("overdue");
    // The draft is the engine's, so the card never writes a message of its own.
    expect(row.suggestedMessage).toBe("Hi Alex — hope you've been well.");
  });

  it("leaves the tile absent when the engine sent no rows", () => {
    // The card reads "no follow-ups needed" — a different sentence from a card
    // that never learned whether there were any, and the difference matters
    // for a user who has not added a contact yet.
    const dashboard = normalizeDashboard({ ...BASE, followUps: [] });
    expect(dashboard?.followUps).toBeUndefined();
  });

  it("does not invent a cadence the engine did not send", () => {
    const dashboard = normalizeDashboard({
      ...BASE,
      followUps: [{ id: "c1", name: "Alex Chen", priority: "soon" }],
    });
    const row = dashboard!.followUps![0];
    expect(row.daysSince).toBeNull();
    expect(row.cadenceDays).toBeNull();
    expect(row.suggestedMessage).toBeNull();
  });
});
