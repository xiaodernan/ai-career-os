"use client";

import * as React from "react";
import { FileUp, TriangleAlert, Upload } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { TaskProgress } from "@/components/ai/task-stream";
import { pick, str } from "@/lib/api/normalize";
import { RESUME_ACCEPT, validateResumeFile, useUploadResume } from "@/lib/hooks/actions";

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
 * The five stages the ingestion pipeline reports, in the order it reports them.
 * `id` must equal the `step` value published by ai-service/app/ingestion/pipeline.py
 * (the backend relay renames nothing) — a mismatched id leaves this row pending
 * forever while the real step is appended as a sixth, raw-named row.
 */
export const INGEST_SEED = [
  { id: "extracting", label: "Extracting text from the file" },
  { id: "cleaning", label: "Cleaning and normalizing the text" },
  { id: "chunking", label: "Splitting into retrievable chunks" },
  { id: "embedding", label: "Generating embeddings for each chunk" },
  { id: "indexing", label: "Indexing the document" },
];

function pickTaskId(raw: unknown): string | null {
  return str(raw, "taskId", "task_id") ?? str(pick(raw, "ingest"), "taskId", "task_id") ?? null;
}

function pickResumeId(raw: unknown): string | null {
  return (
    str(raw, "resumeId", "resume_id") ??
    str(pick(raw, "resume"), "id") ??
    null
  );
}

export function UploadDropzone({ onUploaded, className, compact = false, ...props }: UploadDropzoneProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const resumeIdRef = React.useRef<string | null>(null);
  const [dragging, setDragging] = React.useState(false);
  const [rejected, setRejected] = React.useState<string | null>(null);
  const [taskId, setTaskId] = React.useState<string | null>(null);
  const upload = useUploadResume();

  const handleFiles = React.useCallback(
    (files: FileList | null) => {
      const file = files?.[0];
      if (!file) return;
      const problem = validateResumeFile(file);
      if (problem) {
        setRejected(problem);
        toast.error(problem);
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
    [upload, onUploaded]
  );

  return (
    <div className={cn("space-y-3", className)} {...props}>
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload resume"
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
          {upload.isPending ? "Uploading…" : "Drop your resume here, or click to browse"}
        </p>
        <p className="text-xs text-muted-foreground">
          {RESUME_ACCEPT.join(" · ")} — up to 10 MB. Files stay in your workspace and feed the
          knowledge base the agents cite from.
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
          {rejected}
        </p>
      )}

      {taskId && (
        <Card>
          <CardContent className="space-y-2">
            <TaskProgress
              taskId={taskId}
              title="Ingesting"
              seed={INGEST_SEED}
              onDone={() => {
                setTaskId(null);
                toast.success("Resume ingested — your knowledge base is updated.");
                onUploaded?.(resumeIdRef.current);
              }}
            />
            <p className="text-xs text-muted-foreground">
              You can leave this page — the run continues server-side and the list below reflects
              its real status.
            </p>
          </CardContent>
        </Card>
      )}

      {upload.isPending && !taskId && (
        <TaskProgress pending title="Uploading" steps={[{ id: "upload", label: "Sending the file…", status: "active" }]} />
      )}
    </div>
  );
}
