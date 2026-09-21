"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import {
  coverLetterText,
  normalizeMatch,
  normalizeTailor,
  pick,
  str,
} from "@/lib/api/normalize";
import { tokenStore } from "@/lib/api/token-store";
import type {
  Application,
  ApplicationStatus,
  CopilotReply,
  InterviewReport,
  InterviewQuestion,
  Job,
  JobMatch,
  KnowledgeNote,
  ParseResult,
  Resume,
  Suggestion,
  TailorResponse,
  TextIngestResult,
  UploadResult,
  User,
} from "@/lib/api/types";

/**
 * Mutation hooks: one place for the write side of the contract, so every
 * surface gets the same invalidation + toast behaviour. Optimistic updates are
 * used where the backend echo is guaranteed to be cheap (save toggle, kanban
 * moves) and are always rolled back on error.
 */

function describe(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.isNotFound) return "This endpoint isn't live on the backend yet.";
    return err.message || fallback;
  }
  if (err instanceof TypeError) return "Cannot reach the API — is the backend running?";
  return err instanceof Error && err.message ? err.message : fallback;
}

function fail(fallback: string) {
  return (err: unknown) => toast.error(describe(err, fallback));
}

/* ------------------------------------------------------------------ */
/* Resumes                                                             */
/* ------------------------------------------------------------------ */

export const RESUME_ACCEPT = [".pdf", ".docx", ".txt"];
export const RESUME_MAX_BYTES = 10 * 1024 * 1024;

export function validateResumeFile(file: File): string | null {
  const name = file.name.toLowerCase();
  const okExt = RESUME_ACCEPT.some((ext) => name.endsWith(ext));
  const okMime = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/msword",
  ].includes(file.type);
  if (!okExt && !okMime) return "Only PDF, DOCX or TXT files are supported.";
  if (file.size > RESUME_MAX_BYTES) return `File is larger than ${RESUME_MAX_BYTES / 1024 / 1024}MB.`;
  if (file.size === 0) return "That file looks empty.";
  return null;
}

export function useUploadResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.upload<UploadResult>(endpoints.resumeUpload, form);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resumes"] });
      toast.success("Uploaded — parsing your resume.");
    },
    onError: fail("Upload failed."),
  });
}

export function useParseResume(resumeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<ParseResult> =>
      (await api.request<ParseResult>(endpoints.resumeParse(resumeId), { method: "POST" })) ?? {},
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resume", resumeId] });
      qc.invalidateQueries({ queryKey: ["resumes"] });
      qc.invalidateQueries({ queryKey: ["knowledge", "sources"] });
    },
    onError: fail("Parsing failed."),
  });
}

export function useSetCurrentResume(resumeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (versionId: string) =>
      api.request<Resume>(endpoints.resumeSetCurrent(resumeId), {
        method: "POST",
        body: { versionId, version_id: versionId },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resume", resumeId] });
      qc.invalidateQueries({ queryKey: ["resumes"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Current version updated.");
    },
    onError: fail("Couldn't change the current version."),
  });
}

export function useDeleteResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => api.remove(endpoints.resume(id)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resumes"] });
      toast.success("Resume deleted.");
    },
    onError: fail("Delete failed."),
  });
}

/* ------------------------------------------------------------------ */
/* Jobs                                                                */
/* ------------------------------------------------------------------ */

export function useToggleSaveJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, saved }: { id: string; saved: boolean }) =>
      saved
        ? api.remove(endpoints.jobSave(id))
        : api.request<unknown>(endpoints.jobSave(id), { method: "POST" }),
    onMutate: async ({ id, saved }) => {
      await qc.cancelQueries({ queryKey: ["job", id] });
      const previous = qc.getQueryData<{ job: Job } | undefined>(["job", id]);
      if (previous) {
        qc.setQueryData(["job", id], { ...previous, job: { ...previous.job, saved: !saved } });
      }
      return { previous };
    },
    onError: (err, _v, ctx) => {
      if (ctx?.previous) qc.setQueryData(["job", _v.id], ctx.previous);
      fail("Couldn't update the saved list.")(err);
    },
    onSuccess: (_d, { saved }) =>
      toast.success(saved ? "Removed from saved jobs." : "Saved to your pipeline."),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["saved-jobs"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["job"] });
      qc.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

