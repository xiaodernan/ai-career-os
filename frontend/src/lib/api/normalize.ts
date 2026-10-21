/**
 * Normalizers — the backend is built in parallel and may serialize either
 * camelCase (JPA DTOs) or snake_case (ai-service passthrough), and may return
 * dimension maps or arrays. These helpers coerce the *real* payload into view
 * models. They never invent values: missing → undefined, and the UI hides it.
 */

import type {
  ActivityRun,
  Application,
  ApplicationEvent,
  AttentionItem,
  CopilotAction,
  CopilotArtifact,
  DashboardMetrics,
  DashboardPayload,
  Evidence,
  FollowUpItem,
  InterviewDimension,
  Job,
  JobMatch,
  MatchDimension,
  MemoryItem,
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

/** The one list envelope this backend answers — `PageDTO`'s `{items,total,page,size}` — plus the bare
 *  array `GET /jobs/saved` returns instead (#225 moved `/activity/runs` onto the envelope). The other
 *  sixteen names were Spring-`Page` folklore
 *  (`content`/`totalElements`/`number`/`sizePerPage`…) and generic wrapper guesses (`data`/`results`/
 *  `records`/`list`/`doc`/`document`/`metadata`): no controller in the repo returns a raw `Page`, so
 *  a payload carrying them was silently read as an empty page rather than a tolerated shape. */
export function normalizePage<T>(
  raw: unknown,
  map: (item: unknown, index: number) => T
): NormalizedPage<T> {
  if (Array.isArray(raw)) {
    return { items: raw.map(map), total: raw.length, page: 0, size: raw.length };
  }
  const arr = list(raw, "items");
  return {
    items: arr.map(map),
    total: num(raw, "total") ?? arr.length,
    page: num(raw, "page") ?? 0,
    size: num(raw, "size") ?? arr.length,
  };
}

/* ------------------------------ long-term memory ---------------------------- */

/**
 * One memory row. The wire is the ai-service's camelCase, so the reader asks for both
 * spellings rather than mapping a record — and a row missing `importance` still renders,
 * because "no weight" and "weight zero" are different claims.
 */
export function normalizeMemory(raw: unknown): MemoryItem {
  return {
    id: str(raw, "id") ?? "",
    kind: str(raw, "kind") ?? "",
    key: str(raw, "key") ?? "",
    content: str(raw, "content") ?? "",
    importance: num(raw, "importance") ?? 0,
    source: str(raw, "source"),
    createdAt: str(raw, "createdAt", "created_at"),
    updatedAt: str(raw, "updatedAt", "updated_at"),
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

/**
 * The citation list under an AI conclusion. One mapper, three row authors and two envelopes, which is
 * why both bound receivers are unions:
 *
 *   - `compute_match`'s `evidence` rows are `EvidenceItem`s — `criterion`, `score`, `chunk_ids`,
 *     `quote`, `source`, `section`, `reasoning` — where **`source` is a string** holding the document
 *     title ("Resume", "Job Description", the chunk's own title);
 *   - `to_evidence`'s retrieved rows — `ref`, `chunk_id`, `document_id`, `doc_title`, `source_kind`,
 *     `section`, `quote`, `score` — which is what the tailor response's `evidence` and the cover
 *     letter response's `sources` both carry;
 *   - the copilot's `out.sources` rows — `type`, `chunk_id`, `document_id`, `label`, `quote`.
 *
 * #151 measured this reader at 16 sites / 49 names with the contract gate's own scanner and deleted
 * 35 of the names, the biggest group being a **nested source object**: `pick(e, "source", "doc",
 * "document", "metadata")` and the eighteen names tried on whatever it returned. No author on either
 * service writes an object under any of those four keys — the only `source` any producer emits is the
 * string above — so every read through `src` answered undefined and the match's own document title
 * was discarded on the way to a card that renders `source.docTitle`. The title is now read where it
 * is written. `href`/`url` went with them: no row carries either, so `Evidence.href` was empty on
 * every path and the card's link came from the caller's `hrefFor` all along.
 *
 * A retrieved row has no `criterion` and a copilot row has no `score`, which is what the two defaults
 * below are for. Neither invents a number.
 */
export function normalizeEvidence(raw: unknown): Evidence[] {
  const items = Array.isArray(raw) ? raw : list(raw, "evidence", "sources");
  return items.map((e) => ({
    criterion: str(e, "criterion", "label") ?? "Evidence",
    score: pct(num(e, "score")),
    quote: str(e, "quote") ?? "",
    reasoning: str(e, "reasoning"),
    chunkIds: list<string>(e, "chunk_ids", "chunk_id").map(String),
    source: {
      docTitle: str(e, "doc_title", "source"),
      docId: str(e, "document_id"),
      kind: str(e, "source_kind"),
      path: pathOf(e, "section"),
    },
  }));
}

/** Breadcrumb path for an evidence entry (may arrive as "A > B" or ["A","B"]). */
export function evidencePath(e: Evidence): string[] | undefined {
  return e.source?.path?.length ? e.source.path : undefined;
}

/* --------------------------------- match --------------------------------- */

// A bar label is looked up by a dimension name, and there are only two vocabularies of those in the
// product: the four scores a match is made of (below, and `normalizeDimensions`), and the interview
// report's (`normalizeInterviewDims`, keyed by ai-service's `DIMENSIONS`). `project` and the
// `skills`/`domain`/`location`/`seniority`/`overall` rows are #150's deletions -- the match reader
// used to accept a caller-supplied dimension map, so those six names were reachable only by a
// payload no endpoint ever sends. The gate checks this table's keys against both vocabularies.
const DIMENSION_LABELS: Record<string, string> = {
  technical: "Technical",
  experience: "Experience",
  projects: "Projects",
  education: "Education",
};

/**
 * The match panel's bars. `MatchResult` and `MatchSummary` carry the four scores as flat columns,
 * and `compute_match`'s own `_overall(technical, experience, projects, education)` is what fixes
 * that vocabulary, so one name per dimension is the whole wire shape and this reads four literal
 * names rather than walking a map.
 *
 * #150 deleted the map. The reader used to probe `dimensions` / `dimension_scores` /
 * `dimensionScores` / `breakdown` / `scores` and walk whatever it got, either as a record of
 * per-dimension values or as an array of rows, reading `score` / `value` / `points`, `label` /
 * `name`, `note` / `reason` / `comment` and `evidence` off each entry. Six sites, and no author on
 * either service writes any of those names for a match: `POST /jobs/{id}/match` answers with
 * `MatchResult.model_dump()` relayed through a `Map`, `GET /jobs/{id}` replays the `MatchSummary`
 * row, and neither has a dimension map to hand over. It is the same fold #141 made on the
 * interview side -- a fallback no producer reaches is not tolerance but a shape the mapper silently
 * reinterprets -- and the `${key}_score` / `${key}Score` alias twins went with it, for the same
 * reason the nine beside `normalizeMatch`'s own four fields did.
 *
 * A dimension whose score is absent is skipped rather than shown as 0, which is what the panel's
 * `?.length` branch and its own fallback list are written against.
 */
export function normalizeDimensions(raw: unknown): MatchDimension[] {
  const bars: Array<[string, number | undefined]> = [
    ["technical", pct(num(raw, "technical"))],
    ["experience", pct(num(raw, "experience"))],
    ["projects", pct(num(raw, "projects"))],
    ["education", pct(num(raw, "education"))],
  ];
  const out: MatchDimension[] = [];
  for (const [key, score] of bars) {
    if (score != null) out.push({ key, label: DIMENSION_LABELS[key], score });
  }
  return out;
}

/**
 * The match under a job. Two envelopes hand it over (`MatchResponse` and `JobDetail`, both under the
 * one key `match`) and two authors fill the map itself — `MatchResult` for a fresh compute,
 * `MatchSummary` for the stored row — which is why every site below asks for one name: the #155
 * measurement found 26 candidates that neither author, nor either envelope, writes on any path
 * (`latestMatch`/`jobMatch` and their snake twins, `overallScore`/`score`/`matchScore`,
 * `matched`/`strengths`, `missing`/`gaps`/`skillGap`, `why`/`reasons`, `summary`/`explanation`,
 * `computedAt`, `recommendedPreparation`). A tolerant alias beside a live name is invisible to the
 * per-site liveness rule, so each site is now pinned to its one spelling in the gate's census too.
 *
 * `idOf` keeps its shared table, and the two sites whose every name is unauthored — `jobId`,
 * `resumeVersionId` — stay as they are, declared dead with their reasons at
 * `DEAD_SITES` in `ai-service/tests/test_response_field_contract.py`: the columns exist on
 * `job_matches`, the projection omits them, and every caller already knows which job it asked about.
 */
export function normalizeMatch(raw: unknown): JobMatch | null {
  const m = pick(raw, "match") ?? raw;
  if (!rec(m) && !Array.isArray(m)) return null;
  const overall = pct(num(m, "overall"));
  const matched = list<string>(m, "matchedSkills");
  const missing = list<string>(m, "missingSkills");
  // One spelling. `citations` is what the RAG answer route calls this list, and the app never calls
  // that route (the copilot answers through `ChatResponse`, whose sources field is `sources`), so
  // tolerating it here bought nothing; the field-contract gate now refuses the name outright.
  const evidence = normalizeEvidence(pick(m, "evidence"));
  const gaps = normalizeSkillGaps(pick(m, "skillGaps"));
  if (overall == null && !matched.length && !missing.length && !evidence.length) return null;
  return {
    id: idOf(m, "match"),
    jobId: str(m, "jobId", "job_id"),
    resumeVersionId: str(m, "resumeVersionId", "resume_version_id"),
    overall: overall ?? 0,
    // One name each. `technicalScore`/`technical_score` and their seven twins were read here until
    // #150 measured that no author on either service writes them: `MatchResult`'s fields and
    // `MatchSummary`'s components are all bare camel-free columns, and the relay that carries the
    // fresh one is a `Map` copy of `model_dump()`. A dimension reaches this mapper under one key.
    technical: pct(num(m, "technical")),
    experience: pct(num(m, "experience")),
    projects: pct(num(m, "projects")),
    education: pct(num(m, "education")),
    dimensions: normalizeDimensions(m),
    matchedSkills: matched.map(String),
    missingSkills: missing.map(String),
    whyMatch: list<string>(m, "whyMatch").map(String),
    // `narrative` is what the matcher answers with; `reasoning` is this view's own field name, which
    // is the distinction that made four aliases look plausible here.
    reasoning: str(m, "narrative"),
    evidence: evidence.length ? evidence : undefined,
    // Only the fresh compute carries these two: the stored row's projection leaves them out, which is
    // why the interview card treats a missing topic list as "re-run the match" rather than as empty.
    interviewTopics: list<string>(m, "interviewTopics").map(String),
    preparation: list(m, "preparation"),
    skillGaps: gaps.length ? gaps : undefined,
    createdAt: str(m, "createdAt"),
  };
}

/* Gap items are stored exactly as ai-service's SkillGap emits them: {skill, importance, reason},
 * where `importance` is the JD's own priority word and `reason` the phrase it used to ask. There is
 * deliberately no advice column — what to do about a gap is the preparation card's job. */
export function normalizeSkillGaps(raw: unknown): SkillGap[] {
  // Two names, two authors: `skillGaps` is what MatchResult and MatchSummary write, and `gaps` is the
  // literal normalizeDashboard hands this call. `skill_gaps` was a third name only a test ever wrote,
  // so #167 deleted it.
  const arr = list(raw, "skillGaps", "gaps");
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
    resumeVersionId: str(raw, "resumeVersionId", "resume_version_id") ?? null,
    jdId: str(raw, "jdId", "jd_id") ?? null,
    matchId: str(raw, "matchId", "match_id") ?? null,
    offerCompensation: str(raw, "offerCompensation", "offer_compensation") ?? null,
    rejectionReason: str(raw, "rejectionReason", "rejection_reason") ?? null,
    appliedAt: str(raw, "appliedAt", "applied_at") ?? null,
    createdAt: str(raw, "createdAt", "created_at"),
    updatedAt: str(raw, "updatedAt", "updated_at"),
  };
}

/**
 * One row of `GET /applications/{id}/timeline`.
 *
 * `TimelineEvent` is `{id, kind, payload, createdAt}` — the detail sits one level down, under
 * `payload`, and its keys differ per kind (`{from,to}` for a status change, `{note}`, and
 * `{reminder_at}` or `{cleared}` for a reminder). A reader that looks only at the top level
 * finds no status and no note at all, which renders the whole history as blank badges, so the
 * detail is read where `ApplicationService.writeEvent` puts it -- and only there. Every name
 * below is one a writer fills: an alias beside a name no writer fills is a field the history
 * renders blank forever, which is a defect, not tolerance.
 */
export function normalizeApplicationEvent(raw: unknown, index = 0): ApplicationEvent {
  const payload = rec(pick(raw, "payload")) ?? {};
  return {
    id: str(raw, "id") ?? `ev-${index}`,
    type: str(raw, "kind"),
    status: str(payload, "to"),
    note: str(payload, "note"),
    reminderAt: str(payload, "reminder_at"),
    cleared: bool(payload, "cleared"),
    field: str(payload, "field"),
    createdAt: str(raw, "createdAt"),
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
 *  `tailored` is the parse answer with its bullets, `profile.summary` and skill
 *  order edited, so the camelCase skeleton that prompt draws is the whole
 *  vocabulary here; #147 deleted the snake_case twins no author ever wrote. */
export function structuredResumeToMarkdown(raw: unknown): string {
  const s = rec(raw);
  if (!s) return "";
  const lines: string[] = [];
  // A heading or bullet with nothing after it is not content. #147 removed the invented aliases
  // that used to fill these slots, which is what exposed the case: a row whose names are all empty
  // (the prompt allows `title: ""`, `company: ""`) put a bare "###" into the document the candidate
  // copies or downloads as their resume.
  const push = (...t: Array<string | undefined>) => {
    const l = t.filter(Boolean).join(" ").trim();
    if (l && !/^[#-]+$/.test(l)) lines.push(l);
  };
  const bulletList = (o: unknown) => list<string>(o, "bullets").map(String);

  const profile = pick(s, "profile");
  const name = str(profile, "name");
  const headline = str(profile, "headline");
  if (name) push("#", name);
  else if (headline) push("#", headline);
  if (name && headline) push("###", headline);
  push(
    [str(profile, "email"), str(profile, "phone"), str(profile, "location")]
      .filter(Boolean)
      .join(" · ")
  );

  const summary = str(profile, "summary");
  if (summary) {
    push("## Summary");
    push(summary);
  }

  const experience = list(s, "experience");
  if (experience.length) {
    push("## Experience");
    for (const e of experience) {
      const title = str(e, "title") ?? "";
      const org = str(e, "company") ?? "";
      const start = str(e, "start") ?? "";
      const end = str(e, "end") ?? "";
      const dates = [start, end].filter(Boolean).join(" – ");
      push("###", [title, org].filter(Boolean).join(" — "), dates ? `(${dates})` : "");
      for (const b of bulletList(e)) push("- " + b);
    }
  }

  const projects = list(s, "projects");
  if (projects.length) {
    push("## Projects");
    for (const p of projects) {
      const title = str(p, "name") ?? "";
      push("###", title, str(p, "period") ? `(${str(p, "period")})` : "");
      for (const b of bulletList(p)) push("- " + b);
      const tech = list<string>(p, "tech").map(String);
      if (tech.length) push("_" + tech.join(", ") + "_");
    }
  }

  const education = list(s, "education");
  if (education.length) {
    push("## Education");
    for (const ed of education) {
      const school = str(ed, "school") ?? "";
      const deg = [str(ed, "degree"), str(ed, "field")].filter(Boolean).join(", ");
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
 * header-less empty badges and education dates silently vanish.
 * Not idempotent, and cannot be: #147 deleted the branch that carried an already-grouped `skills`
 * row through, because `_merge_skills` is the only author of a skill row and it always writes the
 * flat `{name,category,proficiency}` shape. Feeding this function's own output back into it — which
 * is what a stored tailored draft used to be — now yields no skills at all, so callers pass the
 * jsonb and never the view model.
 */
export function normalizeStructuredResume(raw: unknown): StructuredResume | null {
  // Both callers hand over the jsonb itself -- `normalizeStructuredResume(r.structured)` on the
  // resume page and `profileSkillSuggestions(resume.data?.structured)` in the filter panel -- so the
  // `structured`/`structuredResume`/`structured_resume` probe unwrapped a nesting no producer writes:
  // `ResumeVersionItem.structured` is the DTO's own field name, and nothing ever passed the DTO in.
  const s = rec(raw);
  if (!s) return null;

  const profile = rec(pick(s, "profile"));
  // `links` is a key of the profile map only -- the parse prompt draws `"profile": {… "links":{}}`
  // and `ResumeProfile.links` types it, while the top-level skeleton has no such key -- so the
  // `?? s` this read used to carry could only ever answer `[]`, and an expression receiver kept the
  // one live read out of the per-site census (#162).
  const links = list<string>(profile, "links").map(String).filter(Boolean);
  const viewProfile: ResumeProfileSummary = {
    name: str(profile, "name"),
    headline: str(profile, "headline"),
    email: str(profile, "email"),
    phone: str(profile, "phone"),
    location: str(profile, "location"),
    links: links.length ? links : undefined,
  };
  const hasProfile = Object.values(viewProfile).some((v) => v !== undefined);

  const experience: ResumeExperience[] = list(s, "experience")
    .map((e): ResumeExperience => ({
      company: str(e, "company"),
      role: str(e, "title"),
      location: str(e, "location"),
      start: str(e, "start"),
      end: str(e, "end"),
      bullets: list<string>(e, "bullets").map(String),
    }));

  const projects: ResumeProject[] = list(s, "projects").map((p): ResumeProject => ({
    name: str(p, "name"),
    role: str(p, "role"),
    period: str(p, "period"),
    bullets: list<string>(p, "bullets").map(String),
    techStack: list<string>(p, "tech").map(String),
    url: str(p, "url"),
  }));

  const education: ResumeEducation[] = list(s, "education").map((ed): ResumeEducation => ({
    school: str(ed, "school"),
    degree: str(ed, "degree"),
    major: str(ed, "field"),
    start: str(ed, "startYear"),
    end: str(ed, "endYear"),
    gpa: str(ed, "gpa"),
    courses: list<string>(ed, "courses").map(String),
  }));

  const achievements = list<string>(s, "achievements").map(String).filter(Boolean);
  const careerGoals = list<string>(s, "careerGoals").map(String).filter(Boolean);
  const preferredRoles = list<string>(s, "preferredRoles").map(String).filter(Boolean);
  const preferredLocations = list<string>(s, "preferredLocations").map(String).filter(Boolean);

  const group = (v: string[] | undefined) => (v && v.length ? v : undefined);
  return {
    profile: hasProfile ? viewProfile : undefined,
    summary: str(profile, "summary"),
    experience: experience.length ? experience : undefined,
    projects: projects.length ? projects : undefined,
    education: education.length ? education : undefined,
    skills: groupSkillBuckets(s),
    achievements: group(achievements),
    careerGoals: group(careerGoals),
    preferredRoles: group(preferredRoles),
    preferredLocations: group(preferredLocations),
  };
}

/**
 * Bucket ai-service's flat `[{name,category,proficiency}]` skills into the grouped
 * view model the renderer expects (`{group, skills:string[]}`). `_merge_skills` is
 * the only author of a skill row and always states those three keys, so #147 deleted
 * the pre-grouped branch — it probed for `skills`/`items`/`group`/`level` no
 * producer writes, which made the whole nested case (and the renderer's `level`)
 * unreachable rather than idempotent.
 */
function groupSkillBuckets(s: Record<string, unknown>): ResumeSkillGroup[] | undefined {
  const out: ResumeSkillGroup[] = [];
  const buckets = new Map<string, ResumeSkillGroup>();
  for (const g of list(s, "skills")) {
    const name = str(g, "name");
    if (!name) continue;
    const cat = str(g, "category") ?? "";
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

/* The cover letter the `/jobs/{id}/cover-letter` relay hands back, and the same dict the copilot's
 * `cover_letter` artifact carries as its payload: `generate` answers {letter, sources, mode, model}.
 * `content`/`text`/`markdown`/`body` had no author, and the nested `coverLetter`/`cover_letter` drill
 * answered to a wrapper nothing produces -- both were ways for a reply that never arrived to look like
 * an empty letter rather than a missing one. */
export function coverLetterText(raw: unknown): string {
  return str(raw, "letter") ?? "";
}

/* ------------------------------- dashboard -------------------------------- */

/** {status: count} map → rows, keeping count coercion in one place. `DashboardDtos.Kanban` declares
 *  `Map<String, Long>`, so a value is a number or nothing: the `num(v, "count", "total")` fallback
 *  tried two names on a value that has never been a record, which #160's census caught only after the
 *  ban started counting module-private mappers as well as exported ones. */
function statusCountsToRows(statusCounts: unknown): { status: string; count: number }[] {
  const record = rec(statusCounts);
  if (!record) return [];
  return Object.entries(record).map(([status, v]) => ({
    status,
    count: typeof v === "number" ? v : 0,
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

/**
 * The rubric's unmet criteria, as the criteria's own codes.
 *
 * The codes are the ai-service's (`resume_parse`'s rubric) and the names the
 * product gives them live in `lib/dimensions.ts`, which reads them through the
 * locale -- so a gap is named in the reader's language rather than in the
 * English this mapper used to bake in. The mapper carries the code because a
 * mapper's job is to say *which* rubric criterion was unmet, and the word for
 * it is the page's business.
 */
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
  // source there is, and the criterion's own code is what travels -- the name the product gives
  // it is read from the locale by the page that shows it (`lib/dimensions.ts`).
  const gaps = list<Record<string, unknown>>(s, "detail")
    .filter((c) => bool(c, "met") === false)
    .map((c) => str(c, "criterion") ?? "")
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

/**
 * One row of the dashboard's attention list (`reports/dashboard` → `attention`).
 *
 * The backend picks both the rows and the reason (`reminder_due` / `stale`), so nothing here
 * re-tests the reminder or stale window: a second implementation of "is this row due" is how the
 * strip's count and the card's list end up arguing on screen. The names are the record's own
 * components and nothing else -- `AttentionItem` is the one producer, and an alias beside each
 * live name would be a second shape this mapper silently reinterprets. A row without an id is
 * dropped rather than rendered, because every row on the card links to its application.
 */
function normalizeAttention(raw: unknown): AttentionItem | null {
  const id = str(raw, "id");
  if (!id) return null;
  return {
    id,
    title: str(raw, "title"),
    companyName: str(raw, "companyName"),
    status: str(raw, "status"),
    reason: str(raw, "reason"),
    reminderAt: str(raw, "reminderAt") ?? null,
    updatedAt: str(raw, "updatedAt") ?? null,
  };
}

/**
 * One contact needing a follow-up, ranked by its relation's cadence. The draft
 * message is the ai-service's own, so the tile never invents text the engine did
 * not produce.
 *
 * The names are the backend record's own components: `FollowUpItem` is the one
 * producer, and it speaks camelCase (the ai-service's snake_case reaches it
 * through the bridge, which maps it into the record's own field names). A
 * snake_case twin beside each live name would be a second shape this mapper
 * silently reinterprets.
 */
function normalizeFollowUp(raw: unknown): FollowUpItem {
  return {
    id: str(raw, "id") ?? "",
    name: str(raw, "name"),
    company: str(raw, "company") ?? null,
    relation: str(raw, "relation") ?? null,
    priority: str(raw, "priority") ?? null,
    daysSince: num(raw, "daysSince") ?? null,
    cadenceDays: num(raw, "cadenceDays") ?? null,
    suggestedMessage: str(raw, "suggestedMessage") ?? null,
  };
}

export function normalizeDashboard(raw: unknown): DashboardPayload | null {
  // `api.get` already unwraps the {success,data} envelope, so what arrives here is
  // `DashboardResponse` and nothing else: { kanban{statusCounts,total,offers}, interviews,
  // avgMatch(0..1 or null), needsAttention(long), attention[] (the rows behind that count),
  // currentResume{resumeId,versionId,title,status,score}, skillGaps(digest), recommendedJobs[],
  // recentRuns[], recentActivity[] }.
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
    // No `attention` alias: that key is now the row list below, so reading it as a number would
    // turn "3 applications are waiting on you" into `NaN` and hide the strip on a served payload.
    needsAttention: num(d, "needsAttention", "needs_attention"),
  };
  const runs = list(d, "recentRuns", "recent_runs", "activity", "runs").map(normalizeRun);
  const attention = list(d, "attention")
    .map(normalizeAttention)
    .filter((row): row is AttentionItem => row !== null);
  const followUps = list(d, "followUps", "follow_ups").map(normalizeFollowUp);
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
    attention: attention.length ? attention : undefined,
    followUps: followUps.length ? followUps : undefined,
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
  // and `RunItem` from `GET /activity/runs`, which answers a `PageDTO` since #225. So every snake_case twin this
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

/**
 * The next question the agent proposes, which is a different payload from the turn above: the
 * interview advance decision (`decide_next` in `app/features/interview.py`) is relayed verbatim as
 * `AnswerResponse.next` by the backend, so its keys are that function's own -- `action`, `question`,
 * `topic`, `difficulty`, and a `reasoning` no card shows.
 *
 * `kind` is this view's word for `action`, and reading the wire's name is what the follow-up sentence
 * on the session page branches on: the alias list this read used to carry (`kind`/`type`/`nextAction`/
 * `next_action`) never named `action`, so the branch was always the other one.
 */
export function normalizeNextQuestion(raw: unknown): {
  text: string;
  topic?: string;
  kind?: string;
  difficulty?: number;
} | null {
  const q = rec(raw);
  if (!q) return null;
  const difficulty = num(raw, "difficulty");
  return {
    text: str(raw, "question") ?? "",
    topic: str(raw, "topic") || undefined,
    kind: str(raw, "action"),
    difficulty: difficulty == null ? undefined : difficulty,
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
      const next = rows[j];
      if (next.role === "interviewer") break;
      if (next.role === "candidate") score = pct(num(next, "score", "value"));
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

/**
 * The cards a copilot answer carries. One author: `orchestrator._collect_artifacts`, which appends
 * five literals in **two** shapes — every row draws `{type, payload}`, and the match row alone also
 * carries `job_id`. So this mapper reads the consensus and nothing else; `kind`, `title`/`name`/`label`
 * and `data`/`value` had no author on any path, which made `type` fall through to a `"text"` no
 * producer emits and let each renderer's own heading (which is what always showed) look configurable.
 * Takes the whole reply because both of its callers held the list already, and the name only has an
 * author on the record.
 */
export function normalizeArtifacts(raw: unknown): CopilotArtifact[] {
  return list(raw, "artifacts").map((a) => ({
    type: str(a, "type"),
    data: pick(a, "payload"),
  }));
}

/**
 * Where each action the orchestrator offers actually goes. The wire carries no `href`:
 * `_derive_actions` states a `kind` plus one locator — `job_id` for the four job actions,
 * `session_id` for a saved interview — so the destination is the browser's to build, and building
 * it is what makes the chip a button instead of a label. `{id}` in a template is the locator slot:
 * a row whose kind needs one and does not carry one gets no href, so the `open_interview` whose
 * `session_id` came back null becomes no chip rather than a link to `/interviews/null`.
 */
export const CHAT_ACTION_ROUTES: Record<string, string> = {
  open_job: "/jobs/{id}",
  tailor: "/jobs/{id}#tailor",
  cover_letter: "/jobs/{id}#cover-letter",
  interview: "/interviews",
  open_interview: "/interviews/{id}",
  // The growth engines' answers: the gap report and the learning order live on
  // the growth page, the market band and the offer comparison on the offers
  // page. Neither needs a locator -- the page is the destination.
  open_growth: "/growth",
  open_offers: "/offers",
};

/** Follow-up action chips. Takes the whole reply — the live `ChatResponse` or a persisted
 *  `MessageItem`, which carry the same `actions` list — and picks it itself, so the name the read
 *  goes under has an author. Shared by the history read path AND the live chat reply so a
 *  freshly-generated reply can't drop actions until a refetch. */
export function normalizeChatActions(raw: unknown): CopilotAction[] {
  return list(raw, "actions").map((a) => {
    const kind = str(a, "kind");
    const route = kind ? CHAT_ACTION_ROUTES[kind] : undefined;
    const needsId = route?.includes("{id}");
    const id = str(a, "job_id", "session_id");
    return {
      label: str(a, "label"),
      kind,
      href: !route || (needsId && !id) ? undefined : route.replace("{id}", id ?? ""),
    };
  });
}

/**
 * The translation key for an action's label, when the label is fixed by its kind.
 *
 * The orchestrator writes the label in English, and most of them are fixed
 * phrases ("Draft cover letter"), so the browser can say them in the reader's
 * language. `open_job` is not here: its label carries the job's own title and
 * company, which are the user's data and not copy to translate.
 */
export function actionLabelKey(kind?: string): string | undefined {
  const fixed: Record<string, string> = {
    cover_letter: "actions.coverLetter",
    interview: "actions.interview",
    tailor: "actions.tailor",
    open_growth: "actions.openGrowth",
    open_offers: "actions.openOffers",
    open_interview: "actions.openInterview",
  };
  return kind ? fixed[kind] : undefined;
}

export function normalizeMessages(raw: unknown) {
  // Bare, by contract: GET /conversations/{id}/messages answers `List<MessageItem>` and the client
  // hands over the unwrapped `data`, so the payload *is* the array. `messages`/`items`/`content` were
  // three names no path to this reader can fill -- `items` belongs to a PageDTO this route never
  // returns and `content` to a message's body -- and the field-contract gate now derives this reader's
  // rows from a nameless read instead of excusing them.
  return list(raw).map((m, i) => ({
    id: idOf(m, `msg-${i}`),
    role: str(m, "role", "sender") ?? "assistant",
    content: str(m, "content", "text", "message", "body") ?? "",
    createdAt: str(m, "createdAt", "created_at", "timestamp"),
    artifacts: normalizeArtifacts(m),
    sources: normalizeEvidence(pick(m, "sources")),
    actions: normalizeChatActions(m),
  }));
}
