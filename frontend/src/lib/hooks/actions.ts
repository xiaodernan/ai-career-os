"use client";

import { useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, ApiError, postSSE } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { field } from "@/lib/api/body";
import {
  coverLetterText,
  normalizeArtifacts,
  normalizeChatActions,
  normalizeEvidence,
  normalizeInterviewReport,
  normalizeJdParsed,
  normalizeMatch,
  normalizeNextQuestion,
  normalizeQuestion,
  normalizeSuggestions,
  normalizeTailor,
  normalizeTrajectory,
  tailorSaveBody,
  num,
  pct,
  pick,
  str,
} from "@/lib/api/normalize";
import { tokenStore } from "@/lib/api/token-store";
import { translate, useLocale } from "@/lib/i18n/locale-context";
import type {
  Application,
  ApplicationStatus,
  Contact,
  CopilotReply,
  GrowthReport,
  InterviewQuestion,
  Job,
  JobMatch,
  KnowledgeNote,
  MemoryItem,
  ParseResult,
  Resume,
  SavedSearchCriteria,
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

/**
 * The failure handler lives in `lib/hooks/failure.ts` — one implementation of
 * "what a failed write says to the user", shared by every mutation hook in the
 * product. It is imported (not just re-exported) so this file's own callers
 * keep the name they have always used.
 */
import { describe, fail } from "./failure";

export { describe, fail };

/* ------------------------------------------------------------------ */
/* Resumes                                                             */
/* ------------------------------------------------------------------ */

export const RESUME_ACCEPT = [".pdf", ".docx", ".txt"];
export const RESUME_MAX_BYTES = 10 * 1024 * 1024;

/**
 * Why a picked file was refused, as a code rather than a sentence.
 *
 * The dropzone shows this refusal twice -- inline under the box and in a toast
 * -- and a Chinese reader was shown an English sentence both times. The words
 * belong to the screen, which owns the reader's language; this module only
 * knows the three things that can be wrong with a file.
 */
export type ResumeFileProblem = "unsupported" | "too-large" | "empty";

export function validateResumeFile(file: File): ResumeFileProblem | null {
  const name = file.name.toLowerCase();
  const okExt = RESUME_ACCEPT.some((ext) => name.endsWith(ext));
  const okMime = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/msword",
  ].includes(file.type);
  if (!okExt && !okMime) return "unsupported";
  if (file.size > RESUME_MAX_BYTES) return "too-large";
  if (file.size === 0) return "empty";
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
      toast.success(translate("toasts.resumeUploaded"));
    },
    onError: fail("failures.upload"),
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
    onError: fail("failures.parse"),
  });
}

export function useSetCurrentResume(resumeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (versionId: string) =>
      api.request<Resume>(endpoints.resumeSetCurrent(resumeId), {
        method: "POST",
        body: field("versionId", versionId),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resume", resumeId] });
      qc.invalidateQueries({ queryKey: ["resumes"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(translate("toasts.resumeCurrent"));
    },
    onError: fail("failures.versionSwitch"),
  });
}

export function useDeleteResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => api.remove(endpoints.resume(id)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resumes"] });
      toast.success(translate("toasts.resumeDeleted"));
    },
    onError: fail("failures.resumeDelete"),
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
      fail("failures.savedListUpdate")(err);
    },
    onSuccess: (_d, { saved }) =>
      toast.success(
        saved ? translate("toasts.savedJobRemoved") : translate("toasts.jobSavedToPipeline")
      ),
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
        body: field("resumeVersionId", resumeVersionId),
      });
      return normalizeMatch(pick(raw, "match") ?? raw);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["job", jobId] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(translate("toasts.matchComplete"));
    },
    onError: fail("failures.matchAnalysis"),
  });
}

export interface JdAnalysis {
  requiredSkills: string[];
  preferredSkills: string[];
  responsibilities: string[];
  interviewTopics: string[];
  hiddenRequirements: string[];
  raw: unknown;
}

export function useAnalyzeJd() {
  return useMutation({
    mutationFn: async (rawText: string): Promise<JdAnalysis> => {
      // `POST /jds` answers a JdItem and nothing else: no gap and no suggestion can come out of an
      // analysis, which is why the dialog calls /jds/suggestions for those two cards itself (#143).
      const raw = await api.create<unknown>(endpoints.jdAnalyze, { rawText });
      return { ...normalizeJdParsed(raw), raw };
    },
    onError: fail("failures.jdAnalysis"),
  });
}

