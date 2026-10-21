"use client";

import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileUp, Loader2, Trash2, XCircle } from "lucide-react";
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
import { SOURCE_KINDS, sourceKindLabel } from "@/lib/source-kinds";
import { useSourceStatus } from "@/lib/hooks/resources";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * Upload + delete for knowledge sources. The mutations live here — next to the
 * only screen that uses them — rather than in the shared actions module, so the
 * knowledge panel never has to grow the global hook surface to change.
 */

/**
 * The kinds a source may have, and the name each is given.
 *
 * The vocabulary lives in `lib/source-kinds.ts` -- it is a vocabulary,
 * not a piece of this screen, and its English column is the fallback the
 * reader sees when the locale does not name a kind. It is re-exported
 * here because the uploader is where the kinds are offered.
 */
export { SOURCE_KINDS, sourceKindLabel } from "@/lib/source-kinds";

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

/**
 * There is no single-file hook: `useBatchUpload` below uploads one file or a whole
 * selection through the same loop, so a selection of one *is* the single-file flow. A
 * second hook here would be a second writer of the same request, and the endpoint-parity
 * gate would rightly ask why one route has two call sites.
 */

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

/* -------------------------------------------------------------------------- */
/* Batch upload                                                               */
/* -------------------------------------------------------------------------- */

/**
 * Where one file in a batch stands.
 *
 * `ingesting` is deliberately *not* success: the upload endpoint answers when the bytes
 * are stored, and the chunks that make the document citable are parsed, embedded and
 * indexed after that. Only `ready` and `failed` settle a row.
 *
 * `progress` is 0-100 during upload, undefined otherwise.
 */
export type UploadStage = "queued" | "uploading" | "ingesting" | "ready" | "rejected" | "failed";

export interface UploadRow {
  /** Stable within a batch, so React can key it and a retry can find it. */
  key: string;
  name: string;
  size: number;
  stage: UploadStage;
  /** The validation message for `rejected`, or the transport error for `failed`. */
  message?: string;
  /**
   * The source to poll for ingestion progress. Absent when the answer carried no id, in
   * which case the row stays at `ingesting` and the panel says so rather than pretending
   * it is watching something it cannot see.
   */
  sourceId?: string;
  /**
   * 0-100 during upload, undefined otherwise.
   */
  progress?: number;
}

/** One file a batch will try to send, paired with the row that reports it. */
export interface PlannedUpload {
  row: UploadRow;
  file: File;
}

/**
 * Splits a picked selection into rows, refusing the files the server would 400.
 *
 * Rejection is decided *before* anything is sent, and the message names the file: a batch
 * of seven where three are .zip would otherwise look like a successful upload of four
 * with no accounting for the other three. The same guard runs per file, so a batch is
 * never allowed to be stronger than the single-file check it is built from.
 *
 * The pairing is returned rather than inferred later: matching a row back to its `File` by
 * name would mis-attribute an upload whenever two files in one selection share a name.
 */
export function planBatch(
  files: readonly File[],
  usedKeys: readonly string[] = []
): { accepted: PlannedUpload[]; rejected: UploadRow[] } {
  const seen = new Set(usedKeys);
  const accepted: PlannedUpload[] = [];
  const rejected: UploadRow[] = [];
  for (const file of files) {
    let key = file.name;
    // Two files with the same name in one selection are distinct uploads; the key is
    // what React tracks, so it has to differ.
    let n = 2;
    while (seen.has(key)) {
      key = `${file.name} (${n++})`;
    }
    seen.add(key);
    const row: UploadRow = { key, name: file.name, size: file.size, stage: "queued" };
    const problem = validateDocumentFile(file);
    if (problem) {
      rejected.push({ ...row, stage: "rejected", message: problem });
    } else {
      accepted.push({ row, file });
    }
  }
  return { accepted, rejected };
}

/**
 * How many files are finished, however they finished.
 *
 * A file still ingesting counts as *not* done, and that is the point of the counter: the
 * upload finishing is not the document being usable, so "3 of 5 done" has to keep moving
 * after the last request returns or it reports a batch as complete while the last two
 * files are still being chunked.
 */
