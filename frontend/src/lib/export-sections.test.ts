import { describe, expect, it } from "vitest";

import {
  SECTION_LABELS,
  bundleSections,
  humanizeSection,
  sectionLabelKey,
} from "./export-sections";
import { lookup } from "./i18n/locale-context";
import { translations } from "./i18n/translations";

describe("bundleSections", () => {
  it("keeps the manifest's own order", () => {
    expect(bundleSections({ profile: 1, resumes: 2, inbound_mails: 0 })).toEqual([
      "profile",
      "resumes",
      "inbound_mails",
    ]);
  });

  it("reads a missing manifest as no sections rather than throwing", () => {
    expect(bundleSections(null)).toEqual([]);
    expect(bundleSections(undefined)).toEqual([]);
  });
});

describe("section labels", () => {
  it("has a word in both languages for every section the bundle carries", () => {
    // Membership comes from the bundle's manifest; the map only names the
    // sections this build can label. The server-side census (40.4) holds the
    // keys to the bundle's section tuple.
    for (const [section, key] of Object.entries(SECTION_LABELS)) {
      expect(lookup(translations.en, key), `en label for ${section}`).toBeTruthy();
      expect(lookup(translations.zh, key), `zh label for ${section}`).toBeTruthy();
    }
  });

  it("falls back to a humanized name for a section this build does not know", () => {
    expect(sectionLabelKey("profile")).toBe("data.sections.profile");
    expect(sectionLabelKey("a_section_from_the_future")).toBeNull();
    expect(humanizeSection("a_section_from_the_future")).toBe(
      "a section from the future"
    );
  });
});
