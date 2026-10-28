/** Domain types mirroring docs/architecture.md §4 + the frozen /api/v1 contract. */

export interface User {
  id: string;
  email: string;
  displayName: string;
  avatarUrl?: string | null;
  role: string;
  createdAt?: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn?: number;
}

/**
 * `POST /auth/register` and `POST /auth/login` both return the user *and* a fresh
 * token pair (`AuthResponse` on the backend). Destructure `tokens` before passing
 * it to `tokenStore.set` — the payload is not `AuthTokens` itself.
 */
export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

/* ------------------------------------------------------------------ */
/* Resumes                                                             */
/* ------------------------------------------------------------------ */

export interface Resume {
  id: string;
  title: string;
  status: "uploaded" | "parsing" | "parsed" | "failed" | string;
  currentVersionId?: string | null;
  createdAt?: string;
  updatedAt?: string | null;
  /** populated on the detail route */
  structured?: StructuredResume | null;
  versions?: ResumeVersion[];
  score?: ResumeScore | null;
  /**
   * The detail route answers it when the resume was uploaded as a file, and the download route
   * (`endpoints.resumeFile`) has bytes behind it exactly when this is set. Produced by the
   * `resume.source_file_key` column in the backend entity.
   */
  sourceFileKey?: string | null;
}

export interface ResumeVersion {
  id: string;
  resumeId?: string;
  label?: string;
  versionNo?: number;
  isCurrent?: boolean;
  source?: string;
  createdAt?: string;
  score?: ResumeScore | null;
  structured?: StructuredResume | null;
  /** free-form diff against the parent version, when the backend supplies it */
  diff?: unknown;
}

export interface ResumeScore {
  overall?: number;
  bullets?: number;
  structure?: number;
  impact?: number;
  clarity?: number;
  keywords?: number;
  gaps?: string[];
}

export interface StructuredResume {
  profile?: ResumeProfileSummary;
  summary?: string;
  experience?: ResumeExperience[];
  projects?: ResumeProject[];
  education?: ResumeEducation[];
  skills?: ResumeSkillGroup[];
  achievements?: string[];
  careerGoals?: string[];
  preferredRoles?: string[];
  preferredLocations?: string[];
  [key: string]: unknown;
}

export interface ResumeProfileSummary {
  name?: string;
  headline?: string;
  email?: string;
  phone?: string;
  location?: string;
  links?: string[];
}

export interface ResumeExperience {
  company?: string;
  role?: string;
  location?: string;
  start?: string;
  end?: string;
  bullets?: string[];
}

export interface ResumeProject {
  name?: string;
  role?: string;
  period?: string;
  bullets?: string[];
  techStack?: string[];
  url?: string;
}

export interface ResumeEducation {
  school?: string;
  degree?: string;
  major?: string;
  start?: string;
  end?: string;
  gpa?: string | number;
  courses?: string[];
}

/** One category bucket as `groupSkillBuckets` builds it: nothing else writes this shape. */
export interface ResumeSkillGroup {
  group?: string;
  skills?: string[];
}

/* ------------------------------------------------------------------ */
/* Jobs / JD / matching                                               */
/* ------------------------------------------------------------------ */

export interface Job {
  id: string;
  companyId: string;
  company?: Pick<Company, "id" | "name" | "logoUrl">;
  companyName?: string | null;
  title: string;
  location?: string | null;
  remoteType?: string | null;
  employmentType?: string | null;
  experienceLevel?: string | null;
  postedAt?: string | null;
  salaryMin?: number | null;
  salaryMax?: number | null;
  salaryCurrency?: string | null;
  skills?: string[];
  status: "open" | "closed" | string;
  source?: "seed" | "user_paste" | "agent_research" | string;
  externalUrl?: string | null;
  saved?: boolean;
  /** only saved rows carry these two (`SavedJobItem`): the note written at save time, and when */
  note?: string | null;
  savedAt?: string | null;
  /** joined from /jobs or /reports/dashboard */
  latestMatch?: JobMatch | null;
  /** detail payload */
  jd?: JobDescription | null;
  description?: string | null;
}

/** The board's own filter names, under a name the reader chose (roadmap 19.1). */
export interface SavedSearchCriteria {
  q?: string;
  location?: string;
  company?: string;
  remote?: boolean;
  minSalary?: number;
  maxSalary?: number;
  skills?: string[];
}

export interface SavedSearch {
  id: string;
  name: string;
  criteria: SavedSearchCriteria;
  createdAt?: string;
}

export interface JobDescription {
  id?: string;
  jobId?: string;
  rawText?: string;
  requirements?: JdRequirement[];
  responsibilities?: string[];
  requiredSkills?: string[];
  preferredSkills?: string[];
  interviewTopics?: string[];
  hiddenRequirements?: string[];
  softSkills?: string[];
  priorities?: string[];
  skillGap?: string[];
  suggestions?: string[];
  [key: string]: unknown;
}

