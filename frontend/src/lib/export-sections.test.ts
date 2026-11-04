import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

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

const DATA_PAGE = new URL("../app/(app)/data/page.tsx", import.meta.url);

/**
 * The charge is the print of a section's name.
 *
 * A section slug is a wire value (`job_descriptions`); the page has a label table for
 * the sections this build knows and a humanizer for the rest, so a name assembled with
 * `.replace(/_/g, " ")` at render time draws the slug on every reader's page and
 * bypasses both. The population is the files that import the label table -- other
 * `replace(/_/g, " ")` calls in the tree name different vocabularies (suggestion types,
 * diff keys, dimension keys) and are not this page's sections.
 */
function rawSectionPrints(files: { path: string; text: string }[]): string[] {
  return files
    .filter((f) => /from "@\/lib\/export-sections"/.test(f.text))
    .filter((f) => /\bsection\s*\.replace\s*\(\s*\/_\/g/.test(f.text))
    .map((f) => f.path);
}

describe("the section names on the data page", () => {
  it("route every print through the label table", () => {
    const page = readFileSync(fileURLToPath(DATA_PAGE), "utf8");
    // The two places the page names a section: the import preview's applied rows and
    // the skipped rows beneath them. A third print added later is caught by the charge.
    expect(page).toContain("{sectionLabel(section)}");
    expect(page).toContain("{sectionLabel(s.section)}");
    const offenders = rawSectionPrints([{ path: "app/(app)/data/page.tsx", text: page }]);
    expect(
      offenders,
      `surfaces spelling a section's name themselves:\n${offenders.join("\n")}`
    ).toEqual([]);
  });

  it("would still see a surface that spelled a section itself", () => {
    // The probe has to import the table to be in this gate's population -- that is the
    // population's definition, tested below by the `other.tsx` case.
    const IMPORT = 'import { sectionLabel } from "@/lib/export-sections";\n';
    expect(
      rawSectionPrints([
        { path: "app/probe.tsx", text: `${IMPORT}<span>{section.replace(/_/g, " ")}</span>` },
      ])
    ).toEqual(["app/probe.tsx"]);
    expect(
      rawSectionPrints([
        { path: "app/probe.tsx", text: `${IMPORT}<span>{s.section.replace(/_/g, " ")}</span>` },
      ])
    ).toEqual(["app/probe.tsx"]);
    expect(
      rawSectionPrints([
        { path: "app/ok.tsx", text: `${IMPORT}<span>{sectionLabel(section)}</span>` },
      ])
    ).toEqual([]);
    // Only a file that imports the label table is in this population.
    expect(
      rawSectionPrints([
        {
          path: "app/other.tsx",
          text: 'import { x } from "./elsewhere";\n<span>{section.replace(/_/g, " ")}</span>',
        },
      ])
    ).toEqual([]);
  });
});
