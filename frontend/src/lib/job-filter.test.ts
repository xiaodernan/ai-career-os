import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import {
  hasActiveJobFilters,
  profileSkillSuggestions,
  salaryFromInput,
} from "@/lib/job-filter";
import { serializeJobFilters } from "@/lib/api/normalize";

describe("the module that used to decide which rows match", () => {
  const source = readFileSync(new URL("./job-filter.ts", import.meta.url), "utf8");
  const page = readFileSync(new URL("../app/(app)/jobs/page.tsx", import.meta.url), "utf8");

  it("exports no predicate over a row", () => {
    // 74.1 moved the answer to SQL, and the mirror went with it. A second export here would be a
    // second copy of the board's WHERE -- which is what this file documented as "narrower than
    // Discover, never wider", and what a reader experienced as the same chip losing roles.
    expect(source).not.toMatch(/function matchesJobFilters/);
    expect(source).not.toMatch(/function contains\(/);
    expect(source).not.toMatch(/function hasAnySkill\(/);
    expect(page).not.toContain("matchesJobFilters");
  });

  it("touches no job row anywhere the module still reads", () => {
    // The clause list, column by column: a row inspected for title, company, location, remote
    // type or salary is the mirror coming back, and the server's answer is the only copy of
    // that question now. The scan covers everything up to `profileSkillSuggestions`, which is
    // legitimately row-reading -- it reads the *resume profile* group objects
    // (`{ name, category, proficiency }`), not any job row, and its fixtures prove the shape.
    const rowReads = (text: string, column: string) => new RegExp(`\\.${column}\\b`).test(text);
    const fnStart = source.indexOf("export function profileSkillSuggestions");
    const rest = fnStart < 0 ? source : source.slice(0, fnStart);
    for (const column of ["title", "skills", "location", "salaryMin", "salaryMax", "remoteType", "companyName", "company"]) {
      expect(rowReads(rest, column), column).toBe(false);
    }
  });

  it("keeps the two decisions a server read cannot make for the browser", () => {
    // What a `type="number"` box holds, and whether the panel is showing a filtered view: both
    // are UI facts, and neither belongs in SQL.
    expect(source).toMatch(/export function salaryFromInput/);
    expect(source).toMatch(/export function hasActiveJobFilters/);
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

describe("the saved tab's list screen", () => {
  // React can't render in the node environment, so these guard the wiring that makes
  // the panel's controls real on this tab: without it the filters move the URL while
  // the rendered rows never change.
  const source = readFileSync(new URL("../app/(app)/jobs/page.tsx", import.meta.url), "utf8");
  const resources = readFileSync(new URL("./hooks/resources.ts", import.meta.url), "utf8");

  it("sends the panel to the shelf read", () => {
    // The whole 74.1/74.2 wiring: the request carries the controls and the window, so the rows
    // that come back are the answer, not an input to be filtered or paged again here.
    // Written as a pattern rather than a quoted call: a source walk that counts the app's real
    // call sites (`ai-service`'s window census) must not mistake this line for one.
    expect(source).toMatch(/const saved = useSavedJobs\(\s*tab === "saved" \? filters : undefined\s*\);/);
    expect(resources).toMatch(/export function useSavedJobs\(params\?: JobFilters\)/);
    expect(resources).toContain('queryKey: ["saved-jobs", params]');
    expect(resources).toContain(
      "...serializeJobFilters({ ...params, sort: undefined })"
    );
    // 74.2: the window travels to the wire instead of being cut in the browser.
    expect(resources).not.toContain("page: undefined, size: undefined");
  });

  it("renders the server's answer whole, and filters or windows nothing", () => {
    expect(source).toContain('from "@/lib/job-filter"');
    // The saved list must not reach for a predicate or a window of its own -- that is the
    // mirror, and it is what made the two tabs disagree about the same chip.
    expect(source).not.toMatch(/filterAndPaginate|matchesJobFilters|windowSavedRows/);
    expect(source).not.toContain("savedPage");
    expect(source).toMatch(/const listView = tab === "discover" \? jobs : saved;/);
  });

  it("hands the server's answer to the boundary, not the raw query", () => {
    expect(source).toContain("query={listView}");
    expect(source).not.toContain("query={active}");
    // The Saved tab must never fall through to the Discover query while its own rows
    // are still in flight — that would render someone else's list under the bookmark
    // heading.
    // The count the panel prints under "matching roles" is the answer's own total, which the
    // server narrowed and counted. It is no longer a count of survivors in the browser.
    expect(source).toContain("resultCount={listView.data ? total : undefined}");
  });

  it("shows the clamped page it rendered, not the stale one in the URL", () => {
    expect(source).toContain("page={listView.data?.page ?? filters.page}");
  });

  it("says which kind of empty the Saved tab is from the panel, not the payload", () => {
    // The two empty states are named in the translation table now, so the
    // page reads them through keys rather than carrying the copy itself.
    expect(source).toContain('t("jobs.noSavedMatch")');
    // A filtered shelf says nothing about how many bookmarks sit behind the filter, so the
    // only honest "did a control cause this" is whether a control is set.
    expect(source).toContain("const filteredToEmpty = hasActiveJobFilters(filters);");
    expect(source).toContain("tab === \"saved\" && filteredToEmpty");
    // A shelf the server answered with nothing, filter set or not, still gets its own state.
    expect(source).toContain('t("jobs.nothingSaved")');
  });
});

describe("profileSkillSuggestions", () => {
  // The one production caller passes `useResume(...).data?.structured`, which is the parse answer's
  // jsonb: skills are the flat `{name, category, proficiency}` rows `_merge_skills` writes. #147
  // deleted `groupSkillBuckets`' carry-through of an already-grouped row -- a shape only these
  // fixtures ever had -- so the fixtures now use the shape that arrives.
  const skill = (name: string, category = "tool") => ({ name, category, proficiency: null });

  it("offers every skill the profile knows — a missing chip is a filter that cannot be set", () => {
    const many = Array.from({ length: 31 }, (_, i) => skill(`skill-${i}`));
    const got = profileSkillSuggestions({ skills: many });
    expect(got).toHaveLength(31);
    expect(got).toContain("skill-24");
    expect(got[got.length - 1]).toBe("skill-30");
  });

  it("folds case-only duplicates and keeps the first spelling", () => {
    const got = profileSkillSuggestions({
      skills: [skill("Kubernetes", "cloud"), skill("Go", "language"), skill("kubernetes", "cloud")],
    });
    expect(got).toEqual(["Kubernetes", "Go"]);
  });

  it("trims what it keeps and drops blanks", () => {
    const got = profileSkillSuggestions({ skills: [skill(" TypeScript "), skill(""), skill("   ")] });
    expect(got).toEqual(["TypeScript"]);
  });

  it("answers with nothing when there is no parsed profile", () => {
    expect(profileSkillSuggestions(null)).toEqual([]);
    expect(profileSkillSuggestions(undefined)).toEqual([]);
    expect(profileSkillSuggestions({})).toEqual([]);
    expect(profileSkillSuggestions({ skills: null, experience: null })).toEqual([]);
  });

  it("answers with nothing from a resume nested under a key no caller uses", () => {
    // `ResumeVersionItem.structured` is the DTO's own field name, and both production callers pass
    // the jsonb itself, so unwrapping a `structured` member was tolerance for a shape nobody serves.
    expect(profileSkillSuggestions({ structured: { skills: [skill("Elixir")] } })).toEqual([]);
  });

  it("suggests only chips the answer can actually read", () => {
    // A chip is worth rendering only if picking it filters. The filtering is SQL now, so what
    // this side owes is that the chip's own spelling survives the request: the server's skill
    // clause compares skills case-insensitively -- SavedJobBoardIT holds the shelf and the board
    // to the same word -- and a chip folded or split on the way there is a filter that silently
    // matches nothing.
    const suggestion = profileSkillSuggestions({ skills: [skill("Kubernetes", "cloud")] })[0];
    expect(suggestion).toBe("Kubernetes");
    expect(serializeJobFilters({ skills: suggestion })).toEqual({ skills: "Kubernetes" });
    expect(serializeJobFilters({ skills: "Kubernetes,Go" })).toEqual({ skills: "Kubernetes,Go" });
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

describe("every job filter the UI can send is a parameter the endpoint binds", () => {
  // Spring ignores a query parameter no `@RequestParam` declares: the request still returns 200
  // with the unfiltered list, so a filter key that drifts is a chip that looks applied and a
  // result that never changed -- which is how `remote=true` once matched nothing at all.
  const resources = readFileSync(new URL("./hooks/resources.ts", import.meta.url), "utf8");
  const controller = readFileSync(
    new URL("../../../backend/src/main/java/com/careeros/job/web/JobController.java", import.meta.url),
    "utf8",
  );

  const interface_ = resources.match(/export interface JobFilters \{([^}]*)\}/);
  const declared = [...(interface_?.[1].matchAll(/^\s+(\w+)\?:/gm) ?? [])].map((m) => m[1]);

  // every declared key, with a value that survives the serializer's "empty means absent" filter
  const probe = Object.fromEntries(declared.map((k) => [k, k === "remote" ? true : "x"]));
  const emitted = Object.keys(serializeJobFilters(probe));

  // only the parameters *these* endpoints declare: another handler in the same file binding
  // `company` must not stand in for the list, or the gate passes while the filter goes unanswered
  const paramsOf = (signature: string) =>
    [...signature.matchAll(/@RequestParam\b(?:\(([^)]*)\))?\s+(?:[\w.]+(?:<[^>]*>)?)\s+(\w+)/g)]
      .map((m) => m[1]?.match(/name\s*=\s*"([^"]+)"/)?.[1] ?? m[2]);
  const boundList = paramsOf(controller.match(/PageDTO<JobListItem> list\(([\s\S]*?)\) \{/)?.[1] ?? "");
  const boundSaved = paramsOf(controller.match(/PageDTO<SavedJobItem> saved\(([\s\S]*?)\) \{/)?.[1] ?? "");

  // What the shelf is actually sent: `useSavedJobs` strips the ordering this route does not
  // read, so a stripped key is not a key that went unanswered -- it never left. The strip
  // itself is pinned in "the saved tab's list screen", which is what makes this a projection and
  // not a guess. 74.2: the window (`page`/`size`) is bound now and travels with the predicates.
  const shelfEmitted = emitted.filter((k) => k !== "sort");

  it("reads both sides, not an empty list of them", () => {
    expect(declared.length).toBeGreaterThanOrEqual(8);
    expect(boundList).toEqual(expect.arrayContaining(["q", "skills", "minSalary", "maxSalary", "sort"]));
    expect(boundSaved).toEqual(expect.arrayContaining(["q", "skills", "minSalary", "maxSalary", "remote"]));
    expect(emitted).toEqual(expect.arrayContaining(["q", "minSalary", "maxSalary", "remote"]));
    expect(emitted).not.toContain("min_salary");
  });

  it("sends nothing the board has not declared", () => {
    expect(emitted.filter((key) => !boundList.includes(key))).toEqual([]);
  });

  it("asks the shelf the panel's whole question", () => {
    // 74.1 is the reason this half exists: while the route bound only `user`, every control in
    // the panel moved the URL on the Saved tab and moved nothing on the screen, which is what
    // forced a browser-side copy of the WHERE clause. A control dropped from this signature
    // reopens that hole. 74.2 adds the window: a pager sending a window the route ignores is a
    // pager lying about its answer.
    for (const key of ["q", "skills", "location", "company", "remote", "minSalary", "maxSalary", "page", "size"]) {
      expect(boundSaved, key).toContain(key);
    }
    expect(shelfEmitted.filter((key) => !boundSaved.includes(key))).toEqual([]);
  });
});

describe("the board's sort control", () => {
  // React can't render in this environment, so the wiring is guarded the way the rest of
  // this file guards it: the page is read as data and reconciled against the repository's
  // own ORDERINGS map — the same source the server actually orders by, and the one
  // docs/API.md's sort row is contract-tested against on the backend side.
  const page = readFileSync(new URL("../app/(app)/jobs/page.tsx", import.meta.url), "utf8");
  const repository = readFileSync(
    new URL(
      "../../../backend/src/main/java/com/careeros/job/repository/JobSearchRepository.java",
      import.meta.url,
    ),
    "utf8",
  );

  const orderings = new Set(
    [...(repository.match(/ORDERINGS = Map\.of\(([\s\S]*?)\);/)?.[1].matchAll(/"([a-z_]+)",\s+"/g) ?? [])].map(
      (m) => m[1],
    ),
  );
  const options = page.match(/const SORT_OPTIONS[^=]*= (\[[\s\S]*?\]);/)?.[1] ?? "";
  const offered = new Set([...options.matchAll(/value: "([a-z_]+)"/g)].map((m) => m[1]));

  it("offers every ordering the repository maps and invents none", () => {
    // The control reads the map, not a copy of it: a new ORDERINGS key that never
    // reaches the UI is a feature only a curl invocation can use.
    expect(orderings).toEqual(new Set(["posted", "salary", "title", "match", "relevance"]));
    // `auto` is the spelling for *omitting* the parameter, which the server answers with
    // relevance for a query and recency for a browse — relevance is therefore the one
    // key the control reaches by absence rather than by name.
    expect(offered).toEqual(new Set(["auto", ...[...orderings].filter((k) => k !== "relevance")]));
  });

  it("sends the repository's key, and nothing at all while left on auto", () => {
    expect(page).toContain('setFilters({ sort: v === "auto" ? "" : v, page: 0 })');
    expect(serializeJobFilters({ sort: "" })).toEqual({});
    expect(serializeJobFilters({ sort: "salary" })).toEqual({ sort: "salary" });
  });

  it("is a Discover question while the shelf binds no ordering", () => {
    // Two ways to be wrong here, and they are the same way: a control the route cannot answer,
    // and an answer the control cannot reach. The Saved tab's shelf comes back in bookmark
    // order and `JobController#saved` declares no `sort`, so the control is guarded -- and the
    // guard is tied to the signature rather than to a comment, so 74.2's `sort` parameter is
    // what has to move this case.
    const controller = readFileSync(
      new URL("../../../backend/src/main/java/com/careeros/job/web/JobController.java", import.meta.url),
      "utf8",
    );
    const savedSignature = controller.match(/List<SavedJobItem> saved\(([\s\S]*?)\) \{/)?.[1] ?? "";
    expect(savedSignature).not.toContain("String sort");

    const guard = page.indexOf('{tab === "discover" && (');
    expect(guard).toBeGreaterThan(-1);
    expect(page.indexOf("<Select")).toBeGreaterThan(guard);
  });
});