export interface JdRequirement {
  skill?: string;
  name?: string;
  text?: string;
  required?: boolean;
  priority?: "must" | "nice_to_have" | "hidden" | string;
  evidence?: string;
}

export interface JobDetail extends Job {
  latest?: JobMatch | null;
  dimensions?: MatchDimension[];
  evidence?: Evidence[];
  skillGaps?: SkillGap[];
  interviewTopics?: string[];
  preparation?: PreparationItem[];
}

/** One scored bar of a match. `note`/`evidence` are #150's deletions: the mapper fills a dimension
 *  from `MatchResult`'s four score columns, and no producer sends a per-dimension explanation. */
export interface MatchDimension {
  key: string;
  label: string;
  score?: number;
}

export interface JobMatch {
  id: string;
  jobId?: string;
  resumeVersionId?: string | null;
  overall: number;
  technical?: number;
  experience?: number;
  projects?: number;
  education?: number;
  dimensions?: MatchDimension[];
  matchedSkills?: string[];
  missingSkills?: string[];
  whyMatch?: string[];
  reasoning?: string;
  evidence?: Evidence[];
  interviewTopics?: string[];
  preparation?: PreparationItem[];
  skillGaps?: SkillGap[];
  createdAt?: string;
  computedAt?: string;
}

export interface SkillGap {
  skill: string;
  importance?: "critical" | "high" | "medium" | "low" | string;
  reason?: string;
  relatedEvidence?: string;
}

export interface PreparationItem {
  topic?: string;
  title?: string;
  reason?: string;
  resource?: string;
  hours?: number;
  priority?: string;
}

export interface Evidence {
  criterion: string;
  score?: number;
  chunkIds?: string[];
  quote: string;
  reasoning?: string;
  // No wire row carries an `href`, so #151 deleted that field: a citation's destination comes from
  // the surface rendering it (`EvidenceList`'s `hrefFor`), never from the payload.
  source?: { docTitle?: string; docId?: string; path?: string[]; kind?: string };
}

/* ------------------------------------------------------------------ */
/* Companies                                                          */
/* ------------------------------------------------------------------ */

/**
 * One company, read under the names `JobDtos.CompanyItem` spells.
 *
 * `culture` and `interviewProcess` are single text columns on the `companies` row, so the wire
 * carries one string each — not the arrays this interface used to allow. `openRoleCount` is the
 * number of open roles; the rows themselves are `CompanyDetail.openRoles`, and the two used to share
 * the name `openRoles`, which is how the browser came to read a number as a list.
 */
export interface Company {
  id: string;
  name: string;
  website?: string | null;
  logoUrl?: string | null;
  industry?: string | null;
  size?: string | null;
  overview?: string | null;
  techStack?: string[];
  culture?: string | null;
  interviewProcess?: string | null;
  /** External facts, each carrying where it came from. */
  sources?: CompanySource[];
  openRoleCount?: number;
}

/**
 * One row of `companies.sources`, the jsonb column the schema comments "external data MUST carry
 * source". Two writers exist — the seed and `JobService.upsertCompany` — and both write `type` plus a
 * human-readable field, so those are what this names; anything else is not rendered.
 */
export interface CompanySource {
  type?: string;
  title?: string;
  note?: string;
  url?: string;
}

/** `GET /api/v1/companies/{id}`: the profile, plus the roles it is hiring for. */
export interface CompanyDetail {
  company: Company;
  openRoles: Job[];
}

/* ------------------------------------------------------------------ */
/* Applications                                                       */
/* ------------------------------------------------------------------ */

export type ApplicationStatus =
  | "saved"
  | "applied"
  | "oa"
  | "interview"
  | "final_round"
  | "offer"
  | "rejected";

export interface Application {
  id: string;
  jobId?: string | null;
  companyId?: string | null;
  company?: Pick<Company, "id" | "name" | "logoUrl">;
  companyName?: string | null;
  title: string;
  status: ApplicationStatus | string;
  matchScore?: number | null;
  note?: string | null;
  reminderAt?: string | null;
  /** kanban order inside a stage — persisted via PATCH /applications/{id} {position} */
  position?: number | null;
  orderIndex?: number;
  /** Linked resume version used for matching/tailoring this application */
  resumeVersionId?: string | null;
  /** Linked JD analysis used for this application */
  jdId?: string | null;
  /** Linked match analysis for this application */
  matchId?: string | null;
  /** Compensation written on the offer, when the terminal outcome is known. */
  offerCompensation?: string | null;
  /** Why the application did not proceed, when it was rejected. */
  rejectionReason?: string | null;
  /** When the application was moved to 'applied' stage */
  appliedAt?: string | null;
  createdAt?: string;
  updatedAt?: string;
}

