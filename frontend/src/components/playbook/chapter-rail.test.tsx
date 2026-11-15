import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string) => `[${key}]`,
    setLocale: () => undefined,
  }),
}));

import { ChapterRail } from "./chapter-rail";

describe("ChapterRail", () => {
  it("renders every chapter as an anchor link, numbered like the dividers", () => {
    const html = renderToStaticMarkup(<ChapterRail />);
    for (const anchor of [
      "#firstweek",
      "#loop",
      "#quickstart",
      "#surfaces",
      "#ai",
      "#keyboard",
      "#faq",
      "#offer",
      "#yearloop",
      "#manual",
      "#keptgoing",
      "#about",
    ]) {
      expect(html).toContain(`href="${anchor}"`);
    }
    expect(html).toContain("[playbook.tocEyebrow]");
    expect(html).toContain("[playbook.colophonTitle]");
    expect(html).toContain("00"); // first chapter numbered zero like the divider
  });
});
