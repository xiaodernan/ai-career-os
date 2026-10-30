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

const render = (row: AttentionItem, busy = false) =>
  renderToStaticMarkup(<AttentionRow row={row} busy={busy} onSnooze={() => {}} onClear={() => {}} />);

describe("AttentionRow", () => {
  it("offers both answers on a reminder that has come due", () => {
    const html = render(due);
    expect(html).toContain("dashboard.reminderDue");
    expect(html).toContain("dashboard.snoozeReminder");
    expect(html).toContain("dashboard.clearReminder");
  });

  it("leaves a stale row with nothing to press", () => {
    const html = render(stale);
    expect(html).toContain("dashboard.lastStep");
    expect(html).not.toContain("dashboard.snoozeReminder");
    expect(html).not.toContain("dashboard.clearReminder");
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

  it("says no step rather than nothing when the row has no timestamp", () => {
    const html = renderToStaticMarkup(
      <AttentionRow row={{ id: "app-3", title: "Untitled" }} onSnooze={() => {}} onClear={() => {}} />
    );
    expect(html).toContain("dashboard.noStep");
  });
});
