import type { Job } from "@/lib/api/types";
import type { JobFilters } from "@/lib/hooks/resources";
import type { NormalizedPage } from "@/lib/api/normalize";
import { normalizeStructuredResume, serializeJobFilters } from "@/lib/api/normalize";
import { lastPageOf } from "@/lib/page-window";

/**
 * Local filtering for a set the server already handed over whole.
 *
 * `GET /jobs/saved` accepts no query parameters (`JobController.saved`) and returns
 * every bookmark, so the Jobs page cannot delegate its filter panel to the wire on
 * the Saved tab — it has to run the same predicates over the rows in hand. Each
 * clause below mirrors the matching branch of `JobSearchRepository.applyWhere`, so a
 * chip or a salary box means the same thing on both tabs. Where the list payload is
 * thinner than the database, the difference is stated on the clause instead of
 * being left for the user to discover. `status` is a server parameter this panel
 * never exposes, so it is deliberately not mirrored.
 */

/** Wire-form filter: `page`/`size` are carried through and ignored here. */
type Wire = Record<string, unknown>;

/** A constraint is only a constraint once it has content, matching the serializer. */
function text(wire: Wire, key: string): string {
  const v = wire[key];
  return typeof v === "string" && v.trim() ? v.trim() : "";
}

function bound(wire: Wire, key: string): number | undefined {
  const v = wire[key];
  return typeof v === "number" && Number.isFinite(v) ? v : undefined;
}

/**
 * What a salary box actually holds. `type="number"` reports anything the browser can
 * read as a number, not just integers: `"12.5"` arrives intact (a step mismatch is not
 * "bad input"), and so does `"1e999"`, which parses to `Infinity`. Both are sent as
 * `minSalary`/`maxSalary`, which the server binds as `Integer` — so a fraction does not
 * narrow the search, it fails the entire request and the board shows an error instead
 * of jobs. Whole yuan is the only grain those columns hold, so that is what the field
 * yields; a bound too large to be a salary is read as "no bound", which is what the
 * person meant and is also how `bound()` below already treats it. An empty box stays
 * no constraint at all.
 */
export function salaryFromInput(raw: string): number | undefined {
  if (!raw.trim()) return undefined;
  const n = Number(raw);
  if (!Number.isFinite(n)) return undefined;
  return Math.trunc(n);
}

/** `ILIKE '%needle%'`: case-insensitive containment, no pattern metacharacters. */
function contains(haystack: string | null | undefined, needle: string): boolean {
  if (!haystack) return false;
  return haystack.toLowerCase().includes(needle.toLowerCase());
}

function jobCompanyName(job: Job): string {
  return job.company?.name ?? job.companyName ?? "";
}

/** `j.skills @> ARRAY[skill]` for ANY selected skill — the SQL is an OR, not an AND. */
function hasAnySkill(job: Job, wanted: string[]): boolean {
  const owned = (job.skills ?? []).map((s) => String(s).trim().toLowerCase());
  return wanted.some((w) => owned.includes(w.trim().toLowerCase()));
}

export function matchesJobFilters(job: Job, filters: JobFilters): boolean {
  const wire: Wire = serializeJobFilters({ ...filters, page: undefined, size: undefined });

  // The server's keyword branch is `tsv @@ plainto_tsquery(...) OR title ILIKE OR
  // company ILIKE`. The text index covers description text, which the list payload
  // never carries, so the local form is the two ILIKE sides: keyword search here can
  // be narrower than Discover, never wider.
  const q = text(wire, "q");
  if (q && !(contains(job.title, q) || contains(jobCompanyName(job), q))) return false;

  const location = text(wire, "location");
  if (location && !contains(job.location, location)) return false;

  const company = text(wire, "company");
  if (company && !contains(jobCompanyName(job), company)) return false;

  // `j.remote_type = :remote`; the serializer turns the switch's `true` into the
  // domain value "remote", so this clause compares the same value the server binds.
  // A job with no remote_type stated is dropped exactly as SQL drops a NULL.
  const remote = text(wire, "remote");
  if (remote && String(job.remoteType ?? "").toLowerCase() !== remote.toLowerCase()) return false;

  // Salary is an overlap test against the *other* column, so a band that only partly
  // enters the range still counts. A job with no salary stated is dropped exactly as
  // SQL drops it: `NULL >= x` is not true.
  const min = bound(wire, "minSalary");
  if (min != null && !(job.salaryMax != null && job.salaryMax >= min)) return false;
  const max = bound(wire, "maxSalary");
  if (max != null && !(job.salaryMin != null && job.salaryMin <= max)) return false;

  const skills = text(wire, "skills")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  if (skills.length && !hasAnySkill(job, skills)) return false;

  return true;
}

/** Everything the panel can narrow by, minus paging. Empty means "no constraint". */
export function hasActiveJobFilters(filters: JobFilters): boolean {
  const wire: Wire = serializeJobFilters({ ...filters, page: undefined, size: undefined });
  return ["q", "skills", "location", "company", "remote", "minSalary", "maxSalary"].some((k) => {
    const v = wire[k];
    return typeof v === "string" ? v.trim() !== "" : v != null;
  });
}

/**
 * Filter, then page a set that arrived in one piece.
 *
 * The page index is clamped rather than trusted: the filter values live in the URL,
 * so a reload of `?q=rust&page=3` can point past a set that is now two rows long. A
 * clamped read still shows those two rows and says so in the count, while an
 * unclamped slice would render an empty list with a pager that is already on the
 * right page.
 */
export function filterAndPaginate(
  items: Job[],
  filters: JobFilters
): NormalizedPage<Job> {
  const filtered = hasActiveJobFilters(filters) ? items.filter((j) => matchesJobFilters(j, filters)) : items;
  const size = filters.size && filters.size > 0 ? filters.size : filtered.length || 1;
  const lastPage = lastPageOf(filtered.length, size);
  const page = Math.min(Math.max(0, filters.page ?? 0), lastPage);
  return {
    items: filtered.slice(page * size, page * size + size),
    total: filtered.length,
    page,
    size,
  };
}

/**
 * The skill chips the filter panel offers, read off the parsed resume profile.
 *
 * Every skill the profile knows has to come back: the panel has no free-text entry,
 * so a skill that isn't in this list is a filter the user cannot set, however much
 * it describes them. Case is folded for the duplicate check only — both this panel's
 * local predicate and the server's skill clause already compare skills
 * case-insensitively, so "Kubernetes" and "kubernetes" are one chip, spelled the way
 * the profile wrote it first.
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
