/** Domain types mirroring docs/architecture.md §4. */

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

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface Resume {
  id: string;
  title: string;
  status: "uploaded" | "parsing" | "parsed" | "failed";
  currentVersionId?: string | null;
  createdAt?: string;
}

export interface Job {
  id: string;
  companyId: string;
  company?: Pick<Company, "id" | "name" | "logoUrl">;
  title: string;
  location?: string | null;
  remoteType?: string | null;
  salaryMin?: number | null;
  salaryMax?: number | null;
  salaryCurrency?: string | null;
  skills?: string[];
  status: "open" | "closed";
  source: "seed" | "user_paste" | "agent_research";
  externalUrl?: string | null;
}

export interface Company {
  id: string;
  name: string;
  website?: string | null;
  logoUrl?: string | null;
  industry?: string | null;
  size?: string | null;
  techStack?: string[];
}

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
  companyId: string;
  company?: Pick<Company, "id" | "name" | "logoUrl">;
  title: string;
  status: ApplicationStatus;
  reminderAt?: string | null;
  updatedAt?: string;
}

export interface JobMatch {
  id: string;
  jobId: string;
  overall: number;
  technical?: number;
  experience?: number;
  projects?: number;
  education?: number;
  matchedSkills?: string[];
  missingSkills?: string[];
}

export interface Evidence {
  criterion: string;
  score?: number;
  chunkIds?: string[];
  quote: string;
  reasoning?: string;
  source?: { docTitle?: string; path?: string[] };
}

export interface KnowledgeSource {
  id: string;
  kind: string;
  title: string;
  status: "pending" | "ingesting" | "ready" | "failed";
  error?: string | null;
}

export interface InterviewSession {
  id: string;
  jobId?: string | null;
  mode: string;
  status: "active" | "paused" | "completed" | "abandoned";
  difficulty?: number;
  startedAt?: string;
  finishedAt?: string | null;
}

export interface Conversation {
  id: string;
  title: string;
  updatedAt?: string;
  lastMessagePreview?: string;
}

export interface ActivityEvent {
  id: string;
  agent?: string;
  kind: string;
  summary?: string;
  status?: string;
  createdAt: string;
}

export interface DashboardMetrics {
  applications?: number;
  interviews?: number;
  offers?: number;
  avgMatch?: number;
  [key: string]: number | undefined;
}

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
  kind: "step_start" | "tool_call" | "tool_result" | "llm_call" | "retrieval" | "rerank" | "handoff" | "message" | "final";
  label?: string;
  durationMs?: number;
  payload?: Record<string, unknown>;
  [key: string]: unknown;
}

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
