import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  // An identity translator with the variables left visible: a key renders as `key{a,b}`, so a
  // test fails on the wrong kind's sentence or a payload value that never reached the copy.
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, string | number>) =>
      vars ? `${key}{${Object.values(vars).join(",")}}` : key,
    setLocale: () => {},
  }),
}));

import { RecentActivityRow } from "./recent-activity";
import type { RecentActivityItem } from "@/lib/api/types";

const render = (row: RecentActivityItem) => renderToStaticMarkup(<RecentActivityRow row={row} />);

const base: RecentActivityItem = {
  id: "evt-1",
  applicationId: "app-1",
  createdAt: "2026-10-27T12:00:00Z",
};

describe("RecentActivityRow", () => {
  it("names each kind from the backend's own vocabulary", () => {
    expect(render({ ...base, kind: "status", payload: { to: "interview" } })).toContain(
      "dashboard.activityStatus"
    );
    expect(render({ ...base, kind: "note", payload: { note: "called back" } })).toContain(
      "dashboard.activityNote{called back}"
    );
    expect(render({ ...base, kind: "reminder", payload: { reminder_at: "2026-11-01" } })).toContain(
      "dashboard.activityReminderSet"
    );
    expect(render({ ...base, kind: "outcome", payload: { field: "rejection_reason" } })).toContain(
      "dashboard.activityOutcomeRejection"
    );
    expect(
      render({ ...base, kind: "reply", payload: { subject: "Re: your application", sender: "x@y" } })
    ).toContain("dashboard.activityReply{Re: your application}");
  });

  it("separates a cleared reminder from a set one", () => {
    expect(render({ ...base, kind: "reminder", payload: { cleared: true } })).toContain(
      "dashboard.activityReminderCleared"
    );
    expect(render({ ...base, kind: "reminder", payload: { cleared: true } })).not.toContain(
      "dashboard.activityReminderSet"
    );
  });

  it("names the two outcome fields the product writes and keeps a neutral word for a stranger", () => {
    expect(render({ ...base, kind: "outcome", payload: { field: "offer_compensation" } })).toContain(
      "dashboard.activityOutcomeCompensation"
    );
    expect(render({ ...base, kind: "outcome", payload: { field: "a_new_field" } })).toContain(
      "dashboard.activityOutcome"
    );
  });

  it("shows a localized stage badge for a status move", () => {
    // `stageLabel` resolves `interview` through the stages table, so the badge is the reader's word
    // and not the wire value; identity translation falls back to the roster's own English label.
    const html = render({ ...base, kind: "status", payload: { from: "applied", to: "interview" } });
    expect(html).toContain("data-slot=\"badge\"");
    expect(html).toContain("Interview");
    expect(html).not.toContain(">interview<");
  });

  it("keeps a real event whose kind the card does not know yet", () => {
    // Dropping it is the bug this card closes: a stranger gets a neutral line, not a missing row.
    const html = render({ ...base, kind: "a_future_kind", payload: {} });
    expect(html).toContain("dashboard.activityUnknown");
    expect(html).toContain("<li");
  });

  it("renders a payload-less row without inventing copy", () => {
    expect(render({ ...base, kind: "note" })).toContain("dashboard.activityNote{—}");
  });

  it("links a row with an application id and leaves an older row as text", () => {
    const linked = render({ ...base, kind: "status", payload: { to: "offer" } });
    expect(linked).toContain('href="/applications?application=app-1"');
    const plain = render({ id: "evt-2", kind: "status", payload: { to: "offer" } });
    expect(plain).not.toContain("href=");
    expect(plain).toContain("dashboard.activityStatus");
  });

  it("shows the event's own instant, not the payload's reminder time", () => {
    // `relativeTime` turns createdAt into a localized phrase; an invalid/missing date adds no line.
    const html = render({ ...base, kind: "note", payload: { note: "hi" } });
    expect(html).not.toContain("2026-10-27T12:00:00Z");
    const undated = render({ id: "evt-3", kind: "note", payload: { note: "hi" } });
    expect(undated).not.toContain("text-xs text-muted-foreground");
  });
});
