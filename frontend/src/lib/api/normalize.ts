/**
 * Normalizers — the backend is built in parallel and may serialize either
 * camelCase (JPA DTOs) or snake_case (ai-service passthrough), and may return
 * dimension maps or arrays. These helpers coerce the *real* payload into view
 * models. They never invent values: missing → undefined, and the UI hides it.
 */

import type {
  ActivityRun,
  AgentTrace,
  Application,
  CopilotArtifact,
  DashboardMetrics,
  DashboardPayload,
  Evidence,
  InterviewDimension,
  Job,
  JobMatch,
  MatchDimension,
  ResumeScore,
  SkillGap,
  TailorChange,
  TailorDiff,
  TailorResponse,
  TailoredResult,
} from "./types";

/* ------------------------------- primitives ------------------------------ */

export function rec(v: unknown): Record<string, unknown> | null {
  return v !== null && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : null;
}

/** First present key — tolerates snake_case / camelCase drift. */
export function pick<T = unknown>(obj: unknown, ...keys: string[]): T | undefined {
  const o = rec(obj);
  if (!o) return undefined;
  for (const k of keys) {
    const v = o[k];
    if (v !== undefined && v !== null) return v as T;
  }
  return undefined;
}

export function str(obj: unknown, ...keys: string[]): string | undefined {
  const v = pick(obj, ...keys);
  if (typeof v === "string") return v;
  if (typeof v === "number") return String(v);
  return undefined;
}

export function num(obj: unknown, ...keys: string[]): number | undefined {
  const v = pick(obj, ...keys);
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "" && !Number.isNaN(Number(v))) return Number(v);
  return undefined;
}

export function bool(obj: unknown, ...keys: string[]): boolean | undefined {
  const v = pick(obj, ...keys);
  if (typeof v === "boolean") return v;
  if (typeof v === "string") return v === "true";
  return undefined;
}

export function list<T = unknown>(obj: unknown, ...keys: string[]): T[] {
  for (const k of keys) {
    const v = pick(obj, k);
    if (Array.isArray(v)) return v as T[];
    if (rec(v)) return Object.values(v as Record<string, unknown>) as T[];
    if (typeof v === "string" && v.trim()) return [v as unknown as T];
  }
  return [];
}

/** 0–1 or 0–100 → 0–100 */
export function pct(v: number | undefined | null): number | undefined {
  if (v == null || !Number.isFinite(v)) return undefined;
  if (v <= 1) return Math.round(v * 100);
  return Math.round(v > 100 ? 100 : v);
}

/* --------------------------------- id ------------------------------------ */

export function idOf(raw: unknown, fallbackPrefix = "x"): string {
  return (
    str(raw, "id", "uuid", "key", "_id") ??
    str(raw, "eventId", "event_id") ??
    `${fallbackPrefix}-${Math.random().toString(36).slice(2, 9)}`
  );
}

/* ------------------------------- list page ------------------------------- */

export interface NormalizedPage<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

/** Accepts {items,total,page,size} | {content,totalElements} | bare array. */
export function normalizePage<T>(
  raw: unknown,
  map: (item: unknown, index: number) => T
): NormalizedPage<T> {
  if (Array.isArray(raw)) {
    return { items: raw.map(map), total: raw.length, page: 0, size: raw.length };
  }
  const arr = list(raw, "items", "content", "data", "results", "records", "list");
  return {
    items: arr.map(map),
    total: num(raw, "total", "totalElements", "totalCount", "count") ?? arr.length,
    page: num(raw, "page", "pageNumber", "number") ?? 0,
    size: num(raw, "size", "pageSize", "sizePerPage") ?? arr.length,
  };
}

/* -------------------------------- evidence ------------------------------- */

/** Breadcrumb path from a payload that may hold ["A","B"] or "A › B". */
function pathOf(obj: unknown, ...keys: string[]): string[] | undefined {
  const v = pick(obj, ...keys);
  if (Array.isArray(v) && v.length) return v.map(String);
  if (typeof v === "string" && v.trim()) return v.split(/\s*[>›/]\s*/).filter(Boolean);
  return undefined;
}

