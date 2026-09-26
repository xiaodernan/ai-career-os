/**
 * Normalizers — the backend is built in parallel and may serialize either
 * camelCase (JPA DTOs) or snake_case (ai-service passthrough), and may return
 * dimension maps or arrays. These helpers coerce the *real* payload into view
 * models. They never invent values: missing → undefined, and the UI hides it.
 */

import type {
  ActivityRun,
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
import { seniorityLabel } from "../format";

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

/* Gap items are stored exactly as ai-service's SkillGap emits them: {skill, importance, reason},
 * where `importance` is the JD's own priority word and `reason` the phrase it used to ask. There is
 * deliberately no advice column — what to do about a gap is the preparation card's job. */
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
    employmentType: str(raw, "employmentType", "employment_type", "type"),
    // The only seniority the backend models is `jobs.experience_years` (Integer on both
    // JobListItem and JobDetail); nothing ever sent an `experienceLevel` string, so the
    // header's chip could never appear. Label it here rather than at the call site —
    // the list, search and saved-job rows all project through this one mapper.
    experienceLevel: seniorityLabel(num(raw, "experienceYears", "experience_years")),
    postedAt: str(raw, "postedAt", "posted_at", "publishedAt", "published_at"),
    salaryMin: num(raw, "salaryMin", "salary_min", "minSalary", "min_salary"),
    salaryMax: num(raw, "salaryMax", "salary_max", "maxSalary", "max_salary"),
    salaryCurrency: str(raw, "salaryCurrency", "salary_currency", "currency"),
    skills: list<string>(raw, "skills", "requiredSkills", "required_skills", "tags").map(String),
    status: str(raw, "status") ?? "open",
    source: str(raw, "source", "origin"),
    externalUrl: str(raw, "externalUrl", "external_url", "url", "applyUrl", "apply_url"),
    saved: bool(raw, "saved", "isSaved", "is_saved", "bookmarked"),
    latestMatch: resolvedMatch,
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
}

/** `POST /jds` and `GET /jobs/{id}` both answer a JdItem whose ai-service dict (skills /
 *  responsibilities / topics / hidden asks) is nested under `parsed`, NOT at the top level — read it
 *  there or the whole analysis dialog comes back empty. The names below are the only ones that dict
 *  can carry: they are the keys the analyze prompt draws, tied to this reader by the cross-language
 *  contract gate. A skill gap is a comparison against one resume, so no analysis emits one — the
 *  gap card reads the match, and the analyze dialog `POST /jds/suggestions`. */
export function normalizeJdParsed(raw: unknown): JdParsed {
  const body = rec(pick(raw, "parsed"));
  const arr = (key: string): string[] => {
    const v = pick(body, key);
    if (!Array.isArray(v)) return [];
    return v
      .map((x): string =>
        typeof x === "object" && x !== null ? str(x, "name") ?? "" : String(x)
      )
      .filter(Boolean);
  };
  return {
    requiredSkills: arr("requiredSkills"),
    preferredSkills: arr("preferredSkills"),
    responsibilities: arr("responsibilities"),
    interviewTopics: arr("interviewTopics"),
    hiddenRequirements: arr("hiddenRequirements"),
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
    // A change row carries no identifier on any path (the prompt draws section/index/before/after/
    // reason, and a kept version relays that same object), so the row is keyed by its position.
    id: `chg-${index}`,
    section: str(raw, "section"),
    before: str(raw, "before"),
    after: str(raw, "after"),
    reason: str(raw, "reason"),
  };
}

/** The two edit lists the verifier split. `raw` is either the tailor response (which wraps the
 *  lists under `diff`) or the diff map itself — a saved tailored version projects that object, so
 *  both shapes arrive here and both carry exactly `accepted` and `rejected`. */
export function normalizeTailorDiff(raw: unknown): TailorDiff {
  const diff = pick(raw, "diff") ?? raw;
  return {
    accepted: list(diff, "accepted").map(changeFrom),
    rejected: list(diff, "rejected").map(changeFrom),
  };
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
 * summary lives under `profile.summary`. Both readers here (`StructuredProfileView`,
 * and `profileSkillSuggestions` in `lib/job-filter`) expect the camel/grouped view
 * model instead — so without this bridge the entire skill inventory renders as
 * header-less empty badges and education dates silently vanish. Same alias policy as
 * structuredResumeToMarkdown.
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
  return pick(raw, "tailored") ?? raw;
}

