"use client";

import * as React from "react";
import { useLocale } from "@/lib/i18n/locale-context";
import { Brain, Pencil, Trash2 } from "lucide-react";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useMemories } from "@/lib/hooks/resources";
import { useDeleteMemory, useUpdateMemory } from "@/lib/hooks/actions";
import { relativeTime, weightLabel } from "@/lib/format";
import { MEMORY_WEIGHTS, memoryPatch, shownWeight } from "@/lib/memory-edit";

/**
 * t("memory.whatAgentsRemember") about the user, and the one surface that can correct it
 * (AGENTS.md §6).
 *
 * Every memory here was written by the model: the extraction path runs at the end of each
 * chat turn and at interview finalize, and until this card existed it only ever *added*.
 * A sentence it invented was replayed as fact on every later turn with no way to say
 * otherwise, which is the gap this closes — so the card leads with reading, and each row
 * offers the two corrections the endpoint supports independently: fix the text, or lower
 * the weight.
 */

const LENGTH_LIMIT = 4000;

/** The three weights a user can set, labelled. The prompt reader sorts by `importance`, so
 *  "low" keeps a fact without being told it first every time. The values are the ladder
 *  `lib/memory-edit.ts` maps a stored weight onto -- a test holds the two lists together --
 *  and the labels are what the select shows. */
export const WEIGHTS = [
  { value: "0.3", label: "Low" },
  { value: "0.6", label: "Normal" },
  { value: "0.9", label: "High" },
];

export function MemoryCard() {
  const { t, locale } = useLocale();
  const memories = useMemories();
  const remove = useDeleteMemory();
  const [editing, setEditing] = React.useState<string | null>(null);
  const [draft, setDraft] = React.useState("");
  const [confirmId, setConfirmId] = React.useState<string | null>(null);

  const items = memories.data ?? [];

  const startEdit = (id: string, content: string) => {
    setEditing(id);
    setDraft(content);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("memory.whatAgentsRemember")}</CardTitle>
        <CardDescription>
          Facts the model extracted from your conversations and interviews. Correct a wrong
          one, or lower its weight — these shape every answer you get.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {memories.isPending ? (
          <div className="space-y-2" role="status">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-3/4" />
            <span className="sr-only">{t("memory.loading")}</span>
          </div>
        ) : memories.isError ? (
          <ErrorState
            title={t("memory.loadFailed")}
            error={memories.error}
            onRetry={() => void memories.refetch()}
            retrying={memories.isFetching}
          />
        ) : items.length ? (
          <ul className="divide-y divide-border/60">
            {items.map((m) => (
              <li key={m.id} className="py-3 first:pt-0 last:pb-0">
                {editing === m.id ? (
                  <MemoryEditor
                    id={m.id}
                    draft={draft}
                    setDraft={setDraft}
                    importance={m.importance}
                    onCancel={() => setEditing(null)}
                    onSaved={() => setEditing(null)}
                  />
                ) : (
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline" className="shrink-0 text-2xs font-normal capitalize">
                          {m.kind}
                        </Badge>
                        <Badge variant="secondary" className="shrink-0 text-2xs font-normal">
                          {weightLabel(m.importance)}
                        </Badge>
                        {m.updatedAt && (
                          <span className="text-2xs text-muted-foreground">
                            {relativeTime(m.updatedAt, locale)}
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-sm">{m.content}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Edit memory: ${m.content.slice(0, 40)}`}
                        onClick={() => startEdit(m.id, m.content)}
                      >
                        <Pencil aria-hidden />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Forget memory: ${m.content.slice(0, 40)}`}
                        onClick={() => setConfirmId(m.id)}
                      >
                        <Trash2 aria-hidden />
                      </Button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            icon={<Brain aria-hidden />}
            title={t("memory.emptyTitle")}
            description={t("memory.empty")}
          />
        )}
      </CardContent>

      <ConfirmDialog
        open={confirmId !== null}
        onOpenChange={(open) => !open && setConfirmId(null)}
        title={t("memory.forgetConfirm")}
        description={t("memory.forgetDescription")}
        confirmLabel="Forget"
        destructive
        onConfirm={() => {
          if (confirmId) {
            remove.mutate(confirmId, { onSettled: () => setConfirmId(null) });
          }
        }}
      />
    </Card>
  );
}

/**
 * The two corrections, side by side: the text and the weight.
 *
 * They save independently because they correct different problems — a fact that is wrong
 * needs new content, a fact the user is tired of hearing only needs to stop leading. Both
 * are sent as one PATCH, which the endpoint reads as "whichever of these is set".
 */
function MemoryEditor({
  id,
  draft,
  setDraft,
  importance,
  onCancel,
  onSaved,
}: {
  id: string;
  draft: string;
  setDraft: (v: string) => void;
  importance: number;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const update = useUpdateMemory();
  const { t } = useLocale();
  // null until the reader moves the select: an untouched weight must not be sent, or a
  // text-only edit would rewrite a stored 0.7 to the "Normal" band's canonical 0.6.
  const [weight, setWeight] = React.useState<string | null>(null);

  const save = () => update.mutate(memoryPatch(id, draft, weight), { onSuccess: onSaved });

  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <Label htmlFor={`memory-${id}`}>{t("memory.whatAgentRemembers")}</Label>
        <Textarea
          id={`memory-${id}`}
          value={draft}
          maxLength={LENGTH_LIMIT}
          onChange={(e) => setDraft(e.target.value)}
          rows={3}
          className="font-mono text-xs"
        />
        <p className="text-2xs text-muted-foreground">
          {draft.length} / {LENGTH_LIMIT} characters
        </p>
      </div>
      <div className="space-y-1.5">
        <Label>Weight</Label>
        <Select value={shownWeight(importance, weight)} onValueChange={setWeight}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {WEIGHTS.map((w) => (
              <SelectItem key={w.value} value={w.value}>
                {w.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-2xs text-muted-foreground">
          {t("memory.weightHigherFirst")}
        </p>
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={update.isPending}>
          Cancel
        </Button>
        <Button
          variant="ai"
          size="sm"
          onClick={save}
          loading={update.isPending}
          disabled={!draft.trim()}
        >
          Save
        </Button>
      </div>
    </div>
  );
}
