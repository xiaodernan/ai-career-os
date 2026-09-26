import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";

import {
  bool,
  coverLetterText,
  idOf,
  list,
  normalizeArtifacts,
  normalizeApplication,
  normalizeChatActions,
  normalizeDashboard,
  normalizeDimensions,
  normalizeInterviewDims,
  normalizeEvidence,
  normalizeInterviewReport,
  normalizeJob,
  normalizeJdParsed,
  normalizeSuggestions,
  missingSkillGaps,
  normalizeMatch,
  normalizeMessages,
  normalizePage,
  normalizePipeline,
  normalizeRun,
  normalizeResumeScore,
  normalizeSearch,
  serializeJobFilters,
  normalizeSkillGaps,
  normalizeStructuredResume,
  normalizeTailor,
  normalizeTailorDiff,
  normalizeTrajectory,
  SEARCH_GROUPS,
  searchGroupNames,
  num,
  pct,
  pick,
  runTotalTokens,
  str,
  structuredResumeToMarkdown,
} from "./normalize";

describe("primitives", () => {
  it("pick tolerates snake/camel drift and skips null", () => {
    expect(pick({ a: null, b: 3 }, "a", "b")).toBe(3);
    expect(pick(null, "x")).toBeUndefined();
  });
  it("str coerces numbers, num parses numeric strings", () => {
    expect(str({ n: 12 }, "n")).toBe("12");
    expect(num({ n: "42.5" }, "n")).toBe(42.5);
    expect(num({ n: "abc" }, "n")).toBeUndefined();
  });
  it("bool reads string booleans", () => {
    expect(bool({ r: "true" }, "r")).toBe(true);
    expect(bool({ r: "no" }, "r")).toBe(false);
  });
  it("list accepts arrays, record values and bare strings", () => {
    expect(list({ a: [1, 2] }, "a")).toEqual([1, 2]);
    expect(list({ a: { x: "Go" } }, "a")).toEqual(["Go"]);
    expect(list({ a: "solo" }, "a")).toEqual(["solo"]);
    expect(list({}, "a")).toEqual([]);
  });
});

describe("pct", () => {
  it("normalizes 0-1, 0-100 and clamps", () => {
    expect(pct(0.87)).toBe(87);
    expect(pct(1)).toBe(100);
    expect(pct(50)).toBe(50);
    expect(pct(150)).toBe(100);
    expect(pct(null)).toBeUndefined();
  });
});

describe("idOf", () => {
  it("prefers a real id and falls back to a prefixed random", () => {
    expect(idOf({ id: "abc" })).toBe("abc");
    expect(idOf({}, "job")).toMatch(/^job-[a-z0-9]+$/);
  });
});

describe("normalizePage", () => {
  it("handles a bare array", () => {
    const p = normalizePage([1, 2, 3], (x) => x);
    expect(p).toEqual({ items: [1, 2, 3], total: 3, page: 0, size: 3 });
  });
  it("handles a spring-style content page", () => {
    const p = normalizePage({ content: [{ id: "a" }], totalElements: 9, pageNumber: 2 }, (x) => x);
    expect(p.total).toBe(9);
    expect(p.page).toBe(2);
  });
});

describe("normalizeEvidence", () => {
  it("maps snake_case citations with score and quote", () => {
    const ev = normalizeEvidence({
      citations: [{ skill: "Go", score: 0.9, quote: "wrote a service", doc_title: "Resume" }],
    });
    expect(ev[0]).toMatchObject({
      criterion: "Go",
      score: 90,
      quote: "wrote a service",
      source: { docTitle: "Resume" },
    });
  });

  it("reads source_kind/document_id/doc_title from a flat ai-service to_evidence item", () => {
    // Exact shape produced by ai-service app/rag/pipeline.py::to_evidence.
    const ev = normalizeEvidence([
      {
        ref: 1,
        chunk_id: "c-1",
        document_id: "doc-9",
        doc_title: "resume-v3",
        source_kind: "resume",
        section: "Experience › Acme",
        quote: "shipped the API",
        score: 0.62,
      },
    ]);
    expect(ev[0].source).toMatchObject({ kind: "resume", docId: "doc-9", docTitle: "resume-v3" });
    expect(ev[0].source?.path).toEqual(["Experience", "Acme"]);
  });

  it("prefers a nested source.kind over the flat fallback", () => {
    const ev = normalizeEvidence([{ source_kind: "note", source: { kind: "jd" } }]);
    expect(ev[0].source?.kind).toBe("jd");
  });
});

describe("normalizeMatch", () => {
  it("returns null when there is nothing signal-bearing", () => {
    expect(normalizeMatch({})).toBeNull();
  });
  it("reads snake_case skills and normalizes overall", () => {
    const m = normalizeMatch({ match_score: 0.82, matched_skills: ["Go", "K8s"], missing_skills: ["Rust"] });
    expect(m).not.toBeNull();
    expect(m!.overall).toBe(82);
    expect(m!.matchedSkills).toEqual(["Go", "K8s"]);
    expect(m!.missingSkills).toEqual(["Rust"]);
  });
  it("accepts a nested match wrapper and evidence", () => {
    const m = normalizeMatch({ match: { overall: 60, evidence: [{ criterion: "A", quote: "q" }] } });
    expect(m!.overall).toBe(60);
    expect(m!.evidence?.[0].criterion).toBe("A");
  });
  it("keeps the stored gap items when the row is replayed after a refresh", () => {
    // GET /jobs/{id} answers MatchSummary — the persisted jsonb, not the compute response — and the
    // gap card indexes `importance` for its badge and `reason` for its line. A reader that dropped
    // either rendered an unlabelled skill, and a page that only looked at the fresh response
    // emptied the whole card the moment the user reloaded.
    const m = normalizeMatch({
      match: {
        overall: 0.62,
        skillGaps: [{ skill: "Kubernetes", importance: "should",
                      reason: "production experience with Kubernetes" }],
      },
    });
    expect(m!.skillGaps).toEqual([
      { skill: "Kubernetes", importance: "should",
        reason: "production experience with Kubernetes" },
    ]);
  });
  it("leaves the gap list undefined when the row carries none", () => {
    // A stored match from before the column existed reads back as `[]`; the card hides itself
    // rather than showing an empty "Growth" section.
    expect(normalizeMatch({ overall: 0.5, skillGaps: [] })!.skillGaps).toBeUndefined();
  });
});

