import type { Job } from "@/lib/api/types";
import type { JobFilters } from "@/lib/hooks/resources";
import type { NormalizedPage } from "@/lib/api/normalize";
import { normalizeStructuredResume, serializeJobFilters } from "@/lib/api/normalize";
import { lastPageOf } from "@/lib/page-window";

/**
 * The panel's own vocabulary, and the window the Saved tab still cuts locally.
 *
 * <p>This module used to answer which rows match. It did so because
 * `GET /jobs/saved` bound no query parameters and handed back every bookmark, so the Jobs page had
 * no choice but to run the board's predicates over the rows in hand — and each clause then had to
 * mirror `JobSearchRepository.applyWhere` or the two tabs meant different things by the same chip.
 * The mirror was narrower by construction: the keyword branch reaches `j.tsv`, which covers
 * description text, and the list payload carries no description, so a word found a role on Discover
 * and lost it on Saved (74.1).
 *
 * <p>The route reads the panel now, so the mirror is gone: there is one predicate, it is SQL, and
 * both tabs read its answer. What remains here is what no server read can decide — how a salary box
 * turns into a number the route can bind, which controls count as "a filter is set", and the window
 * the Saved tab still pages by hand because its route answers the shelf whole (74.2 moves that too).
 */

/** Wire-form filter: `page`/`size` are carried through and ignored here. */
type Wire = Record<string, unknown>;

function wireOf(filters: JobFilters): Wire {
  return serializeJobFilters({ ...filters, page: undefined, size: undefined });
}

/**
 * What a salary box actually holds. `type="number"` reports anything the browser can
 * read as a number, not just integers: `"12.5"` arrives intact (a step mismatch is not
 * "bad input"), and so does `"1e999"`, which parses to `Infinity`. Both are sent as
 * `minSalary`/`maxSalary`, which the server binds as `Integer` — so a fraction does not
 * narrow the search, it fails the entire request and the board shows an error instead
 * of jobs. Whole yuan is the only grain those columns hold, so that is what the field
 * yields; a bound too large to be a salary is read as "no bound". An empty box stays
 * no constraint at all.
 */
export function salaryFromInput(raw: string): number | undefined {
  if (!raw.trim()) return undefined;
  const n = Number(raw);
  if (!Number.isFinite(n)) return undefined;
  return Math.trunc(n);
}

/** Everything the panel can narrow by, minus paging. Empty means "no constraint". */
export function hasActiveJobFilters(filters: JobFilters): boolean {
  const wire = wireOf(filters);
  return ["q", "skills", "location", "company", "remote", "minSalary", "maxSalary"].some((k) => {
    const v = wire[k];
    return typeof v === "string" ? v.trim() !== "" : v != null;
  });
}

/**
 * The URL's window over rows the server already narrowed.
 *
 * The page index is clamped rather than trusted: the filter values live in the URL too, so a
 * reload of `?q=rust&page=3` points past a shelf that is now two bookmarks long. A clamped read
 * still shows those two and says so in the count, while an unclamped slice would render an empty
 * list under a pager that is already on the right page.
 *
 * <p>The order is the answer's. Nothing here sorts: a client that reordered the shelf would put the
 * paged windows out of step with each other, which is the defect every board in this app is guarded
 * against by ending its ORDER BY in the row's own id. That is 74.2's job — this function's whole
 * contract is to window and to change nothing else.
 */
export function windowSavedRows(items: Job[], filters: JobFilters): NormalizedPage<Job> {
  const size = filters.size && filters.size > 0 ? filters.size : items.length || 1;
  const lastPage = lastPageOf(items.length, size);
  const page = Math.min(Math.max(0, filters.page ?? 0), lastPage);
  return {
    items: items.slice(page * size, page * size + size),
    total: items.length,
    page,
    size,
  };
}

/**
 * The skill chips the filter panel offers, read off the parsed resume profile.
 *
 * Every skill the profile knows has to come back: the panel has no free-text entry,
 * so a skill that isn't in this list is a filter the user cannot set, however much
 * it describes them. Case is folded for the duplicate check only — the chip rides to the wire as
 * the `skills` parameter and the server's skill clause compares skills case-insensitively, so
 * "Kubernetes" and "kubernetes" are one chip, spelled the way the profile wrote it first.
 *
 * The argument is the `resume_versions.structured` jsonb the caller holds, not a
 * `StructuredResume`: this function normalizes it. (Its parameter used to claim the
 * view model, which is how its fixtures ended up in a shape no producer writes.)
 */
export function profileSkillSuggestions(structured?: unknown): string[] {
  const s = normalizeStructuredResume(structured);
  if (!s) return [];
  const owned = (s.skills ?? []).flatMap((g) => g.skills ?? []);
  const byFoldedName = new Map<string, string>();
  for (const raw of owned) {
    const name = String(raw ?? "").trim();
    const folded = name.toLowerCase();
    if (name && !byFoldedName.has(folded)) byFoldedName.set(folded, name);
  }
  return [...byFoldedName.values()];
}
