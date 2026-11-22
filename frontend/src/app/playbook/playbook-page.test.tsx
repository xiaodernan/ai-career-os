import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  LocaleProvider: ({ children }: { children: React.ReactNode }) => children,
  useLocale: () => ({
    locale: "en",
    t: (key: string) => (key.startsWith("playbook.") ? key : `[${key}]`),
    setLocale: () => undefined,
  }),
}));

import PlaybookPage from "./playbook-page";

describe("/playbook — the manual", () => {
  it("renders every chapter and its eyebrow", () => {
    const html = renderToStaticMarkup(<PlaybookPage />);

    for (const key of [
      "playbook.loopEyebrow",
      "playbook.quickstartEyebrow",
      "playbook.surfacesEyebrow",
      "playbook.aiEyebrow",
      "playbook.keyboardEyebrow",
      "playbook.faqEyebrow",
      "playbook.codaTitle",
    ]) {
      expect(html).toContain(key);
    }
    expect(html).toContain("playbook.title");
    expect(html).toContain("playbook.loopBody");
  });

  it("describes every surface of the product map", () => {
    const html = renderToStaticMarkup(<PlaybookPage />);

    for (const key of [
      "playbook.surfacesFindBody",
      "playbook.surfacesPrepareBody",
      "playbook.surfacesTrackBody",
      "playbook.surfacesDecideBody",
      "playbook.surfacesSeeBody",
    ]) {
      expect(html).toContain(key);
    }
  });

  it("366: teaches the atlas — the manual must cover every surface a reader can stand on", () => {
    const html = renderToStaticMarkup(<PlaybookPage />);
    expect(html).toContain('id="atlas"');
    for (const key of [
      "playbook.atlasEyebrow",
      "playbook.atlasTitle",
      "playbook.atlasIntro",
      "playbook.atlasRegionTitle",
      "playbook.atlasSiteTitle",
      "playbook.atlasSiteMomentTitle",
      "playbook.atlasRouteTitle",
      "playbook.atlasFrontierTitle",
      "playbook.atlasNothingTitle",
      "playbook.atlasCta",
    ]) {
      expect(html, key).toContain(key);
    }
  });

  it("389: teaches the quiet instruments — capsule, echo, calendar and its feed", () => {
    const html = renderToStaticMarkup(<PlaybookPage />);
    expect(html).toContain('id="quietly"');
    for (const key of [
      "playbook.quietlyEyebrow",
      "playbook.quietlyTitle",
      "playbook.quietlyIntro",
      "playbook.quietlyCapsuleTitle",
      "playbook.quietlyCapsuleBody",
      "playbook.quietlyEchoTitle",
      "playbook.quietlyEchoBody",
      "playbook.quietlyCalendarTitle",
      "playbook.quietlyCalendarBody",
      "playbook.quietlyFeedTitle",
      "playbook.quietlyFeedBody",
      "playbook.quietlyClosing",
      "playbook.quietlyCtaCalendar",
    ]) {
      expect(html, key).toContain(key);
    }
    expect(html).toContain('href="/calendar"');
    expect(html).toContain('href="/settings"');
  });

  it("402: lists the calendar among the power moves", () => {
    const html = renderToStaticMarkup(<PlaybookPage />);
    expect(html).toContain("playbook.key5");
  });

  it("honors the same anchor shape the route prints", () => {
    const html = renderToStaticMarkup(<PlaybookPage />);

    expect(html).toContain('id="loop"');
    expect(html).toContain('id="quickstart"');
    expect(html).toContain('id="surfaces"');
    expect(html).toContain('id="ai"');
    expect(html).toContain('id="keyboard"');
    expect(html).toContain('id="faq"');
    expect(html).toContain('id="assistant"');
    expect(html).toContain('id="decode"');
    expect(html).toContain('id="letters"');
  });
});