describe("normalizeJob", () => {
  it("reconstructs a match score from JobListItem's flat matchOverall/matchId", () => {
    const j = normalizeJob({
      id: "job-1",
      title: "Backend Engineer",
      companyName: "Acme",
      matchOverall: 0.81,
      matchId: "m-9",
    });
    expect(j.latestMatch).not.toBeNull();
    expect(j.latestMatch!.overall).toBe(81);
    expect(j.latestMatch!.id).toBe("m-9");
    expect(j.latestMatch!.jobId).toBe("job-1");
  });

  it("treats a 0% flat match as present, not missing", () => {
    const j = normalizeJob({ id: "job-2", title: "T", matchOverall: 0 });
    expect(j.latestMatch?.overall).toBe(0);
  });

  it("leaves latestMatch null when no match is carried", () => {
    const j = normalizeJob({ id: "job-3", title: "T", companyName: "Acme" });
    expect(j.latestMatch).toBeNull();
  });

  it("prefers a real nested match object over the flat scalar", () => {
    const j = normalizeJob({
      id: "job-4",
      match: { overall: 90, matchedSkills: ["Go"] },
      matchOverall: 0.4,
    });
    expect(j.latestMatch?.overall).toBe(90);
    expect(j.latestMatch?.matchedSkills).toEqual(["Go"]);
  });

  it("unwraps a SavedJobItem envelope (GET /jobs/saved nests the job under `job`)", () => {
    // Real shape: List<SavedJobItem{ job: JobListItem, note, savedAt }>.
    const j = normalizeJob({
      job: {
        id: "8f1c-uuid",
        title: "Senior Backend Engineer",
        companyId: "co-1",
        companyName: "Acme",
        location: "Remote",
        matchOverall: 0.72,
        matchId: "m-3",
      },
      note: "referred by a friend",
      savedAt: "2026-05-01T10:00:00Z",
    });
    expect(j.id).toBe("8f1c-uuid");
    expect(j.title).toBe("Senior Backend Engineer");
    expect(j.companyName).toBe("Acme");
    expect(j.location).toBe("Remote");
    expect(j.latestMatch?.overall).toBe(72);
  });

  it("still reads a flat JobListItem that carries no `job` envelope", () => {
    const j = normalizeJob({ id: "job-5", title: "Data Engineer", companyName: "Beta" });
    expect(j.id).toBe("job-5");
    expect(j.title).toBe("Data Engineer");
    expect(j.companyName).toBe("Beta");
  });

  it("labels the seniority from experienceYears, the only seniority column there is", () => {
    // `jobs.experience_years` reaches the client as `experienceYears` on both
    // JobListItem and JobDetail. The header's chip used to read `experienceLevel` /
    // `experience_level` / `seniority`, which no producer in either service ever sent,
    // so 41 of the 46 stored jobs rendered a job page that never said what it asks for.
    expect(normalizeJob({ id: "job-6", experienceYears: 3 }).experienceLevel).toBe(
      "3+ years experience"
    );
    expect(normalizeJob({ id: "job-7", experience_years: 0 }).experienceLevel).toBe("Entry level");
  });

  it("hides the chip when the posting never stated a requirement", () => {
    // null must not become "0+ years": that would claim the posting said something.
    const j = normalizeJob({ id: "job-8", title: "T", experienceYears: null });
    expect(j.experienceLevel).toBeUndefined();
    expect(normalizeJob({ id: "job-9", experienceYears: 2024 }).experienceLevel).toBeUndefined();
  });
});

describe("normalizeApplication", () => {
  /** Exactly the columns `ApplicationDtos.ApplicationItem` serializes — no nested objects. */
  const ITEM = {
    id: "app-1",
    jobId: "job-1",
    companyId: "co-1",
    title: "Senior Backend Engineer",
    companyName: "Acme Cloud",
    status: "interview",
    position: 3,
    notes: "onsite 周四",
    reminderAt: "2026-09-30T09:00:00Z",
    resumeVersionId: "rv-1",
    jdId: "jd-1",
    matchId: "m-1",
    appliedAt: "2026-09-10T02:00:00Z",
    createdAt: "2026-09-09T02:00:00Z",
    updatedAt: "2026-09-20T02:00:00Z",
  };

  it("names the company on the field the row actually reads", () => {
    // applications/page.tsx renders `app.company?.name`; the DTO only has flat columns, so
    // without this projection every row's second line is blank.
    const a = normalizeApplication(ITEM);
    expect(a.company?.name).toBe("Acme Cloud");
    expect(a.company?.id).toBe("co-1");
    expect(a.companyName).toBe("Acme Cloud");
  });

  it("keeps the rest of the row: stage, kanban order, reminder and timestamps", () => {
    const a = normalizeApplication(ITEM);
    expect(a).toMatchObject({
      id: "app-1",
      jobId: "job-1",
      title: "Senior Backend Engineer",
      status: "interview",
      position: 3,
      reminderAt: "2026-09-30T09:00:00Z",
    });
  });

  it("reads the note under the DTO's plural column", () => {
    expect(normalizeApplication(ITEM).note).toBe("onsite 周四");
    expect(normalizeApplication({ id: "a", note: "single" }).note).toBe("single");
  });

  it("accepts either spelling of the reminder column", () => {
    expect(normalizeApplication({ id: "a", reminder_at: "2026-09-30" }).reminderAt).toBe("2026-09-30");
  });

  it("prefers a nested company object when a deployment sends one", () => {
    const a = normalizeApplication({
      id: "a",
      company: { id: "co-9", name: "Nested Co", logoUrl: "https://x/logo.png" },
    });
    expect(a.company).toEqual({ id: "co-9", name: "Nested Co", logoUrl: "https://x/logo.png" });
    expect(a.companyName).toBe("Nested Co");
  });

  it("leaves the company absent when the application has none", () => {
    // a title-only application is real (create accepts one); an object with an empty name
    // would render as a blank row that looks like a loading failure.
    const a = normalizeApplication({ id: "a", title: "Freelance gig", status: "saved" });
    expect(a.company).toBeUndefined();
    expect(a.companyName).toBeNull();
    expect(a.companyId).toBeNull();
  });

  it("reports no match score rather than a zero: the DTO carries no such column", () => {
    // ApplicationItem has matchId but not matchScore, and no page renders it today. When the
    // list starts embedding the score, this assertion is the one to change deliberately.
    expect(normalizeApplication(ITEM).matchScore).toBeNull();
  });
});

describe("normalizeSkillGaps", () => {
  it("accepts bare strings and objects", () => {
    const g = normalizeSkillGaps({ skill_gaps: ["Go", { skill: "Rust", importance: "high" }] });
    expect(g[0]).toEqual({ skill: "Go" });
    expect(g[1]).toMatchObject({ skill: "Rust", importance: "high" });
  });
});

describe("normalizeDimensions", () => {
  it("reads a dimension record with mixed value shapes", () => {
    const d = normalizeDimensions({ dimensions: { technical: 0.9, experience: { score: 60, note: "senior" } } });
    expect(d).toHaveLength(2);
    expect(d[0]).toMatchObject({ key: "technical", label: "Technical", score: 90 });
    expect(d[1]).toMatchObject({ key: "experience", score: 60, note: "senior" });
  });
});

describe("normalizeResumeScore", () => {
  // Every fixture is a record that *carries* the map, because that is all any caller sends:
  // `useResume`/`useResumeScore` hand over a ResumeDetail and the dashboard hands over a
  // ResumeSummary, both of which name the rubric map `score`. The fixtures that passed the map bare
  // -- and the one that passed a bare 0.8 -- leaned on a `?? raw` fallback no producer ever
  // reached, so they went with it in #132.
  it("derives labeled gaps from unmet rubric detail", () => {
    const s = normalizeResumeScore({
      score: {
        total: 40,
        detail: [
          { criterion: "has_contact", met: true, points: 15 },
          { criterion: "quantified_impact", met: false, points: 10 },
          { criterion: "has_skills", met: false, points: 10 },
        ],
      },
    });
    expect(s).toMatchObject({
      overall: 40,
      gaps: ["Quantified impact (numbers or %)", "Enough skills (5+)"],
    });
  });

  it("carries the rubric's own 0-100 dimension figures through unscaled", () => {
    // `structure: 38` means 38% of the structural criteria, not 38% of the total (#131).
    const s = normalizeResumeScore({
      score: { total: 65, structure: 38, bullets: 100, impact: 47, clarity: 50, keywords: 0 },
    });
    expect(s).toMatchObject({ overall: 65, structure: 38, bullets: 100, impact: 47, clarity: 50,
                             keywords: 0 });
    // A dimension of exactly 1 is 1%, not a full bar: these must not go through `pct`.
    expect(normalizeResumeScore({ score: { total: 105, clarity: 1 } })?.clarity).toBe(1);
    expect(normalizeResumeScore({ score: { total: 105 } })?.clarity).toBeUndefined();
  });

  it("clamps the 110-point rubric to the 100 the panel prints, and leaves a low score low", () => {
    expect(normalizeResumeScore({ score: { total: 110 } })?.overall).toBe(100);
    expect(normalizeResumeScore({ score: { total: 1 } })?.overall).toBe(1);
  });

  it("answers null for a record with no score and a score with nothing in it", () => {
    // `ResumeVersionItem` projects no score column, so a version row has always answered null here;
    // an empty map would render "0/100", which is a claim about the resume rather than the absence
    // of one, so it stays null too.
    expect(normalizeResumeScore({ id: "v1", label: "Original", kind: "original" })).toBeNull();
    expect(normalizeResumeScore({ score: {} })).toBeNull();
    expect(normalizeResumeScore(null)).toBeNull();
  });
});

