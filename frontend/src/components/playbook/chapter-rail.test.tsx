import { readFileSync } from "node:fs";
import { resolve } from "node:path";
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
      "#gate",
      "#newinstruments",
      "#about",
    ]) {
      expect(html).toContain(`href="${anchor}"`);
    }
    expect(html).toContain("[playbook.tocEyebrow]");
    expect(html).toContain("[playbook.colophonTitle]");
    expect(html).toContain("00"); // first chapter numbered zero like the divider
  });

  it("walks the chapters in the exact order the manual's sections appear", () => {
    // A reader taps the 13th chapter in the index and lands on the 12th section:
    // that is what happened when veto/gate and ledger/afterward drifted apart.
    // The index is a promise about the document's order, so pin the two together.
    const html = renderToStaticMarkup(<ChapterRail />);
    const rail = [...html.matchAll(/href="#([^"]+)"/g)].map((m) => m[1]);
    const page = readFileSync(
      resolve(__dirname, "../../app/playbook/playbook-page.tsx"),
      "utf8",
    );
    const sections = [...page.matchAll(/<section id="([^"]+)"/g)].map((m) => m[1]);
    expect(rail).toEqual(sections);
  });
});
