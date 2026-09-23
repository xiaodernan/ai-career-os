import { describe, expect, it } from "vitest";

import {
  bool,
  coverLetterText,
  idOf,
  list,
  normalizeArtifacts,
  normalizeChatActions,
  normalizeDashboard,
  normalizeDimensions,
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
  normalizeResumeScore,
  normalizeSearch,
  serializeJobFilters,
  normalizeSkillGaps,
  normalizeTailor,
  normalizeTailorDiff,
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
  it("coerces a bare number", () => {
    expect(normalizeResumeScore(0.8)).toEqual({ overall: 80 });
  });
  it("reads an object with subscores and gaps", () => {
    const s = normalizeResumeScore({ overall: 0.75, bullets: 0.6, gaps: ["no metrics"] });
    expect(s).toMatchObject({ overall: 75, bullets: 60, gaps: ["no metrics"] });
  });
  it("returns null for an empty object", () => {
    expect(normalizeResumeScore({})).toBeNull();
  });
  it("derives labeled gaps from unmet rubric detail (the real backend shape)", () => {
    const s = normalizeResumeScore({
      total: 40,
      detail: [
        { criterion: "has_contact", met: true, points: 15 },
        { criterion: "quantified_impact", met: false, points: 10 },
        { criterion: "has_skills", met: false, points: 10 },
      ],
    });
    expect(s).toMatchObject({
      overall: 40,
      gaps: ["Quantified impact (numbers or %)", "Enough skills (5+)"],
    });
  });
  it("prefers explicit gaps over derived ones", () => {
    const s = normalizeResumeScore({
      total: 40,
      gaps: ["explicit one"],
      detail: [{ criterion: "has_projects", met: false, points: 10 }],
    });
    expect(s?.gaps).toEqual(["explicit one"]);
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
  it("reads an array of stages", () => {
    expect(normalizePipeline({ pipeline: [{ status: "applied", count: 3 }] })).toEqual([
      { status: "applied", count: 3 },
    ]);
  });
  it("reads a status->count record", () => {
    const p = normalizePipeline({ pipeline: { saved: 2, offer: 1 } });
    expect(p).toContainEqual({ status: "saved", count: 2 });
    expect(p).toContainEqual({ status: "offer", count: 1 });
  });
});

describe("coverLetterText", () => {
  it("unwraps nested cover_letter payloads", () => {
    expect(coverLetterText({ content: "Dear" })).toBe("Dear");
    expect(coverLetterText({ cover_letter: { text: "Hi" } })).toBe("Hi");
    expect(coverLetterText({})).toBe("");
  });
});

describe("runTotalTokens", () => {
  it("prefers direct counts, else sums traces, else undefined", () => {
    expect(runTotalTokens({ tokensIn: 10, tokensOut: 5 } as never)).toBe(15);
    expect(runTotalTokens({ traces: [{ tokens: 3 }, { tokens: 4 }] } as never)).toBe(7);
    expect(runTotalTokens({} as never)).toBeUndefined();
  });
});

describe("normalizeDashboard", () => {
  it("coerces metrics from snake_case and computes resume score", () => {
    const d = normalizeDashboard({
      metrics: { application_count: 12, in_pipeline: 5, resume_score: 0.7 },
      resume: { id: "r1", title: "My resume", score: { overall: 0.7 } },
    });
    expect(d!.metrics).toMatchObject({ applications: 12, inPipeline: 5, resumeScore: 70 });
    expect(d!.resume?.title).toBe("My resume");
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

  it("still honours an explicit {groups:[…]} payload", () => {
    const { groups } = normalizeSearch({
      groups: [{ label: "People", items: [{ id: "p1", name: "Ada", href: "/people/p1" }] }],
    });
    expect(groups[0]).toMatchObject({ label: "People" });
    expect(groups[0].items[0]).toMatchObject({ id: "p1", title: "Ada", href: "/people/p1" });
  });

  it("groups a flat {items:[…]} list by type", () => {
    const { groups } = normalizeSearch({
      items: [
        { id: "a", type: "job", title: "A" },
        { id: "b", type: "note", title: "B" },
        { id: "c", type: "job", title: "C" },
      ],
    });
    expect(groups.find((g) => g.label === "Job")?.items).toHaveLength(2);
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
    expect(serializeJobFilters({ q: "react", remote: true, page: 2, skills: "go,k8s" })).toEqual({
      q: "react",
      remote: true,
      page: 2,
      skills: "go,k8s",
    });
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

describe("normalizeInterviewReport", () => {
  it("reads scalar results nested inside summary (real EvaluationItem shape)", () => {
    const report = normalizeInterviewReport({
      id: "e1",
      dims: { communication: 0.8, technical: { score: 75 } },
      summary: {
        overall: 0.72,
        what_you_did_well: ["clear structure", "solid tradeoffs"],
        what_was_weak: ["vague on scaling"],
        recommended_study: [{ title: "DDIA", url: "https://x", why: "partitioning", kind: "book" }],
        trajectory_note: "Held altitude until depth-4.",
      },
      trajectory: [{ question: "rate limiting", depth: 3, score: 0.6 }],
      createdAt: "2026-09-22T00:00:00Z",
    });
    expect(report?.overall).toBe(72);
    expect(report?.well).toEqual(["clear structure", "solid tradeoffs"]);
    expect(report?.weak).toEqual(["vague on scaling"]);
    expect(report?.summary).toBe("Held altitude until depth-4.");
    expect(report?.study).toEqual([{ title: "DDIA", url: "https://x", why: "partitioning", kind: "book" }]);
    expect(report?.trajectory).toEqual([{ question: "rate limiting", score: 60, depth: 3 }]);
    expect(report?.dims.map((d) => d.key)).toEqual(["communication", "technical"]);
    expect(report?.hasContent).toBe(true);
  });

  it("still reads a flat/legacy report with a string summary", () => {
    const report = normalizeInterviewReport({
      overall: 88,
      strengths: ["fast"],
      weaknesses: ["shaky tests"],
      study: [{ name: "docs" }],
      trajectory: [{ label: "q1", score: 80, level: 2 }],
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
          recommended_study: [{ title: "Designing Data-Intensive Applications", kind: "book" }],
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