describe("normalizeTailorDiff", () => {
  it("splits explicit accepted/rejected lists", () => {
    const d = normalizeTailorDiff({
      diff: {
        accepted: [{ section: "summary", before: "a", after: "b" }],
        rejected: [{ section: "skills", status: "rejected" }],
      },
    });
    expect(d.accepted[0]).toMatchObject({ section: "summary", before: "a", after: "b" });
    expect(d.rejected).toHaveLength(1);
  });
  it("partitions a flat list by status", () => {
    const d = normalizeTailorDiff({
      diff: {
        changes: [
          { section: "x", status: "accepted" },
          { section: "y", status: "skipped" },
        ],
      },
    });
    expect(d.accepted).toHaveLength(1);
    expect(d.rejected).toHaveLength(1);
  });
});

describe("normalizePipeline", () => {
  it("turns kanban.statusCounts into one row per stage", () => {
    // This is what /reports/dashboard actually carries. The function used to also accept a
    // `pipeline` key as an array of {status, count} or as a bare status->count record; no
    // response of either service has ever sent either shape, so the branch and these fixtures
    // went together in #130.
    const p = normalizePipeline({
      kanban: { statusCounts: { saved: 2, applied: 5, offer: 1 }, total: 8, offers: 1 },
    });
    expect(p).toContainEqual({ status: "saved", count: 2 });
    expect(p).toContainEqual({ status: "offer", count: 1 });
    expect(p.reduce((s, row) => s + row.count, 0)).toBe(8);
  });

  it("answers with no rows for a payload that has no kanban", () => {
    expect(normalizePipeline({ interviews: 0 })).toEqual([]);
    expect(normalizePipeline(null)).toEqual([]);
  });
});

describe("coverLetterText", () => {
  it("unwraps nested cover_letter payloads", () => {
    expect(coverLetterText({ content: "Dear" })).toBe("Dear");
    expect(coverLetterText({ cover_letter: { text: "Hi" } })).toBe("Hi");
    expect(coverLetterText({})).toBe("");
  });
});

describe("normalizeRun", () => {
  // Both fixtures are field-for-field out of the records that answer: `DashboardDtos.RecentRun` and
  // `ActivityController.RunItem`. The reader had no direct test before #133 -- only the dashboard's
  // recentRuns path touched it -- which is how four reads for columns neither record has ever had
  // (`summary`, `createdAt`, `relatedHref`, `traces`) survived here.
  it("maps the dashboard's RecentRun, whose kind is the trigger column", () => {
    const run = normalizeRun({
      id: "run-1", agent: "career", trigger: "manual", status: "success", model: "claude-x",
      inputTokens: 120, outputTokens: 34, costUsd: 0.02,
      startedAt: "2026-09-26T02:00:00Z", finishedAt: "2026-09-26T02:00:07Z",
    });
    expect(run).toMatchObject({
      id: "run-1", agent: "career", kind: "manual", status: "success", model: "claude-x",
      startedAt: "2026-09-26T02:00:00Z", finishedAt: "2026-09-26T02:00:07Z",
      tokensIn: 120, tokensOut: 34, costUsd: 0.02,
    });
    expect(runTotalTokens(run)).toBe(154);
    expect(run.error).toBeUndefined();
    expect(run.durationMs).toBeUndefined();
  });

  it("maps the activity list's RunItem, including the columns RecentRun lacks", () => {
    const run = normalizeRun({
      id: "run-2", agent: "tailor", trigger: "scheduled", status: "failed", model: null,
      inputTokens: 10, outputTokens: 0, cachedTokens: 4, costUsd: 0.01, latencyMs: 1830,
      error: "provider timeout", startedAt: "2026-09-26T02:00:00Z", finishedAt: null,
      rootRunId: "run-1", conversationId: "c-9",
    });
    expect(run).toMatchObject({
      id: "run-2", kind: "scheduled", status: "failed", error: "provider timeout",
      durationMs: 1830, tokensIn: 10, tokensOut: 0,
    });
    // cachedTokens / rootRunId / conversationId arrive and are dropped -- the row has no place for
    // them, and the gate's surplus floor names that set so it cannot grow quietly.
    expect("cachedTokens" in run).toBe(false);
    expect("traces" in run).toBe(false);
  });
});

describe("runTotalTokens", () => {
  it("adds the two token counts a run row carries", () => {
    expect(runTotalTokens({ id: "r1", tokensIn: 10, tokensOut: 5 })).toBe(15);
    expect(runTotalTokens({ id: "r1", tokensIn: 10 })).toBe(10);
    // ...and answers undefined for a row the AI service never metered, so the activity list shows no
    // chip rather than a confident zero. The trace-summing branch this test used to assert read
    // `traces`, which no caller of `normalizeRun` can produce: traces arrive on `RunDetail`, and the
    // detail page maps them through `activity-trace` instead.
    expect(runTotalTokens({ id: "r1", agent: "career" })).toBeUndefined();
  });
});