/**
 * Paste a posting in: the backend runs the JD analyst once and lands the job (company, skills,
 * responsibilities, its own JD row) in the tracker. 201 answers a JobListItem - the id is what
 * the caller needs to jump to the new detail page.
 */
export function useImportJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { rawText: string; url?: string }): Promise<{ id?: string }> =>
      api.create<unknown>(endpoints.jobsImport, {
        rawText: body.rawText,
        url: body.url,
      }) as Promise<{ id?: string }>,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(translate("toasts.jobImported"));
    },
    onError: fail("import.runFailed"),
  });
}

/* ------------------------------------------------------------------ */
/* Saved searches                                                      */
/* ------------------------------------------------------------------ */

/** Keep the board's current question under a name (roadmap 19.1). */
export function useCreateSavedSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; criteria: SavedSearchCriteria }) =>
      api.create<unknown>(endpoints.savedSearches, {
        name: body.name,
        criteria: body.criteria,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saved-searches"] });
      toast.success(translate("savedSearches.savedToast"));
    },
    onError: fail("savedSearches.saveFailed"),
  });
}

export function useDeleteSavedSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.remove(endpoints.savedSearch(id)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saved-searches"] });
      toast.success(translate("savedSearches.deletedToast"));
    },
    onError: fail("savedSearches.deleteFailed"),
  });
}

/* ------------------------------------------------------------------ */
/* AI actions                                                          */
/* ------------------------------------------------------------------ */

/** The server response is kept alongside the view because saving a draft posts it back verbatim. */
export type TailorRun = TailorResponse & { raw: unknown };

export function useTailorResume(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (resumeVersionId?: string | null): Promise<TailorRun> => {
      const raw = await api.request<unknown>(endpoints.jobTailor(jobId), {
        method: "POST",
        body: field("resumeVersionId", resumeVersionId),
      });
      return { ...normalizeTailor(raw), raw };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resumes"] });
      qc.invalidateQueries({ queryKey: ["activity"] });
      toast.success(translate("toasts.resumeTailored"));
    },
    onError: fail("tailor.failed"),
  });
}

/**
 * Keeps a reviewed draft as a version of the resume it was tailored from. The structured body
 * is posted back verbatim (not the rendered markdown) because the version's experience,
 * project and skill rows are projected from it server-side.
 */
export function useSaveTailoredVersion(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (draft: {
      raw: unknown;
      plaintext: string;
      resumeVersionId?: string | null;
    }): Promise<unknown> =>
      api.request<unknown>(endpoints.jobTailoredVersion(jobId), {
        method: "POST",
        body: tailorSaveBody(draft),
      }),
    onSuccess: () => {
      // ["resume"] covers every detail cache and every versions list.
      qc.invalidateQueries({ queryKey: ["resume"] });
      qc.invalidateQueries({ queryKey: ["resumes"] });
    },
    onError: fail("failures.draftVersionSave"),
  });
}

/**
 * 19.5 — one saved version as a print-ready document. The HTML is built by the
 * renderer (the export's print chrome, the reader's section words), so the
 * window it opens is the same document the bundle export prints and the
 * browser's own "save as PDF" is the PDF. The version's content is read on the
 * server: no client-facing read returns a version's body.
 */
export function usePrintResumeVersion() {
  const { locale } = useLocale();
  return useMutation({
    mutationFn: async (versionId: string): Promise<string> => {
      // Opened before the request, while the click is still the gesture: a
      // window opened after the await is the popup blocker's to refuse.
      const win = window.open("", "_blank");
      try {
        const raw = await api.request<unknown>(endpoints.resumeVersionPrint(versionId), {
          method: "POST",
          body: { locale },
        });
        const html = str(raw, "html") ?? "";
        if (!html) throw new Error(translate("failures.rendererEmpty") ?? "failures.rendererEmpty");
        if (!win) {
          toast.error(translate("resumes.printBlocked") ?? "resumes.printBlocked");
          return html;
        }
        win.document.write(html);
        win.document.close();
        win.focus();
        return html;
      } catch (error) {
        win?.close();
        throw error;
      }
    },
    onError: fail("failures.printView"),
  });
}

