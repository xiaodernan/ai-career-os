"use client";

import * as React from "react";
import { Check, Mail, Pencil, Trash2, X } from "lucide-react";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { CopyButton, DownloadButton } from "@/components/common/export-buttons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/error-state";
import { Textarea } from "@/components/ui/textarea";
import { letterDownloadName, relativeTime } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";
import { useDeleteApplicationLetter, useUpdateApplicationLetter } from "@/lib/hooks/actions";
import { useApplicationLetters } from "@/lib/hooks/resources";
import type { CoverLetter } from "@/lib/api/types";

/**
 * The cover letters kept with this application (47.4).
 *
 * A draft is written on the job page where the letter was made; this is where a reader comes
 * back to check, correct, take away or remove what they kept. Each letter opens in place -- the
 * body is the whole point, and a link to another screen would hide it behind a navigation.
 */
export function ApplicationLettersPanel({
  applicationId,
  jobLabel,
}: {
  applicationId: string;
  /** The posting's title, used to name a downloaded letter after the application it belongs to. */
  jobLabel?: string | null;
}) {
  const { t, locale } = useLocale();
  const letters = useApplicationLetters(applicationId);
  const remove = useDeleteApplicationLetter(applicationId);
  const update = useUpdateApplicationLetter(applicationId);
  const [pendingRemoval, setPendingRemoval] = React.useState<CoverLetter | null>(null);
  const [editing, setEditing] = React.useState<{ letterId: string; body: string } | null>(null);

  return (
    <section className="space-y-2">
      <div className="flex items-baseline gap-2">
        <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
          {t("applications.dialog.letters")}
        </h4>
        {letters.data && letters.data.length > 0 && (
          <Badge variant="secondary" className="font-normal tabular-nums">
            {letters.data.length}
          </Badge>
        )}
      </div>

      {letters.isPending && (
        <div className="space-y-2" role="status">
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-5 w-1/2" />
          <span className="sr-only">{t("applications.dialog.letters")}</span>
        </div>
      )}
      {letters.isError && (
        <ErrorState
          title={t("applications.dialog.lettersFailed")}
          error={letters.error}
          onRetry={() => void letters.refetch()}
          retrying={letters.isFetching}
        />
      )}
      {letters.data?.length === 0 && (
        <p className="text-sm text-muted-foreground">
          {t("applications.dialog.lettersEmpty")}{" "}
          <span className="text-xs">{t("applications.dialog.lettersHint")}</span>
        </p>
      )}

      <ul className="space-y-2">
        {(letters.data ?? []).map((letter) => {
          const dials = [letter.mode, letter.tone, letter.length].filter(Boolean).join(" · ");
          const moment =
            letter.updatedAt && letter.updatedAt !== letter.createdAt
              ? t("applications.dialog.letterEdited", {
                  when: relativeTime(letter.updatedAt, locale),
                })
              : letter.createdAt
                ? t("applications.dialog.letterKept", {
                    when: relativeTime(letter.createdAt, locale),
                  })
                : "";
          const isEditing = editing?.letterId === letter.id;
          return (
            <li key={letter.id}>
              <details className="group rounded-lg border border-border/70 bg-muted/20">
                <summary className="flex cursor-pointer list-none items-center gap-2 p-3 text-sm">
                  <Mail className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                  <span className="min-w-0 flex-1 truncate">
                    {firstLine(letter)}
                  </span>
                  {dials && (
                    <span className="hidden shrink-0 text-xs text-muted-foreground sm:inline">
                      {dials}
                    </span>
                  )}
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {moment}
                  </span>
                </summary>
                <div className="border-t border-border/70 p-3">
                  {editing && isEditing ? (
                    <div className="space-y-2">
                      <Textarea
                        value={editing.body}
                        onChange={(event) =>
                          setEditing({ letterId: editing.letterId, body: event.target.value })
                        }
                        rows={8}
                        autoFocus
                      />
                      <div className="flex justify-end gap-1.5">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditing(null)}
                          disabled={update.isPending}
                        >
                          <X aria-hidden />
                          {t("applications.dialog.letterCancel")}
                        </Button>
                        <Button
                          type="button"
                          variant="primary"
                          size="sm"
                          loading={update.isPending}
                          disabled={!editing.body.trim()}
                          onClick={() =>
                            update.mutate(
                              { letterId: editing.letterId, body: editing.body },
                              { onSuccess: () => setEditing(null) }
                            )
                          }
                        >
                          <Check aria-hidden />
                          {t("applications.dialog.letterSave")}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">{letter.body}</p>
                  )}
                  <div className="mt-3 flex flex-wrap justify-end gap-1.5">
                    {!isEditing && (
                      <>
                        <CopyButton
                          text={letter.body ?? ""}
                          label={t("applications.dialog.letterCopy")}
                          variant="ghost"
                          size="sm"
                        />
                        <DownloadButton
                          text={letter.body ?? ""}
                          filename={letterDownloadName(letter, jobLabel)}
                          label={t("applications.dialog.letterDownload")}
                          mime="text/markdown;charset=utf-8"
                          variant="ghost"
                          size="sm"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={!letter.id}
                          onClick={() =>
                            letter.id && setEditing({ letterId: letter.id, body: letter.body ?? "" })
                          }
                        >
                          <Pencil aria-hidden />
                          {t("applications.dialog.letterEdit")}
                        </Button>
                      </>
                    )}
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={isEditing}
                      onClick={() => setPendingRemoval(letter)}
                    >
                      <Trash2 aria-hidden />
                      {t("applications.dialog.letterDelete")}
                    </Button>
                  </div>
                </div>
              </details>
            </li>
          );
        })}
      </ul>

      <ConfirmDialog
        open={pendingRemoval !== null}
        onOpenChange={(open) => {
          if (!open) setPendingRemoval(null);
        }}
        title={t("applications.dialog.letterDeleteTitle")}
        description={t("applications.dialog.letterDeleteBody")}
        confirmLabel={t("applications.dialog.letterDeleteConfirm")}
        destructive
        loading={remove.isPending}
        onConfirm={() => {
          if (!pendingRemoval?.id) return;
          remove.mutate(pendingRemoval.id, {
            onSuccess: () => setPendingRemoval(null),
          });
        }}
      />
    </section>
  );
}

/** The first non-empty line, so a long letter still has a readable summary. */
function firstLine(letter: CoverLetter): string {
  const line = (letter.body ?? "").split(/\r?\n/).find((part) => part.trim().length > 0);
  return line?.trim() ?? "";
}