describe("normalizeDashboard", () => {
  it("accepts the snake_case twins of the record's own components", () => {
    // The reader keeps one snake_case twin per drilled component; this is what they are for.
    // It used to also read a `metrics`/`stats` wrapper of flat numbers, which no response of
    // this route carries -- `/reports/dashboard` answers with DashboardResponse and `api.get`
    // has already unwrapped the envelope by the time this function sees it.
    const d = normalizeDashboard({
      kanban: { status_counts: { applied: 3 }, total: 3, offers: 0 },
      current_resume: {
        resume_id: "r1",
        version_id: "v1",
        title: "My resume",
        status: "parsed",
        // The score map stays camel inside the snake wrapper: it is a jsonb blob the Python rubric
        // wrote (`{total, detail, …}`), and Jackson renames the record's own components, not the
        // keys of a Map it is handing through. This fixture used to claim `overall: 0.7`, a name
        // and a scale nothing has ever emitted; #132's reader only asks for what is there.
        score: { total: 70 },
      },
      skill_gaps: { missing_skills: ["Rust"] },
    });
    expect(d!.metrics).toMatchObject({ applications: 3, inPipeline: 3, resumeScore: 70, skillGaps: 1 });
    expect(d!.resume).toMatchObject({ id: "r1", currentVersionId: "v1", title: "My resume" });
  });

  it("maps the real DashboardResponse (kanban / currentResume / skillGaps digest)", () => {
    const payload = {
      kanban: { statusCounts: { saved: 2, applied: 5, interview: 1, offer: 1 }, total: 9, offers: 1 },
      interviews: 1,
      currentResume: {
        resumeId: "resume-1",
        versionId: "version-1",
        title: "Backend Eng 2026",
        status: "parsed",
        score: { total: 78, detail: [{ criterion: "quantified_impact", met: false, points: 10 }] },
      },
      skillGaps: {
        jobId: "j1",
        jobTitle: "Staff Eng",
        overall: 0.62,
        missingSkills: ["Rust", "gRPC"],
        matchedSkills: ["Go"],
      },
      recommendedJobs: [{ id: "j2", title: "Senior Eng", companyName: "Acme", matchOverall: 0.81 }],
      recentRuns: [{ id: "r1", agent: "match", trigger: "manual", status: "success", inputTokens: 100, outputTokens: 40 }],
    };
    // pipeline reaches into kanban.statusCounts (previously always empty)
    expect(normalizePipeline(payload)).toEqual(
      expect.arrayContaining([
        { status: "saved", count: 2 },
        { status: "applied", count: 5 },
        { status: "offer", count: 1 },
      ]),
    );
    const d = normalizeDashboard(payload)!;
    // stat strip pulls applications/offers from kanban, resume score from currentResume.score
    expect(d.metrics).toMatchObject({ applications: 9, offers: 1, interviews: 1, resumeScore: 78, skillGaps: 2 });
    expect(d.metrics!.inPipeline).toBe(9); // 2+5+1+1
    // resume id/version map from resumeId/versionId so the Open link + parse gate work
    expect(d.resume).toMatchObject({
      id: "resume-1",
      currentVersionId: "version-1",
      title: "Backend Eng 2026",
      status: "parsed",
      score: { overall: 78 },
    });
    // the digest's missingSkills become SkillGap rows
    expect(d.skillGaps).toEqual([{ skill: "Rust" }, { skill: "gRPC" }]);
    expect(d.recommendedJobs?.[0]).toMatchObject({ id: "j2", title: "Senior Eng" });
    expect(d.recentRuns?.[0]).toMatchObject({ id: "r1", agent: "match", status: "success" });
  });

  it("scales the reported 0..1 average match into the percentage the ring draws", () => {
    // float4 round-trip, exactly as Postgres surfaces avg() over job_matches.overall.
    const d = normalizeDashboard({
      kanban: { statusCounts: { saved: 1 }, total: 1, offers: 0 },
      interviews: 0,
      avgMatch: 0.6956999897956848,
      needsAttention: 3,
    })!;
    expect(d.metrics!.avgMatch).toBe(70);
    expect(d.metrics!.needsAttention).toBe(3);
  });

  it("leaves the average undefined rather than zero for an account with no matches", () => {
    // The endpoint sends null here; a coerced 0 would draw a 0% ring and read as "scored badly".
    const d = normalizeDashboard({
      kanban: {
        statusCounts: { saved: 0, applied: 0, oa: 0, interview: 0, final_round: 0, offer: 0, rejected: 0 },
        total: 0,
        offers: 0,
      },
      interviews: 0,
      avgMatch: null,
      needsAttention: 0,
      currentResume: null,
      skillGaps: null,
      recommendedJobs: [],
      recentRuns: [],
      recentActivity: [],
    })!;
    expect(d.metrics!.avgMatch).toBeUndefined();
    // ...while the zero count still reports as zero, and the strip keeps rendering the other cards.
    expect(d.metrics!.needsAttention).toBe(0);
    expect(d.metrics).toBeDefined();
  });

  it("reports needsAttention as the metric, and never as rows it would have to invent", () => {
    const d = normalizeDashboard({
      kanban: { statusCounts: {}, total: 0, offers: 0 },
      avgMatch: 0.5,
      needsAttention: 4,
    })!;
    expect(d.metrics!.needsAttention).toBe(4);
    // The reader used to also build an `attention` list from a key this record has never
    // carried; it could only ever answer `[]`, so both the read and the empty list are gone.
    expect("attention" in d).toBe(false);
  });
});

describe("copilot chat: live reply must normalize identically to history", () => {
  // Real ai-service orchestrator sub-shapes (top-level snake_case, no nested
  // `source` map): see agents/orchestrator.py sources/actions/artifacts.
  const aiServiceReply = {
    answer: "Based on your resume…",
    runId: "run-1",
    artifacts: [
      { type: "match", job_id: "j1", payload: { overall: 0.8 } },
      { type: "cover_letter", payload: { letter: "Hi" } },
    ],
    sources: [
      { type: "source", chunk_id: "c9", document_id: "doc-7", label: "resume › skills", quote: "5y React" },
    ],
    actions: [
      { kind: "open_job", label: "Open Frontend @ Acme", job_id: "j1" },
      { kind: "tailor", label: "Tailor resume", job_id: "j1" },
    ],
  };

  it("reads document_id / chunk_id (top-level snake) so citations link to /knowledge", () => {
    const [src] = normalizeEvidence(pick(aiServiceReply, "sources"));
    expect(src.quote).toBe("5y React");
    expect(src.source?.docId).toBe("doc-7"); // was dropped → dead citation link
    expect(src.chunkIds).toEqual(["c9"]);
    expect(src.criterion).toBe("resume › skills"); // label → criterion
  });

  it("normalizeChatActions maps ai-service action objects", () => {
    const acts = normalizeChatActions(pick(aiServiceReply, "actions"));
    expect(acts[0]).toMatchObject({ label: "Open Frontend @ Acme", kind: "open_job" });
    // no href on these → MessageRow filters them out; but label is preserved
    expect(acts.every((a) => typeof a.label === "string" && a.label.length)).toBe(true);
  });

  it("normalizeArtifacts coerces type + payload", () => {
    const arts = normalizeArtifacts(pick(aiServiceReply, "artifacts"));
    expect(arts[0]).toMatchObject({ type: "match" });
    expect(arts[0].data).toEqual({ overall: 0.8 });
  });

  it("history path yields the same normalized sources/actions as the live path", () => {
    const [historyMsg] = normalizeMessages([
      { id: "m1", role: "assistant", content: aiServiceReply.answer, ...aiServiceReply },
    ]);
    const liveSources = normalizeEvidence(pick(aiServiceReply, "sources"));
    const liveActions = normalizeChatActions(pick(aiServiceReply, "actions"));
    expect(historyMsg.sources).toEqual(liveSources);
    expect(historyMsg.actions).toEqual(liveActions);
  });
});

describe("normalizeJdParsed", () => {
  // Real POST /jds response = JdItem: the ai-service dict is nested under `parsed`.
  const jdItem = {
    id: "jd-1",
    jobId: "job-1",
    rawText: "We need a senior engineer…",
    parsed: {
      title: "Senior Engineer",
      requiredSkills: [
        { name: "go", priority: "must", evidence_phrase: "proficient in Go" },
        { name: "kubernetes", priority: "must", evidence_phrase: "k8s experience" },
      ],
      preferredSkills: [{ name: "rust", priority: "nice" }],
      responsibilities: ["Own services", "Mentor juniors"],
      interviewTopics: ["system design", "concurrency"],
      hiddenRequirements: ["on-call", "fast pace"],
    },
    createdAt: "2026-01-01T00:00:00Z",
  };

  it("reads skills/topics from the nested parsed map (not the JdItem top level)", () => {
    const p = normalizeJdParsed(jdItem);
    expect(p.requiredSkills).toEqual(["go", "kubernetes"]); // object items → name
    expect(p.preferredSkills).toEqual(["rust"]);
    expect(p.responsibilities).toEqual(["Own services", "Mentor juniors"]);
    expect(p.interviewTopics).toEqual(["system design", "concurrency"]);
    expect(p.hiddenRequirements).toEqual(["on-call", "fast pace"]);
  });

  it("returns empty arrays when the caller passes the flat top level only (regression guard)", () => {
    // Before the fix the reader looked here and silently got nothing.
    const flat = normalizeJdParsed({ requiredSkills: ["go"] }); // flat, no `parsed`
    expect(flat.requiredSkills).toEqual(["go"]); // still tolerates a flat body
    const wrongShape = normalizeJdParsed({ id: "jd-1", rawText: "…" }); // JdItem with empty parsed
    expect(wrongShape.requiredSkills).toEqual([]);
  });

  it("snake_case inner keys and skill/text aliases still resolve", () => {
    const p = normalizeJdParsed({
      parsed: { required_skills: [{ skill: "Go" }], interview_topics: [{ text: "RAG" }] },
    });
    expect(p.requiredSkills).toEqual(["Go"]);
    expect(p.interviewTopics).toEqual(["RAG"]);
  });
});