export function normalizeEvidence(raw: unknown): Evidence[] {
  return list(raw, "evidence", "items", "citations", "sources", "chunks").map((e) => {
    const src = pick(e, "source", "doc", "document", "metadata");
    return {
      criterion: str(e, "criterion", "name", "label", "requirement", "skill") ?? "Evidence",
      score: pct(num(e, "score", "value")),
      quote: str(e, "quote", "text", "excerpt", "snippet", "content") ?? "",
      reasoning: str(e, "reasoning", "why", "explanation", "rationale"),
      chunkIds: list<string>(e, "chunkIds", "chunk_ids", "chunks").map(String),
      source: {
        docTitle:
          str(src, "docTitle", "doc_title", "title", "name", "fileName", "file_name") ??
          str(e, "docTitle", "doc_title"),
        docId: str(src, "docId", "doc_id", "documentId", "document_id") ?? str(e, "documentId"),
        kind: str(src, "kind", "type", "sourceType", "source_type"),
        path: pathOf(src, "path", "section", "sections", "breadcrumbs") ?? pathOf(e, "path", "section"),
      },
      href: str(e, "href", "url"),
    };
  });
}

/** Breadcrumb path for an evidence entry (may arrive as "A > B" or ["A","B"]). */
export function evidencePath(e: Evidence): string[] | undefined {
  return e.source?.path?.length ? e.source.path : undefined;
}

/* --------------------------------- match --------------------------------- */

const DIMENSION_LABELS: Record<string, string> = {
  technical: "Technical",
  experience: "Experience",
  projects: "Projects",
  project: "Projects",
  education: "Education",
  skills: "Skills",
  domain: "Domain fit",
  location: "Location",
  seniority: "Seniority",
  overall: "Overall",
};

export function normalizeDimensions(raw: unknown): MatchDimension[] {
  const out: MatchDimension[] = [];
  const push = (key: string, value: unknown) => {
    const score =
      typeof value === "number" || typeof value === "string"
        ? pct(num({ v: value }, "v"))
        : pct(num(value, "score", "value", "points"));
    const evidence = Array.isArray(value) ? [] : normalizeEvidence(pick(value, "evidence"));
    const note = typeof value === "object" ? str(value, "note", "reason", "comment") : undefined;
    if (score == null && !note && !evidence.length) return;
    out.push({
      key,
      label: str(value, "label", "name") ?? DIMENSION_LABELS[key] ?? key.replace(/_/g, " "),
      score,
      note,
      evidence: evidence.length ? evidence : undefined,
    });
  };

  const dims = pick(raw, "dimensions", "dimension_scores", "dimensionScores", "breakdown", "scores");
  const dimsRecord = rec(dims);
  if (dimsRecord) for (const [k, v] of Object.entries(dimsRecord)) push(k, v);
  else if (Array.isArray(dims)) for (const d of dims) push(str(d, "key", "name", "dimension") ?? "dim", d);

  for (const key of ["technical", "experience", "projects", "education"] as const) {
    const v = num(raw, key, `${key}_score`, `${key}Score`);
    if (v != null && !out.some((d) => d.key === key)) push(key, { score: v });
  }
  return out;
}

export function normalizeMatch(raw: unknown): JobMatch | null {
  const m = pick(raw, "match", "latestMatch", "latest_match", "jobMatch", "job_match") ?? raw;
  if (!rec(m) && !Array.isArray(m)) return null;
  const overall = pct(num(m, "overall", "overallScore", "overall_score", "score", "matchScore", "match_score"));
  const matched = list<string>(m, "matchedSkills", "matched_skills", "matched", "strengths");
  const missing = list<string>(m, "missingSkills", "missing_skills", "missing", "gaps", "skillGap", "skill_gap");
  const evidence = normalizeEvidence(pick(m, "evidence", "citations"));
  const gaps = normalizeSkillGaps(pick(m, "skillGaps", "skill_gaps", "gaps"));
  if (overall == null && !matched.length && !missing.length && !evidence.length) return null;
  return {
    id: idOf(m, "match"),
    jobId: str(m, "jobId", "job_id"),
    resumeVersionId: str(m, "resumeVersionId", "resume_version_id"),
    overall: overall ?? 0,
    technical: pct(num(m, "technical", "technicalScore", "technical_score")),
    experience: pct(num(m, "experience", "experienceScore", "experience_score")),
    projects: pct(num(m, "projects", "projectScore", "project_score", "projectsScore")),
    education: pct(num(m, "education", "educationScore", "education_score")),
    dimensions: normalizeDimensions(m),
    matchedSkills: matched.map(String),
    missingSkills: missing.map(String),
    whyMatch: list<string>(m, "whyMatch", "why_match", "reasons", "why").map(String),
    reasoning: str(m, "reasoning", "summary", "explanation"),
    evidence: evidence.length ? evidence : undefined,
    interviewTopics: list<string>(m, "interviewTopics", "interview_topics").map(String),
    preparation: list(m, "preparation", "recommendedPreparation", "recommended_preparation"),
    skillGaps: gaps.length ? gaps : undefined,
    createdAt: str(m, "createdAt", "created_at", "computedAt", "computed_at"),
  };
}

