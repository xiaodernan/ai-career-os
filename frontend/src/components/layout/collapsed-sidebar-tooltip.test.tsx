import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";

vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard" }));
vi.mock("@/lib/i18n/locale-context", () => ({
  // The identity translator keeps the label rule visible: an item with a key
  // renders that key, an item without one keeps its English name.
  useLocale: () => ({ locale: "en", t: (key: string) => key, setLocale: () => {} }),
}));
// The rail now reads the inbox for its unread badge; this test is about the
// labels, and an unanswered query is the state before the first answer.
vi.mock("@/lib/hooks/resources", () => ({ useNotifications: () => ({ data: undefined }) }));

import { NavLinks } from "./sidebar";
import { NAV_ITEMS } from "./nav";

/**
 * The collapsed rail keeps the label in a tooltip instead of the row. Radix
 * throws when a tooltip is rendered outside a provider, and because the
 * collapsed state is restored from localStorage the throw happens on the next
 * load too -- the whole shell ends up in its error boundary. A server render
 * reaches the same code path, so it is the cheapest place to hold it.
 */

const expectedLabel = (item: (typeof NAV_ITEMS)[number]) => item.labelKey ?? item.label;

describe("the collapsed sidebar", () => {
  it("renders one link per nav item without a provider throwing", () => {
    const html = renderToStaticMarkup(<NavLinks collapsed />);
    expect(html.match(/href="\//g)?.length ?? 0).toBe(NAV_ITEMS.length);
  });

  it("renders the icon-only branch, not the labelled one", () => {
    const html = renderToStaticMarkup(<NavLinks collapsed />);
    for (const item of NAV_ITEMS) {
      expect(html, `${item.label} is still visible in the collapsed rail`).not.toContain(
        `>${expectedLabel(item)}<`
      );
    }
  });

  it("keeps every label visible when expanded (control)", () => {
    const html = renderToStaticMarkup(<NavLinks />);
    for (const item of NAV_ITEMS) {
      expect(html, `${item.label} is missing from the expanded rail`).toContain(
        `>${expectedLabel(item)}<`
      );
    }
  });
});