describe("structuredResumeToMarkdown / normalizeTailor document", () => {
  // ai-service tailor returns `tailored` as a structured resume dict (no markdown).
  const tailoredStructured = {
    profile: { name: "Ada L", headline: "Backend Engineer", email: "ada@x.io" },
    summary: "Builds distributed systems.",
    experience: [
      {
        company: "Acme",
        title: "Senior Engineer",
        start: "2021-01",
        current: true,
        bullets: ["Shipped API", "Cut p99 40%"],
      },
    ],
    projects: [{ name: "Gateway", bullets: ["Rate limiter"], tech_stack: ["Go", "gRPC"] }],
    education: [{ school: "MIT", degree: "BS", major: "CS" }],
    skills: [{ group: "Languages", skills: ["Go", "Java"] }],
    technologies: ["Kubernetes"],
    achievements: ["Speaker"],
  };

  it("renders every present section into markdown without inventing", () => {
    const md = structuredResumeToMarkdown(tailoredStructured);
    expect(md).toContain("# Ada L");
    expect(md).toContain("### Backend Engineer");
    expect(md).toContain("ada@x.io");
    expect(md).toContain("## Summary");
    expect(md).toContain("### Senior Engineer — Acme (2021-01 – Present)");
    expect(md).toContain("- Shipped API");
    expect(md).toContain("- Rate limiter");
    expect(md).toContain("_Go, gRPC_");
    expect(md).toContain("MIT — BS, CS");
    expect(md).toContain("- Languages: Go, Java");
    expect(md).toContain("Technologies: Kubernetes");
    expect(md).toContain("- Speaker");
  });

  it("returns empty string for a non-object", () => {
    expect(structuredResumeToMarkdown(null)).toBe("");
    expect(structuredResumeToMarkdown("hi")).toBe("");
  });

  it("renders flat {name,category} skill names under their category (not a bare label)", () => {
    // ai-service parse/tailor emit skills as a FLAT list; without bucketing the
    // markdown showed only "language"/"framework" and dropped every skill name.
    const md = structuredResumeToMarkdown({
      skills: [
        { name: "Java", category: "language", proficiency: null },
        { name: "Kotlin", category: "language", proficiency: null },
        { name: "Spring", category: "framework", proficiency: null },
      ],
    });
    expect(md).toContain("- language: Java, Kotlin");
    expect(md).toContain("- framework: Spring");
    expect(md).not.toMatch(/^- language\s*$/m); // no name-less "category only" line
  });

  it("normalizeTailor derives markdown so the document view is no longer dead", () => {
    const t = normalizeTailor({
      tailored: tailoredStructured,
      diff: { accepted: [{ section: "experience", before: "a", after: "b", reason: "JD match" }], rejected: [] },
      notes: ["double-check dates"],
      stats: { accepted: 1, rejected: 0 },
    });
    // previously tailored===undefined (structured dict has no markdown/text keys)
    expect(t.tailored).toBeTruthy();
    expect(t.tailored?.markdown).toContain("# Ada L");
    expect(t.diff?.accepted[0]).toMatchObject({ before: "a", after: "b", reason: "JD match" });
    expect(t.notes).toEqual(["double-check dates"]);
    expect(t.stats).toMatchObject({ accepted: 1 });
  });

  it("explicit markdown/text wins over derivation", () => {
    const t = normalizeTailor({ tailored: { markdown: "PRESET", ...tailoredStructured } });
    expect(t.tailored?.markdown).toBe("PRESET");
  });

  it("offers no run to follow: tailoring answers with the run itself", () => {
    // /jobs/{id}/tailor is a synchronous pass-through of the ai-service answer, which carries
    // these five keys and no task id. Reading `taskId` off it used to hand the panel a stream
    // affordance that could never open.
    const t = normalizeTailor({ tailored: tailoredStructured });
    expect(Object.keys(t).sort()).toEqual([
      "diff", "evidence", "notes", "stats", "tailored",
    ]);
  });
});

describe("normalizeSearch", () => {
  const backendShape = {
    query: "react",
    jobs: [{ id: "j1", title: "Frontend Eng", companyName: "Acme", location: "Remote", status: "open" }],
    companies: [{ id: "c1", name: "Acme", industry: "SaaS", website: "acme.com" }],
    resumes: [{ id: "r1", title: "Resume 2026", status: "parsed" }],
    notes: [{ id: "n1", title: "Idea", snippet: "about react" }],
    conversations: [{ id: "v1", title: "Chat", snippet: "prev" }],
    applications: [{ id: "a1", title: "Applied", companyName: "Acme", status: "applied" }],
  };

  it("maps the backend typed-lists shape into groups with real routes", () => {
    const { groups } = normalizeSearch(backendShape);
    expect(groups.map((g) => g.label)).toEqual([
      "Jobs", "Companies", "Resumes", "Notes", "Conversations", "Applications",
    ]);
    const job = groups[0].items[0];
    expect(job).toMatchObject({ id: "j1", type: "job", title: "Frontend Eng", subtitle: "Acme" });
    expect(job.href).toBe("/jobs/j1");
    expect(groups[1].items[0].href).toBe("/companies"); // no company detail route
    expect(groups[1].items[0].subtitle).toBe("SaaS"); // company subtitle falls back to industry
    expect(groups[2].items[0].href).toBe("/resumes/r1");
    expect(groups[3].items[0].href).toBe("/knowledge");
    expect(groups[4].items[0].href).toBe("/copilot");
    expect(groups[5].items[0].href).toBe("/applications");
    expect(groups.flatMap((g) => g.items).every((i) => i.type && i.href)).toBe(true);
  });

  it("drops empty typed buckets so no blank headings appear", () => {
    const { groups } = normalizeSearch({ query: "x", jobs: backendShape.jobs, companies: [] });
    expect(groups).toHaveLength(1);
    expect(groups[0].label).toBe("Jobs");
  });

  it("returns no groups for an all-empty backend response", () => {
    expect(normalizeSearch({ query: "zzz", jobs: [], notes: [] }).groups).toEqual([]);
  });

  it("keeps a hit whose match lives outside the title", () => {
    // SearchRepository's WHERE clauses, group by group: only `resumes` match the title.
    // The rest can answer for a term the displayed title never contains, so nothing in
    // here may filter on the term — the palette used to, and printed "No results." over
    // these exact rows.
    const k8s = "k8s";
    const { groups } = normalizeSearch({
      query: k8s,
      jobs: [{ id: "j1", title: "Platform Engineer", companyName: "Northwind", location: "Remote" }],
      companies: [{ id: "c1", name: "Northwind", industry: "Kubernetes tooling" }],
      resumes: [{ id: "r1", title: "k8s platform resume", status: "parsed" }],
      notes: [{ id: "n1", title: "SRE plan", snippet: "adopt k8s in Q3" }],
      conversations: [{ id: "v1", title: "Weekly sync", snippet: "we moved to k8s" }],
      applications: [{ id: "a1", title: "Infra Engineer", companyName: "Northwind", status: "applied" }],
    });
    const survivors = groups.flatMap((g) => g.items);
    expect(survivors.map((i) => i.id)).toEqual(["j1", "c1", "r1", "n1", "v1", "a1"]);
    // Five of the six titles carry no trace of the term — resumes are the exception,
    // because that one query matches the title and nothing else.
    expect(survivors.filter((i) => !i.title.toLowerCase().includes(k8s))).toHaveLength(5);
  });

  it("answers for exactly the groups the backend's SearchResponse carries", () => {
    // Cross-language contract: a new List<…> in the Java DTO that SEARCH_GROUPS doesn't
    // know about would be searched, returned, and silently never shown.
    const java = readFileSync(
      new URL("../../../../backend/src/main/java/com/careeros/search/dto/SearchDtos.java", import.meta.url),
      "utf8"
    );
    const response = java.slice(java.indexOf("record SearchResponse"));
    const wireKeys = [...response.matchAll(/List<\w+>\s+(\w+)/g)].map((m) => m[1]);
    expect(wireKeys.length).toBeGreaterThan(0);
    // Same keys, same order — the palette renders groups in response order.
    expect(SEARCH_GROUPS.map((g) => g.key)).toEqual(wireKeys);
  });

  it("says every group it can search, in one sentence", () => {
    expect(searchGroupNames()).toBe(
      "jobs, companies, resumes, notes, conversations and applications"
    );
  });
});