export function normalizeSkillGaps(raw: unknown): SkillGap[] {
  const arr = list(raw, "skillGaps", "skill_gaps", "gaps");
  return arr
    .map((g) => {
      const skill = str(g, "skill", "name", "title");
      if (!skill) {
        if (typeof g === "string") return { skill: g };
        return null;
      }
      return {
        skill,
        importance: str(g, "importance", "severity", "level", "priority"),
        reason: str(g, "reason", "detail", "description", "why"),
        howToClose: str(g, "howToClose", "how_to_close", "action", "recommendation", "suggestion"),
      };
    })
    .filter((g): g is SkillGap => Boolean(g))
    .slice(0, 40);
}

/* --------------------------------- jobs ---------------------------------- */

export function normalizeJob(raw: unknown): Job {
  const company = pick(raw, "company");
  return {
    id: idOf(raw, "job"),
    companyId: str(raw, "companyId", "company_id") ?? str(company, "id") ?? "",
    company: {
      id: str(company, "id") ?? str(raw, "companyId", "company_id") ?? "",
      name: str(company, "name") ?? str(raw, "companyName", "company_name", "company") ?? "",
      logoUrl: str(company, "logoUrl", "logo_url", "logo"),
    },
    companyName: str(raw, "companyName", "company_name") ?? str(company, "name"),
    title: str(raw, "title", "position", "name") ?? "Untitled role",
    location: str(raw, "location", "city"),
    remoteType: str(raw, "remoteType", "remote_type", "workMode", "work_mode"),
    remote: bool(raw, "remote", "isRemote", "is_remote"),
    employmentType: str(raw, "employmentType", "employment_type", "type"),
    experienceLevel: str(raw, "experienceLevel", "experience_level", "seniority"),
    postedAt: str(raw, "postedAt", "posted_at", "publishedAt", "published_at"),
    salaryMin: num(raw, "salaryMin", "salary_min", "minSalary", "min_salary"),
    salaryMax: num(raw, "salaryMax", "salary_max", "maxSalary", "max_salary"),
    salaryCurrency: str(raw, "salaryCurrency", "salary_currency", "currency"),
    salaryText: str(raw, "salaryText", "salary_text", "salary"),
    skills: list<string>(raw, "skills", "requiredSkills", "required_skills", "tags").map(String),
    tags: list<string>(raw, "tags").map(String),
    status: str(raw, "status") ?? "open",
    source: str(raw, "source", "origin"),
    externalUrl: str(raw, "externalUrl", "external_url", "url", "applyUrl", "apply_url"),
    saved: bool(raw, "saved", "isSaved", "is_saved", "bookmarked"),
    latestMatch: normalizeMatch(pick(raw, "latestMatch", "latest_match", "match")),
    whyMatch: list<string>(raw, "whyMatch", "why_match", "why", "reasons").map(String),
    jd: rec(pick(raw, "jd", "jobDescription", "job_description"))
      ? (pick(raw, "jd", "jobDescription", "job_description") as Job["jd"])
      : undefined,
    description: str(raw, "description", "rawText", "raw_text", "content"),
  };
}

/** The `latest match` object on /jobs/{id} can sit under several keys. */
export function jobDetailMatch(raw: unknown): JobMatch | null {
  return normalizeMatch(
    pick(raw, "match", "latestMatch", "latest_match") ??
      pick(pick(raw, "detail", "job", "data"), "match", "latestMatch", "latest_match") ??
      raw
  );
}

/* -------------------------------- tailor --------------------------------- */

function changeFrom(raw: unknown, index: number): TailorChange {
  return {
    id: idOf(raw, `chg-${index}`),
    section: str(raw, "section", "area", "category"),
    before: str(raw, "before", "original", "from", "old", "previous"),
    after: str(raw, "after", "revised", "to", "new", "proposed"),
    reason: str(raw, "reason", "why", "explanation", "rationale"),
    evidence: normalizeEvidence(pick(raw, "evidence", "citations")),
  };
}