export function useCoverLetter(jobId: string) {
  return useMutation({
    mutationFn: async (opts?: { resumeVersionId?: string | null; tone?: string; length?: string }) => {
      const raw = await api.request<unknown>(endpoints.jobCoverLetter(jobId), {
        method: "POST",
        body: {
          ...field("resumeVersionId", opts?.resumeVersionId),
          ...field("tone", opts?.tone),
          ...field("length", opts?.length),
        },
      });
      // `letter` is the one name `generate` answers for the text; `taskId` is not among them, so the
      // panel gets no stream affordance it could not open -- the same correction #98 made for tailor.
      return { text: coverLetterText(raw), evidence: raw };
    },
    onError: fail("failures.coverLetter"),
  });
}

export function useResumeSuggestions() {
  return useMutation({
    mutationFn: async (body: { jdRaw: string; resumeVersionId?: string | null }) => {
      const raw = await api.request<unknown>(endpoints.jdSuggestions, {
        method: "POST",
        body: {
          jdRaw: body.jdRaw,
          ...field("resumeVersionId", body.resumeVersionId),
        },
      });
      const suggestions = normalizeSuggestions(raw);
      return { raw, suggestions };
    },
    onError: fail("failures.suggestionsFetch"),
  });
}

/* ------------------------------------------------------------------ */
/* Applications                                                        */
/* ------------------------------------------------------------------ */

/**
 * The create body, named the way `CreateApplicationRequest` binds it — the note is `notes`
 * (plural) here and `note` on the update route. Jackson drops the spelling a record does not
 * declare, silently, so the body is declared instead of spread from an `Application` row.
 */
export interface CreateApplicationBody {
  title: string;
  companyName?: string;
  status?: ApplicationStatus;
  notes?: string;
  reminderAt?: string;
  jobId?: string;
  companyId?: string;
}

/** The PATCH body: `note` singular, and the reminder pair (a null component means "leave it"). */
export interface UpdateApplicationBody {
  status?: ApplicationStatus;
  position?: number;
  note?: string;
  reminderAt?: string;
  clearReminderAt?: boolean;
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateApplicationBody) =>
      api.create<Application>(endpoints.applications, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(translate("toasts.addedToPipeline"));
    },
    onError: fail("failures.applicationCreate"),
  });
}

/**
 * The cached row as it reads once this command has been applied to it.
 *
 * `clearReminderAt` is a command, not a column: `UpdateApplicationRequest` has no `reminderAt`
 * component that can be sent as null — a null component there means "leave it alone" — so the only
 * way a removal can reach the cache is by naming the field it removes. Spreading the command alone
 * leaves the old instant on the row, and the board card both draws its chip from `app.reminderAt`
 * and decides `overdue` from it, so the cleared reminder stays on screen until the settled refetch.
 */
export function optimisticApplicationRow(row: Application, patch: UpdateApplicationBody): Application {
  return { ...row, ...patch, ...(patch.clearReminderAt ? { reminderAt: null } : null) };
}

