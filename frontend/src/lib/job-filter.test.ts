import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import {
  filterAndPaginate,
  hasActiveJobFilters,
  matchesJobFilters,
  profileSkillSuggestions,
  salaryFromInput,
} from "@/lib/job-filter";
import { serializeJobFilters } from "@/lib/api/normalize";
import type { Job, StructuredResume } from "@/lib/api/types";

/**
 * Fixtures are shaped like `normalizeJob`'s output for a `JobListItem`, i.e. what
 * `GET /jobs/saved` actually yields after the `SavedJobItem.job` unwrap.
 */
function job(over: Partial<Job> = {}): Job {
  return {
    id: "j-1",
    companyId: "c-1",
    title: "Staff Platform Engineer",
    status: "open",
    ...over,
  };
}

const SET = [
  job({
    id: "rust-remote",
    title: "Rust Systems Engineer",
    company: { id: "c-2", name: "Ferrous Cloud" },
    location: "Berlin",
    remoteType: "remote",
    salaryMin: 120_000,
    salaryMax: 160_000,
    skills: ["Rust", "Kubernetes"],
  }),
  job({
    id: "java-hybrid",
    title: "Senior Backend Engineer",
    companyName: "Acme Cloud",
    location: "Shanghai",
    remoteType: "hybrid",
    salaryMin: 70_000,
    salaryMax: 95_000,
    skills: ["Java", "Spring"],
  }),
  job({ id: "no-salary", title: "Data Platform Intern", companyName: "Acme Cloud", location: null }),
];

const ids = (jobs: Job[]) => jobs.map((j) => j.id);

describe("matchesJobFilters", () => {
  it("keeps every row when nothing is constrained", () => {
    expect(matchesJobFilters(SET[0], {})).toBe(true);
    expect(ids(SET.filter((j) => matchesJobFilters(j, { q: "", skills: " " })))).toEqual(ids(SET));
  });

  it("reads keyword against title and company, case-insensitively", () => {
    expect(ids(SET.filter((j) => matchesJobFilters(j, { q: "RUST systems" })))).toEqual(["rust-remote"]);
    expect(ids(SET.filter((j) => matchesJobFilters(j, { q: "acme" })))).toEqual(["java-hybrid", "no-salary"]);
  });

  it("cannot match description text the saved payload never carries", () => {
    // The server's keyword branch also ORs the tsvector over the full posting; the
    // list rows have no description, so a body-only hit is a documented narrower.
    const bodyOnly = job({ id: "body", title: "Engineer", description: "postgres and pgvector" });
    expect(matchesJobFilters(bodyOnly, { q: "postgres" })).toBe(false);
  });

  it("matches a nested company object and a flat company column alike", () => {
    expect(ids(SET.filter((j) => matchesJobFilters(j, { company: "cloud" })))).toEqual([
      "rust-remote",
      "java-hybrid",
      "no-salary",
    ]);
    expect(ids(SET.filter((j) => matchesJobFilters(j, { company: "ferrous" })))).toEqual(["rust-remote"]);
  });

  it("treats location as containment and drops an unstated location", () => {
    expect(ids(SET.filter((j) => matchesJobFilters(j, { location: "han" })))).toEqual(["java-hybrid"]);
    expect(ids(SET.filter((j) => matchesJobFilters(j, { location: "shang" })))).toEqual(["java-hybrid"]);
    expect(matchesJobFilters(SET[2], { location: "anywhere" })).toBe(false);
  });

  it("sends the remote switch to the remote_type domain value, not a boolean", () => {
    expect(ids(SET.filter((j) => matchesJobFilters(j, { remote: true })))).toEqual(["rust-remote"]);
    expect(ids(SET.filter((j) => matchesJobFilters(j, { remote: undefined })))).toEqual(ids(SET));
  });

  it("drops a job whose remote_type is null, the way `= :remote` drops a NULL", () => {
    expect(matchesJobFilters(job({ id: "unknown-remote" }), { remote: true })).toBe(false);
  });

  it("overlaps salary against the opposite bound, and NULL never satisfies a bound", () => {
    // A band only partly inside the range still counts: min tests salaryMax, max tests
    // salaryMin. `no-salary` states neither, and SQL's `NULL <= x` is not true either.
    expect(ids(SET.filter((j) => matchesJobFilters(j, { min_salary: 100_000 })))).toEqual(["rust-remote"]);
    expect(ids(SET.filter((j) => matchesJobFilters(j, { max_salary: 80_000 })))).toEqual(["java-hybrid"]);
    expect(ids(SET.filter((j) => matchesJobFilters(j, { min_salary: 60_000, max_salary: 90_000 })))).toEqual([
      "java-hybrid",
    ]);
  });

  it("drops a job with no salary stated instead of treating it as free", () => {
    expect(matchesJobFilters(job({ id: "unpaid" }), { min_salary: 1 })).toBe(false);
    expect(matchesJobFilters(job({ id: "unpaid" }), { max_salary: 999_999 })).toBe(false);
  });

  it("keeps a row that carries ANY selected skill, matching the SQL's EXISTS", () => {
    expect(ids(SET.filter((j) => matchesJobFilters(j, { skills: "Rust,Java" })))).toEqual([
      "rust-remote",
      "java-hybrid",
    ]);
    expect(ids(SET.filter((j) => matchesJobFilters(j, { skills: "Elixir" })))).toEqual([]);
  });

  it("compares skills ignoring case so a chip cannot silently match nothing", () => {
    expect(ids(SET.filter((j) => matchesJobFilters(j, { skills: "kubernetes" })))).toEqual(["rust-remote"]);
  });

  it("ignores a whitespace-only skill list rather than filtering everything out", () => {
    expect(ids(SET.filter((j) => matchesJobFilters(j, { skills: " ,  , " })))).toEqual(ids(SET));
  });
});