/**
 * One audit row of an application's history, as `TimelineEvent` puts it on the wire:
 * `{id, kind, payload, createdAt}`, with the detail nested under `payload`.
 *
 * `applicationId` and `label` used to sit here. No writer fills either — the row is written by
 * `ApplicationService.writeEvent`, which sets a kind and a payload, and the DTO has no such
 * components — so a reader for them could only ever render blank.
 */
export interface ApplicationEvent {
  id: string;
  /** The `kind` the event was written under: `status`, `note` or `reminder`. */
  type?: string;
  /** Set on an `outcome` event: which terminal field was written (`offer_compensation` / `rejection_reason`). */
  field?: string;
  status?: string;
  note?: string;
  /** Set on a `reminder` event: the instant the reminder was moved to. */
  reminderAt?: string;
  /** True when that `reminder` event is the removal of one rather than a new date. */
  cleared?: boolean;
  createdAt?: string;
}

/* ------------------------------------------------------------------ */
/* Knowledge base                                                     */
/* ------------------------------------------------------------------ */

export interface KnowledgeSource {
  id: string;
  kind: string;
  title: string;
  status: "pending" | "ingesting" | "ready" | "failed" | string;
  error?: string | null;
  chunks?: number;
  chunkCount?: number;
  createdAt?: string;
  updatedAt?: string;
  sizeBytes?: number;
  taskId?: string | null;
  documentId?: string | null;
}

export interface KnowledgeNote {
  id: string;
  title: string;
  content?: string;
  body?: string;
  kind?: string;
  tags?: string[];
  sourceId?: string | null;
  createdAt?: string;
  updatedAt?: string;
}

/* ------------------------------------------------------------------ */
/* Interviews                                                         */
/* ------------------------------------------------------------------ */

export interface InterviewSession {
  id: string;
  jobId?: string | null;
  jobTitle?: string | null;
  companyName?: string | null;
  mode: string;
  status: "active" | "paused" | "completed" | "abandoned" | string;
  difficulty?: number;
  questionCount?: number;
  startedAt?: string;
  finishedAt?: string | null;
  overall?: number | null;
  dims?: InterviewDimension[];
}

export interface InterviewDimension {
  key: string;
  label: string;
  score?: number;
}

/**
 * A question the interviewer asked, from either of its two authors: the persisted `TurnItem` (whose
 * text is `content`, with topic and action in its `questionMeta`) or the advance decision
 * `AnswerResponse.next` (whose text is `question`, and whose action/difficulty are top level). The two
 * readers are bound to those two shapes in `test_response_field_contract.py`; this is the fold the page
 * renders. `question`/`hint` were dropped by #157 -- no path ever wrote them.
 */
export interface InterviewQuestion {
  id?: string;
  text: string;
  topic?: string;
  /** "opening" | "followup" | "next_topic" | "finish" -- the wire's `action`. */
  kind?: string;
  difficulty?: number;
}

export interface InterviewAnswerEvaluation {
  score?: number;
  dims?: Record<string, number> | InterviewDimension[];
  strengths?: string[];
  whatWentWell?: string[];
  weaknesses?: string[];
  whatWasWeak?: string[];
  missing?: string[];
  missingConcepts?: string[];
  betterAnswer?: string;
  feedback?: string;
  followUps?: string[];
  next?: InterviewQuestion | null;
  trajectory?: { question?: string; score?: number; depth?: number; at?: string }[];
  finishHint?: boolean;
}

export interface InterviewReport {
  sessionId?: string;
  dims?: Record<string, number> | InterviewDimension[];
  dimensions?: InterviewDimension[];
  overall?: number;
  whatWentWell?: string[];
  whatWasWeak?: string[];
  studyMaterials?: { title?: string; url?: string; why?: string; kind?: string }[];
  trajectory?: { question?: string; score?: number; depth?: number; at?: string }[];
  difficultyCurve?: number[];
  summary?: string;
  mode?: string;
  jobTitle?: string | null;
  companyName?: string | null;
  finishedAt?: string | null;
}

/* ------------------------------------------------------------------ */
/* Copilot                                                            */
/* ------------------------------------------------------------------ */

export interface Conversation {
  id: string;
  title: string;
  updatedAt?: string;
  createdAt?: string;
  lastMessagePreview?: string;
  messageCount?: number;
}

/**
 * One card the copilot's answer carries. `type` is free-form on purpose: the row comes out of a jsonb
 * column the agent orchestrator wrote, so the browser's vocabulary lives in `ArtifactCard`'s switch and
 * the field-contract gate bounds that against the `type` values `_collect_artifacts` actually appends --
 * a union here would be a second copy of a list the gate already reads from both ends.
 */
export interface CopilotArtifact {
  type?: string;
  data?: unknown;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system" | string;
  content: string;
  createdAt?: string;
  artifacts?: CopilotArtifact[];
  sources?: Evidence[];
  actions?: CopilotAction[];
  runId?: string | null;
  pending?: boolean;
  error?: string | null;
}