export function useRunJobMatch(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (resumeVersionId?: string | null): Promise<JobMatch | null> => {
      const raw = await api.request<unknown>(endpoints.jobMatch(jobId), {
        method: "POST",
        body: resumeVersionId ? { resumeVersionId, resume_version_id: resumeVersionId } : {},
      });
      return normalizeMatch(pick(raw, "match") ?? raw);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["job", jobId] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Match analysis complete.");
    },
    onError: fail("Match analysis failed."),
  });
}

export interface JdAnalysis {
  requiredSkills: string[];
  preferredSkills: string[];
  responsibilities: string[];
  interviewTopics: string[];
  skillGap: string[];
  suggestions: Suggestion[];
  hiddenRequirements: string[];
  raw: unknown;
}

export function useAnalyzeJd() {
  return useMutation({
    mutationFn: async (rawText: string): Promise<JdAnalysis> => {
      const raw = await api.create<unknown>(endpoints.jobJds, { raw_text: rawText, rawText });
      const body = pick(raw, "jd", "analysis", "data") ?? raw;
      const arr = (...keys: string[]) => {
        for (const k of keys) {
          const v = pick(body, k);
          if (Array.isArray(v)) return v.map((x) => String(typeof x === "object" ? (pick(x, "skill", "name", "text") ?? "") : x));
        }
        return [];
      };
      return {
        requiredSkills: arr("requiredSkills", "required_skills", "requirements"),
        preferredSkills: arr("preferredSkills", "preferred_skills", "nice_to_have", "niceToHave"),
        responsibilities: arr("responsibilities", "duties"),
        interviewTopics: arr("interviewTopics", "interview_topics", "topics"),
        skillGap: arr("skillGap", "skill_gap", "skillGaps", "gaps"),
        hiddenRequirements: arr("hiddenRequirements", "hidden_requirements"),
        suggestions: (pick(body, "suggestions", "resumeSuggestions", "resume_suggestions") ??
          []) as Suggestion[],
        raw,
      };
    },
    onError: fail("JD analysis failed."),
  });
}

/* ------------------------------------------------------------------ */
/* AI actions                                                          */
/* ------------------------------------------------------------------ */

export function useTailorResume(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (resumeVersionId?: string | null): Promise<TailorResponse> => {
      const raw = await api.request<unknown>(endpoints.aiTailor, {
        method: "POST",
        body: {
          job_id: jobId,
          jobId,
          ...(resumeVersionId ? { resume_version_id: resumeVersionId, resumeVersionId } : {}),
        },
      });
      return normalizeTailor(raw);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resumes"] });
      qc.invalidateQueries({ queryKey: ["resume", jobId] });
      qc.invalidateQueries({ queryKey: ["activity"] });
      toast.success("Tailored resume ready — review the diff before you export it.");
    },
    onError: fail("Tailoring failed."),
  });
}

export function useCoverLetter(jobId: string) {
  return useMutation({
    mutationFn: async (opts?: { resumeVersionId?: string | null; tone?: string; length?: string }) => {
      const raw = await api.request<unknown>(endpoints.aiCoverLetter, {
        method: "POST",
        body: {
          job_id: jobId,
          jobId,
          ...(opts?.resumeVersionId
            ? { resume_version_id: opts.resumeVersionId, resumeVersionId: opts.resumeVersionId }
            : {}),
          ...(opts?.tone ? { tone: opts.tone } : {}),
          ...(opts?.length ? { length: opts.length } : {}),
        },
      });
      return { text: coverLetterText(raw), evidence: raw, taskId: str(raw, "taskId", "task_id") };
    },
    onError: fail("Cover letter generation failed."),
  });
}

export function useResumeSuggestions() {
  return useMutation({
    mutationFn: async (body: { jdRaw: string; resumeVersionId?: string | null }) => {
      const raw = await api.request<unknown>(endpoints.aiSuggestions, {
        method: "POST",
        body: {
          jd_raw: body.jdRaw,
          jdRaw: body.jdRaw,
          ...(body.resumeVersionId
            ? { resume_version_id: body.resumeVersionId, resumeVersionId: body.resumeVersionId }
            : {}),
        },
      });
      const items = pick(raw, "suggestions", "items") ?? raw;
      return { raw, items: Array.isArray(items) ? items : [] };
    },
    onError: fail("Couldn't fetch suggestions."),
  });
}