export function batchProgress(rows: readonly UploadRow[]): { done: number; total: number } {
  return {
    done: rows.filter((r) => r.stage === "ready" || r.stage === "failed").length,
    total: rows.length,
  };
}

/** True while any row is still waiting on the upload or on ingestion. */
export function batchRunning(rows: readonly UploadRow[]): boolean {
  return rows.some((r) => r.stage === "uploading" || r.stage === "ingesting");
}

export function useBatchUpload() {
  const qc = useQueryClient();
  const [rows, setRows] = React.useState<UploadRow[]>([]);
  // A ref beside the state, so `start` can read the keys already taken without taking
  // `rows` as a dependency and being rebuilt (and re-bound to an onChange) per row.
  const rowsRef = React.useRef(rows);
  rowsRef.current = rows;

  const reset = React.useCallback(() => setRows([]), []);

  const patch = React.useCallback((key: string, next: Partial<UploadRow>) => {
    setRows((cur) => cur.map((r) => (r.key === key ? { ...r, ...next } : r)));
  }, []);

  /**
   * Uploads the accepted rows one at a time, reporting each as it lands.
   *
   * Sequential rather than parallel for a reason, and it is not caution: the endpoint
   * binds one file per request, and firing six at once would make the panel's counter
   * meaningless -- arrival order is not selection order -- and would let one rate limit
   * answer the whole batch with 429.
   *
   * Each row is addressed by its own key, never by index, so a file the user renames
   * mid-run cannot make one update land on the wrong entry. The list is invalidated
   * once at the end rather than per file: the reader sees the same answer either way,
   * and one refetch after the last file is six times cheaper than six.
   */
  const start = React.useCallback(
    async (files: readonly File[], title: string, kind: string) => {
      // The keys already in the panel, read without `rows` as a dependency: `start` is
      // called from an onChange, and a stale closure there would reuse a key a row has
      // held since the last batch and make two entries React cannot tell apart.
      const used = rowsRef.current.map((r) => r.key);
      const plan = planBatch(files, used);
      if (!plan.accepted.length) {
        setRows((cur) => [...cur, ...plan.rejected]);
        return plan;
      }
      setRows((cur) => [...cur, ...plan.rejected, ...plan.accepted.map((p) => p.row)]);

      for (const { row, file } of plan.accepted) {
        patch(row.key, { stage: "uploading", progress: 0 });
        try {
          const result = await api.uploadWithProgress<{ sourceId?: string; documentId?: string }>(
            endpoints.knowledgeDocuments,
            buildDocumentForm(file, title, kind),
            (progress) => {
              patch(row.key, { progress: Math.round(progress * 100) });
            }
          );
          // The upload is a receipt, not the outcome: the row's chunks are being parsed,
          // embedded and indexed after this returns, and a document nobody can cite yet
          // is not a finished upload. So the row moves to "ingesting" carrying the id to
          // poll, and only the poll's own answer settles it.
          patch(row.key, {
            stage: "ingesting",
            sourceId: result?.sourceId ?? result?.documentId ?? undefined,
          });
        } catch (e) {
          patch(row.key, {
            stage: "failed",
            message: e instanceof Error ? e.message : "the request did not complete",
          });
        }
      }
      invalidateSources(qc);
      return plan;
    },
    [patch, qc]
  );

  /**
   * Settles the row whose ingestion poll answered.
   *
   * Called by `IngestStageText`, which owns the only per-row poll a component can run and
   * the only thing that knows which row it is. The row's stage has to move for the same
   * reason the display does: the counter counts `ready`/`failed`, and the panel stays
   * `running` while anything is ingesting, so a document that is ready but still marked
   * `ingesting` would keep the panel spinning after the last upload had finished.
   */
  const onRowSettled = React.useCallback(
    (key: string, outcome: { stage: "ready" | "failed"; message?: string }) => {
      patch(key, outcome);
    },
    [patch]
  );

  return { rows, start, reset, onRowSettled };
}