/** One action chip the copilot offers. `href` is built from `kind` and the row's locator, because
 *  the wire carries neither an href nor a payload — see `CHAT_ACTION_ROUTES`. */
export interface CopilotAction {
  label?: string;
  href?: string;
  kind?: string;
}

export interface CopilotReply {
  answer: string;
  artifacts?: CopilotArtifact[];
  sources?: Evidence[];
  actions?: CopilotAction[];
  runId?: string | null;
  taskId?: string | null;
  conversationId?: string | null;
}

/* ------------------------------------------------------------------ */
/* AI actions                                                         */
/* ------------------------------------------------------------------ */

export interface TailorChange {
  id: string;
  section?: string;
  before?: string;
  after?: string;
  reason?: string;
}

export interface TailoredResult {
  markdown?: string;
}

export interface TailorDiff {
  accepted: TailorChange[];
  rejected: TailorChange[];
}

export interface TailorResponse {
  tailored?: TailoredResult;
  diff?: TailorDiff;
  notes?: string[];
  evidence?: Evidence[];
  stats?: Record<string, unknown>;
  taskId?: string | null;
  runId?: string | null;
}

export interface CoverLetter {
  id?: string;
  content?: string;
  text?: string;
  markdown?: string;
  subject?: string | null;
  tone?: string | null;
  length?: string | null;
  wordCount?: number | null;
  evidence?: Evidence[];
  createdAt?: string;
  taskId?: string | null;
}

export interface Suggestion {
  id?: string;
  title?: string;
  text?: string;
  body?: string;
  section?: string;
  priority?: string;
  evidence?: Evidence[];
}

/* ------------------------------------------------------------------ */
/* Activity / usage / reports                                         */
/* ------------------------------------------------------------------ */

export interface ActivityEvent {
  id: string;
  agent?: string;
  kind: string;
  summary?: string;
  status?: string;
  createdAt: string;
  durationMs?: number;
  tokens?: number;
  costUsd?: number;
}

export interface ActivityRun {
  id: string;
  agent?: string;
  kind?: string;
  status?: string;
  error?: string;
  model?: string | null;
  startedAt?: string;
  finishedAt?: string | null;
  durationMs?: number;
  tokensIn?: number;
  tokensOut?: number;
  costUsd?: number;
}

/**
 * One memory the agents hold about the user (AGENTS.md §6). Read through
 * `GET /memories`, corrected through `PATCH /memories/{id}`.
 *
 * `importance` is the weight the prompt reader sorts by, so lowering it is how the user
 * keeps a fact without being told it first every time.
 */