/** PATCH {status, position, note} — optimistic across every list cached for it. */
export function useUpdateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: UpdateApplicationBody }) =>
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
          items: cur.items.map((a) => (a.id === id ? optimisticApplicationRow(a, patch) : a)),
        };
      });
      return { previous };
    },
    onError: (err, _v, ctx) => {
      ctx?.previous?.forEach(([key, data]) => qc.setQueryData(key, data));
      fail("failures.applicationUpdate")(err);
    },
    onSuccess: (_d, { patch }) => {
      if (patch.note !== undefined) toast.success(translate("toasts.applicationNoteSaved"));
      else if (patch.reminderAt !== undefined) toast.success(translate("toasts.reminderSet"));
      else if (patch.clearReminderAt) toast.success(translate("toasts.reminderCleared"));
    },
    onSettled: (_d, err, vars) => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      // The inbox lists the same reminder as a row of its own, so a reminder moved or cleared
      // from the attention card must not leave the old copy standing there until a reload.
      if (!err && (vars.patch.reminderAt !== undefined || vars.patch.clearReminderAt))
        qc.invalidateQueries({ queryKey: ["notifications"] });
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
        // ReorderRequest binds exactly these two; the extra spellings this call used to post were
        // dropped by Jackson on every drag.
        body: { status: body.status, position: body.order },
      }),
    // Without this the card snapped back to its old column until the refetch landed, and the
    // error copy below promised a rollback that never happened.
    onMutate: async ({ id, status, order }) => {
      await qc.cancelQueries({ queryKey: ["applications"] });
      const previous = qc.getQueriesData<{ items: Application[] } | undefined>({
        queryKey: ["applications"],
      });
      qc.setQueriesData<{ items: Application[] } | undefined>({ queryKey: ["applications"] }, (cur) => {
        if (!cur?.items) return cur;
        return {
          ...cur,
          items: cur.items.map((a) => (a.id === id ? { ...a, status, position: order } : a)),
        };
      });
      return { previous };
    },
    onError: (err, _v, ctx) => {
      ctx?.previous?.forEach(([key, data]) => qc.setQueryData(key, data));
      fail("failures.applicationMove")(err);
    },
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
      toast.success(translate("toasts.removedFromPipeline"));
    },
    onError: fail("failures.applicationDelete"),
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
      toast.success(translate("toasts.queuedForIngestion"));
    },
    onError: fail("failures.ingest"),
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
        toast.success(translate("toasts.knowledgeNoteCreated"));
      },
      onError: fail("failures.noteSave"),
    }),
    update: useMutation({
      mutationFn: (body: { id: string; title?: string; content?: string }) =>
        api.update<KnowledgeNote>(endpoints.knowledgeNote(body.id), {
          title: body.title,
          content: body.content,
        }),
      onSuccess: () => {
        invalidate();
        toast.success(translate("toasts.knowledgeNoteUpdated"));
      },
      onError: fail("failures.noteUpdate"),
    }),
    remove: useMutation({
      mutationFn: async (id: string) => api.remove(endpoints.knowledgeNote(id)),
      onSuccess: () => {
        invalidate();
        qc.invalidateQueries({ queryKey: ["knowledge", "sources"] });
        toast.success(translate("toasts.knowledgeNoteDeleted"));
      },
      onError: fail("failures.noteDelete"),
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
    onError: fail("failures.interviewStart"),
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
      // The turn the opening POST persisted is an interviewer `TurnItem`, and the session page's other
      // question path (`SessionDetail.turns`) is the same row -- so both go through `normalizeQuestion`,
      // which the contract gate binds to that record and to its `questionMeta`. The twelve candidates this
      // body used to try (`questionId`, `question`/`text`/`prompt`, `category`, `type`, `difficulty`,
      // `depth`, `level`, plus an `"opening"` default for a kind the wire calls `action`) had no author;
      // `difficulty` in particular has one table that owns it -- the session, not the turn.
      const q = normalizeQuestion(pick(raw, "question"));
      return {
        question: q && { id: q.id, text: q.text, topic: q.topic, kind: q.kind },
        raw,
      };
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interview", "session", sessionId] }),
    onError: fail("failures.openingQuestion"),
  });
}

export interface AnswerResponse {
  evaluation: {
    /** 0–100 — the same scale the report page uses, because both feed one renderer. */
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

/**
 * POST /interview/sessions/{id}/answer → {@link AnswerResponse}. Split out so the scale
 * coercion below is testable without a renderer, and so the report path
 * (`normalizeInterviewReport`) has a named sibling to be checked against.
 */
export function normalizeAnswerResponse(raw: unknown): AnswerResponse {
  const ev = (pick(raw, "evaluation", "result") ?? raw) as Record<string, unknown>;
  // `next` is the only spelling: those five are `AnswerResponse`'s components, and the relay passes the
  // advance decision through under that one name.
  const nx = pick(raw, "next") as Record<string, unknown> | null;
  const arr = (...keys: string[]) => {
    for (const k of keys) {
      const v = pick(ev, k);
      if (Array.isArray(v)) return v.map((x) => String(typeof x === "object" ? (pick(x, "text", "point", "item", "label") ?? "") : x));
    }
    return [];
  };
  return {
    evaluation: {
      // The evaluator answers in 0..1 (the ai-service prompt asks for it and its fallback is
      // 0.5), while the badge on the other end compares against 75/50 and prints "/100".
      score: pct(num(ev, "score", "overall")),
      strengths: arr("strengths", "what_went_well", "whatWentWell", "good"),
      weaknesses: arr("weaknesses", "what_was_weak", "whatWasWeak", "weak"),
      missing: arr("missing", "missing_concepts", "missingConcepts", "gaps"),
      betterAnswer: str(ev, "better_answer", "betterAnswer", "improved", "model_answer"),
      feedback: str(ev, "feedback", "comment", "summary"),
      dims: normalizeDimsList(ev),
      // One shared fold with normalizeInterviewReport, so the live turn and the report
      // of that turn cannot disagree about what the user scored — and cannot drift on
      // which key names carry the rows (this call used to miss "trajectory_detail").
      trajectory: normalizeTrajectory(ev),
    },
    // The next question is read by the mapper the contract gate binds to `decide_next`, so the one
    // name the page branches on -- `action` -> `kind` -- is the wire's and not a guess.
    next: nx ? normalizeNextQuestion(nx) : null,
    raw,
  };
}

export function useSubmitInterviewAnswer(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (answer: string): Promise<AnswerResponse> => {
      const raw = await api.request<unknown>(endpoints.interviewAnswer(sessionId), {
        method: "POST",
        body: { answer },
      });
      return normalizeAnswerResponse(raw);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interview", "session", sessionId] }),
    onError: fail("failures.answerEvaluate"),
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
    mutationFn: async () => {
      const raw = await api.request<unknown>(endpoints.interviewFinalize(sessionId), {
        method: "POST",
      });
      // The report page renders via normalizeInterviewReport on the fresh GET
      // (persistFinalization stores the summary under what_you_did_well /
      // recommended_study and trajectory_detail); reuse that same canonical
      // mapping here so the two paths can never drift.
      return { sessionId, report: normalizeInterviewReport(pick(raw, "evaluation", "report") ?? raw) };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["interview"] });
      toast.success(translate("toasts.interviewReportReady"));
    },
    onError: fail("failures.interviewFinalize"),
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
    onError: fail("failures.conversationStart"),
  });
}

