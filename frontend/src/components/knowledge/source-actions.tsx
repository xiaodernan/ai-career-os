"use client";

import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUp, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";

/**
 * Upload + delete for knowledge sources. The mutations live here — next to the
 * only screen that uses them — rather than in the shared actions module, so the
 * knowledge panel never has to grow the global hook surface to change.
 */

/**
 * Exactly `KnowledgeService.KINDS` (validateKind rejects anything else with a 400 —
 * there is no `document` value; a blank kind falls back to `note` server-side), so the
 * selector offers the set verbatim and defaults to that fallback.
 */
export const SOURCE_KINDS = [
  { value: "note", label: "Note" },
  { value: "resume", label: "Resume" },
  { value: "project", label: "Project" },
  { value: "jd", label: "Job description" },
  { value: "company", label: "Company" },
  { value: "interview_feedback", label: "Interview feedback" },
  { value: "certificate", label: "Certificate" },
  { value: "course", label: "Course" },
  { value: "goal", label: "Goal" },
] as const;

/** Mirrors `storage/FileValidator`: 20 MB cap, PDF/DOCX/TXT by magic bytes server-side. */
export const MAX_DOCUMENT_BYTES = 20 * 1024 * 1024;
export const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt"] as const;

export function validateDocumentFile(file: { name: string; size: number }): string | null {
  const lower = file.name.toLowerCase();
  const dot = lower.lastIndexOf(".");
  const ext = dot >= 0 ? lower.slice(dot) : "";
  if (!(ACCEPTED_EXTENSIONS as readonly string[]).includes(ext)) {
    return `Only ${ACCEPTED_EXTENSIONS.join(", ")} files can be ingested — “${file.name}” would be rejected by the server.`;
  }
  if (file.size > MAX_DOCUMENT_BYTES) {
    return `“${file.name}” is over the 20 MB ingestion cap.`;
  }
  if (file.size <= 0) {
    return `“${file.name}” is empty — nothing to ingest.`;
  }
  return null;
}

export function buildDocumentForm(file: File, title: string, kind: string): FormData {
  const form = new FormData();
  form.append("file", file);
  if (title.trim()) form.append("title", title.trim());
  form.append("kind", kind);
  return form;
}

function invalidateSources(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ["knowledge", "sources"] });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (form: FormData) => api.upload<unknown>(endpoints.knowledgeDocuments, form),
    onSuccess: () => {
      invalidateSources(qc);
      toast.success("Document queued — ingestion runs in the background.");
    },
    onError: (e) =>
      toast.error(e instanceof Error ? e.message : "Upload failed — the file was not ingested."),
  });
}

export function useDeleteSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.remove(endpoints.knowledgeSource(id)),
    onSuccess: () => {
      invalidateSources(qc);
      toast.success("Source deleted — its chunks stop being cited.");
    },
    onError: (e) =>
      toast.error(e instanceof Error ? e.message : "Couldn't delete the source."),
  });
}

export function SourceUploadCard() {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = React.useState<string | null>(null);
  const [title, setTitle] = React.useState("");
  const [kind, setKind] = React.useState<string>("note");
  const [rejected, setRejected] = React.useState<string | null>(null);
  const upload = useUploadDocument();

  const pick = React.useCallback(() => inputRef.current?.click(), []);

  const submit = React.useCallback(
    (files: FileList | null) => {
      const file = files?.[0];
      if (!file || upload.isPending) return;
      const problem = validateDocumentFile(file);
      if (problem) {
        setRejected(problem);
        toast.error(problem);
        return;
      }
      setRejected(null);
      setFileName(file.name);
      upload.mutate(buildDocumentForm(file, title, kind), {
        onSuccess: () => {
          setTitle("");
          setFileName(null);
          if (inputRef.current) inputRef.current.value = "";
        },
      });
    },
    [upload, title, kind]
  );

  return (
    <Card>
      <CardContent className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1 basis-56 space-y-2">
          <Label htmlFor="kb-file">Document</Label>
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              id="kb-file"
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(",")}
              className="hidden"
              aria-label="Choose a document to ingest"
              onChange={(e) => submit(e.target.files)}
            />
            <Button variant="outline" size="sm" onClick={pick} disabled={upload.isPending}>
              <FileUp aria-hidden />
              {fileName ?? "Choose file"}
            </Button>
          </div>
          {rejected && (
            <p role="alert" className="text-xs text-destructive">
              {rejected}
            </p>
          )}
        </div>
        <div className="min-w-0 flex-1 basis-48 space-y-2">
          <Label htmlFor="kb-title">Title (optional)</Label>
          <Input
            id="kb-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. System design notes"
            autoComplete="off"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="kb-kind">Kind</Label>
          <Select value={kind} onValueChange={setKind}>
            <SelectTrigger id="kb-kind" size="sm" className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SOURCE_KINDS.map((k) => (
                <SelectItem key={k.value} value={k.value}>
                  {k.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button
          variant="ai"
          size="sm"
          loading={upload.isPending}
          disabled={upload.isPending}
          onClick={() => inputRef.current?.click()}
        >
          <Upload aria-hidden />
          Upload & ingest
        </Button>
      </CardContent>
    </Card>
  );
}

export function SourceDeleteButton({ id, title }: { id: string; title: string }) {
  const [confirming, setConfirming] = React.useState(false);
  const remove = useDeleteSource();
  return (
    <>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label={`Delete ${title}`}
        onClick={() => setConfirming(true)}
      >
        <Trash2 aria-hidden />
      </Button>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={`Delete “${title}”?`}
        description="The source row is removed and its chunks stop being cited. This cannot be undone."
        confirmLabel="Delete"
        destructive
        loading={remove.isPending}
        onConfirm={() =>
          remove.mutate(id, {
            onSuccess: () => setConfirming(false),
          })
        }
      />
    </>
  );
}