export interface MemoryItem {
  id: string;
  kind: string;
  key: string;
  content: string;
  importance: number;
  source?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface AIUsageSummary {
  requests?: number;
  totalTokens?: number;
  costUsd?: number;
}

export interface DashboardMetrics {
  applications?: number;
  inPipeline?: number;
  interviews?: number;
  offers?: number;
  skillGaps?: number;
  resumeScore?: number;
  avgMatch?: number;
  needsAttention?: number;
  [key: string]: number | undefined;
}

/**
 * One open application the dashboard says needs the user. `reason` is the backend's own
 * classification (`reminder_due` when a reminder has come due, `stale` when nobody has logged a
 * step for the window), so the row's action is read off the payload rather than re-derived here.
 */
export interface AttentionItem {
  id: string;
  title?: string;
  companyName?: string;
  status?: string;
  reason?: string;
  reminderAt?: string | null;
  updatedAt?: string | null;
}

/**
 * One contact needing a follow-up, ranked by its relation's cadence. The draft
 * message is the ai-service's own, so the tile never invents text the engine did
 * not produce.
 */
export interface FollowUpItem {
  id: string;
  name?: string;
  company?: string | null;
  relation?: string | null;
  priority?: string | null;
  daysSince?: number | null;
  cadenceDays?: number | null;
  suggestedMessage?: string | null;
}

export interface DashboardPayload {
  metrics?: DashboardMetrics;
  /** either {status: count} or [{status,count}] */
  pipeline?: Record<string, number> | { status: string; count: number }[];
  recommendedJobs?: Job[];
  skillGaps?: SkillGap[];
  /** The rows behind `metrics.needsAttention`, most-due reminder first. */
  attention?: AttentionItem[];
  /** Contacts ranked by their relation's cadence, each with a drafted message. */
  followUps?: FollowUpItem[];
  resume?: (Pick<Resume, "id" | "title" | "status" | "currentVersionId"> & {
    score?: ResumeScore | number;
  }) | null;
  score?: ResumeScore | number | null;
  recentRuns?: ActivityRun[];
  activity?: ActivityRun[];
  greeting?: string | null;
  [key: string]: unknown;
}

/* ------------------------------------------------------------------ */
/* Upload / ingestion                                                 */
/* ------------------------------------------------------------------ */

export interface UploadResult {
  resume_id?: string;
  resumeId?: string;
  version_id?: string;
  versionId?: string;
  document_id?: string;
  documentId?: string;
  source_id?: string;
  sourceId?: string;
  task_id?: string;
  taskId?: string;
}

export interface ParseResult {
  parsed?: boolean;
  structured?: StructuredResume | null;
  score?: ResumeScore | number | null;
  taskId?: string | null;
  task_id?: string | null;
}

export interface TextIngestResult {
  task_id?: string;
  taskId?: string;
  document_id?: string;
  documentId?: string;
  source_id?: string;
  sourceId?: string;
}

/* ------------------------------------------------------------------ */
/* Analysis                                                           */
/* ------------------------------------------------------------------ */

/** One stalled application in the insight digest. */
export interface StalledApplication {
  id: string;
  title?: string;
  company?: string;
  status?: string;
  daysSinceLastActivity?: number;
}

/**
 * The weekly insight digest (15.3): stalled applications, live stage mix, and
 * headline rates, composed by the ai-service's analytics engine.
 */
export interface InsightDigest {
  generatedAt?: string;
  windowDays?: number;
  totalApplications?: number;
  activePipeline?: number;
  stageCounts?: Record<string, number>;
  responseRate?: number;
  offerRate?: number;
  stalledCount?: number;
  stalled?: StalledApplication[];
  signals?: string[];
  growthDeltas?: unknown[];
  topMatches?: unknown[];
}

/** One stage of the pipeline funnel (15.1). */
export interface FunnelStage {
  stage?: string;
  count?: number;
  conversionFromApplied?: number;
  stepConversion?: number | null;
}

/** 15.1 — how many applications reached each stage, and where the leak is. */
export interface PipelineFunnel {
  pipeline?: FunnelStage[];
  appliedCount?: number;
  savedCount?: number;
  rejectedCount?: number;
  totalApplications?: number;
}

/** 15.2 — the reply / interview / offer rates and the per-stage durations. */
export interface ResponseRate {
  appliedCount?: number;
  respondedCount?: number;
  responseRate?: number;
  offerCount?: number;
  offerRate?: number;
  interviewCount?: number;
  interviewRate?: number;
  timeInStage?: Record<string, { avgDays?: number | null; medianDays?: number | null; n?: number }>;
}

/* ------------------------------------------------------------------ */
/* Monitoring                                                         */
/* ------------------------------------------------------------------ */

/**
 * Production monitoring (16.1): agent health, cost, and regression detection.
 * The report is composed by the ai-service's monitoring engine.
 */
export interface HealthReport {
  verdict?: string;
  errorRate?: number;
  totalRuns?: number;
  totalCostUsd?: number;
  totalTokens?: number;
  p50LatencyMs?: number;
  p95LatencyMs?: number;
  alerts?: string[];
  regressions?: Array<{ metric: string; direction: string; severity: string }>;
}

/* ------------------------------------------------------------------ */
/* Job ingestion (14.2-14.3)                                         */
/* ------------------------------------------------------------------ */

/** One raw posting as a connector hands it over. */
export interface RawPosting {
  id?: string;
  title?: string;
  company?: string;
  location?: string;
  remote_type?: string;
  employment_type?: string;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string;
  description?: string;
  skills?: string[];
  external_url?: string | null;
  posted_at?: string | null;
  source?: string;
  [key: string]: unknown;
}

/** The parse result (14.2): the raw postings a feed carried. */
export interface ParsedFeed {
  postings?: RawPosting[];
  count?: number;
}

/** The dedupe result (14.3): survivors, losers, and the counts. */
export interface PostingCollection {
  unique?: RawPosting[];
  duplicates?: RawPosting[];
  inputCount?: number;
  uniqueCount?: number;
  duplicateCount?: number;
}

/** The freshness sweep (14.3): the corpus partitioned by age. */
export interface FreshnessSweep {
  fresh?: Array<{ id?: string; title?: string }>;
  stale?: Array<{ id?: string; title?: string; daysSinceSeen?: number }>;
  expired?: Array<{ id?: string; title?: string; ageDays?: number }>;
  undated?: Array<{ id?: string; title?: string }>;
  counts?: { fresh: number; stale: number; expired: number; undated: number };
}

/** The ingestion plan (14.3): the three writes a sweep needs. */
export interface IngestPlan {
  source?: string;
  create?: RawPosting[];
  update?: RawPosting[];
  close?: Array<{ id?: string; title?: string }>;
  duplicates?: RawPosting[];
  counts?: {
    incoming: number;
    create: number;
    update: number;
    close: number;
    duplicates: number;
  };
}

/** What one run counted, read off the engine's own answer (roadmap 19.2). */
export interface IngestCounts {
  incoming?: number;
  create?: number;
  update?: number;
  close?: number;
  duplicates?: number;
  [key: string]: number | undefined;
}

/** One pull of one feed — the record that makes a failed night visible. */
export interface IngestionRun {
  id: string;
  feedId: string;
  feedName: string;
  /** "completed" or "failed"; the backend's own vocabulary. */
  status: string;
  error?: string | null;
  counts?: IngestCounts | null;
  startedAt?: string;
  finishedAt?: string;
}

/** A subscribed source the nightly sweep fetches (roadmap 19.2). */
export interface IngestionFeed {
  id: string;
  name: string;
  url: string;
  source: string;
  enabled: boolean;
  createdAt?: string;
  lastRun?: IngestionRun | null;
}

/** One run plus the plan it filed; the plan is the engine's, shown rather than applied. */
export interface IngestionRunDetail {
  run: IngestionRun;
  plan?: Record<string, unknown> | null;
}

/* ------------------------------------------------------------------ */
/* Granular growth engines (10.1-10.13)                               */
/* ------------------------------------------------------------------ */

/**
 * The names below are the engines' own spellings, not a frontend dialect.
 *
 * Each route's answer crosses the bridge verbatim (no key is renamed), and no
 * normalizer sits on these paths, so a field name invented here reads as an
 * empty row on screen while the engine is answering it fine. `tests/
 * test_the_growth_panel_reads_the_keys_the_engines_emit.py` grades every name
 * in this block against the engine's own emitted shape.
 */

/** One skill the market asks for (10.9). */
export interface DemandSkill {
  skill?: string;
  count?: number;
  share?: number;
}

/** 10.9 — which skills a role family's postings ask for, and how often. */
export interface SkillDemand {
  role?: string;
  location?: string;
  /** Postings the count came from -- the denominator behind every `share`. */
  postings?: number;
  skills?: DemandSkill[];
}

/** 10.1 — the distance between the profile and the target role.
 *
 *  Same answer the aggregate report nests under `gap`, so it is one declaration
 *  (`GapBlock`) rather than two that can drift apart.
 */
export type GapReport = GapBlock;

/** 10.7 — target-role readiness, as one verdict. */
export interface ReadinessVerdict {
  targetRole?: string;
  verdict?: string;
  coverage?: number;
  gapCount?: number;
  coveredCount?: number;
  blockers?: string[];
}

/** 10.5 — the phased learning plan. The route nests the plan under `plan`. */
export interface LearningPlan {
  plan?: {
    targetRole?: string;
    totalItems?: number;
    phases?: Array<{ phase?: string; label?: string; items?: LearningItem[] }>;
  };
  gap?: GapReport;
}

/** 10.12 — a gap ranked by importance and market pull. */
export interface LearningPriorityItem {
  skill?: string;
  importance?: string;
  category?: string;
  /** 0–1 share of the postings that ask for this skill. */
  marketShare?: number;
  marketPostings?: number;
  marketRank?: number;
  /** "critical" | "high" | … — the tier the engine assigned. */
  priority?: string;
}

/** 10.12 — the learning priority ranking. */
export interface LearningPriority {
  targetRole?: string;
  coverage?: number;
  gapCount?: number;
  prioritizedGaps?: LearningPriorityItem[];
  topPriority?: LearningPriorityItem | null;
}

/** One stepping-stone role (10.11). */
export interface ProgressionStep {
  /** The role family, named by the engine -- there is no per-step role title. */
  family?: string;
  currentCoverage?: number;
  postings?: number;
  buildsSkills?: string[];
  buildsMustCount?: number;
  buildsCount?: number;
  bridgeScore?: number;
  reason?: string;
}

/** 10.11 — the progression plan toward a dream role. */
export interface ProgressionPlan {
  aspirationalRole?: string;
  aspirationalCoverage?: number;
  aspirationalMustGaps?: string[];
  steppingStones?: ProgressionStep[];
  advice?: unknown;
}

/** One gap to shore up before the interview (10.13). */
export interface PrepWeakArea {
  skill?: string;
  importance?: string;
  action?: string;
}

/** One strength story to rehearse, and the gap-report evidence behind it (10.13). */
export interface PrepStrengthStory {
  skill?: string;
  evidence?: string;
  storyTitle?: string | null;
  storyId?: string | null;
  quantified?: boolean;
}

/** 10.13 — the pre-interview checklist. */
export interface InterviewPrep {
  targetRole?: string;
  coverage?: number;
  weakAreaCount?: number;
  strengthStoryCount?: number;
  /** Study these: the role's gaps. */
  weakAreas?: PrepWeakArea[];
  /** Rehearse these: the covered skills that already carry a story. */
  strengthStories?: PrepStrengthStory[];
  likelyTopics?: string[];
}

/** One STAR story (6.5). */
export interface Story {
  id?: string;
  kind?: string;
  title?: string;
  bullets?: string[];
  skills?: string[];
  quantified?: boolean;
}

/** 6.5 — the story bank. */
export interface StoryBank {
  stories?: Story[];
  count?: number;
  quantifiedCount?: number;
  skillsCovered?: string[];
}

/** One suggested target role family (10.10). */
export interface SuggestedRole {
  family?: string;
  postings?: number;
  /** 0–1: how much of the family's demands the profile already has. */
  coverage?: number;
  topDemands?: string[];
  youHave?: string[];
  missing?: string[];
}

/** 10.10 — the target roles this profile could plausibly aim at. */
export interface RoleSuggestions {
  families?: SuggestedRole[];
}

/** 4.8 — what the corpus says about one company. */
export interface CompanyBrief {
  company?: string;
  roles?: Array<{ title?: string; location?: string }>;
  skills?: Array<{ name?: string; count?: number }>;
  interviewTopics?: string[];
}

/** 10.6 — the skill progress between two snapshots. */
export interface SkillProgress {
  baseline?: boolean;
  closed?: string[];
  improved?: string[];
  regressed?: string[];
  stillOpen?: string[];
  previousCoverage?: number;
  currentCoverage?: number;
  delta?: number;
}

/** 11.2 — the drafted outreach message and the evidence it cited.
 *
 *  The field names are the engine's own: `body` is the message, `subject`
 *  its subject line, and `evidenceUsed` the skills the validator let it
 *  cite. The page used to read a `message` field the engine has never
 *  sent, so the draft never appeared.
 */
export interface OutreachDraft {
  subject?: string;
  body?: string;
  contactName?: string;
  purpose?: string;
  evidenceUsed?: string[];
  allowedEvidence?: string[];
}

/* ------------------------------------------------------------------ */
/* Salary & offers (12.1-12.5)                                       */
/* ------------------------------------------------------------------ */

/** The salary percentiles the benchmark answers with (12.1). */
export interface SalaryBenchmark {
  role?: string;
  location?: string;
  sampleSize?: number;
  percentiles?: { p25?: number; p50?: number; p75?: number };
  currency?: string;
  note?: string;
}

/** The negotiation coach's answer (12.2). */
export interface NegotiationPlan {
  verdict?: string;
  offerBase?: number;
  benchmark?: { p25?: number; p50?: number; p75?: number };
  leverage?: string;
  talkingPoints?: string[];
  note?: string;
}

/** One offer in a comparison (12.3 / 12.5). */
export interface OfferRow {
  label?: string;
  base?: number;
  bonus?: number;
  firstYearCash?: number;
  annualEquity?: number;
  totalComp?: number;
  assessment?: { verdict?: string };
}

/** The offer comparison (12.3 / 12.5). */
export interface OfferComparison {
  rows?: OfferRow[];
  best?: OfferRow | null;
  notes?: string[];
}

/** The counter-offer draft (12.4). */
export interface CounterOfferDraft {
  anchor?: number;
  reasons?: string[];
  script?: string;
  note?: string;
}

/* ------------------------------------------------------------------ */
/* Data portability                                                   */
/* ------------------------------------------------------------------ */

/**
 * The export bundle (13.1): a versioned, content-hashed snapshot of everything
 * the user owns. The hash covers only the data payload, so re-exporting
 * unchanged data yields the same hash.
 */
export interface ExportBundle {
  schema_version?: string;
  generator?: string;
  generated_at?: string;
  user?: { id?: string; anonymized?: boolean };
  manifest?: {
    schema_version?: string;
    generator?: string;
    counts?: Record<string, number>;
    content_hash?: string;
    anonymized?: boolean;
    redacted_sections?: string[];
  };
  data?: Record<string, unknown>;
}

/** One write operation in an import plan (13.2). */
export interface ImportOp {
  /**
   * `skip` is a row the target already has, unchanged: the plan names it so
   * the preview can count it, and the apply writes nothing for it.
   */
  op: "create" | "update" | "delete" | "skip";
  id?: string;
  content_hash?: string | null;
}

/** The idempotent write plan for a re-import (13.2). */
export interface ImportPlan {
  schema_version?: string;
  source_content_hash?: string;
  sections?: Record<string, ImportOp[]>;
  op_counts?: {
    create: number;
    update: number;
    delete: number;
    skip: number;
    total: number;
  };
}

/**
 * What an applied re-import wrote (13.2). `skipped` names every section the
 * backend could not write **with the reason** — a partial restore is visible
 * rather than reported as a success.
 */
export interface ImportApplied {
  applied?: Record<
    string,
    { created?: number; updated?: number; deleted?: number; unchanged?: number }
  >;
  skipped?: Array<{ section: string; reason: string }>;
  op_counts?: {
    create: number;
    update: number;
    delete: number;
    skip: number;
    total: number;
  };
}

/** A bundle with sections dropped (13.3). */
export type RedactedBundle = ExportBundle;

/**
 * The human-readable rendering of a bundle (13.1): a self-contained,
 * print-ready document. `bytes_base64` carries the PDF when the optional
 * converter is installed; the HTML is always there and is already
 * print-ready in a browser.
 */
export interface RenderedBundle {
  format?: "html" | "pdf" | "markdown";
  html?: string;
  markdown?: string;
  bytes_base64?: string;
}

/* ------------------------------------------------------------------ */
/* Rate limiting                                                      */
/* ------------------------------------------------------------------ */

/**
 * Rate-limit status (16.2): the current rate-limit configuration and the caller's
 * current bucket usage.
 */
export interface RateLimitStatus {
  enabled?: boolean;
  aiPerMinute?: number;
  authPerMinute?: number;
  aiRemaining?: number;
}

/* ------------------------------------------------------------------ */
/* Search                                                             */
/* ------------------------------------------------------------------ */

export interface SearchResultItem {
  id: string;
  type: string;
  title: string;
  subtitle?: string;
  href: string;
}

export interface SearchResults {
  groups: { label: string; items: SearchResultItem[] }[];
}

/* ------------------------------------------------------------------ */
/* SSE                                                                */
/* ------------------------------------------------------------------ */

/** SSE event payloads — architecture.md §9: status|token|trace|artifact|done|error */
export type SSEEventName = "status" | "token" | "trace" | "artifact" | "done" | "error";

export interface SSEStatusEvent {
  step?: string;
  label?: string;
  progress?: number;
  [key: string]: unknown;
}
export interface SSETraceEvent {
  id?: string;
  kind:
    | "step_start"
    | "tool_call"
    | "tool_result"
    | "llm_call"
    | "retrieval"
    | "rerank"
    | "handoff"
    | "message"
    | "final";
  label?: string;
  durationMs?: number;
  payload?: Record<string, unknown>;
  [key: string]: unknown;
}

/* ------------------------------------------------------------------ */
/* Contacts                                                            */
/* ------------------------------------------------------------------ */

/**
 * One person in the networking registry (`ContactDtos.ContactItem`), roadmap 11.1.
 * The optionals are absence on the wire, never empty strings; `lastTouchAt` is the
 * user's own claim about when contact last happened.
 */
export interface Contact {
  id: string;
  name: string;
  role?: string | null;
  company?: string | null;
  relation?: string | null;
  email?: string | null;
  notes?: string | null;
  lastTouchAt?: string | null;
  createdAt?: string;
  updatedAt?: string;
}

/* ------------------------------------------------------------------ */
/* Growth report                                                       */
/* ------------------------------------------------------------------ */

/**
 * The growth page's one answer (`POST /growth-report`, roadmap 10.3), as the 10.8
 * aggregate composes it: readiness, gap, salary, learning plan and progress. The
 * schema is the AI service's — this names only what the panel renders, and each
 * sub-block is read defensively because the engine owns the shape and evolves it.
 */
export interface GrowthReport {
  readiness?: {
    targetRole?: string;
    seniority?: string;
    /** 0–1: evidence-weighted share of the role's expected skills. */
    skillReadiness?: number;
    /** "ready" | "borderline" | "not_ready" — the coverage verdict. */
    skillVerdict?: string;
    salaryVerdict?: string | null;
    /** The overall verdict; a required-skill gap caps a "ready" at "borderline". */
    verdict?: string;
    coveredCount?: number;
    gapCount?: number;
    blockers?: string[];
  };
  gap?: GapBlock;
  salary?: {
    role?: string;
    location?: string;
    seniority?: string;
    currency?: string;
    sampleSize?: number;
    percentiles?: {
      min?: number;
      p25?: number;
      p50?: number;
      p75?: number;
      max?: number;
    };
    position?: { verdict?: string; note?: string };
  };
  learningPlan?: {
    phases?: {
      phase?: string;
      label?: string;
      items?: LearningItem[];
    }[];
  };
  progress?: {
    targetRole?: string;
    /** True on the first run: no previous report existed to diff against. */
    baseline?: boolean;
    closed?: string[];
    improved?: string[];
    opened?: string[];
    regressed?: string[];
    stillOpen?: string[];
    previousCoverage?: number;
    currentCoverage?: number;
    delta?: number;
  };
}

/** One expected skill, classified against the resume's evidence. */
export interface GapBlock {
  targetRole?: string;
  expectedSkillCount?: number;
  coveredCount?: number;
  partialCount?: number;
  gapCount?: number;
  /** 0–1: covered counts fully, partial counts half. */
  coverage?: number;
  covered?: SkillRow[];
  partial?: SkillRow[];
  gaps?: SkillRow[];
  strengths?: string[];
}

export interface SkillRow {
  skill?: string;
  category?: string;
  importance?: "must" | "should" | "nice" | string;
  /** Where the evidence came from, when it did. */
  evidence?: string;
}

/** One study item, phased foundation → core → applied by the engine. */
export interface LearningItem {
  /** snake_case on the wire: the learning engine spells it that way. */
  topic?: string;
  category?: string;
  phase?: string;
  priority?: string;
  resource_hint?: string;
  note?: string;
}
