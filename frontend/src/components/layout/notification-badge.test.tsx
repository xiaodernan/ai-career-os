import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";

vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard" }));
vi.mock("@/lib/i18n/locale-context", () => ({
  // Two rules on purpose: the nav label answers the English name so the link's
  // accessible name is readable, and the count key keeps its own spelling so
  // the test can prove the count reached the translator.
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, string | number>) => {
      if (vars && "count" in vars) return `${key}=${vars.count}`;
      return key === "nav.notifications" ? "Notifications" : key;
    },
    setLocale: () => {},
  }),
}));

const inbox = vi.hoisted(() => ({ unread: 3 }));
vi.mock("@/lib/hooks/resources", () => ({
  useNotifications: () => ({ data: { items: [], unread: inbox.unread } }),
}));

import { NavLinks } from "./sidebar";

/**
 * The bell on the notifications row (roadmap 29.3).
 *
 * The inbox is synthesized from clocks rather than from writes, so the count is
 * how a reader learns a reminder came due without opening the page. What is
 * pinned: the number rides the notifications row and no other; the link's
 * accessible name carries the count (in the rail the label is hidden, so the
 * name is the only thing a screen reader would hear); and a read inbox paints
 * nothing rather than a zero.
 */
describe("the sidebar's unread bell", () => {
  it("shows the count on the notifications row exactly once", () => {
    inbox.unread = 3;
    const html = renderToStaticMarkup(<NavLinks />);
    expect(html.match(/>3</g)?.length ?? 0).toBe(1);
    // The visible label is the link's name in the expanded rail; the count is
    // added to it, not swapped in for it.
    expect(html).not.toContain('aria-label="Notifications');
    const row = html.slice(html.indexOf('href="/notifications"'));
    expect(row.slice(0, row.indexOf("</a>"))).toContain("notifications.unreadBadge=3");
  });

  it("paints nothing when the inbox is read", () => {
    inbox.unread = 0;
    const html = renderToStaticMarkup(<NavLinks />);
    expect(html).not.toContain("notifications.unreadBadge");
    expect(html).not.toContain(">0<");
  });

  it("names the rail link with the count, because the rail hides the label", () => {
    inbox.unread = 3;
    const html = renderToStaticMarkup(<NavLinks collapsed />);
    expect(html).toContain('aria-label="Notifications, notifications.unreadBadge=3"');
    // The badge itself is decorative -- the name already carries the count.
    expect(html).toContain(">3<");
  });
});
