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
  CopilotAction,
  CopilotArtifact,
  DashboardMetrics,
  DashboardPayload,
  Evidence,
  InterviewDimension,
  Job,
  JobMatch,
  MatchDimension,
  ResumeScore,
  SearchResults,
  SkillGap,
  ResumeExperience,
  ResumeProfileSummary,
  ResumeProject,
  ResumeEducation,
  ResumeSkillGroup,
  StructuredResume,
  Suggestion,
  TailorChange,
  TailorDiff,
  TailorResponse,
  TailoredResult,
} from "./types";
import { field } from "./body";

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
  // A payload may already BE the list (e.g. a bare `List<TimelineEvent>`),
  // not wrapped under a key — return it as-is rather than dropping it.
  if (Array.isArray(obj)) return obj as T[];
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
  const items = Array.isArray(raw) ? raw : list(raw, "evidence", "items", "citations", "sources", "chunks");
  return items.map((e) => {
    const src = pick(e, "source", "doc", "document", "metadata");
    return {
      criterion: str(e, "criterion", "name", "label", "requirement", "skill") ?? "Evidence",
      score: pct(num(e, "score", "value")),
      quote: str(e, "quote", "text", "excerpt", "snippet", "content") ?? "",
      reasoning: str(e, "reasoning", "why", "explanation", "rationale"),
      chunkIds: list<string>(e, "chunkIds", "chunk_ids", "chunk_id", "chunks").map(String),
      source: {
        docTitle:
          str(src, "docTitle", "doc_title", "title", "name", "fileName", "file_name") ??
          str(e, "docTitle", "doc_title"),
        // Copilot/ai-service sources carry document_id at the TOP level (snake),
        // not nested — read it or the /knowledge citation link is dead.
        docId:
          str(src, "docId", "doc_id", "documentId", "document_id") ??
          str(e, "documentId", "document_id", "docId", "doc_id"),
        kind:
          str(src, "kind", "type", "sourceType", "source_type") ??
          // ai-service `to_evidence` emits `source_kind` at the TOP level (flat
          // evidence, no nested source object) — mirror the docTitle/docId
          // fallbacks above or the citation's source type is silently dropped.
          str(e, "sourceKind", "source_kind", "kind"),
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
    reasoning: str(m, "reasoning", "narrative", "summary", "explanation"),
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
  // GET /jobs/saved returns SavedJobItem{ job: JobListItem, note, savedAt } —
  // the job is NESTED under `job`. Reading the wrapper's (absent) top-level
  // keys rendered every saved card as "Untitled role" with a dead random id.
  raw = rec(pick(raw, "job", "data")) ?? raw;
  const company = pick(raw, "company");
  // A job's match can arrive two ways: nested under `match`/`latestMatch` (the
  // detail response) or as FLAT scalars `matchOverall`/`matchId` on JobListItem
  // (GET /jobs list + discover). Reading only the nested form left every list
  // card without a score ring even when the backend had computed one.
  const nestedMatch = normalizeMatch(pick(raw, "latestMatch", "latest_match", "match"));
  const flatOverall = pct(num(raw, "matchOverall", "match_overall"));
  const resolvedMatch: JobMatch | null =
    nestedMatch ??
    (flatOverall != null
      ? {
          id: str(raw, "matchId", "match_id") ?? "",
          jobId: idOf(raw, "job"),
          overall: flatOverall,
        }
      : null);
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
    latestMatch: resolvedMatch,
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

export interface JdParsed {
  requiredSkills: string[];
  preferredSkills: string[];
  responsibilities: string[];
  interviewTopics: string[];
  hiddenRequirements: string[];
  skillGap: string[];
}

/** `POST /jds` returns a JdItem whose ai-service dict (skills / responsibilities
 *  / topics / hidden asks) is nested under `parsed`, NOT at the top level —
 *  read it there or the whole analysis dialog comes back empty. */
export function normalizeJdParsed(raw: unknown): JdParsed {
  const body = rec(pick(raw, "parsed", "jd", "analysis", "data")) ?? raw;
  const arr = (...keys: string[]): string[] => {
    for (const k of keys) {
      const v = pick(body, k);
      if (Array.isArray(v)) {
        return v
          .map((x): string =>
            typeof x === "object" && x !== null ? str(x, "skill", "name", "text") ?? "" : String(x)
          )
          .filter(Boolean);
      }
    }
    return [];
  };
  return {
    requiredSkills: arr("requiredSkills", "required_skills", "requirements"),
    preferredSkills: arr("preferredSkills", "preferred_skills", "nice_to_have", "niceToHave"),
    responsibilities: arr("responsibilities", "duties"),
    interviewTopics: arr("interviewTopics", "interview_topics", "topics"),
    hiddenRequirements: arr("hiddenRequirements", "hidden_requirements"),
    skillGap: arr("skillGap", "skill_gap", "skillGaps", "gaps"),
  };
}

/* ------------------------------ applications ------------------------------ */

/**
 * `ApplicationItem` names the company in flat columns (`companyId` + `companyName`) and never
 * sends a nested object, while a list row reads `app.company?.name` — the shape `normalizeJob`
 * already guarantees. So the flat name is projected into `company` here instead of teaching every
 * reader which column the backend happened to use; an application with no company keeps
 * `company` absent rather than getting an object with an empty name.
 */
export function normalizeApplication(raw: unknown): Application {
  const nested = pick<Record<string, unknown>>(raw, "company");
  const name = str(raw, "companyName", "company_name") ?? str(nested, "name") ?? null;
  const companyId = str(raw, "companyId", "company_id") ?? str(nested, "id") ?? null;
  return {
    id: str(raw, "id") ?? "",
    jobId: str(raw, "jobId", "job_id") ?? null,
    companyId,
    company: name
      ? {
          id: companyId ?? "",
          name,
          logoUrl: str(nested, "logoUrl", "logo_url", "logo") ?? null,
        }
      : undefined,
    companyName: name,
    title: str(raw, "title", "position", "role") ?? "Untitled",
    status: str(raw, "status") ?? "saved",
    matchScore: num(raw, "matchScore", "match_score") ?? null,
    note: str(raw, "note", "notes") ?? null,
    reminderAt: str(raw, "reminderAt", "reminder_at") ?? null,
    position: num(raw, "position", "orderIndex", "order_index", "sortOrder", "sort_order"),
    createdAt: str(raw, "createdAt", "created_at"),
    updatedAt: str(raw, "updatedAt", "updated_at"),
  };
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

/** Render a structured resume (the ai-service `tailored` payload — a resume
 *  dict, not markdown) into the markdown the tailor panel copies/downloads.
 *  Reads both camelCase and the snake_case the parser emits; never invents. */
export function structuredResumeToMarkdown(raw: unknown): string {
  const s = rec(pick(raw, "structured", "structuredResume", "structured_resume") ?? raw);
  if (!s) return "";
  const lines: string[] = [];
  const push = (...t: Array<string | undefined>) => {
    const l = t.filter(Boolean).join(" ").trim();
    if (l) lines.push(l);
  };
  const bulletList = (o: unknown) => list<string>(o, "bullets", "highlights").map(String);

  const profile = pick(s, "profile");
  const name = str(profile, "name") ?? str(s, "name");
  const headline = str(profile, "headline", "title") ?? str(s, "headline");
  if (name) push("#", name);
  else if (headline) push("#", headline);
  if (name && headline) push("###", headline);
  push(
    [str(profile, "email"), str(profile, "phone"), str(profile, "location")]
      .filter(Boolean)
      .join(" · ")
  );

  const summary = str(s, "summary") ?? str(profile, "summary");
  if (summary) {
    push("## Summary");
    push(summary);
  }

  const experience = list(s, "experience", "workExperience", "work_experience");
  if (experience.length) {
    push("## Experience");
    for (const e of experience) {
      const role = str(e, "role", "title") ?? "";
      const org = str(e, "company", "organization", "organisation") ?? "";
      let end = str(e, "end", "endDate", "end_date") ?? "";
      if (!end && bool(e, "current")) end = "Present";
      const start = str(e, "start", "startDate", "start_date") ?? "";
      const dates = [start, end].filter(Boolean).join(" – ");
      push("###", [role, org].filter(Boolean).join(" — "), dates ? `(${dates})` : "");
      for (const b of bulletList(e)) push("- " + b);
    }
  }

  const projects = list(s, "projects");
  if (projects.length) {
    push("## Projects");
    for (const p of projects) {
      const title = str(p, "name", "title") ?? "";
      push("###", title, str(p, "period") ? `(${str(p, "period")})` : "");
      const desc = str(p, "description");
      if (desc) push(desc);
      for (const b of bulletList(p)) push("- " + b);
      const tech = list<string>(p, "techStack", "tech_stack", "skills").map(String);
      if (tech.length) push("_" + tech.join(", ") + "_");
    }
  }

  const education = list(s, "education");
  if (education.length) {
    push("## Education");
    for (const ed of education) {
      const school = str(ed, "school", "institution") ?? "";
      const deg = [str(ed, "degree"), str(ed, "major") ?? str(ed, "field")].filter(Boolean).join(", ");
      push("###", school, deg ? `— ${deg}` : "");
    }
  }

  const skillLines: string[] = [];
  // Bucket through the shared helper so ai-service's flat {name,category} skills
  // render their names under a category instead of a bare, name-less label line.
  for (const g of groupSkillBuckets(s) ?? []) {
    const items = (g.skills ?? []).map(String);
    if (!items.length) continue;
    skillLines.push((g.group ? `${g.group}: ` : "") + items.join(", "));
  }
  const tech = list<string>(s, "technologies").map(String);
  if (tech.length) skillLines.push("Technologies: " + tech.join(", "));
  if (skillLines.length) {
    push("## Skills");
    for (const l of skillLines) push("- " + l);
  }

  const achievements = list<string>(s, "achievements").map(String);
  if (achievements.length) {
    push("## Achievements");
    for (const a of achievements) push("- " + a);
  }

  return lines.join("\n").trim();
}

/**
 * The `resume_versions.structured` jsonb is persisted verbatim from ai-service
 * `parse_resume` (ResumeService.persistParse → `version.setStructured(parsed)`),
 * whose schema is snake_case + flat: skills are `[{name,category,proficiency}]`,
 * education dates are `startYear`/`endYear`, project tech is `tech`, and the
 * summary lives under `profile.summary`. Both renderers here (`StructuredProfileView`
 * and `skillsFrom`) expect the camel/grouped view model instead — so without this
 * bridge the entire skill inventory renders as header-less empty badges and
 * education dates silently vanish. Same alias policy as structuredResumeToMarkdown.
 * Idempotent: an already-grouped payload (e.g. tailor output) passes through.
 */
export function normalizeStructuredResume(raw: unknown): StructuredResume | null {
  const s = rec(pick(raw, "structured", "structuredResume", "structured_resume") ?? raw);
  if (!s) return null;

  const profile = rec(pick(s, "profile"));
  const links = list<string>(profile ?? s, "links").map(String).filter(Boolean);
  const viewProfile: ResumeProfileSummary = {
    name: str(profile, "name"),
    headline: str(profile, "headline", "title"),
    email: str(profile, "email"),
    phone: str(profile, "phone"),
    location: str(profile, "location"),
    links: links.length ? links : undefined,
  };
  const hasProfile = Object.values(viewProfile).some((v) => v !== undefined);

  const experience: ResumeExperience[] = list(s, "experience", "workExperience", "work_experience")
    .map((e): ResumeExperience => ({
      company: str(e, "company", "organization", "organisation"),
      role: str(e, "role", "title"),
      location: str(e, "location"),
      start: str(e, "start", "startDate", "start_date"),
      end: str(e, "end", "endDate", "end_date"),
      current: bool(e, "current"),
      bullets: list<string>(e, "bullets", "highlights").map(String),
      techStack: list<string>(e, "techStack", "tech_stack", "tech").map(String),
    }));

  const projects: ResumeProject[] = list(s, "projects").map((p): ResumeProject => ({
    name: str(p, "name", "title"),
    role: str(p, "role"),
    period: str(p, "period"),
    description: str(p, "description", "summary"),
    bullets: list<string>(p, "bullets", "highlights").map(String),
    techStack: list<string>(p, "techStack", "tech_stack", "tech").map(String),
    url: str(p, "url", "link"),
  }));

  const education: ResumeEducation[] = list(s, "education").map((ed): ResumeEducation => ({
    school: str(ed, "school", "institution"),
    degree: str(ed, "degree"),
    major: str(ed, "major", "field"),
    start: str(ed, "start", "startDate", "start_date", "startYear", "start_year"),
    end: str(ed, "end", "endDate", "end_date", "endYear", "end_year"),
    gpa: str(ed, "gpa"),
    courses: list<string>(ed, "courses").map(String),
  }));

  const achievements = list<string>(s, "achievements").map(String).filter(Boolean);
  const technologies = list<string>(s, "technologies").map(String).filter(Boolean);
  const careerGoals = list<string>(s, "careerGoals", "career_goals").map(String).filter(Boolean);
  const preferredRoles = list<string>(s, "preferredRoles", "preferred_roles").map(String).filter(Boolean);
  const preferredLocations = list<string>(s, "preferredLocations", "preferred_locations")
    .map(String)
    .filter(Boolean);

  const group = (v: string[] | undefined) => (v && v.length ? v : undefined);
  return {
    profile: hasProfile ? viewProfile : undefined,
    summary: str(s, "summary") ?? str(profile, "summary"),
    experience: experience.length ? experience : undefined,
    projects: projects.length ? projects : undefined,
    education: education.length ? education : undefined,
    skills: groupSkillBuckets(s),
    achievements: group(achievements),
    technologies: group(technologies),
    careerGoals: group(careerGoals),
    preferredRoles: group(preferredRoles),
    preferredLocations: group(preferredLocations),
  };
}

/**
 * Bucket ai-service's flat `[{name,category}]` skills into the grouped view model
 * the renderer expects (`{group, skills:string[]}`). Pre-grouped entries (a nested
 * `skills`/`items` array) are carried through unchanged, so this is idempotent.
 */
function groupSkillBuckets(s: Record<string, unknown>): ResumeSkillGroup[] | undefined {
  const out: ResumeSkillGroup[] = [];
  const buckets = new Map<string, ResumeSkillGroup>();
  for (const g of list(s, "skills")) {
    const nested = list<string>(g, "skills", "items").map(String).filter(Boolean);
    if (nested.length) {
      out.push({ group: str(g, "group", "category", "name"), skills: nested, level: str(g, "level") });
      continue;
    }
    const name = str(g, "name", "skill");
    if (!name) continue;
    const cat = str(g, "category", "group") ?? "";
    let bucket = buckets.get(cat);
    if (!bucket) {
      bucket = { group: cat || undefined, skills: [] };
      buckets.set(cat, bucket);
      out.push(bucket);
    }
    if (!bucket.skills!.includes(name)) bucket.skills!.push(name);
  }
  return out.length ? out : undefined;
}

/**
 * The structured draft exactly as the tailor response carries it. normalizeTailor renders
 * from this and saving a kept draft has to post the very same object back — reading the two
 * independently is how a stored version stops matching the diff the user reviewed.
 */
export function tailoredDict(raw: unknown): unknown {
  return pick(raw, "tailored", "tailoredResume", "tailored_resume", "result") ?? raw;
}

/** The change list the service attached to the draft, in whatever shape it arrived. */
export function tailorDiffDict(raw: unknown): unknown {
  return pick(raw, "diff", "changes", "edits") ?? {};
}

/**
 * Body for POST /jobs/{id}/tailored-version. Each field goes out under exactly ONE name: the
 * backend's request records accept either spelling through @JsonAlias, but a body carrying both
 * makes Jackson bind the same constructor property twice, which it can only resolve through a
 * setter a record does not have — so the request is refused before the handler runs. The
 * structured dict — not the rendered markdown — is what the version's rows are projected from.
 */
export function tailorSaveBody(draft: {
  raw: unknown;
  plaintext: string;
  resumeVersionId?: string | null;
}): Record<string, unknown> {
  return {
    tailored: tailoredDict(draft.raw),
    diff: tailorDiffDict(draft.raw),
    plaintext: draft.plaintext,
    ...field("resumeVersionId", draft.resumeVersionId),
  };
}

export function normalizeTailor(raw: unknown): TailorResponse {
  const tailoredRaw = tailoredDict(raw);
  const stats = pick(raw, "stats", "statistics", "summary");
  // ai-service returns `tailored` as a structured resume dict (no markdown/text);
  // render one or the panel's Full-document / copy / download stay dead.
  const markdown = str(tailoredRaw, "markdown", "md");
  const text = str(tailoredRaw, "text", "content", "plainText", "plain_text", "body");
  const derived = markdown || text ? "" : structuredResumeToMarkdown(tailoredRaw);
  const tailored: TailoredResult = {
    resumeVersionId: str(tailoredRaw, "resumeVersionId", "resume_version_id", "versionId", "version_id"),
    markdown: markdown || derived || undefined,
    text: text || undefined,
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

/* ------------------------------ suggestions ------------------------------ */

const SUGGESTION_TYPE_LABELS: Record<string, string> = {
  missing_required: "Missing required skill",
  structure: "Structure",
  impact: "Impact",
};

/**
 * Map the ai-service rule-engine's `{skill, type, advice}` suggestions (as
 * returned by `POST /jds/suggestions`, either a bare array or wrapped under a
 * `suggestions` key) into the view `Suggestion`. The dialog renders `title` +
 * `text`, which the raw ai-service shape never supplies — without this the
 * "Resume improvement suggestions" section would render blank `<li>`s. Objects
 * already shaped as a `Suggestion` pass through unchanged.
 */
export function normalizeSuggestions(raw: unknown): Suggestion[] {
  const items = Array.isArray(raw) ? raw : list(raw, "suggestions", "items", "improvements");
  return items
    .map((item): Suggestion | null => {
      const bare = typeof item === "string" ? item : undefined;
      const skill = (str(item, "skill", "name") ?? "").trim();
      const type = str(item, "type", "kind");
      const advice = str(item, "advice", "reason", "why");
      const title =
        str(item, "title") ??
        (type === "missing_required" && skill
          ? `Add ${skill}`
          : skill || (type ? SUGGESTION_TYPE_LABELS[type] ?? type.replace(/_/g, " ") : undefined));
      const text = str(item, "text", "body") ?? advice ?? bare;
      if (!title && !text) return null;
      return {
        id: str(item, "id") ?? undefined,
        title: title || undefined,
        text,
        body: str(item, "body") ?? advice ?? undefined,
        section: type ?? undefined,
        priority: type === "missing_required" ? "high" : str(item, "priority") ?? undefined,
      };
    })
    .filter((s): s is Suggestion => s !== null);
}

/** The JD-required skills the resume lacks — the `missing_required` subset. */
export function missingSkillGaps(suggestions: Suggestion[]): string[] {
  return suggestions
    .filter((s) => s.section === "missing_required")
    .map((s) => (s.title ?? "").replace(/^Add\s+/, "").trim())
    .filter(Boolean);
}

export function coverLetterText(raw: unknown): string {
  return (
    str(raw, "content", "text", "markdown", "body", "letter") ??
    str(pick(raw, "coverLetter", "cover_letter"), "content", "text", "markdown", "body") ??
    ""
  );
}

/* ------------------------------- dashboard -------------------------------- */

/** {status: count} map → rows, keeping count coercion in one place. */
function statusCountsToRows(statusCounts: unknown): { status: string; count: number }[] {
  const record = rec(statusCounts);
  if (!record) return [];
  return Object.entries(record).map(([status, v]) => ({
    status,
    count: typeof v === "number" ? v : (num(v, "count", "total") ?? 0),
  }));
}

export function normalizePipeline(raw: unknown): { status: string; count: number }[] {
  const p = pick(raw, "pipeline", "stages", "applicationPipeline", "application_pipeline");
  if (Array.isArray(p)) {
    return p.map((row) => ({
      status: str(row, "status", "stage", "key", "name") ?? "saved",
      count: num(row, "count", "total", "value") ?? 0,
    }));
  }
  if (rec(p)) return statusCountsToRows(p);
  // Real GET /reports/dashboard carries no `pipeline` key: the per-stage counts
  // live at kanban.statusCounts. Reach into it or the mini-kanban is always empty.
  const kanban = pick(raw, "kanban");
  const fromKanban = pick(kanban, "statusCounts", "status_counts");
  if (rec(fromKanban)) return statusCountsToRows(fromKanban);
  return [];
}

/** Human labels for the deterministic rubric criteria (ai-service resume_parse). */
const RESUME_CRITERION_LABELS: Record<string, string> = {
  has_contact: "Contact info (email / phone)",
  has_summary: "A summary section",
  has_experience: "Work experience",
  experience_has_bullets: "Bullets under your roles",
  quantified_impact: "Quantified impact (numbers or %)",
  has_projects: "Projects",
  has_education: "Education",
  has_skills: "Enough skills (5+)",
  years_experience_stated: "Stated years of experience",
  dates_present: "Start dates on all roles",
};

export function normalizeResumeScore(raw: unknown): ResumeScore | null {
  const s = pick(raw, "score", "resumeScore", "resume_score") ?? raw;
  if (typeof s === "number") return { overall: pct(s) };
  const r = rec(s);
  if (!r) return null;
  const overall = pct(num(s, "overall", "score", "total"));
  const explicitGaps = list<string>(s, "gaps", "issues", "weaknesses").map(String);
  // The backend's rubric is a checklist of {criterion, met, points}; the unmet
  // items ARE the gaps. Derive them when the payload carries no explicit gaps.
  const derivedGaps = list<Record<string, unknown>>(s, "detail", "checks", "criteria")
    .filter((c) => bool(c, "met", "ok", "passed") === false)
    .map((c) => {
      const code = str(c, "criterion", "name", "why") ?? "";
      return RESUME_CRITERION_LABELS[code] ?? code.replace(/_/g, " ");
    })
    .filter(Boolean);
  const gaps = explicitGaps.length ? explicitGaps : derivedGaps;
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
  // Real GET /reports/dashboard: { kanban{statusCounts,total,offers}, interviews,
  // currentResume{resumeId,versionId,title,status,score}, skillGaps(digest),
  // recommendedJobs[], recentRuns[], recentActivity[] }. Fall back to `d` itself
  // so older flat payloads still resolve.
  const kanban = rec(pick(d, "kanban")) ? (pick(d, "kanban") as Record<string, unknown>) : d;
  const currentResume = pick(d, "currentResume", "current_resume", "resume");
  const skillGapDigest = pick(d, "skillGaps", "skill_gaps", "skillGap", "skill_gap");
  // Older payloads wrapped the flat numbers under `metrics` / `stats`.
  const legacy = pick(d, "metrics", "stats", "summary");

  const pipelineRows = normalizePipeline(d);
  const inPipeline = pipelineRows.reduce((s, r) => s + r.count, 0);
  // Missing skills arrive inside a single digest object, not as a SkillGap list.
  const gaps = normalizeSkillGaps({
    gaps: list(skillGapDigest, "missingSkills", "missing_skills", "missing"),
  });
  const resumeScore = normalizeResumeScore(currentResume) ?? normalizeResumeScore(d);

  const metrics: DashboardMetrics = {
    applications:
      num(kanban, "total") ??
      num(d, "applications", "applicationCount", "application_count") ??
      num(legacy, "applications", "applicationCount", "application_count", "total"),
    inPipeline: inPipeline || num(d, "inPipeline", "in_pipeline", "active") || num(legacy, "inPipeline", "in_pipeline", "active"),
    interviews: num(d, "interviews", "interviewCount", "interview_count") ?? num(legacy, "interviews", "interviewCount", "interview_count"),
    offers:
      num(kanban, "offers") ??
      num(d, "offers", "offerCount", "offer_count") ??
      num(legacy, "offers", "offerCount", "offer_count"),
    skillGaps: gaps.length || num(d, "skillGaps", "skill_gaps", "gapCount") || num(legacy, "skillGaps", "skill_gaps", "gapCount"),
    resumeScore: resumeScore?.overall ?? pct(num(d, "resumeScore", "resume_score")) ?? pct(num(legacy, "resumeScore", "resume_score")),
    avgMatch: pct(num(d, "avgMatch", "avg_match", "averageMatch", "average_match")) ?? pct(num(legacy, "avgMatch", "avg_match", "averageMatch", "average_match")),
    needsAttention: num(d, "needsAttention", "needs_attention", "attention") ?? num(legacy, "needsAttention", "needs_attention", "attention"),
  };
  const runs = list(d, "recentRuns", "recent_runs", "activity", "runs").map(normalizeRun);
  return {
    metrics: Object.values(metrics).some((v) => v != null) ? metrics : undefined,
    pipeline:
      (pick(d, "pipeline", "stages", "applicationPipeline", "application_pipeline") ??
        pick(kanban, "statusCounts", "status_counts")) as
        | DashboardPayload["pipeline"]
        | undefined,
    pipelineItems: list(d, "pipelineItems", "pipeline_items", "applications", "recentApplications").map(
      (a) => a as Application
    ),
    recommendedJobs: list(d, "recommendedJobs", "recommended_jobs", "recommendations", "jobs").map(
      normalizeJob
    ),
    skillGaps: gaps,
    resume: rec(currentResume)
      ? {
          id: str(currentResume, "resumeId", "resume_id", "id") ?? "",
          title: str(currentResume, "title", "name") ?? "Resume",
          status: str(currentResume, "status") ?? "uploaded",
          currentVersionId:
            str(currentResume, "versionId", "version_id", "currentVersionId", "current_version_id") ?? null,
          score: resumeScore ?? undefined,
        }
      : null,
    score: resumeScore ?? normalizeResumeScore(d),
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
    kind: str(raw, "kind", "type", "task", "operation", "trigger"),
    summary: str(raw, "summary", "title", "label", "message", "name"),
    status: str(raw, "status", "state"),
    error: str(raw, "error", "errorMessage", "error_message"),
    model: str(raw, "model", "modelName", "model_name"),
    startedAt: str(raw, "startedAt", "started_at", "createdAt", "created_at"),
    finishedAt: str(raw, "finishedAt", "finished_at", "endedAt", "ended_at"),
    createdAt: str(raw, "createdAt", "created_at"),
    durationMs: num(raw, "durationMs", "duration_ms", "elapsedMs", "latencyMs", "latency_ms"),
    tokensIn: num(raw, "tokensIn", "tokens_in", "promptTokens", "prompt_tokens", "inputTokens", "input_tokens"),
    tokensOut: num(raw, "tokensOut", "tokens_out", "completionTokens", "completion_tokens", "outputTokens", "output_tokens"),
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

/* --------------------------- interview report ---------------------------- */

/**
 * The backend stores an evaluation as `EvaluationItem{ dims, summary, trajectory }`,
 * and the evaluator's scalar/text results (`overall`, `what_you_did_well`,
 * `what_was_weak`, `recommended_study`, `trajectory_note`) live NESTED inside the
 * `summary` map — not on the item root. The report page used to read them from the
 * root (and never got a report object at all), so a finished session rendered empty.
 * This flattens the real shape into view models, still tolerating a legacy payload
 * that kept everything at the top level.
 */
export interface InterviewStudyItem {
  title?: string;
  url?: string;
  why?: string;
  kind?: string;
}

export interface InterviewTrajectoryPoint {
  question?: string;
  score?: number;
  depth?: number;
}

export interface InterviewReport {
  overall?: number;
  dims: InterviewDimension[];
  well: string[];
  weak: string[];
  summary?: string;
  study: InterviewStudyItem[];
  trajectory: InterviewTrajectoryPoint[];
  hasContent: boolean;
}

export function normalizeInterviewReport(raw: unknown): InterviewReport | null {
  const ev = pick(raw, "evaluation", "report") ?? raw;
  if (!rec(ev)) return null;
  const summary = pick(ev, "summary");
  const merged = { ...(rec(ev) ?? {}), ...(rec(summary) ?? {}) };

  const dims = normalizeInterviewDims(ev);
  const overall = pct(num(merged, "overall", "score", "overallScore", "overall_score"));
  const well = list<string>(merged, "what_you_did_well", "what_went_well", "whatWentWell", "strengths", "well").map(String);
  const weak = list<string>(merged, "what_was_weak", "whatWasWeak", "weaknesses", "weak").map(String);
  const summaryText =
    str(merged, "trajectory_note", "narrative", "comment", "assessment") ??
    (typeof summary === "string" ? summary : undefined);
  // ai-service FINALIZE emits recommended_study as {topic, why, resource_hint}, and
  // the backend copies that dict verbatim into summary.recommended_study
  // (InterviewService.persistFinalization); the mock and some models use a bare
  // resource string. Reading only title/name+url made every card fall through to
  // "Untitled resource" and silently dropped the hint.
  const study = list<unknown>(
    merged,
    "recommended_study",
    "study",
    "studyMaterials",
    "study_materials",
    "materials"
  ).map((s): InterviewStudyItem => {
    if (typeof s === "string") return { title: s.trim() || undefined };
    const url = str(s, "url", "link", "href", "resourceUrl", "resource_url");
    const hint = str(s, "resource_hint", "resourceHint");
    const hintIsLink = !!hint && /^https?:\/\//i.test(hint);
    const nameHint = hintIsLink ? undefined : hint;
    const reason = str(s, "why", "reason", "description");
    return {
      title: str(s, "title", "name", "topic", "resource"),
      url: url ?? (hintIsLink ? hint : undefined),
      // A non-URL resource_hint is a resource NAME: fold it into the why line so the
      // recommendation still surfaces instead of being dropped.
      why: reason && nameHint ? `${reason} · ${nameHint}` : reason ?? nameHint,
      kind: str(s, "kind", "type"),
    };
  });
  const trajectory = list<Record<string, unknown>>(
    merged,
    "trajectory",
    "trajectory_detail",
    "depth_trajectory",
    "depthTrajectory"
  ).map((t) => ({
    question: str(t, "question", "label", "topic"),
    score: pct(num(t, "score", "value")),
    depth: num(t, "depth", "level", "difficulty"),
  }));

  const hasContent =
    overall != null ||
    dims.length > 0 ||
    well.length > 0 ||
    weak.length > 0 ||
    study.length > 0 ||
    trajectory.length > 0 ||
    !!summaryText;

  return { overall, dims, well, weak, summary: summaryText, study, trajectory, hasContent };
}

/* --------------------------------- search --------------------------------- */

/**
 * Turn Jobs filter/URL state (snake_case) into the query string the backend
 * actually binds: salary is `@RequestParam(minSalary/maxSalary)` in camelCase.
 * Drops empty/undefined values. Any other key passes through unchanged.
 */
export function serializeJobFilters(params: object): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v === "" || v === undefined || v === false) continue;
    if (k === "min_salary") out.minSalary = v;
    else if (k === "max_salary") out.maxSalary = v;
    // The "Remote only" checkbox holds a boolean, but the backend filters on the
    // remote_type DOMAIN (onsite|hybrid|remote): `j.remote_type = :remote`. Sending
    // `true` matched nothing, so translate the boolean to its remote_type value and
    // let a real value (e.g. "hybrid") pass through untouched.
    else if (k === "remote") out.remote = v === true ? "remote" : v;
    else out[k] = v;
  }
  return out;
}

/**
 * Global search: the backend /search returns results as typed top-level lists
 * (`{query, jobs, companies, resumes, notes, conversations, applications}`), not
 * a `groups` array. Map each entity to a navigable item, choosing the deepest
 * real route that exists. Also tolerates `{groups:[…]}` and flat `{items:[…]}`.
 */
export function normalizeSearch(raw: unknown): SearchResults {
  const typed: {
    key: string;
    type: string;
    label: string;
    href: (id: string) => string;
  }[] = [
    { key: "jobs", type: "job", label: "Jobs", href: (id) => `/jobs/${id}` },
    { key: "companies", type: "company", label: "Companies", href: () => "/companies" },
    { key: "resumes", type: "resume", label: "Resumes", href: (id) => `/resumes/${id}` },
    { key: "notes", type: "note", label: "Notes", href: () => "/knowledge" },
    { key: "conversations", type: "conversation", label: "Conversations", href: () => "/copilot" },
    { key: "applications", type: "application", label: "Applications", href: () => "/applications" },
  ];

  const groups: SearchResults["groups"] = [];
  let sawTyped = false;
  for (const g of typed) {
    const arr = list(raw, g.key);
    if (!arr.length) continue;
    sawTyped = true;
    groups.push({
      label: g.label,
      items: arr.map((h) => {
        const id = idOf(h, g.type);
        return {
          id,
          type: g.type,
          title: str(h, "title", "name") ?? "Untitled",
          subtitle:
            str(h, "companyName", "company_name", "industry", "snippet", "location", "status") ??
            undefined,
          href: g.href(id),
        };
      }),
    });
  }
  if (sawTyped) return { groups };

  const groupsRaw = list(raw, "groups");
  if (groupsRaw.length) {
    return {
      groups: groupsRaw.map((g) => ({
        label: str(g, "label", "type", "name") ?? "Results",
        items: list(g, "items").map((i) => ({
          id: idOf(i, "result"),
          type: str(i, "type", "kind") ?? "result",
          title: str(i, "title", "name") ?? "",
          subtitle: str(i, "subtitle", "description", "snippet"),
          href: str(i, "href", "url", "link") ?? "#",
        })),
      })),
    };
  }

  const flat = list(raw, "items", "results");
  const byType = new Map<string, unknown[]>();
  for (const i of flat) {
    const t = str(i, "type", "kind") ?? "results";
    byType.set(t, [...(byType.get(t) ?? []), i]);
  }
  return {
    groups: [...byType.entries()].map(([label, items]) => ({
      label: label.charAt(0).toUpperCase() + label.slice(1),
      items: items.map((i) => ({
        id: idOf(i, "result"),
        type: label,
        title: str(i, "title", "name") ?? "",
        subtitle: str(i, "subtitle", "description"),
        href: str(i, "href", "url", "link") ?? "#",
      })),
    })),
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

/** Follow-up action chips. Shared by the history read path AND the live chat
 *  reply so a freshly-generated reply can't drop actions until a refetch. */
export function normalizeChatActions(raw: unknown): CopilotAction[] {
  return list(raw, "actions").map((a) => ({
    label: str(a, "label", "name", "title") ?? "Open",
    href: str(a, "href", "url", "link", "path"),
    kind: str(a, "kind", "type"),
    payload: rec(pick(a, "payload", "data")) ? (pick(a, "payload", "data") as Record<string, unknown>) : undefined,
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
    actions: normalizeChatActions(pick(m, "actions")),
  }));
}