/** `diff` may be {accepted:[],rejected:[]} or one flat list with a status field. */
export function normalizeTailorDiff(raw: unknown): TailorDiff {
  const diff = pick(raw, "diff", "changes", "edits") ?? raw;
  const explicitAccepted = list(diff, "accepted", "applied", "kept");
  const explicitRejected = list(diff, "rejected", "skipped", "declined");
  if (explicitAccepted.length || explicitRejected.length) {
    return {
      accepted: explicitAccepted.map(changeFrom),
      rejected: explicitRejected.map(changeFrom),
    };
  }
  const flat = list(diff, "changes", "diff", "items", "edits");
  const accepted: TailorChange[] = [];
  const rejected: TailorChange[] = [];
  flat.forEach((c, i) => {
    const status = (str(c, "status", "state", "decision") ?? "accepted").toLowerCase();
    (status === "rejected" || status === "skipped" ? rejected : accepted).push(changeFrom(c, i));
  });
  return { accepted, rejected };
}

export function normalizeTailor(raw: unknown): TailorResponse {
  const tailoredRaw = pick(raw, "tailored", "tailoredResume", "tailored_resume", "result") ?? raw;
  const stats = pick(raw, "stats", "statistics", "summary");
  const tailored: TailoredResult = {
    resumeVersionId: str(tailoredRaw, "resumeVersionId", "resume_version_id", "versionId", "version_id"),
    markdown: str(tailoredRaw, "markdown", "md"),
    text: str(tailoredRaw, "text", "content", "plainText", "plain_text", "body"),
    sections: list(tailoredRaw, "sections"),
    notes: list<string>(tailoredRaw, "notes", "comments").map(String),
    stats: rec(stats) ? (stats as Record<string, unknown>) : undefined,
    evidence: normalizeEvidence(pick(tailoredRaw, "evidence")),
  };
  return {
    tailored: tailored.markdown || tailored.text || tailored.sections?.length ? tailored : undefined,
    diff: normalizeTailorDiff(raw),
    notes: list<string>(raw, "notes", "warnings").map(String),
    evidence: normalizeEvidence(raw),
    stats: rec(stats) ? (stats as Record<string, unknown>) : undefined,
    taskId: str(raw, "taskId", "task_id"),
    runId: str(raw, "runId", "run_id"),
  };
}

export function coverLetterText(raw: unknown): string {
  return (
    str(raw, "content", "text", "markdown", "body", "letter") ??
    str(pick(raw, "coverLetter", "cover_letter"), "content", "text", "markdown", "body") ??
    ""
  );
}

/* ------------------------------- dashboard -------------------------------- */

export function normalizePipeline(raw: unknown): { status: string; count: number }[] {
  const p = pick(raw, "pipeline", "stages", "applicationPipeline", "application_pipeline");
  if (Array.isArray(p)) {
    return p.map((row) => ({
      status: str(row, "status", "stage", "key", "name") ?? "saved",
      count: num(row, "count", "total", "value") ?? 0,
    }));
  }
  const record = rec(p);
  if (record) {
    return Object.entries(record).map(([status, v]) => ({
      status,
      count: typeof v === "number" ? v : (num(v, "count", "total") ?? 0),
    }));
  }
  return [];
}

export function normalizeResumeScore(raw: unknown): ResumeScore | null {
  const s = pick(raw, "score", "resumeScore", "resume_score") ?? raw;
  if (typeof s === "number") return { overall: pct(s) };
  const r = rec(s);
  if (!r) return null;
  const overall = pct(num(s, "overall", "score", "total"));
  const gaps = list<string>(s, "gaps", "issues", "weaknesses").map(String);
  const suggestions = list<string>(s, "suggestions", "improvements", "tips").map(String);
  const out: ResumeScore = {
    overall,
    bullets: pct(num(s, "bullets", "bulletScore", "bullet_score")),
    structure: pct(num(s, "structure", "structureScore", "structure_score")),
    impact: pct(num(s, "impact", "impactScore", "impact_score")),
    clarity: pct(num(s, "clarity", "clarityScore", "clarity_score")),
    keywords: pct(num(s, "keywords", "keywordScore", "keyword_score", "ats")),
    gaps: gaps.length ? gaps : undefined,
    suggestions: suggestions.length ? suggestions : undefined,
    computedAt: str(s, "computedAt", "computed_at", "createdAt", "created_at"),
  };
  return out.overall == null && !out.bullets && !out.structure && !out.impact && !out.clarity && !out.keywords && !gaps.length
    ? null
    : out;
}