describe("hasActiveJobFilters", () => {
  it("does not count paging as a filter", () => {
    expect(hasActiveJobFilters({ page: 2, size: 12 })).toBe(false);
    expect(hasActiveJobFilters({ q: "", location: "  ", remote: false })).toBe(false);
  });

  it("counts every control the panel exposes", () => {
    for (const f of [
      { q: "rust" },
      { location: "Berlin" },
      { company: "Acme" },
      { skills: "Rust" },
      { remote: true },
      { min_salary: 10 },
      { max_salary: 10 },
    ]) {
      expect(hasActiveJobFilters(f), JSON.stringify(f)).toBe(true);
    }
  });
});

describe("filterAndPaginate", () => {
  it("reports the filtered count, which is what the panel says it is showing", () => {
    const page = filterAndPaginate(SET, { company: "Acme" });
    expect(page.total).toBe(2);
    expect(ids(page.items)).toEqual(["java-hybrid", "no-salary"]);
  });

  it("pages the filtered set in the order the server sent it", () => {
    const many = Array.from({ length: 30 }, (_, i) => job({ id: `j-${i}`, title: `Role ${i}` }));
    const first = filterAndPaginate(many, { page: 0, size: 12 });
    const second = filterAndPaginate(many, { page: 1, size: 12 });
    const last = filterAndPaginate(many, { page: 2, size: 12 });
    expect(first.items).toHaveLength(12);
    expect(ids(second.items)[0]).toBe("j-12");
    expect(last.items).toHaveLength(6);
    expect(last.total).toBe(30);
  });

  it("clamps a stale page instead of rendering an empty list over live rows", () => {
    // Filters and page index both live in the URL, so `?q=acme&page=4` is a shareable
    // state pointing past a two-row result.
    const page = filterAndPaginate(SET, { company: "Acme", page: 4, size: 12 });
    expect(page.page).toBe(0);
    expect(ids(page.items)).toEqual(["java-hybrid", "no-salary"]);
  });

  it("keeps a filtered-empty result at zero rather than falling back to the full set", () => {
    const page = filterAndPaginate(SET, { skills: "Elixir", page: 3, size: 12 });
    expect(page.items).toEqual([]);
    expect(page.total).toBe(0);
  });

  it("returns the same array untouched when nothing is constrained", () => {
    const page = filterAndPaginate(SET, {});
    expect(ids(page.items)).toEqual(ids(SET));
    expect(page.total).toBe(3);
  });
});