/* ------------------------------------------------------------------ */
/* Applications                                                        */
/* ------------------------------------------------------------------ */

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Application> & { title: string }) =>
      api.create<Application>(endpoints.applications, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Added to your pipeline.");
    },
    onError: fail("Couldn't create the application."),
  });
}

/** PATCH {status, position, note} — optimistic across every list cached for it. */
export function useUpdateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: { status?: ApplicationStatus; position?: number; note?: string } }) =>
      api.update<Application>(endpoints.application(id), patch),
    onMutate: async ({ id, patch }) => {
      await qc.cancelQueries({ queryKey: ["applications"] });
      const previous = qc.getQueriesData<{ items: Application[] } | undefined>({
        queryKey: ["applications"],
      });
      qc.setQueriesData<{ items: Application[] } | undefined>({ queryKey: ["applications"] }, (cur) => {
        if (!cur?.items) return cur;
        return {
          ...cur,
          items: cur.items.map((a) => (a.id === id ? { ...a, ...patch } : a)),
        };
      });
      return { previous };
    },
    onError: (err, _v, ctx) => {
      ctx?.previous?.forEach(([key, data]) => qc.setQueryData(key, data));
      fail("Couldn't update that application.")(err);
    },
    onSuccess: (_d, { patch }) => {
      if (patch.note !== undefined) toast.success("Note saved.");
    },
    onSettled: (_d, err, vars) => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      if (!err && vars.patch.status) qc.invalidateQueries({ queryKey: ["application", vars.id, "events"] });
    },
  });
}

/** PUT /applications/{id}/reorder — final ordering after a drag drop. */
export function useReorderApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { id: string; status: ApplicationStatus; order: number }) =>
      api.request<unknown>(endpoints.applicationReorder(body.id), {
        method: "PUT",
        body: { status: body.status, order: body.order, position: body.order, index: body.order },
      }),
    onError: fail("Couldn't persist that move — the board was reverted."),
    onSettled: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });
}

export function useDeleteApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => api.remove(endpoints.application(id)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Removed from pipeline.");
    },
    onError: fail("Delete failed."),
  });
}

/* ------------------------------------------------------------------ */
/* Knowledge                                                           */
/* ------------------------------------------------------------------ */

export function useIngestText() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { title: string; text: string; kind?: string }) => {
      const raw = await api.request<TextIngestResult>(endpoints.knowledgeText, {
        method: "POST",
        body: { title: body.title, text: body.text, kind: body.kind ?? "note" },
      });
      return raw;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["knowledge"] });
      toast.success("Queued for ingestion.");
    },
    onError: fail("Ingest failed."),
  });
}

export function useNoteMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ["knowledge", "notes"] });
  return {
    create: useMutation({
      mutationFn: (body: { title: string; content: string }) =>
        api.create<KnowledgeNote>(endpoints.knowledgeNotes, body),
      onSuccess: () => {
        invalidate();
        toast.success("Note created.");
      },
      onError: fail("Couldn't save the note."),
    }),
    update: useMutation({
      mutationFn: (body: { id: string; title?: string; content?: string }) =>
        api.update<KnowledgeNote>(endpoints.knowledgeNote(body.id), {
          title: body.title,
          content: body.content,
        }),
      onSuccess: () => {
        invalidate();
        toast.success("Note updated.");
      },
      onError: fail("Couldn't update the note."),
    }),
    remove: useMutation({
      mutationFn: async (id: string) => api.remove(endpoints.knowledgeNote(id)),
      onSuccess: () => {
        invalidate();
        qc.invalidateQueries({ queryKey: ["knowledge", "sources"] });
        toast.success("Note deleted.");
      },
      onError: fail("Couldn't delete the note."),
    }),
  };
}

/* ------------------------------------------------------------------ */
/* Interviews                                                          */
/* ------------------------------------------------------------------ */

export function useCreateInterviewSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { jobId?: string; mode?: string; difficulty?: number }) =>
      api.create<{ id?: string; session?: { id: string }; session_id?: string }>(
        endpoints.interviews,
        body
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interview"] }),
    onError: fail("Couldn't start the interview."),
  });
}