describe("serializeJobFilters", () => {
  it("maps snake_case salary filters to the backend camelCase param names", () => {
    expect(serializeJobFilters({ min_salary: 120, max_salary: 200 })).toEqual({
      minSalary: 120,
      maxSalary: 200,
    });
  });

  it("passes other keys through unchanged", () => {
    expect(serializeJobFilters({ q: "react", page: 2, skills: "go,k8s" })).toEqual({
      q: "react",
      page: 2,
      skills: "go,k8s",
    });
  });

  it("maps the remote boolean to a remote_type value the backend can match", () => {
    // Backend filters `remote_type = :remote` over onsite|hybrid|remote; the old
    // passthrough sent `true`, which matched no job. true -> "remote", a real
    // value passes through untouched, false/undefined drop the filter entirely.
    expect(serializeJobFilters({ remote: true })).toEqual({ remote: "remote" });
    expect(serializeJobFilters({ remote: "hybrid" })).toEqual({ remote: "hybrid" });
    expect(serializeJobFilters({ remote: false })).toEqual({});
    expect(serializeJobFilters({ remote: undefined })).toEqual({});
  });

  it("drops empty strings and undefined values", () => {
    expect(
      serializeJobFilters({ q: "", min_salary: undefined, max_salary: 90, location: undefined })
    ).toEqual({ maxSalary: 90 });
  });

  it("produces no minSalary key when salary is absent (so default is unfiltered)", () => {
    const out = serializeJobFilters({ q: "x" });
    expect("minSalary" in out).toBe(false);
    expect("min_salary" in out).toBe(false);
  });
});

describe("normalizeInterviewDims", () => {
  // The only shape `EvaluationItem.dims` can hold is a jsonb copy of the finalize prompt's
  // `"dims": {technical_accuracy: 0.0-1.0, …}` -- numbers keyed by the AI service's own dimension
  // names. The reader also walked an array of `{key, score}` and an object-valued `{score, label}`
  // per dimension; neither has an author, and #141 deleted both, so this function had no test at
  // all before. Note the labels: `DIMENSION_LABELS` is the *match* vocabulary (technical,
  // experience, …) and matches none of the interview names, so every interview row falls through to
  // the snake-split fallback. Giving them real labels is copy, not a contract, and is left alone.
  it("walks the report's dimension map, keyed by the AI service's names", () => {
    const dims = normalizeInterviewDims({
      dims: { technical_accuracy: 0.9, communication: 0.6, depth: 1 },
    });
    expect(dims.map((d) => [d.key, d.score])).toEqual([
      ["technical_accuracy", 90],
      ["communication", 60],
      ["depth", 100],
    ]);
    expect(dims.map((d) => d.label)).toEqual(["technical accuracy", "communication", "depth"]);
  });

  it("drops a value that is not a number, and answers nothing for the shapes with no author", () => {
    expect(normalizeInterviewDims({ dims: { depth: "high", communication: 0.4 } })).toEqual([
      { key: "communication", label: "communication", score: 40 },
    ]);
    expect(normalizeInterviewDims({})).toEqual([]);
    // the two deleted paths: an array of dimension objects, and one object per dimension
    expect(normalizeInterviewDims({ dims: [{ key: "depth", score: 0.9 }] })).toEqual([]);
    expect(normalizeInterviewDims({ dims: { depth: { score: 0.9, label: "Depth" } } })).toEqual([]);
  });
});

describe("normalizeInterviewReport", () => {
  it("reads scalar results nested inside summary (real EvaluationItem shape)", () => {
    const report = normalizeInterviewReport({
      id: "e1",
      dims: { communication: 0.8, technical_accuracy: 0.9 },
      summary: {
        overall: 0.72,
        what_you_did_well: ["clear structure", "solid tradeoffs"],
        what_was_weak: ["vague on scaling"],
        recommended_study: [
          { topic: "DDIA", why: "partitioning", resource_hint: "https://x" },
          { topic: "Idempotency", why: "retries", resource_hint: "the Kafka docs" },
        ],
        trajectory_note: "Held altitude until depth-4.",
      },
      trajectory: [{ question: "rate limiting", depth: 3, score: 0.6 }],
      createdAt: "2026-09-22T00:00:00Z",
    });
    expect(report?.overall).toBe(72);
    expect(report?.well).toEqual(["clear structure", "solid tradeoffs"]);
    expect(report?.weak).toEqual(["vague on scaling"]);
    expect(report?.summary).toBe("Held altitude until depth-4.");
    expect(report?.study).toEqual([
      { title: "DDIA", url: "https://x", why: "partitioning" },
      { title: "Idempotency", why: "retries · the Kafka docs" },
    ]);
    expect(report?.trajectory).toEqual([{ question: "rate limiting", score: 60, depth: 3 }]);
    expect(report?.dims.map((d) => d.key)).toEqual(["communication", "technical_accuracy"]);
    expect(report?.hasContent).toBe(true);
  });

  it("reads a report whose summary is the plain string rather than a map", () => {
    // The names here are the declared contract (ai-service `FINALIZE_FIELDS`): the fixture used to
    // hand the reader `strengths`/`weaknesses`/`study`/`label`/`level`, none of which any producer
    // has ever emitted, which is what kept those alternate probes alive.
    const report = normalizeInterviewReport({
      overall: 88,
      what_you_did_well: ["fast"],
      what_was_weak: ["shaky tests"],
      recommended_study: [{ topic: "docs" }],
      trajectory: [{ topic: "q1", score: 80, depth: 2 }],
      summary: "Strong overall.",
    });
    expect(report?.overall).toBe(88);
    expect(report?.well).toEqual(["fast"]);
    expect(report?.weak).toEqual(["shaky tests"]);
    expect(report?.summary).toBe("Strong overall.");
    expect(report?.study[0].title).toBe("docs");
    expect(report?.trajectory[0]).toEqual({ question: "q1", score: 80, depth: 2 });
    expect(report?.hasContent).toBe(true);
  });

  it("reads the raw finalize envelope {evaluation,session} the POST /finalize returns", () => {
    // useFinalizeInterview now unwraps `evaluation` and feeds this exact
    // InterviewDtos.FinalizeResponse shape to the same normalizer the report
    // page uses, so both paths agree. trajectory arrives as [] because the
    // backend stores it separately (trajectory_detail) — the summary sub-map
    // carries the scalar results.
    const report = normalizeInterviewReport({
      evaluation: {
        id: "e1",
        dims: { technical: 0.9, communication: 0.6 },
        summary: {
          overall: 0.78,
          what_you_did_well: ["grounded examples"],
          what_was_weak: ["skipped failure modes"],
          recommended_study: [{ topic: "Designing Data-Intensive Applications", why: "partitioning" }],
          trajectory_note: "Depth reached level 3.",
        },
        trajectory: [],
        createdAt: "2026-09-22T00:00:00Z",
      },
      session: { id: "s1", status: "completed" },
    });
    expect(report?.overall).toBe(78);
    expect(report?.well).toEqual(["grounded examples"]);
    expect(report?.weak).toEqual(["skipped failure modes"]);
    expect(report?.summary).toBe("Depth reached level 3.");
    expect(report?.study[0].title).toBe("Designing Data-Intensive Applications");
    expect(report?.dims.map((d) => d.score)).toEqual([90, 60]);
    expect(report?.hasContent).toBe(true);
  });

  it("maps the real ai-service study shape {topic, why, resource_hint} onto title/why", () => {
    // ai-service FINALIZE + InterviewService.persistFinalization emit/copy
    // recommended_study as {topic, why, resource_hint}. Reading only title/name
    // rendered every card as "Untitled resource".
    const report = normalizeInterviewReport({
      summary: {
        overall: 0.6,
        recommended_study: [
          { topic: "Failure modes", why: "you skipped them", resource_hint: "DDIA ch.9" },
        ],
      },
    });
    expect(report?.study[0]).toEqual({
      title: "Failure modes",
      url: undefined,
      why: "you skipped them · DDIA ch.9",
      kind: undefined,
    });
    expect(report?.hasContent).toBe(true);
  });

  it("turns an http resource_hint into a real link, a plain one into the why line", () => {
    const link = normalizeInterviewReport({
      summary: { recommended_study: [{ topic: "Concurrency", resource_hint: "https://example.com/c" }] },
    });
    expect(link?.study[0].url).toBe("https://example.com/c");
    expect(link?.study[0].why).toBeUndefined();

    const name = normalizeInterviewReport({
      summary: { recommended_study: [{ topic: "Concurrency", resource_hint: "The Art of Concurrency" }] },
    });
    expect(name?.study[0].url).toBeUndefined();
    expect(name?.study[0].why).toBe("The Art of Concurrency");
  });

  it("keeps a bare-string recommended_study (the backend test fixture) from vanishing", () => {
    // FakeAiServiceClientConfig returns recommended_study as List.of("Designing
    // Data-Intensive Applications") — a string, not an object.
    const report = normalizeInterviewReport({
      summary: { overall: 0.5, recommended_study: ["Designing Data-Intensive Applications"] },
    });
    expect(report?.study[0].title).toBe("Designing Data-Intensive Applications");
    expect(report?.hasContent).toBe(true);
  });

  it("returns null for non-object payloads", () => {
    expect(normalizeInterviewReport(null)).toBeNull();
    expect(normalizeInterviewReport(undefined)).toBeNull();
    expect(normalizeInterviewReport("nope")).toBeNull();
  });

  it("an object with nothing scoreable reports no content", () => {
    const report = normalizeInterviewReport({ id: "x", dims: {}, summary: {}, trajectory: [] });
    expect(report).not.toBeNull();
    expect(report?.hasContent).toBe(false);
    expect(report?.dims).toEqual([]);
  });
});