describe("the saved tab's list screen", () => {
  // React can't render in the node environment, so these guard the wiring that makes
  // the panel's controls real on this tab: without it the filters move the URL while
  // the rendered rows never change.
  const source = readFileSync(new URL("../app/(app)/jobs/page.tsx", import.meta.url), "utf8");

  it("filters and pages the bookmarks it already has", () => {
    expect(source).toContain('from "@/lib/job-filter"');
    expect(source).toContain("filterAndPaginate(saved.data.items, filters)");
  });

  it("hands the derived page to the boundary, not the raw query", () => {
    expect(source).toContain("query={listView}");
    expect(source).not.toContain("query={active}");
    // The Saved tab must never fall through to the Discover query while its own rows
    // are still in flight — that would render someone else's list under the bookmark
    // heading. Only `data` is swapped out.
    expect(source).toMatch(/const listView = tab === "saved" \? \(\{ \.\.\.saved, data: savedPage \}/);
    // The count the panel prints under "matching roles" is the filtered one.
    expect(source).toContain("resultCount={listView.data ? total : undefined}");
  });

  it("shows the clamped page it rendered, not the stale one in the URL", () => {
    expect(source).toContain("page={listView.data?.page ?? filters.page}");
  });

  it("says which kind of empty the Saved tab is", () => {
    expect(source).toContain("No saved role matches these filters");
    expect(source).toContain("hasActiveJobFilters(filters)");
    // A bookmark set that is genuinely empty must still get its own state.
    expect(source).toContain("Nothing saved yet");
  });
});

describe("profileSkillSuggestions", () => {
  it("offers every skill the profile knows — a missing chip is a filter that cannot be set", () => {
    const many = Array.from({ length: 31 }, (_, i) => `skill-${i}`);
    const got = profileSkillSuggestions({ skills: [{ group: "Core", skills: many }], technologies: ["extra"] });
    expect(got).toHaveLength(32);
    expect(got).toContain("skill-24");
    expect(got[got.length - 1]).toBe("extra");
  });

  it("folds case-only duplicates and keeps the first spelling", () => {
    const got = profileSkillSuggestions({
      skills: [{ skills: ["Kubernetes", "Go"] }],
      technologies: ["kubernetes", "Rust"],
    });
    expect(got).toEqual(["Kubernetes", "Go", "Rust"]);
  });

  it("trims what it keeps and drops blanks", () => {
    const got = profileSkillSuggestions({
      skills: [{ skills: [" TypeScript ", "", "   "] }],
      technologies: ["Node"],
    });
    expect(got).toEqual(["TypeScript", "Node"]);
  });

  it("answers with nothing when there is no parsed profile", () => {
    expect(profileSkillSuggestions(null)).toEqual([]);
    expect(profileSkillSuggestions(undefined)).toEqual([]);
    expect(profileSkillSuggestions({})).toEqual([]);
    expect(
      profileSkillSuggestions({ skills: null, technologies: null } as unknown as StructuredResume)
    ).toEqual([]);
  });

  it("reads a structured resume nested under the payload's own key", () => {
    expect(profileSkillSuggestions({ structured: { technologies: ["Elixir"] } })).toEqual(["Elixir"]);
  });

  it("suggests only chips the rows can actually answer", () => {
    // A chip is worth rendering only if picking it filters; the panel and the server
    // both compare skills case-insensitively, so folded spelling must not break that.
    const suggestion = profileSkillSuggestions({ skills: [{ skills: ["Kubernetes"] }] })[0];
    expect(matchesJobFilters(job({ skills: ["kubernetes"] }), { skills: suggestion })).toBe(true);
    expect(matchesJobFilters(job({ skills: ["Java"] }), { skills: suggestion })).toBe(false);
  });
});

describe("the skill filter's suggestion chips", () => {
  const panel = readFileSync(new URL("../components/jobs/job-filters.tsx", import.meta.url), "utf8");
  const page = readFileSync(new URL("../app/(app)/jobs/page.tsx", import.meta.url), "utf8");

  it("renders one chip per suggestion instead of a window", () => {
    expect(panel).toContain("{skillSuggestions.map((s) => (");
    expect(panel).not.toMatch(/skillSuggestions\.slice\(/);
  });

  it("builds the list in the shared module the filters live in", () => {
    expect(page).toContain("profileSkillSuggestions(resume.data?.structured)");
    expect(page).not.toMatch(/function skillsFrom/);
    expect(page).not.toMatch(/normalizeStructuredResume/);
  });
});

describe("salaryFromInput", () => {
  const panel = readFileSync(new URL("../components/jobs/job-filters.tsx", import.meta.url), "utf8");

  it("yields whole yuan, which is all the server can bind", () => {
    // minSalary/maxSalary are `Integer` request parameters: a fraction does not
    // narrow the search, it fails the request and the board shows an error.
    expect(salaryFromInput("12.5")).toBe(12);
    expect(salaryFromInput("120000")).toBe(120_000);
    expect(salaryFromInput(" 120000 ")).toBe(120_000);
  });

  it("reads an empty box as no bound at all", () => {
    expect(salaryFromInput("")).toBeUndefined();
    expect(salaryFromInput("   ")).toBeUndefined();
  });

  it("reads a bound too large to be a salary as no bound", () => {
    // Number("1e999") is Infinity, which <input type="number"> reports as a value;
    // on the wire it is "Infinity" and the request dies. Unbounded is the intent.
    expect(salaryFromInput("1e999")).toBeUndefined();
    expect(salaryFromInput("abc")).toBeUndefined();
  });

  it("is what the panel's two boxes hand to the wire", () => {
    expect(serializeJobFilters({ min_salary: salaryFromInput("12.5") })).toEqual({ minSalary: 12 });
    expect(serializeJobFilters({ max_salary: salaryFromInput("1e999") })).toEqual({});
    expect((panel.match(/salaryFromInput\(e\.target\.value\)/g) ?? []).length).toBe(2);
    expect(panel).not.toMatch(/Number\(e\.target\.value\)/);
  });
});