export interface OpeningResponse {
  question: InterviewQuestion | null;
  raw: unknown;
}

export function useInterviewOpening(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<OpeningResponse> => {
      const raw = await api.request<unknown>(endpoints.interviewOpening(sessionId), { method: "POST" });
      const question = (pick(raw, "question", "opening", "next", "data") ?? raw) as Record<
        string,
        unknown
      >;
      return {
        question: {
          id: str(question, "id", "questionId", "question_id") ?? undefined,
          question: str(question, "question", "text", "prompt", "content") ?? "",
          topic: str(question, "topic", "category") ?? undefined,
          kind: str(question, "kind", "type") ?? "opening",
          difficulty: pick<number>(question, "difficulty", "depth", "level") ?? undefined,
        },
        raw,
      };
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interview", "session", sessionId] }),
    onError: fail("Couldn't fetch the opening question."),
  });
}

export interface AnswerResponse {
  evaluation: {
    score?: number;
    strengths: string[];
    weaknesses: string[];
    missing: string[];
    betterAnswer?: string;
    feedback?: string;
    dims: { key: string; label: string; score: number }[];
    trajectory: { question?: string; score?: number; depth?: number }[];
  };
  next: InterviewQuestion | null;
  raw: unknown;
}

export function useSubmitInterviewAnswer(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (answer: string): Promise<AnswerResponse> => {
      const raw = await api.request<unknown>(endpoints.interviewAnswer(sessionId), {
        method: "POST",
        body: { answer },
      });
      const ev = (pick(raw, "evaluation", "result") ?? raw) as Record<string, unknown>;
      const nx = (pick(raw, "next", "question", "nextQuestion", "next_question") ?? null) as Record<
        string,
        unknown
      > | null;
      const arr = (...keys: string[]) => {
        for (const k of keys) {
          const v = pick(ev, k);
          if (Array.isArray(v)) return v.map((x) => String(typeof x === "object" ? (pick(x, "text", "point", "item", "label") ?? "") : x));
        }
        return [];
      };
      return {
        evaluation: {
          score: pick<number>(ev, "score", "overall") ?? undefined,
          strengths: arr("strengths", "what_went_well", "whatWentWell", "good"),
          weaknesses: arr("weaknesses", "what_was_weak", "whatWasWeak", "weak"),
          missing: arr("missing", "missing_concepts", "missingConcepts", "gaps"),
          betterAnswer: str(ev, "better_answer", "betterAnswer", "improved", "model_answer"),
          feedback: str(ev, "feedback", "comment", "summary"),
          dims: normalizeDimsList(ev),
          trajectory: (pick(ev, "trajectory", "depth_trajectory", "depthTrajectory") ?? []) as {
            question?: string;
            score?: number;
            depth?: number;
          }[],
        },
        next: nx
          ? {
              id: str(nx, "id", "questionId", "question_id") ?? undefined,
              question: str(nx, "question", "text", "prompt", "content") ?? "",
              topic: str(nx, "topic", "category") ?? undefined,
              kind: str(nx, "kind", "type", "nextAction", "next_action") ?? undefined,
              difficulty: pick<number>(nx, "difficulty", "depth", "level") ?? undefined,
            }
          : null,
        raw,
      };
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interview", "session", sessionId] }),
    onError: fail("Couldn't evaluate that answer."),
  });
}

function normalizeDimsList(ev: unknown): { key: string; label: string; score: number }[] {
  const dims = pick(ev, "dims", "dimensions", "scores");
  const out: { key: string; label: string; score: number }[] = [];
  if (Array.isArray(dims)) {
    for (const d of dims) {
      const score = pick<number>(d, "score", "value");
      if (typeof score === "number")
        out.push({
          key: String(pick(d, "key", "name", "dimension") ?? `dim-${out.length}`),
          label: String(pick(d, "label", "name", "title") ?? "Score"),
          score: score <= 1 ? score * 100 : score,
        });
    }
  } else if (dims && typeof dims === "object") {
    for (const [k, v] of Object.entries(dims as Record<string, unknown>)) {
      const score = typeof v === "number" ? v : pick<number>(v, "score", "value");
      if (typeof score === "number")
        out.push({
          key: k,
          label: String(pick(v, "label", "name") ?? k.replace(/_/g, " ")),
          score: score <= 1 ? score * 100 : score,
        });
    }
  }
  return out;
}