/** The backend leaves a blank or absent title alone (`!isBlank()`), so an edit never blanks it. */
export function useRenameConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      api.update<unknown>(endpoints.conversation(id), { title }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
      toast.success(translate("toasts.conversationRenamed"));
    },
    onError: fail("failures.conversationRename"),
  });
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.remove(endpoints.conversation(id)),
    onSuccess: (_data, id) => {
      // The transcript of a deleted chat is unreachable — drop its cache rather than
      // invalidating a query whose source row no longer exists.
      qc.removeQueries({ queryKey: ["conversation", id] });
      qc.invalidateQueries({ queryKey: ["conversations"] });
      toast.success(translate("toasts.conversationDeleted"));
    },
    onError: fail("failures.conversationDelete"),
  });
}

/** What the copilot's stream reports while the agent is still working. */
export interface CopilotStreamHandlers {
  /** One model delta: append it and the reply grows on screen. */
  onToken?: (token: string) => void;
  /** `{agent, step}` from the turn itself — "Thinking", "Calling search_jobs". */
  onStatus?: (status: { agent?: string; step?: string }) => void;
}

export function useCopilotChat(stream: CopilotStreamHandlers = {}) {
  const qc = useQueryClient();
  // The mutation has to keep one identity across renders, so the handlers a page passes inline
  // live in a ref and are read when a frame arrives, not when the hook is called.
  const streamRef = useRef(stream);
  streamRef.current = stream;
  return useMutation({
    mutationFn: async (body: {
      message: string;
      conversationId?: string | null;
      context?: Record<string, unknown>;
    }): Promise<CopilotReply> => {
      let raw: unknown;
      try {
        raw = await postSSE<unknown>(
          endpoints.copilotChatStream,
          {
            method: "POST",
            body: {
              message: body.message,
              ...field("conversationId", body.conversationId),
              context: body.context ?? {},
            },
          },
          {
            onToken: (token) => streamRef.current.onToken?.(token),
            onStatus: (data) => {
              const agent = typeof data.agent === "string" ? data.agent : undefined;
              const step = typeof data.step === "string" ? data.step : undefined;
              if (agent || step) streamRef.current.onStatus?.({ agent, step });
            },
          },
        );
      } catch (err) {
        // A backend that has not shipped the stream route still serves the blocking one, and the
        // turn has to happen either way — a 404 is the only failure that means "not served here".
        if (!(err instanceof ApiError && err.status === 404)) throw err;
        raw = await api.request<unknown>(endpoints.copilotChat, {
          method: "POST",
          body: {
            message: body.message,
            ...field("conversationId", body.conversationId),
            context: body.context ?? {},
          },
        });
      }
      return {
        answer: str(raw, "answer", "content", "text", "message", "reply") ?? "",
        artifacts: normalizeArtifacts(raw),
        sources: normalizeEvidence(pick(raw, "sources")),
        actions: normalizeChatActions(raw),
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
    onError: fail("copilot.couldNotAnswer"),
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
      toast.success(translate("toasts.profileSaved"));
    },
    onError: (err) => {
      // Older/newer backends expose the writable copy under /users/me/profile.
      toast.error(describe(err, "failures.profileSave"));
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
      toast.success(translate("toasts.careerProfileSaved"));
    },
    onError: fail("failures.careerProfileSave"),
  });
}

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => (await api.get<unknown>(endpoints.auth.profile)) ?? null,
  });
}

