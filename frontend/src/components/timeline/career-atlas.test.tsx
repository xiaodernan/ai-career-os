import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { TimelineEntry } from "@/lib/api/types";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: "en", t: (key: string) => `[${key}]`, setLocale: () => undefined }),
}));

import { buildAtlas, CareerAtlas } from "./career-atlas";

const EVENTS: TimelineEntry[] = [
  { at: "2026-09-01T09:00:00Z", kind: "application", title: "Backend Engineer · Acme", refId: "a-1", summary: "applied" },
  { at: "2026-09-02T09:00:00Z", kind: "interview", title: "Mock interview 1", refId: "i-1", summary: "mixed" },
  { at: "2026-09-03T09:00:00Z", kind: "unknown-future-kind", title: "A fact without a name", refId: "x-1", summary: "still a fact" },
];

describe("buildAtlas", () => {
  it("turns the reader's own events into ordered, counted regions", () => {
    const regions = buildAtlas(EVENTS);
    expect(regions.map((region) => region.kind)).toEqual(["application", "interview", "unknown"]);
    expect(regions[0].count).toBe(1);
    expect(regions[2].labelKey).toBe("timeline.kinds.unknown");
    expect(regions[2].sites[0].title).toBe("A fact without a name");
  });

  it("projects sites deterministically and admits when it stops drawing", () => {
    const many: TimelineEntry[] = Array.from({ length: 26 }, (_, i) => ({
      at: `2026-09-${String(i + 1).padStart(2, "0")}T09:00:00Z`,
      kind: "note",
      title: `Note ${i + 1}`,
      refId: `n-${i + 1}`,
      summary: "",
    }));
    const first = buildAtlas(many)[0];
    const again = buildAtlas(many)[0];
    expect(first.sites).toHaveLength(24);
    expect(first.hidden).toBe(2);
    expect(first.count).toBe(26);
    expect(first.sites).toEqual(again.sites);
    expect(first.sites.every((site) => site.x >= 0 && site.x <= 100 && site.y >= 0 && site.y <= 100)).toBe(true);
  });
});

describe("CareerAtlas", () => {
  it("renders regions, sites and the honest frontier links from locale keys", () => {
    const html = renderToStaticMarkup(<CareerAtlas events={EVENTS} />);
    expect(html).toContain("[timeline.atlasTitle]");
    expect(html).toContain("[timeline.kinds.application]");
    expect(html).toContain("Backend Engineer · Acme");
    expect(html).toContain("[timeline.kinds.unknown]");
    expect(html).toContain('href="/jobs"');
    expect(html).toContain("[timeline.atlasFrontierNetworking]");
    expect(html).toContain('role="img"');
  });

  it("shows an uncharted map instead of inventing a world on an empty ledger", () => {
    const html = renderToStaticMarkup(<CareerAtlas events={[]} />);
    expect(html).toContain("[timeline.atlasEmpty]");
    expect(html).not.toContain("[timeline.kinds.application]");
    expect(html).toContain("[timeline.atlasFrontierTitle]");
  });
});
