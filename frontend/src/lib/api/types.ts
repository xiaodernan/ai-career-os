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
  fileUrl?: string | null;
  fileName?: string | null;
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
  suggestions?: string[];
  computedAt?: string;
}

export interface StructuredResume {
  profile?: ResumeProfileSummary;
  summary?: string;
  experience?: ResumeExperience[];
  projects?: ResumeProject[];
  education?: ResumeEducation[];
  skills?: ResumeSkillGroup[];
  achievements?: string[];
  technologies?: string[];
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
  title?: string;
  location?: string;
  start?: string;
  end?: string;
  startDate?: string;
  endDate?: string;
  current?: boolean;
  bullets?: string[];
  highlights?: string[];
  techStack?: string[];
}

export interface ResumeProject {
  name?: string;
  title?: string;
  role?: string;
  period?: string;
  description?: string;
  bullets?: string[];
  highlights?: string[];
  techStack?: string[];
  url?: string;
}

export interface ResumeEducation {
  school?: string;
  institution?: string;
  degree?: string;
  major?: string;
  field?: string;
  start?: string;
  end?: string;
  gpa?: string | number;
  courses?: string[];
}

export interface ResumeSkillGroup {
  group?: string;
  category?: string;
  name?: string;
  skills?: string[];
  level?: string;
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
  remote?: boolean | null;
  employmentType?: string | null;
  experienceLevel?: string | null;
  postedAt?: string | null;
  salaryMin?: number | null;
  salaryMax?: number | null;
  salaryCurrency?: string | null;
  salaryText?: string | null;
  skills?: string[];
  tags?: string[];
  status: "open" | "closed" | string;
  source?: "seed" | "user_paste" | "agent_research" | string;
  externalUrl?: string | null;
  saved?: boolean;
  /** joined from /jobs or /reports/dashboard */
  latestMatch?: JobMatch | null;
  match?: JobMatch | null;
  whyMatch?: string[];
  /** detail payload */
  jd?: JobDescription | null;
  description?: string | null;
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

export interface MatchDimension {
  key: string;
  label: string;
  score?: number;
  note?: string;
  evidence?: Evidence[];
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
  source?: { docTitle?: string; docId?: string; path?: string[]; kind?: string };
  href?: string;
}

/* ------------------------------------------------------------------ */
/* Companies                                                          */
/* ------------------------------------------------------------------ */

export interface Company {
  id: string;
  name: string;
  website?: string | null;
  logoUrl?: string | null;
  industry?: string | null;
  size?: string | null;
  hq?: string | null;
  location?: string | null;
  techStack?: string[];
  culture?: string[] | string;
  interviewProcess?: string[] | string;
  overview?: string | null;
  openRoles?: Job[];
  rolesCount?: number;
  sources?: Evidence[];
  bestMatch?: JobMatch | null;
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
  createdAt?: string;
  updatedAt?: string;
}

export interface ApplicationEvent {
  id: string;
  applicationId?: string;
  type?: string;
  status?: string;
  label?: string;
  note?: string;
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

export interface InterviewQuestion {
  id?: string;
  question?: string;
  text?: string;
  topic?: string;
  kind?: "opening" | "followup" | "next_topic" | string;
  difficulty?: number;
  hint?: string;
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

export type ArtifactType =
  | "match"
  | "job_list"
  | "tailored_resume"
  | "cover_letter"
  | "interview_session"
  | "skill_gap"
  | "evidence"
  | "text"
  | string;

export interface CopilotArtifact {
  type: ArtifactType;
  title?: string;
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

export interface CopilotAction {
  label: string;
  href?: string;
  kind?: string;
  payload?: Record<string, unknown>;
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
  evidence?: Evidence[];
}

export interface TailoredResult {
  resumeVersionId?: string | null;
  markdown?: string;
  text?: string;
  content?: string;
  sections?: { name?: string; bullets?: string[]; text?: string }[];
  notes?: string[];
  stats?: { added?: number; removed?: number; rewritten?: number; tokens?: number } & Record<
    string,
    unknown
  >;
  evidence?: Evidence[];
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

export interface AgentTrace {
  id: string;
  kind: string;
  label?: string;
  durationMs?: number;
  status?: string;
  payload?: Record<string, unknown>;
  createdAt?: string;
  tokens?: number;
  costUsd?: number;
}

export interface ActivityRun {
  id: string;
  agent?: string;
  kind?: string;
  summary?: string;
  status?: string;
  error?: string;
  model?: string | null;
  startedAt?: string;
  finishedAt?: string | null;
  createdAt?: string;
  durationMs?: number;
  tokensIn?: number;
  tokensOut?: number;
  costUsd?: number;
  traces?: AgentTrace[];
  relatedHref?: string | null;
}

export interface AIUsageSummary {
  requests?: number;
  tokensTotal?: number;
  tokensIn?: number;
  tokensOut?: number;
  costUsd?: number;
  byAgent?: { agent: string; requests?: number; tokens?: number; costUsd?: number }[];
  byModel?: { model: string; requests?: number; tokens?: number; costUsd?: number }[];
  daily?: { date: string; requests?: number; tokens?: number; costUsd?: number }[];
  updatedAt?: string;
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

export interface DashboardPayload {
  metrics?: DashboardMetrics;
  /** either {status: count} or [{status,count}] */
  pipeline?: Record<string, number> | { status: string; count: number }[];
  pipelineItems?: Application[];
  recommendedJobs?: Job[];
  skillGaps?: SkillGap[];
  resume?: (Pick<Resume, "id" | "title" | "status" | "currentVersionId"> & {
    score?: ResumeScore | number;
  }) | null;
  score?: ResumeScore | number | null;
  recentRuns?: ActivityRun[];
  activity?: ActivityRun[];
  suggestion?: string | null;
  aiSuggestion?: string | null;
  insights?: string[];
  attention?: { label?: string; href?: string; count?: number }[];
  greeting?: string | null;
  empty?: boolean;
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
