import type { SavedSearchCriteria } from "@/lib/api/types";
import type { Translate } from "@/lib/i18n/issue";

/**
 * The board's filters, in the shape a saved search stores (roadmap 19.1).
 *
 * A saved search is the same question the board is already answering, kept
 * under a name. The criteria therefore use the board's own names -- `q`,
 * `skills`, `location`, `company`, `remote`, `minSalary`, `maxSalary` --
 * and not the URL state's spellings (`min_salary`, a comma-joined
 * `skills` string), which exist because a query string is flat. One
 * translation, in one place, so the two cannot drift.
 */

/** The filter values a list screen holds; the fields a saved search can store. */
export interface SavedSearchFilterState {
  q?: string;
  skills?: string;
  location?: string;
  company?: string;
  remote?: boolean;
  min_salary?: number;
  max_salary?: number;
}

/**
 * The storable criteria of the current filters, or undefined when the board
 * is browsing without one.
 *
 * An empty saved search is not a saved search: it would match the whole
 * board, and an alert about "anything new" is an alert about everything. The
 * server refuses one too, and this is the same rule on the near side so the
 * button can say why before the round trip does.
 */
export function criteriaFromFilters(
  filters: SavedSearchFilterState
): SavedSearchCriteria | undefined {
  const criteria: SavedSearchCriteria = {};
  const text = (value?: string) => value?.trim() || undefined;

  const q = text(filters.q);
  if (q) criteria.q = q;
  const location = text(filters.location);
  if (location) criteria.location = location;
  const company = text(filters.company);
  if (company) criteria.company = company;
  if (filters.remote) criteria.remote = true;
  if (filters.min_salary != null) criteria.minSalary = filters.min_salary;
  if (filters.max_salary != null) criteria.maxSalary = filters.max_salary;

  const skills = [
    ...new Set(
      (filters.skills ?? "")
        .split(",")
        .map((skill) => skill.trim())
        .filter(Boolean)
    ),
  ];
  if (skills.length > 0) criteria.skills = skills;

  return Object.keys(criteria).length > 0 ? criteria : undefined;
}

/**
 * The URL state for a saved search: every filter field set, blanks included,
 * so applying a search replaces the previous one rather than adding to it.
 */
export function filtersFromCriteria(criteria: SavedSearchCriteria): SavedSearchFilterState {
  return {
    q: criteria.q ?? "",
    skills: (criteria.skills ?? []).join(","),
    location: criteria.location ?? "",
    company: criteria.company ?? "",
    remote: criteria.remote || undefined,
    min_salary: criteria.minSalary,
    max_salary: criteria.maxSalary,
  };
}

/**
 * A name to start the save dialog with: the most specific criterion the
 * search carries, in the reader's words when it has to invent one.
 */
export function suggestedName(criteria: SavedSearchCriteria, t: Translate): string {
  if (criteria.q) return criteria.q;
  if (criteria.location) return criteria.location;
  if (criteria.company) return criteria.company;
  if (criteria.skills?.length) return criteria.skills.join(", ");
  if (criteria.remote) return t("savedSearches.remoteName");
  return "";
}