/**
 * `interview_evaluations.trajectory` (ai-service `finalize` → `_trajectory_detail`) is
 * one row per TURN: the `interviewer` row carries `topic` + `depth` where depth is only
 * a follow-up FLAG (0 new topic / 1 followed up), and the grade lands on the following
 * `candidate` row. Projecting every row as a question drew the chart with a phantom
 * zero-depth point between each pair, gave every question `score: undefined`, and
 * printed the candidate rows as unanswered questions. ROWS below is the longest run in
 * the live database, transcribed verbatim.
 */
const ROWS = [
  { seq: 1, role: "interviewer", depth: 0, score: null, topic: "your background" },
  { seq: 2, role: "candidate", depth: null, score: 0.72, topic: null },
  { seq: 3, role: "interviewer", depth: 1, score: null, topic: "caching" },
  { seq: 4, role: "candidate", depth: null, score: 0.72, topic: null },
  { seq: 5, role: "interviewer", depth: 1, score: null, topic: "caching" },
];

describe("normalizeTrajectory", () => {
  it("folds per-turn rows into one point per question", () => {
    expect(normalizeTrajectory({ trajectory: ROWS })).toEqual([
      { question: "your background", score: 72, depth: 1 },
      { question: "caching", score: 72, depth: 2 },
      { question: "caching", score: undefined, depth: 3 },
    ]);
  });

  it("makes the ladder the run length, because the producer only flags follow-ups", () => {
    // Three follow-ups in a row is depth 2,3,4 — every row would otherwise say 1, and
    // a chart of "how deep did it push" would be flat no matter how hard it pushed.
    const rows = [
      { role: "interviewer", depth: 1, score: null, topic: "a" },
      { role: "candidate", depth: null, score: 0.4, topic: null },
      { role: "interviewer", depth: 1, score: null, topic: "b" },
      { role: "candidate", depth: null, score: 0.4, topic: null },
      { role: "interviewer", depth: 1, score: null, topic: "c" },
    ];
    expect(normalizeTrajectory({ trajectory: rows }).map((p) => p.depth)).toEqual([1, 2, 3]);
    // A new topic (depth 0) resets the ladder to the first rung.
    expect(
      normalizeTrajectory({
        trajectory: [...rows.slice(0, 3), { role: "interviewer", depth: 0, score: null, topic: "d" }],
      }).map((p) => p.depth)
    ).toEqual([1, 2, 1]);
  });

  it("borrows the next candidate grade without double-borrowing across questions", () => {
    // seq5 was never answered: the last question must not inherit seq4's grade.
    const [first, , third] = normalizeTrajectory({ trajectory: ROWS });
    expect(third.score).toBeUndefined();
    expect(first.score).toBe(72);
    // An unanswered question in the middle stops at its own answer row.
    const rows = [
      { role: "interviewer", depth: 0, score: null, topic: "asked" },
      { role: "candidate", depth: null, score: 0.9, topic: null },
      { role: "interviewer", depth: 0, score: null, topic: "skipped" },
      { role: "interviewer", depth: 1, score: null, topic: "answered" },
      { role: "candidate", depth: null, score: 0.5, topic: null },
    ];
    expect(normalizeTrajectory({ trajectory: rows })).toEqual([
      { question: "asked", score: 90, depth: 1 },
      { question: "skipped", score: undefined, depth: 1 },
      { question: "answered", score: 50, depth: 2 },
    ]);
  });

  it("passes role-less one-per-question rows through untouched", () => {
    // The mock evaluator and the report fixtures already emit folded rows; re-laddering
    // those would rewrite depths the tests (and users) already read.
    expect(
      normalizeTrajectory({ trajectory: [{ question: "rate limiting", depth: 3, score: 0.6 }] })
    ).toEqual([{ question: "rate limiting", score: 60, depth: 3 }]);
    expect(normalizeTrajectory({ trajectory: [{ label: "q1", score: 80, level: 2 }] })).toEqual([
      { question: "q1", score: 80, depth: 2 },
    ]);
  });

  it("reads trajectory_detail, the name the backend column carries", () => {
    expect(normalizeTrajectory({ trajectory_detail: ROWS })).toHaveLength(3);
    expect(normalizeTrajectory({ depth_trajectory: ROWS })).toHaveLength(3);
    expect(normalizeTrajectory({ trajectory: null, trajectory_detail: ROWS })).toHaveLength(3);
  });

  it("returns an empty list for a payload with no trajectory", () => {
    expect(normalizeTrajectory({})).toEqual([]);
    expect(normalizeTrajectory(null)).toEqual([]);
    expect(normalizeTrajectory({ trajectory: [] })).toEqual([]);
  });
});

describe("normalizeMatch reasoning", () => {
  it("maps the backend `narrative` field into reasoning (the match panel's \"why\")", () => {
    const m = normalizeMatch({
      overall: 0.72,
      matched_skills: ["Go"],
      narrative: "Strong systems background.",
    });
    expect(m?.reasoning).toBe("Strong systems background.");
    expect(m?.overall).toBe(72);
    expect(m?.matchedSkills).toEqual(["Go"]);
  });

  it("prefers an explicit reasoning over narrative when both are present", () => {
    const m = normalizeMatch({ overall: 50, reasoning: "r", narrative: "n" });
    expect(m?.reasoning).toBe("r");
  });
});

