/**
 * The export bundle's sections in the browser (Epic 40.4).
 *
 * The bundle is the source of truth for which sections an export carries:
 * the server counts every section into `manifest.counts` (a zero is a count,
 * not an absence), and the data page offers exactly the rows that manifest
 * names -- the badges that say what the file holds and the checkboxes that
 * say what to leave out. The page used to type the list itself, so a section
 * the server started carrying stayed un-redactable until a browser release
 * caught up, and the two lists could disagree.
 *
 * What lives here is only the words: a section's translation key, and a
 * fallback for a section this build has not learned yet, so a bundle from a
 * newer server still renders a readable checkbox in an older browser.
 */

export type SectionCounts = Record<string, number> | null | undefined;

/** Section name -> translation key. Labels only; membership comes from the bundle. */
export const SECTION_LABELS: Record<string, string> = {
  profile: "data.sections.profile",
  resumes: "data.sections.resumes",
  knowledge: "data.sections.knowledge",
  job_descriptions: "data.sections.jobDescriptions",
  interviews: "data.sections.interviews",
  memories: "data.sections.memories",
  applications: "data.sections.applications",
  growth_plans: "data.sections.growthRuns",
  notes: "data.sections.notes",
  contacts: "data.sections.contacts",
  conversations: "data.sections.conversations",
  saved_searches: "data.sections.savedSearches",
  ingestion_feeds: "data.sections.ingestionFeeds",
  saved_jobs: "data.sections.savedJobs",
  inbound_mails: "data.sections.inboundMails",
};

/** The sections an export carries, in the order the manifest counted them. */
export function bundleSections(counts: SectionCounts): string[] {
  return Object.keys(counts ?? {});
}

/** The label key for a section, or null for a section this build does not know. */
export function sectionLabelKey(section: string): string | null {
  return SECTION_LABELS[section] ?? null;
}

/** A section's name as a reader can read it when it has no label of its own. */
export function humanizeSection(section: string): string {
  return section.replace(/_/g, " ");
}
