"use client";

import * as React from "react";
import { FileUp, TriangleAlert, Upload } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { TaskProgress } from "@/components/ai/task-stream";
import { pickResumeId, pickTaskId } from "@/lib/resume-upload";
import { ingestSeed } from "@/lib/ingest-steps";
import {
  RESUME_ACCEPT,
  RESUME_MAX_BYTES,
  validateResumeFile,
  useUploadResume,
  type ResumeFileProblem,
} from "@/lib/hooks/actions";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * The sentence a refusal code names.
 *
 * Exhaustive by union rather than defaulted: a fourth reason becomes a type
 * error here, not a file that is quietly refused with no words at all. The
 * size is derived from `RESUME_MAX_BYTES`, so raising the cap moves the copy
 * and the guard together.
 */
export function problemMessage(
  t: (key: string, vars?: Record<string, string | number>) => string,
  problem: ResumeFileProblem
): string {
  switch (problem) {
    case "unsupported":
      return t("upload.problemUnsupported");
    case "too-large":
      return t("upload.problemTooLarge", { mb: RESUME_MAX_BYTES / 1024 / 1024 });
    case "empty":
      return t("upload.problemEmpty");
  }
}

/**
 * UploadDropzone — drag & drop resume intake with a *client-side* size/mime
 * guard so an unsupported file never hits the network. The upload returns a
 * task id; live ingest progress then streams over /ai/stream/{taskId}.
 */
export interface UploadDropzoneProps extends React.ComponentProps<"div"> {
  /** Called after a run finishes so the page can refresh + surface the new resume. */
  onUploaded?: (resumeId: string | null) => void;
  compact?: boolean;
}

/**
 * The five stages the ingestion pipeline reports.
 *
 * The vocabulary lives in `lib/ingest-steps.ts` -- it is a vocabulary,
 * not a piece of this screen, and its English column is the fallback the
 * reader sees when the locale does not name a stage. It is re-exported
 * here because the dropzone is where the stages are shown.
 */
export { INGEST_SEED, ingestSeed } from "@/lib/ingest-steps";

// How the two ids are read out of the upload answer (top-level vs nested, camel
// vs snake) lives in `@/lib/resume-upload` — a mis-spelled key there means the
// progress panel silently never mounts.

export function UploadDropzone({ onUploaded, className, compact = false, ...props }: UploadDropzoneProps) {
  const { t } = useLocale();
  const inputRef = React.useRef<HTMLInputElement>(null);
  const resumeIdRef = React.useRef<string | null>(null);
  const [dragging, setDragging] = React.useState(false);
  const [rejected, setRejected] = React.useState<ResumeFileProblem | null>(null);
  const [taskId, setTaskId] = React.useState<string | null>(null);
  const upload = useUploadResume();

  const handleFiles = React.useCallback(
    (files: FileList | null) => {
      const file = files?.[0];
      if (!file) return;
      const problem = validateResumeFile(file);
      if (problem) {
        setRejected(problem);
        toast.error(problemMessage(t, problem));
        return;
      }
      setRejected(null);
      upload.mutate(file, {
        onSuccess: (res) => {
          const id = pickResumeId(res);
          resumeIdRef.current = id;
          const task = pickTaskId(res);
          if (task) setTaskId(task);
          else onUploaded?.(id);
        },
      });
    },
    [upload, onUploaded, t]
  );

  return (
    <div className={cn("space-y-3", className)} {...props}>
      <div
        role="button"
        tabIndex={0}
        aria-label={t("upload.ariaLabel")}
        onClick={() => !upload.isPending && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed text-center transition-colors duration-150 focus-visible:ring-[3px] focus-visible:ring-primary/30",
          compact ? "px-4 py-6" : "px-6 py-10",
          dragging
            ? "border-primary bg-primary/5"
            : rejected
              ? "border-destructive/50 bg-destructive/5"
              : "border-border/80 bg-muted/20 hover:border-primary/40 hover:bg-accent/30"
        )}
      >
        <span className="flex size-10 items-center justify-center rounded-xl border border-border/70 bg-card text-muted-foreground shadow-soft">
          {upload.isPending ? (
            <FileUp className="size-5 animate-pulse" aria-hidden />
          ) : (
            <Upload className="size-5" aria-hidden />
          )}
        </span>
        <p className="text-sm font-medium">
          {upload.isPending ? t("upload.uploading") : t("upload.dropHere")}
        </p>
        <p className="text-xs text-muted-foreground">
          {t("upload.accepted", {
            formats: RESUME_ACCEPT.join(" · "),
            mb: RESUME_MAX_BYTES / 1024 / 1024,
          })}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
          className="sr-only"
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {rejected && (
        <p role="alert" className="flex items-center gap-1.5 text-xs text-destructive">
          <TriangleAlert className="size-3.5" aria-hidden />
          {problemMessage(t, rejected)}
        </p>
      )}

      {taskId && (
        <Card>
          <CardContent className="space-y-2">
            <TaskProgress
              taskId={taskId}
              title={t("upload.ingesting")}
              seed={ingestSeed(t)}
              onDone={() => {
                setTaskId(null);
                toast.success(t("upload.ingestedToast"));
                onUploaded?.(resumeIdRef.current);
              }}
            />
            <p className="text-xs text-muted-foreground">
              {t("upload.canLeave")}
            </p>
          </CardContent>
        </Card>
      )}

      {upload.isPending && !taskId && (
        <TaskProgress
          pending
          title={t("upload.uploading")}
          steps={[{ id: "upload", label: t("upload.sending"), status: "active" }]}
        />
      )}
    </div>
  );
}