export function normalizeDashboard(raw: unknown): DashboardPayload | null {
  const d = pick(raw, "dashboard", "data") ?? raw;
  if (!rec(d)) return null;
  const resumeRaw = pick(d, "resume", "currentResume", "current_resume");
  const metricsRaw = pick(d, "metrics", "stats", "summary") ?? d;
  const metrics: DashboardMetrics = {
    applications: num(metricsRaw, "applications", "applicationCount", "application_count", "total"),
    inPipeline: num(metricsRaw, "inPipeline", "in_pipeline", "active"),
    interviews: num(metricsRaw, "interviews", "interviewCount", "interview_count"),
    offers: num(metricsRaw, "offers", "offerCount", "offer_count"),
    skillGaps: num(metricsRaw, "skillGaps", "skill_gaps", "gapCount"),
    resumeScore: pct(num(metricsRaw, "resumeScore", "resume_score")),
    avgMatch: pct(num(metricsRaw, "avgMatch", "avg_match", "averageMatch", "average_match")),
    needsAttention: num(metricsRaw, "needsAttention", "needs_attention", "attention"),
  };
  const runs = list(d, "recentRuns", "recent_runs", "activity", "runs").map(normalizeRun);
  return {
    metrics: Object.values(metrics).some((v) => v != null) ? metrics : undefined,
    pipeline: pick(d, "pipeline", "stages", "applicationPipeline", "application_pipeline") as
      | DashboardPayload["pipeline"]
      | undefined,
    pipelineItems: list(d, "pipelineItems", "pipeline_items", "applications", "recentApplications").map(
      (a) => a as Application
    ),
    recommendedJobs: list(d, "recommendedJobs", "recommended_jobs", "recommendations", "jobs").map(
      normalizeJob
    ),
    skillGaps: normalizeSkillGaps(d),
    resume: rec(resumeRaw)
      ? {
          id: str(resumeRaw, "id") ?? "",
          title: str(resumeRaw, "title", "name") ?? "Resume",
          status: str(resumeRaw, "status") ?? "uploaded",
          currentVersionId: str(resumeRaw, "currentVersionId", "current_version_id") ?? null,
          score: normalizeResumeScore(resumeRaw) ?? undefined,
        }
      : null,
    score: normalizeResumeScore(d),
    recentRuns: runs.length ? runs : undefined,
    suggestion: str(d, "suggestion", "aiSuggestion", "ai_suggestion", "nextStep", "next_step"),
    insights: list<string>(d, "insights", "highlights").map(String),
    attention: list(d, "attention", "needsAttention", "needs_attention").map((a) => ({
      label: str(a, "label", "title", "text"),
      href: str(a, "href", "url", "link"),
      count: num(a, "count", "total"),
    })),
    empty: bool(d, "empty", "isEmpty", "is_empty"),
  };
}

/* -------------------------------- activity -------------------------------- */

export function normalizeTrace(raw: unknown, index: number): AgentTrace {
  return {
    id: idOf(raw, `trace-${index}`),
    kind: str(raw, "kind", "type", "event", "phase") ?? "step_start",
    label: str(raw, "label", "name", "title", "summary", "message") ?? str(raw, "kind") ?? "Step",
    durationMs: num(raw, "durationMs", "duration_ms", "elapsedMs", "elapsed_ms"),
    status: str(raw, "status", "state"),
    payload: rec(pick(raw, "payload", "data", "details", "input", "output"))
      ? (pick(raw, "payload", "data", "details") as Record<string, unknown>)
      : undefined,
    createdAt: str(raw, "createdAt", "created_at", "ts", "timestamp"),
    tokens: num(raw, "tokens", "tokenCount", "token_count"),
    costUsd: num(raw, "costUsd", "cost_usd", "cost"),
  };
}

