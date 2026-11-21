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
    // The application region is already charted, so its door is not advertised.
    expect(html).not.toContain("[timeline.atlasFrontierApplications]");
    expect(html).toContain('role="img"');
  });

  it("361: makes every site on the map a door a keyboard can walk to", () => {
    // The map used to be dots: a reader could look at the world but not step into
    // it, and the only way in was the word list underneath. Each site is now a
    // focusable button with its own accessible name, so the map is explorable.
    const html = renderToStaticMarkup(<CareerAtlas events={EVENTS} />);
    // Only the selected region is drawn, so the doors are that region's sites --
    // one per site, each with its own accessible name.
    const drawn = buildAtlas(EVENTS).find((region) => region.kind === "application");
    const doors = html.match(/role="button"/g) ?? [];
    expect(doors.length).toBe(drawn?.sites.length ?? 0);
    expect(html).toContain('aria-label="Backend Engineer · Acme"');
    // The pressed state is the same fact the word list below shows, so the two
    // readings of the map cannot disagree about where the reader is.
    expect(html).toContain("aria-pressed=");
  });

  it("364: every charted region carries a door to the room that writes it", () => {
    // The map names every room the reader has been; these are the rooms. A region
    // with no screen of its own carries no door rather than a link that 404s.
    const html = renderToStaticMarkup(<CareerAtlas events={EVENTS} />);
    expect(html).toContain('href="/applications"');
    expect(html).toContain("[timeline.atlasDoorApplications]");
    // The frontier's own key is a different claim -- a room nobody has been to --
    // and must not be what a charted region's door answers with.
    expect(html).not.toContain("[timeline.atlasFrontierApplications]");
  });

  it("364: the unknown region is offered no door, because it has no room", () => {
    const only = [{ at: "2026-09-03T09:00:00Z", kind: "no-such-kind", title: "A fact without a name", refId: "x-1", summary: "still a fact" }];
    const html = renderToStaticMarkup(<CareerAtlas events={only} />);
    expect(html).toContain("[timeline.kinds.unknown]");
    expect(html).not.toContain("[timeline.atlasDoorUnknown]");
    // No link is rendered for it at all -- an honest gap beats a dead door.
    expect(html).not.toMatch(/aria-label="\[timeline\.atlasDoor/);
  });

  it("361: reads a region's span off its own first and newest fact", () => {
    const regions = buildAtlas(EVENTS);
    const application = regions.find((r) => r.kind === "application");
    expect(application?.firstAt).toBe("2026-09-01T09:00:00Z");
    expect(application?.lastAt).toBe("2026-09-01T09:00:00Z");
    // A region with a history says so: the span is the reader's own, and a
    // one-fact region's span is that fact rather than an invented range.
    const notes: TimelineEntry[] = [
      { at: "2026-01-01T09:00:00Z", kind: "note", title: "first", refId: "n-1", summary: "" },
      { at: "2026-06-01T09:00:00Z", kind: "note", title: "newest", refId: "n-2", summary: "" },
    ];
    const span = buildAtlas(notes)[0];
    expect(span.firstAt).toBe("2026-01-01T09:00:00Z");
    expect(span.lastAt).toBe("2026-06-01T09:00:00Z");
  });

  it("says every known frontier is charted instead of offering doors to visited regions", () => {
    const charted: TimelineEntry[] = ["match", "application", "interview", "contact", "resume_version"].map(
      (kind, i) => ({
        at: `2026-10-0${i + 1}T09:00:00Z`,
        kind,
        title: `Fact ${i + 1}`,
        refId: `f-${i + 1}`,
        summary: "",
      })
    );
    const html = renderToStaticMarkup(<CareerAtlas events={charted} />);
    expect(html).toContain("[timeline.atlasAllCharted]");
    expect(html).not.toContain("[timeline.atlasFrontierJobs]");
  });

  it("shows an uncharted map instead of inventing a world on an empty ledger", () => {
    const html = renderToStaticMarkup(<CareerAtlas events={[]} />);
    expect(html).toContain("[timeline.atlasEmpty]");
    // No region buttons are drawn: the region label may still appear as a
    // frontier's tooltip, which is exactly the guidance an empty map needs.
    expect(html).not.toContain("aria-pressed=");
    expect(html).toContain("[timeline.atlasFrontierTitle]");
    expect(html).toContain("[timeline.atlasFrontierApplications]");
    expect(html).toContain("[timeline.atlasFrontierResumes]");
  });
});