/** The change list the service attached to the draft. */
export function tailorDiffDict(raw: unknown): unknown {
  return pick(raw, "diff") ?? {};
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
  const stats = pick(raw, "stats");
  // `tailored` is the structured resume dict `_apply_changes` wrote the accepted edits onto, so it
  // carries no markdown and the panel's document view is rendered from it here. #145 deleted the
  // reads that pretended otherwise (`markdown`/`text`/`content` inside the dict, a
  // `resumeVersionId` that lives nowhere on this response, `sections`/`notes`/`evidence` that
  // belong to the wrapper rather than the dict) together with their authorless aliases.
  const markdown = structuredResumeToMarkdown(tailoredRaw);
  const tailored: TailoredResult = { markdown };
  return {
    tailored: markdown ? tailored : undefined,
    diff: normalizeTailorDiff(raw),
    notes: list<string>(raw, "notes").map(String),
    evidence: normalizeEvidence(raw),
    stats: rec(stats) ? (stats as Record<string, unknown>) : undefined,
  };
}

/* ------------------------------ suggestions ------------------------------ */

const SUGGESTION_TYPE_LABELS: Record<string, string> = {
  missing_required: "Missing required skill",
  structure: "Structure",
  impact: "Impact",
};

/**
 * Map the ai-service rule-engine's suggestions into the view `Suggestion`.
 * `POST /jds/suggestions` answers `{"suggestions": [{"skill","type","advice"}], "jd": …}` — the
 * backend relays that map untouched, so these three names are all any producer writes. The dialog
 * renders `title` + `text`, which the raw shape never supplies, so both are derived here; an item
 * that names neither a skill nor a type is dropped rather than rendered as an empty bullet.
 */