/**
 * One card that uploads one file or a whole selection.
 *
 * It replaced two overlapping cards: a single-file one and a batch one beside it. The
 * batch logic is the general case -- `multiple` lets the file dialog hold a selection, and
 * a selection of one is the single-file flow with nothing special-cased -- so the pair
 * collapsed into this. The ids and labels the existing tests read (`kb-file`, `kb-title`,
 * `kb-kind`) are kept, because those names are the form's contract.
 */
export function SourceUploadCard() {
  const { t } = useLocale();
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [title, setTitle] = React.useState("");
  const [kind, setKind] = React.useState<string>("note");
  const batch = useBatchUpload();
  const { rows, reset } = batch;
  const running = batchRunning(rows);
  const progress = batchProgress(rows);

  const submit = React.useCallback(
    (files: FileList | null) => {
      if (!files || running) return;
      // The files are copied out *before* the input is cleared, and the order is the
      // whole fix. A `FileList` is live: it is a view of the input's own selection,
      // so clearing the input empties it. Clearing first and reading afterwards
      // handed the batch an empty list -- and an empty list is not an error, it is
      // a batch of nothing, so the panel showed no row, the request never went
      // out, and the reader was told nothing at all.
      //
      // The input's value is cleared so that re-picking the *same* files starts a
      // fresh batch rather than appending to a finished one.
      const chosen = Array.from(files);
      if (inputRef.current) inputRef.current.value = "";
      // `batch.start` rather than the destructured name: the callback's dependency is the
      // function itself, and naming it through the object keeps the dep array honest
      // without `useCallback` inside the hook having to list every value it closes over.
      void batch.start(chosen, title, kind);
    },
    [batch, title, kind, running]
  );

  const summary = React.useMemo(() => {
    if (!rows.length) return null;
    const failed = rows.filter((r) => r.stage === "failed" || r.stage === "rejected").length;
    return t("knowledge.sources.batchSummary", {
      done: progress.done,
      total: progress.total,
      failed: failed ? t("knowledge.sources.notIngested", { count: failed }) : "",
    });
  }, [rows, progress, t]);

  return (
    <Card>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-0 flex-1 basis-56 space-y-2">
            <Label htmlFor="kb-file">{t("knowledge.sources.documents")}</Label>
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                id="kb-file"
                type="file"
                multiple
                accept={ACCEPTED_EXTENSIONS.join(",")}
                className="sr-only"
                aria-label={t("knowledge.sources.chooseDocuments")}
                onChange={(e) => submit(e.target.files)}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => inputRef.current?.click()}
                disabled={running}
                loading={running}
              >
                <FileUp aria-hidden />
                {running ? t("knowledge.sources.uploading") : t("knowledge.sources.chooseFiles")}
              </Button>
              <span className="text-xs text-muted-foreground">
                {MAX_DOCUMENT_BYTES / (1024 * 1024)} MB each, {ACCEPTED_EXTENSIONS.join(" / ")}
              </span>
            </div>
          </div>
          <div className="min-w-0 flex-1 basis-48 space-y-2">
            <Label htmlFor="kb-title">{t("knowledge.sources.titleLabel")}</Label>
            <Input
              id="kb-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("knowledge.sources.appliedToBatch")}
              autoComplete="off"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="kb-kind">{t("knowledge.sources.kind")}</Label>
            <Select value={kind} onValueChange={setKind}>
              <SelectTrigger id="kb-kind" size="sm" className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SOURCE_KINDS.map((k) => (
                  <SelectItem key={k.value} value={k.value}>
                    {sourceKindLabel(t, k.value)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {summary && (
          <div className="space-y-1.5" role="status">
            <p className="text-xs text-muted-foreground">{summary}</p>
            <ul className="space-y-1">
              {rows.map((r) => (
                <li key={r.key} className="flex items-center gap-2 text-xs">
                  {r.stage === "ready" ? (
                    <CheckCircle2 className="size-3.5 shrink-0 text-success" aria-hidden />
                  ) : r.stage === "rejected" || r.stage === "failed" ? (
                    <XCircle className="size-3.5 shrink-0 text-destructive" aria-hidden />
                  ) : r.stage === "ingesting" ? (
                    <Loader2 className="size-3.5 shrink-0 animate-spin text-muted-foreground" aria-hidden />
                  ) : r.stage === "uploading" ? (
                    <Loader2 className="size-3.5 shrink-0 animate-spin text-muted-foreground" aria-hidden />
                  ) : (
                    <span className="size-3.5 shrink-0" aria-hidden />
                  )}
                  <span className="min-w-0 flex-1 truncate">{r.name}</span>
                  {r.stage === "uploading" && r.progress !== undefined && (
                    <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-200 ease-out"
                        style={{ width: `${r.progress}%` }}
                      />
                    </div>
                  )}
                  <IngestStageText row={r} onSettled={batch.onRowSettled} />
                </li>
              ))}
            </ul>
            {!running && (
              <Button variant="ghost" size="xs" onClick={reset}>
                {t("knowledge.sources.clearList")}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * The word beside a row that explains what is happening to it right now, and the poll
 * that learns it.
 *
 * Kept as its own component because only rows that are *ingesting* need a poll, and a
 * hook cannot be conditional: mounting it per row means the row that is not ingesting
 * polls nothing, rather than one disabled query per row.
 *
 * It also *settles* the row, which is the half that makes the panel useful: the counter
 * counts only `ready`/`failed` and the panel stays `running` while anything is
 * `ingesting`, so a row that displayed "ready" while still counting as in-flight would
 * leave the panel spinning forever after the last upload succeeded.
 */
function IngestStageText({
  row,
  onSettled,
}: {
  row: UploadRow;
  onSettled: (key: string, outcome: { stage: "ready" | "failed"; message?: string }) => void;
}) {
  const { t } = useLocale();
  const watch = useSourceStatus(row.stage === "ingesting" ? (row.sourceId ?? null) : null);

  // Report the terminal answer once, not on every poll tick: `useSourceStatus` keeps
  // re-rendering while it fetches, and an idempotent-but-repeated call would still be
  // noise in the caller's state.
  const settled = React.useRef(false);
  const status = watch.data?.status;
  const failure = watch.data?.error;
  React.useEffect(() => {
    if (settled.current) return;
    if (status === "ready") {
      settled.current = true;
      onSettled(row.key, { stage: "ready" });
    } else if (status === "failed" || failure) {
      settled.current = true;
      onSettled(row.key, { stage: "failed", message: failure ?? t("knowledge.sources.ingestionFailed") });
    }
  }, [status, failure, onSettled, row.key, t]);

  if (row.stage === "rejected" || row.stage === "failed") {
    return row.message ? (
      <span className="min-w-0 shrink-0 truncate text-muted-foreground">{row.message}</span>
    ) : null;
  }
  if (row.stage === "ingesting") {
    if (!row.sourceId) {
      // No id came back, so there is nothing to poll. Saying so is the honest answer; a
      // spinner that never resolves reads as a hung upload.
      return (
        <span className="shrink-0 text-muted-foreground">{t("knowledge.sources.noSourceId")}</span>
      );
    }
    return (
      <span className="min-w-0 shrink-0 truncate text-muted-foreground">
        {failure
          ? t("knowledge.sources.failedPrefix", { reason: failure })
          : (status ?? t("knowledge.sources.pending"))}
      </span>
    );
  }
  return row.stage === "ready" ? (
    <span className="shrink-0 text-muted-foreground">{t("knowledge.sources.ready")}</span>
  ) : null;
}

export function SourceDeleteButton({ id, title }: { id: string; title: string }) {
  const { t } = useLocale();
  const [confirming, setConfirming] = React.useState(false);
  const remove = useDeleteSource();
  return (
    <>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label={t("knowledge.sources.deleteLabel", { title })}
        onClick={() => setConfirming(true)}
      >
        <Trash2 aria-hidden />
      </Button>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={t("knowledge.sources.deleteTitle", { title })}
        description={t("knowledge.sources.deleteDescription")}
        confirmLabel={t("knowledge.sources.delete")}
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
