import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  // The identity translator keeps the row's own copy visible: a key renders as that key, so this
  // test fails on a missing press rather than on a reworded sentence.
  useLocale: () => ({ locale: "en", t: (key: string) => key, setLocale: () => {} }),
}));

import { AttentionRow } from "./attention-row";
import type { AttentionItem } from "@/lib/api/types";

const due: AttentionItem = {
  id: "app-1",
  title: "Staff Engineer",
  companyName: "Northwind",
  status: "interview",
  reason: "reminder_due",
  reminderAt: "2026-10-29T09:00:00Z",
  updatedAt: "2026-10-27T12:00:00Z",
};

const stale: AttentionItem = {
  id: "app-2",
  title: "Product Designer",
  companyName: "Contoso",
  status: "applied",
  reason: "stale",
  updatedAt: "2026-10-10T12:00:00Z",
};

const render = (
  row: AttentionItem,
  busy = false,
  extra: Partial<Parameters<typeof AttentionRow>[0]> = {}
) =>
  renderToStaticMarkup(
    <AttentionRow row={row} busy={busy} onSnooze={() => {}} onClear={() => {}} {...extra} />
  );

describe("AttentionRow", () => {
  it("offers both answers on a reminder that has come due", () => {
    const html = render(due);
    expect(html).toContain("dashboard.reminderDue");
    expect(html).toContain("dashboard.snoozeReminder");
    expect(html).toContain("dashboard.clearReminder");
  });

  it("gives a stale row the one-press answer Epic 272 owes it", () => {
    const html = render(stale, false, { onProgress: () => {} });
    expect(html).toContain("dashboard.lastStep");
    expect(html).not.toContain("dashboard.snoozeReminder");
    expect(html).not.toContain("dashboard.clearReminder");
    // The stale row's answer: touch it today, and it leaves the list by having
    // been acted on. The press carries the row's own status unchanged.
    expect(html).toContain("dashboard.progressedToday");
  });

  it("renders no progress press when the caller wires none", () => {
    const html = renderToStaticMarkup(
      <AttentionRow row={stale} onSnooze={() => {}} onClear={() => {}} />
    );
    expect(html).not.toContain("dashboard.progressedToday");
  });

  it("keeps the progress press outside the link and honest while it writes", () => {
    const html = render(stale, false, { onProgress: () => {} });
    expect(html.indexOf("</a>")).toBeLessThan(html.indexOf("dashboard.progressedToday"));
    expect(html).toContain('title="dashboard.progressedTitle"');
  });

  it("puts the presses outside the link, so answering does not open the application", () => {
    const html = render(due);
    // `href="/applications?…"` belongs to the row's link; both presses must come after its
    // closing tag: a button nested in an anchor would navigate as well as answer.
    expect(html).toContain('href="/applications?application=app-1"');
    expect(html.indexOf("</a>")).toBeLessThan(html.indexOf("dashboard.snoozeReminder"));
  });

  it("disables both presses while this row's write is in flight", () => {
    const html = render(due, true);
    expect(html.match(/disabled=""/g)?.length).toBe(2);
  });

  it("says a recruiter replied when the newest reply rides the row", () => {
    const html = render({
      ...stale,
      replyAt: "2026-10-30T09:00:00Z",
      replySubject: "Re: interview",
      replyId: "mail-1",
    });
    expect(html).toContain("dashboard.replyWaiting");
    expect(html).toContain("Re: interview");
    // The sentence opens the letter itself, not the application behind it.
    expect(html).toContain('href="/replies?mail=mail-1"');
  });

  it("still says it as text when the payload carries no letter to open", () => {
    // An older row cached before the id existed carries the sentence but nothing to press; it
    // must not turn into a link to nowhere.
    const html = render({
      ...stale,
      replyAt: "2026-10-30T09:00:00Z",
      replySubject: "Re: interview",
    });
    expect(html).toContain("dashboard.replyWaiting");
    expect(html).not.toContain("/replies?mail=");
  });

  it("says nothing about a reply when none has landed", () => {
    expect(render(due)).not.toContain("dashboard.replyWaiting");
  });

  it("says no step rather than nothing when the row has no timestamp", () => {
    const html = renderToStaticMarkup(
      <AttentionRow row={{ id: "app-3", title: "Untitled" }} onSnooze={() => {}} onClear={() => {}} />
    );
    expect(html).toContain("dashboard.noStep");
  });
});