export function useFinalizeInterview(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<InterviewReport> => {
      const raw = await api.request<unknown>(endpoints.interviewFinalize(sessionId), {
        method: "POST",
      });
      const r = (pick(raw, "evaluation", "report", "data") ?? raw) as Record<string, unknown>;
      return {
        sessionId,
        dims: normalizeDimsList(r),
        overall: pick<number>(r, "overall", "score", "overallScore") ?? undefined,
        whatWentWell: (pick(r, "what_went_well", "whatWentWell", "strengths", "well") ?? []) as string[],
        whatWasWeak: (pick(r, "what_was_weak", "whatWasWeak", "weaknesses", "weak") ?? []) as string[],
        studyMaterials: (pick(r, "study", "studyMaterials", "study_materials", "materials") ??
          []) as InterviewReport["studyMaterials"],
        trajectory: (pick(r, "trajectory", "depth_trajectory", "depthTrajectory") ??
          []) as InterviewReport["trajectory"],
        summary: str(r, "summary", "comment"),
      };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["interview"] });
      toast.success("Interview report is ready.");
    },
    onError: fail("Couldn't finalize the interview."),
  });
}

/* ------------------------------------------------------------------ */
/* Copilot                                                             */
/* ------------------------------------------------------------------ */

export function useCreateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (title?: string) =>
      api.create<{ id: string; title?: string }>(endpoints.conversations, { title: title ?? "New chat" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
    onError: fail("Couldn't start a conversation."),
  });
}

export function useCopilotChat() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      message: string;
      conversationId?: string | null;
      context?: Record<string, unknown>;
    }): Promise<CopilotReply> => {
      const raw = await api.request<unknown>(endpoints.copilotChat, {
        method: "POST",
        body: {
          message: body.message,
          ...(body.conversationId ? { conversation_id: body.conversationId, conversationId: body.conversationId } : {}),
          context: body.context ?? {},
        },
      });
      return {
        answer: str(raw, "answer", "content", "text", "message", "reply") ?? "",
        artifacts: (pick(raw, "artifacts") ?? []) as CopilotReply["artifacts"],
        sources: (pick(raw, "sources", "citations") ?? []) as CopilotReply["sources"],
        actions: (pick(raw, "actions") ?? []) as CopilotReply["actions"],
        runId: str(raw, "runId", "run_id") ?? null,
        taskId: str(raw, "taskId", "task_id") ?? null,
        conversationId: str(raw, "conversationId", "conversation_id") ?? body.conversationId ?? null,
      };
    },
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
      if (vars.conversationId)
        qc.invalidateQueries({ queryKey: ["conversation", vars.conversationId, "messages"] });
      qc.invalidateQueries({ queryKey: ["activity"] });
    },
    onError: fail("Copilot couldn't answer."),
  });
}

/* ------------------------------------------------------------------ */
/* Profile                                                             */
/* ------------------------------------------------------------------ */

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: { displayName?: string; email?: string; avatarUrl?: string | null }) => {
      const primary = await api.request<User>(endpoints.auth.me, {
        method: "PATCH",
        body: patch,
      });
      return primary;
    },
    onSuccess: (user) => {
      qc.setQueryData(["me"], user);
      qc.invalidateQueries({ queryKey: ["me"] });
      qc.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Profile saved.");
    },
    onError: (err) => {
      // Older/newer backends expose the writable copy under /users/me/profile.
      toast.error(describe(err, "Couldn't save your profile."));
    },
  });
}

export function useUpdateProfileDetails() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: Record<string, unknown>) =>
      api.update<unknown>(endpoints.auth.profile, patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Career profile saved.");
    },
    onError: fail("Couldn't save your career profile."),
  });
}

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => (await api.get<unknown>(endpoints.auth.profile)) ?? null,
  });
}

/* ------------------------------------------------------------------ */
/* Session helper                                                      */
/* ------------------------------------------------------------------ */

export function hasSession(): boolean {
  return tokenStore.hasSession();
}