export function normalizeSuggestions(raw: unknown): Suggestion[] {
  return list(raw, "suggestions")
    .map((item): Suggestion | null => {
      const skill = (str(item, "skill") ?? "").trim();
      const type = str(item, "type");
      const advice = str(item, "advice");
      const title =
        type === "missing_required" && skill
          ? `Add ${skill}`
          : skill || (type ? SUGGESTION_TYPE_LABELS[type] ?? type.replace(/_/g, " ") : undefined);
      if (!title && !advice) return null;
      return {
        title: title || undefined,
        text: advice ?? undefined,
        body: advice ?? undefined,
        section: type ?? undefined,
        priority: type === "missing_required" ? "high" : undefined,
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
  // Both callers hand over the same body: `useDashboardPipeline` GETs /reports/dashboard and
  // `normalizeDashboard` passes the payload it already has. That record carries no `pipeline` key
  // (the per-stage counts live at `kanban.statusCounts`), so the array-of-stages branch and the
  // `pipeline`/`stages`/`applicationPipeline` probe that fed it are #130's deletions: the shape was
  // only ever reachable from a test fixture.
  const kanban = pick(raw, "kanban");
  const fromKanban = pick(kanban, "statusCounts", "status_counts");
  return rec(fromKanban) ? statusCountsToRows(fromKanban) : [];
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
  // `raw` is a record that *carries* the rubric map, never the map itself: `ResumeDetail` and
  // `ResumeSummary` both have a `score` component, while the versions list hands over a
  // `ResumeVersionItem`, which projects no score at all, so its rows answer null. The reader also
  // used to take the map directly (`?? raw`) and a bare number; no caller sends either shape, and
  // a fallback no producer reaches is a payload the mapper silently reinterprets rather than a
  // tolerance anyone asked for.
  const s = pick(raw, "score");
  const r = rec(s);
  if (!r) return null;
  // `total` is already a percentage, so it is clamped here rather than by `pct`: that helper scales
  // any value <= 1 as a fraction, which would read a 1-point rubric as a perfect 100. The rubric's
  // own maximum is 110, and a score above 100 has always been reported as 100.
  const total = num(s, "total");
  const overall = total == null ? undefined : Math.min(100, Math.round(total));
  // The rubric's unmet criteria ARE the gaps: `detail: [{criterion, met, points}]` is the only gap
  // source there is, and RESUME_CRITERION_LABELS above is the human half of that same table.
  const gaps = list<Record<string, unknown>>(s, "detail")
    .filter((c) => bool(c, "met") === false)
    .map((c) => {
      const code = str(c, "criterion") ?? "";
      return RESUME_CRITERION_LABELS[code] ?? code.replace(/_/g, " ");
    })
    .filter(Boolean);
  const out: ResumeScore = {
    overall,
    // The rubric reports each of these on its own 0-100 scale (ai-service `_DIMENSION_OF`), so they
    // go through `num` rather than `pct`: `pct` scales anything <=1 as a fraction, which would turn
    // a dimension worth exactly 1 into a full 100 bar. A score stored before the dimensions existed
    // has none of these keys, and the panel's own filter hides the bars it cannot fill.
    bullets: num(s, "bullets") ?? undefined,
    structure: num(s, "structure") ?? undefined,
    impact: num(s, "impact") ?? undefined,
    clarity: num(s, "clarity") ?? undefined,
    keywords: num(s, "keywords") ?? undefined,
    gaps: gaps.length ? gaps : undefined,
  };
  return out.overall == null && !out.bullets && !out.structure && !out.impact && !out.clarity &&
    !out.keywords && !gaps.length
    ? null
    : out;
}

export function normalizeDashboard(raw: unknown): DashboardPayload | null {
  // `api.get` already unwraps the {success,data} envelope, so what arrives here is
  // `DashboardResponse` and nothing else: { kanban{statusCounts,total,offers}, interviews,
  // avgMatch(0..1 or null), needsAttention(long), currentResume{resumeId,versionId,title,
  // status,score}, skillGaps(digest), recommendedJobs[], recentRuns[], recentActivity[] }.
  // The `dashboard`/`data` pick, the `metrics`/`stats`/`summary` layer that hung off it, and the
  // flat-number aliases (`applicationCount`, `in_pipeline`, `offerCount`, …) each read names no
  // response of this route carries, so #129 deleted them: a fallback a producer cannot reach is
  // not a tolerance, it is a second shape the mapper would silently prefer.
  if (!rec(raw)) return null;
  const d = raw;
  const kanban = pick(d, "kanban");
  const currentResume = pick(d, "currentResume", "current_resume", "resume");
  const skillGapDigest = pick(d, "skillGaps", "skill_gaps", "skillGap", "skill_gap");

  const pipelineRows = normalizePipeline(d);
  const inPipeline = pipelineRows.reduce((s, r) => s + r.count, 0);
  // Missing skills arrive inside a single digest object, not as a SkillGap list.
  const gaps = normalizeSkillGaps({
    gaps: list(skillGapDigest, "missingSkills", "missing_skills", "missing"),
  });
  // The score map is the resume version's stored `score` jsonb, so it exists only while the
  // current resume has a scored version; `currentResume` is null on a workspace with none.
  const resumeScore = normalizeResumeScore(currentResume);

  const metrics: DashboardMetrics = {
    applications: num(kanban, "total"),
    inPipeline: inPipeline || undefined,
    interviews: num(d, "interviews", "interviewCount", "interview_count"),
    offers: num(kanban, "offers"),
    skillGaps: gaps.length || undefined,
    resumeScore: resumeScore?.overall,
    avgMatch: pct(num(d, "avgMatch", "avg_match", "averageMatch", "average_match")),
    needsAttention: num(d, "needsAttention", "needs_attention", "attention"),
  };
  const runs = list(d, "recentRuns", "recent_runs", "activity", "runs").map(normalizeRun);
  return {
    // `Kanban.total` is a primitive `long`, so `applications` is never missing on a served
    // payload and the old "hide the strip when every metric is null" guard had no reachable
    // false branch left once the fallbacks went.
    metrics,
    pipeline: pick(kanban, "statusCounts", "status_counts") as DashboardPayload["pipeline"],
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
    score: resumeScore,
    recentRuns: runs.length ? runs : undefined,
  };
}

/* -------------------------------- activity -------------------------------- */

export function normalizeRun(raw: unknown): ActivityRun {
  // A run arrives as one of two Java records, both camelCase: `RecentRun` in the dashboard payload
  // and `RunItem` from `GET /activity/runs`, which answers a bare list. So every snake_case twin this
  // reader tried (`agent_name`, `latency_ms`, `input_tokens`, `cost_usd`, …) is a name neither record
  // has ever had, and four fields had no author at all: `summary`, `createdAt` (a run row carries
  // `startedAt`/`finishedAt`, never a created column), `relatedHref` (nothing on either service emits
  // a href for a run) and `traces` -- the per-step list belongs to `GET /activity/runs/{id}`, and the
  // detail page reads it through `activity-trace`, which unwraps the `RunDetail` envelope first;
  // handing that envelope to *this* reader would have looked for `agent` on the wrapper. The two
  // pages that list runs compose their own label from `agent` and `kind`, which is what the
  // `summary ?? …` fallback always ended up rendering.
  return {
    id: idOf(raw, "run"),
    agent: str(raw, "agent"),
    kind: str(raw, "trigger"),
    status: str(raw, "status"),
    error: str(raw, "error"),
    model: str(raw, "model"),
    startedAt: str(raw, "startedAt"),
    finishedAt: str(raw, "finishedAt"),
    durationMs: num(raw, "latencyMs"),
    tokensIn: num(raw, "inputTokens"),
    tokensOut: num(raw, "outputTokens"),
    costUsd: num(raw, "costUsd"),
  };
}

export function runTotalTokens(run: ActivityRun): number | undefined {
  const total = (run.tokensIn ?? 0) + (run.tokensOut ?? 0);
  return total ? total : undefined;
}

/* ------------------------------- interviews ------------------------------- */

export function normalizeInterviewDims(raw: unknown): InterviewDimension[] {
  // The one shape that exists: `EvaluationItem.dims` is the jsonb copy of the report's
  // `"dims": {technical_accuracy: 0.0-1.0, …}` -- an object keyed by the AI service's `DIMENSIONS`
  // with a number per dimension. The reader used to also walk an *array* of `{key, label, score}`
  // and an object-valued `{score, label}` per dimension; neither has an author (a Java `Map` cannot
  // arrive as a JSON array, and the prompt asks for scalars), and a fallback no producer reaches is
  // a shape the mapper silently reinterprets rather than a tolerance anyone asked for.
  const dims = pick(raw, "dims");
  const out: InterviewDimension[] = [];
  const dimsRecord = rec(dims);
  if (!dimsRecord) return out;
  for (const [k, v] of Object.entries(dimsRecord)) {
    const score = typeof v === "number" || typeof v === "string" ? pct(Number(v)) : undefined;
    if (score != null) {
      out.push({ key: k, label: DIMENSION_LABELS[k] ?? k.replace(/_/g, " "), score });
    }
  }
  return out;
}

export function normalizeQuestion(raw: unknown): {
  text: string;
  topic?: string;
  kind?: string;
  id?: string;
} | null {
  // The current question is an interviewer `TurnItem`, whichever endpoint carried it: the
  // `OpeningResponse.question` the opening POST answers with, or the last interviewer row of
  // `SessionDetail.turns`. Its text is the turn's `content`. Everything else about the question
  // lives in the turn's free `questionMeta` map -- the topic, and the `action` the runner branches
  // on ("followup" / "next_topic"), which this mapper calls `kind`. That map has two authors
  // (`InterviewService.answer` for follow-ups, ai-service's `opening_meta` for turn one) and the
  // gate binds both; the snake twin is the shape the same column takes on the ai-service side.
  const meta = rec(pick(raw, "questionMeta", "question_meta")) ?? {};
  const text = str(raw, "content");
  if (!text) return null;
  return { text, topic: str(meta, "topic"), kind: str(meta, "action"), id: str(raw, "id") };
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
}

export interface InterviewTrajectoryPoint {
  question?: string;
  /** 0–100 */
  score?: number;
  /**
   * 1–5 ladder: how deep the agent had pushed when it asked this question.
   * The producer only flags *whether* a question was a follow-up, so a run of
   * follow-ups on one topic is what becomes ladder 2, 3, 4…
   */
  depth?: number;
}

const TRAJECTORY_KEYS = ["trajectory", "trajectory_detail", "depth_trajectory", "depthTrajectory"];

/**
 * Fold the evaluator's per-turn rows into one point per QUESTION.
 *
 * `interview_evaluations.trajectory` (written by ai-service `finalize` →
 * `_trajectory_detail`) stores one row per TURN, interleaved: the `interviewer` row
 * carries `topic` + `depth_level` (1 when the agent chose to follow up, 0 for a new
 * topic), the grade lands on the following `candidate` row. Projecting every row as a
 * question counted answers as questions and drew a phantom zero-depth point between
 * each pair. Rows that carry no `role` at all are already one-per-question and pass
 * through untouched.
 */
export function normalizeTrajectory(source: unknown): InterviewTrajectoryPoint[] {
  const rows = list<Record<string, unknown>>(source, ...TRAJECTORY_KEYS);
  const plain = (t: Record<string, unknown>): InterviewTrajectoryPoint => ({
    question: str(t, "question", "label", "topic"),
    score: pct(num(t, "score", "value")),
    depth: num(t, "depth", "level", "difficulty"),
  });
  if (!rows.some((r) => typeof r.role === "string")) return rows.map(plain);

  const points: InterviewTrajectoryPoint[] = [];
  let ladder = 0;
  rows.forEach((row, i) => {
    if (row.role !== "interviewer") return;
    const question = str(row, "question", "label", "topic");
    const depth = num(row, "depth", "level", "difficulty");
    // depth_level is a follow-up flag, not a level: the ladder is the run length.
    ladder = depth && depth >= 1 ? ladder + 1 : 1;
    // The answer that grades this question is the first candidate row before the
    // next question; a row already carrying its own score needs no look-ahead.
    let score = pct(num(row, "score", "value"));
    for (let j = i + 1; j < rows.length && score == null; j++) {
      if (rows[j].role === "interviewer") break;
      if (rows[j].role === "candidate") score = pct(num(rows[j], "score", "value"));
    }
    points.push({ question, score, depth: ladder });
  });
  return points;
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
  // Names only as far as the report's declared contract (ai-service `FINALIZE_FIELDS`) reaches: the
  // snake/camel twins and the speculative alternatives this reader used to try (`score`,
  // `overallScore`, `strengths`, `narrative`, `studyMaterials`, …) are names no producer has ever
  // sent for a report, and a dead candidate inside a live site is how a rename slips through.
  const overall = pct(num(merged, "overall"));
  const well = list<string>(merged, "what_you_did_well").map(String);
  const weak = list<string>(merged, "what_was_weak").map(String);
  const summaryText =
    str(merged, "trajectory_note") ??
    (typeof summary === "string" ? summary : undefined);
  // ai-service FINALIZE emits recommended_study as {topic, why, resource_hint}, and
  // the backend copies that dict verbatim into summary.recommended_study
  // (InterviewService.persistFinalization); the mock and some models use a bare
  // resource string. A non-URL `resource_hint` is a resource NAME, so it folds into the why
  // line rather than being dropped; there is no separate url/kind field in the contract, which is
  // why the card's "Open" link appears only when the hint really is a link.
  const study = list<unknown>(merged, "recommended_study").map((s): InterviewStudyItem => {
    if (typeof s === "string") return { title: s.trim() || undefined };
    const hint = str(s, "resource_hint");
    const hintIsLink = !!hint && /^https?:\/\//i.test(hint);
    const nameHint = hintIsLink ? undefined : hint;
    const reason = str(s, "why");
    return {
      title: str(s, "topic"),
      url: hintIsLink ? hint : undefined,
      why: reason && nameHint ? `${reason} · ${nameHint}` : reason ?? nameHint,
    };
  });
  const trajectory = normalizeTrajectory(merged);

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
 * The six lists GET /search answers with, in response order — each pinned to one
 * `SearchDtos.SearchResponse` component (a contract test keeps them in step). The
 * palette's "what can I search" copy reads this table too, so neither list can rot
 * on its own.
 */
export const SEARCH_GROUPS: {
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

/**
 * "jobs, companies, resumes, notes, conversations and applications" — the palette's
 * capability line, derived from the table that decodes the response so it can never
 * claim fewer groups than /search actually answers.
 */
export function searchGroupNames(): string {
  const names = SEARCH_GROUPS.map((g) => g.label.toLowerCase());
  const last = names.pop();
  return names.length ? `${names.join(", ")} and ${last}` : (last ?? "");
}

/**
 * Global search: `GET /search` answers with typed top-level lists
 * (`{query, jobs, companies, resumes, notes, conversations, applications}`), not a `groups`
 * array, so each entity becomes a navigable item on the deepest route that really exists.
 * `SEARCH_GROUPS` is the only table of those lists and the parity test ties its keys to the
 * Java record's `List<…>` components, so a group nobody renders is a red test rather than a
 * silently missing section.
 *
 * No item is dropped for the term not appearing in its title: four of the six
 * groups can match a column the list never shows (see `SearchRepository`), so a
 * title filter here would hide real hits.
 */
export function normalizeSearch(raw: unknown): SearchResults {
  const groups: SearchResults["groups"] = [];
  for (const g of SEARCH_GROUPS) {
    const arr = list(raw, g.key);
    if (!arr.length) continue;
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
  return { groups };
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