/* ------------------------------------------------------------------ */
/* Long-term memory (AGENTS.md §6)                                     */
/* ------------------------------------------------------------------ */

/**
 * Correct one memory's text, or lower its weight.
 *
 * Either field, for the reason the endpoint allows either: a wrong fact needs its content
 * fixed, a fact the user is tired of being told about only needs its importance lowered, and
 * forcing both would make the second caller invent new content. The list is invalidated
 * rather than optimistically patched, because the row it writes back is the ai-service's own
 * answer and is the only authoritative copy there is.
 */
export function useUpdateMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, content, importance }: { id: string; content?: string; importance?: number }) =>
      // A literal rather than a built map: `JSON.stringify` drops an `undefined` value, so
      // only the field the caller actually passed reaches the wire. The two are independent
      // corrections — fix the text, or lower the weight — and this says so without a helper
      // the endpoint-parity reader cannot follow.
      api.update<MemoryItem>(endpoints.memory(id), { content, importance }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memories"] });
      toast.success(translate("toasts.memoryUpdated"));
    },
    onError: fail("failures.memoryUpdate"),
  });
}

/** Forget one memory. This is the only exit from a fact the extractor got wrong. */
export function useDeleteMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => api.remove(endpoints.memory(id)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memories"] });
      toast.success(translate("toasts.memoryForgotten"));
    },
    onError: fail("failures.memoryForget"),
  });
}

/* ------------------------------------------------------------------ */
/**
 * The registry's three writes (roadmap 11.1). The PATCH is a full replace — the form
 * posts its current values, so a field the caller blanked is cleared on purpose — and
 * every one of them invalidates the single list key, because the list is the only
 * reader of this surface.
 */
export function useCreateContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ContactDraftBody) =>
      api.create<unknown>(endpoints.contacts, contactBody(body)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
      toast.success(translate("toasts.contactSaved"));
    },
    onError: fail("failures.contactSave"),
  });
}

export function useUpdateContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: ContactDraftBody & { id: string }) =>
      api.update<unknown>(endpoints.contact(id), contactBody(body)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
      toast.success(translate("toasts.contactUpdated"));
    },
    onError: fail("failures.contactUpdate"),
  });
}

export function useDeleteContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.remove(endpoints.contact(id)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
      toast.success(translate("toasts.contactDeleted"));
    },
    onError: fail("failures.contactDelete"),
  });
}

/** What the registry's forms post: the editable fields, none of the row's own. */
type ContactDraftBody = Omit<Contact, "id" | "createdAt" | "updatedAt">;

/**
 * The wire body: only the fields the form carries, with blanks as absence — a JSON
 * null and a missing key are the same to the record, and an empty string would come
 * back as an empty string.
 */
function contactBody(body: ContactDraftBody): Record<string, unknown> {
  const out: Record<string, unknown> = { name: body.name.trim() };
  for (const key of ["role", "company", "relation", "email", "notes"] as const) {
    const v = body[key]?.trim();
    if (v) out[key] = v;
  }
  if (body.lastTouchAt) out.lastTouchAt = body.lastTouchAt;
  return out;
}

/**
 * The growth page's one call (roadmap 10.3): a target role in, the composed report
 * out. Deliberately a mutation rather than a query — the request carries the caller's
 * target and the prior report to diff against, so what comes back is an answer to a
 * question the user just asked, not a view of state the server holds. The report is
 * computed, not stored (10.4 will change that), so there is nothing to invalidate:
 * the panel keeps the answer in its own state and hands it back as `previous`.
 */
export function useGrowthReport() {
  return useMutation({
    mutationFn: async (body: {
      targetRole: string;
      seniority?: string;
      location?: string;
      currency?: string;
      targetSalary?: number;
      previous?: unknown;
    }): Promise<GrowthReport> =>
      (await api.request<GrowthReport>(endpoints.growthReport, {
        method: "POST",
        body,
      })) ?? {},
    onError: fail("failures.growthReport"),
  });
}

/* Session helper                                                      */
/* ------------------------------------------------------------------ */

export function hasSession(): boolean {
  return tokenStore.hasSession();
}