export function normalizeRun(raw: unknown): ActivityRun {
  const traces = list(raw, "traces", "events", "steps").map(normalizeTrace);
  return {
    id: idOf(raw, "run"),
    agent: str(raw, "agent", "agentName", "agent_name", "orchestrator"),
    kind: str(raw, "kind", "type", "task", "operation"),
    summary: str(raw, "summary", "title", "label", "message", "name"),
    status: str(raw, "status", "state"),
    model: str(raw, "model", "modelName", "model_name"),
    startedAt: str(raw, "startedAt", "started_at", "createdAt", "created_at"),
    finishedAt: str(raw, "finishedAt", "finished_at", "endedAt", "ended_at"),
    createdAt: str(raw, "createdAt", "created_at"),
    durationMs: num(raw, "durationMs", "duration_ms", "elapsedMs"),
    tokensIn: num(raw, "tokensIn", "tokens_in", "promptTokens", "prompt_tokens"),
    tokensOut: num(raw, "tokensOut", "tokens_out", "completionTokens", "completion_tokens"),
    costUsd: num(raw, "costUsd", "cost_usd", "totalCost", "total_cost", "cost"),
    traces: traces.length ? traces : undefined,
    relatedHref: str(raw, "relatedHref", "related_href", "href", "url"),
  };
}

export function runTotalTokens(run: ActivityRun): number | undefined {
  const fromTraces = run.traces?.reduce((sum, t) => sum + (t.tokens ?? 0), 0);
  const direct = (run.tokensIn ?? 0) + (run.tokensOut ?? 0);
  const total = direct || fromTraces || 0;
  return total ? total : undefined;
}

/* ------------------------------- interviews ------------------------------- */

export function normalizeInterviewDims(raw: unknown): InterviewDimension[] {
  const dims = pick(raw, "dims", "dimensions", "scores", "evaluation");
  const out: InterviewDimension[] = [];
  const dimsRecord = rec(dims);
  if (dimsRecord) {
    for (const [k, v] of Object.entries(dimsRecord)) {
      const score = typeof v === "number" || typeof v === "string" ? pct(num({ v }, "v")) : pct(num(v, "score", "value"));
      if (score != null) out.push({ key: k, label: str(v, "label", "name") ?? DIMENSION_LABELS[k] ?? k.replace(/_/g, " "), score });
    }
  } else if (Array.isArray(dims)) {
    for (const d of dims) {
      const score = pct(num(d, "score", "value"));
      if (score != null)
        out.push({ key: str(d, "key", "name", "dimension") ?? `dim-${out.length}`, label: str(d, "label", "name", "title") ?? "Score", score });
    }
  }
  return out;
}

export function normalizeQuestion(raw: unknown): {
  text: string;
  topic?: string;
  kind?: string;
  difficulty?: number;
  id?: string;
} | null {
  const q = pick(raw, "question", "next", "prompt", "opening", "data") ?? raw;
  const text = str(q, "question", "text", "prompt", "content", "title") ?? str(raw, "question", "text", "prompt");
  if (!text) return null;
  return {
    text,
    topic: str(q, "topic", "category", "area"),
    kind: str(q, "kind", "type", "nextAction", "next_action"),
    difficulty: num(q, "difficulty", "depth", "level"),
    id: str(q, "id", "questionId", "question_id"),
  };
}

/* --------------------------------- copilot -------------------------------- */

export function normalizeArtifacts(raw: unknown): CopilotArtifact[] {
  return list(raw, "artifacts").map((a) => ({
    type: str(a, "type", "kind") ?? "text",
    title: str(a, "title", "name", "label"),
    data: pick(a, "data", "payload", "value") ?? a,
  }));
}

export function normalizeMessages(raw: unknown) {
  return list(raw, "messages", "items", "content").map((m, i) => ({
    id: idOf(m, `msg-${i}`),
    role: str(m, "role", "sender") ?? "assistant",
    content: str(m, "content", "text", "message", "body") ?? "",
    createdAt: str(m, "createdAt", "created_at", "timestamp"),
    artifacts: normalizeArtifacts(pick(m, "artifacts")),
    sources: normalizeEvidence(pick(m, "sources", "citations")),
    actions: list(m, "actions").map((a) => ({
      label: str(a, "label", "name", "title") ?? "Open",
      href: str(a, "href", "url", "link", "path"),
      kind: str(a, "kind", "type"),
      payload: rec(pick(a, "payload", "data")) ? (pick(a, "payload", "data") as Record<string, unknown>) : undefined,
    })),
  }));
}