describe("normalizeSuggestions / missingSkillGaps", () => {
  it("maps the ai-service {skill,type,advice} shape into titled suggestions", () => {
    const raw = {
      suggestions: [
        { skill: "Go", type: "missing_required", advice: "JD requires Go. Add a bullet." },
        { skill: "", type: "structure", advice: "Add a projects section." },
        { skill: "", type: "impact", advice: "Quantify impact." },
      ],
    };
    const out = normalizeSuggestions(raw);
    expect(out).toHaveLength(3);
    expect(out[0]).toMatchObject({ title: "Add Go", section: "missing_required", priority: "high" });
    expect(out[0].text).toContain("JD requires Go");
    expect(out[1].title).toBe("Structure"); // type label when no skill
    expect(out[2].title).toBe("Impact");
    expect(out[2].priority).toBeUndefined();
  });

  it("accepts a bare array and passes through already-shaped items", () => {
    expect(normalizeSuggestions([{ skill: "Rust", type: "missing_required", advice: "x" }])[0].title).toBe(
      "Add Rust",
    );
    const shaped = normalizeSuggestions({ suggestions: [{ title: "T", text: "B" }] });
    expect(shaped[0]).toMatchObject({ title: "T", text: "B", section: undefined });
  });

  it("drops entries with neither title nor text and returns [] for non-lists", () => {
    expect(normalizeSuggestions([{ type: "", skill: "", advice: "" }])).toEqual([]);
    expect(normalizeSuggestions(null)).toEqual([]);
    expect(normalizeSuggestions("nope")).toEqual([]);
    expect(normalizeSuggestions({ suggestions: [] })).toEqual([]);
  });

  it("extracts the resume-lacking skills for the gap list", () => {
    const sugs = normalizeSuggestions({
      suggestions: [
        { skill: "Go", type: "missing_required", advice: "x" },
        { skill: "Kubernetes", type: "missing_required", advice: "y" },
        { skill: "", type: "impact", advice: "z" },
      ],
    });
    expect(missingSkillGaps(sugs)).toEqual(["Go", "Kubernetes"]);
  });
});

describe("normalizeStructuredResume", () => {
  // Verbatim ai-service `parse_resume` output — this is exactly what
  // ResumeService.persistParse stores in the `structured` jsonb.
  const AISERVICE_SHAPED = {
    profile: {
      name: "Ada Lin",
      headline: "Backend Engineer",
      email: "ada@example.com",
      phone: "+86 138",
      location: "Shanghai",
      links: { github: "https://github.com/ada", homepage: "ada.dev" },
      summary: "Builds resilient services.",
      yearsExperience: 5,
    },
    education: [
      { school: "Fudan", degree: "BSc", field: "CS", startYear: 2014, endYear: 2018, gpa: "3.8", courses: ["OS"] },
    ],
    experience: [
      { company: "Acme", title: "SDE II", start: "2020-01", end: "2023-06", location: "SH",
        bullets: ["Cut p99 by 40%"], summary: "" },
    ],
    projects: [
      { name: "gateway", role: "author", period: "2022", bullets: ["Rust"], tech: ["Rust", "gRPC"], url: "https://x" },
    ],
    skills: [
      { name: "Java", category: "language", proficiency: null },
      { name: "Kotlin", category: "language", proficiency: null },
      { name: "Spring", category: "framework", proficiency: null },
      { name: "Mlops", category: "other", proficiency: null },
    ],
    achievements: ["Hackathon winner"],
    careerGoals: ["Staff engineer"],
    preferredRoles: ["Platform"],
    preferredLocations: ["Shanghai"],
    missingSections: [],
    warnings: [],
  };

  it("buckets flat {name,category} skills into grouped {group,skills[]} so badges render", () => {
    const out = normalizeStructuredResume(AISERVICE_SHAPED);
    expect(out?.skills).toEqual([
      { group: "language", skills: ["Java", "Kotlin"], level: undefined },
      { group: "framework", skills: ["Spring"], level: undefined },
      { group: "other", skills: ["Mlops"], level: undefined },
    ]);
    // the exact consumer contract: every group must carry a non-empty skills[]
    for (const g of out?.skills ?? []) expect((g.skills ?? []).length).toBeGreaterThan(0);
  });

  it("maps education startYear/endYear → start/end and field → major", () => {
    const ed = normalizeStructuredResume(AISERVICE_SHAPED)?.education?.[0];
    expect(ed).toMatchObject({ school: "Fudan", major: "CS", start: "2014", end: "2018" });
  });

  it("maps project tech → techStack and promotes profile.summary to the top level", () => {
    const out = normalizeStructuredResume(AISERVICE_SHAPED);
    expect(out?.projects?.[0]?.techStack).toEqual(["Rust", "gRPC"]);
    expect(out?.summary).toBe("Builds resilient services.");
  });

  it("aliases experience title → role and keeps start/end/bullets", () => {
    const exp = normalizeStructuredResume(AISERVICE_SHAPED)?.experience?.[0];
    expect(exp).toMatchObject({ role: "SDE II", company: "Acme", start: "2020-01", end: "2023-06" });
    expect(exp?.bullets).toEqual(["Cut p99 by 40%"]);
  });

  it("coerces an object-map of links into a string[] (renderer calls .slice on it)", () => {
    const links = normalizeStructuredResume(AISERVICE_SHAPED)?.profile?.links;
    expect(Array.isArray(links)).toBe(true);
    expect(links).toContain("https://github.com/ada");
  });

  it("is idempotent on an already-grouped payload", () => {
    const grouped = { skills: [{ group: "Languages", skills: ["Go"], level: "expert" }] };
    expect(normalizeStructuredResume(grouped)?.skills).toEqual([
      { group: "Languages", skills: ["Go"], level: "expert" },
    ]);
  });

  it("puts a category-less flat skill in an unnamed group instead of dropping it", () => {
    const out = normalizeStructuredResume({ skills: [{ name: "Solo" }] });
    expect(out?.skills).toEqual([{ group: undefined, skills: ["Solo"], level: undefined }]);
  });

  it("returns null for absent input and an all-empty object for {} (no crash)", () => {
    expect(normalizeStructuredResume(null)).toBeNull();
    expect(normalizeStructuredResume(undefined)).toBeNull();
    const empty = normalizeStructuredResume({});
    expect(empty).not.toBeNull();
    expect(empty && Object.values(empty).every((v) => v === undefined)).toBe(true);
  });
});

/**
 * `structured.technologies` is read by the resume view's "Core technologies" line and by the
 * analyze dialog's skill suggestions, and neither service ever produces that key: the parse answer
 * describes skills as `{name, category}`. So that section cannot render -- and the useful half of
 * knowing that is saying it somewhere a build checks. When a producer starts emitting the key,
 * this fails where someone will read it, and the section gets verified instead of trusted.
 */
describe("the technologies the resume view reads has no producer", () => {
  const root = new URL("../../../../", import.meta.url);
  const trees = ["backend/src/main/java", "ai-service/app"];
  const scanned = trees.flatMap((dir) =>
    readdirSync(new URL(dir, root), { recursive: true, encoding: "utf8" })
      .filter((name) => /\.(java|py)$/.test(name))
      .map((name) => readFileSync(new URL(`${dir}/${name}`, root), "utf8"))
  );

  it("walks the services, instead of finding nothing by accident", () => {
    expect(scanned.length).toBeGreaterThan(150);
    expect(scanned.join("\n")).toContain("document_chunks");
  });

  it("never mentions technologies, while the view does", () => {
    expect(scanned.filter((src) => /\btechnologies\b/.test(src))).toEqual([]);
    expect(readFileSync(new URL("./normalize.ts", import.meta.url), "utf8")).toContain(
      'list<string>(s, "technologies")'
    );
  });
});
