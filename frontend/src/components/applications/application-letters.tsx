"use client";

import * as React from "react";
import Link from "next/link";
import { Check, Mail, Pencil, Trash2, X } from "lucide-react";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { CopyButton, DownloadButton } from "@/components/common/export-buttons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/error-state";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  COVER_LETTER_LENGTHS,
  COVER_LETTER_TONES,
  UNSET_DIAL,
  dialOptions,
  dialsOf,
  dialsToWire,
  type LetterDials,
} from "@/lib/cover-letter-dials";
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
  jobId,
}: {
  applicationId: string;
  /** The posting's title, used to name a downloaded letter after the application it belongs to. */
  jobLabel?: string | null;
  /** The posting itself, so an empty shelf can point at the page that fills it. */
  jobId?: string | null;
}) {
  const { t, locale } = useLocale();
  const letters = useApplicationLetters(applicationId);
  const remove = useDeleteApplicationLetter(applicationId);
  const update = useUpdateApplicationLetter(applicationId);
  const [pendingRemoval, setPendingRemoval] = React.useState<CoverLetter | null>(null);
  const [editingId, setEditingId] = React.useState<string | null>(null);

  return (
    <section id="letters" className="scroll-mt-4 space-y-2">
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
          {jobId ? (
            <Link
              href={`/jobs/${jobId}#cover-letter`}
              className="text-xs underline underline-offset-2 hover:text-foreground"
            >
              {t("applications.dialog.lettersWriteOne")}
            </Link>
          ) : (
            <span className="text-xs">{t("applications.dialog.lettersHint")}</span>
          )}
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
          const isEditing = editingId !== null && editingId === letter.id;
          return (
            <li key={letter.id}>
              <details className="group rounded-lg border border-border/70 bg-muted/20">
                <summary className="flex cursor-pointer list-none items-center gap-2 p-3 text-sm">
                  <Mail className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                  <span className="min-w-0 flex-1 truncate">{firstLine(letter)}</span>
                  {dials && (
                    <span className="hidden shrink-0 text-xs text-muted-foreground sm:inline">
                      {dials}
                    </span>
                  )}
                  <span className="shrink-0 text-xs text-muted-foreground">{moment}</span>
                </summary>
                <div className="border-t border-border/70 p-3">
                  {isEditing ? (
                    <LetterEditor
                      letter={letter}
                      saving={update.isPending}
                      onCancel={() => setEditingId(null)}
                      onSave={(body, corrected) => {
                        if (!letter.id) return;
                        update.mutate(
                          { letterId: letter.id, body, ...dialsToWire(corrected) },
                          { onSuccess: () => setEditingId(null) }
                        );
                      }}
                    />
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
                          onClick={() => letter.id && setEditingId(letter.id)}
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

/**
 * The in-place correction (50.2): the text, the two dials it was written with, and the two verbs.
 *
 * The dials start from what the letter was kept with, not from the generator's defaults, and
 * "Not set" is a real choice rather than a silence -- `dialsToWire` turns it into the empty
 * string the route reads as "clear this dial" (50.4).
 */
export function LetterEditor({
  letter,
  saving,
  onCancel,
  onSave,
}: {
  letter: CoverLetter;
  saving: boolean;
  onCancel: () => void;
  onSave: (body: string, dials: LetterDials) => void;
}) {
  const { t } = useLocale();
  const [body, setBody] = React.useState(letter.body ?? "");
  const [dials, setDials] = React.useState<LetterDials>(() => dialsOf(letter));
  const suffix = letter.id ?? "letter";

  return (
    <div className="space-y-2">
      <Textarea
        value={body}
        onChange={(event) => setBody(event.target.value)}
        rows={8}
        autoFocus
        aria-label={t("applications.dialog.letterBody")}
      />
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="space-y-1">
          <Label htmlFor={`letter-tone-${suffix}`} className="text-xs">
            {t("coverLetter.tone")}
          </Label>
          <Select
            value={dials.tone}
            onValueChange={(tone) => setDials((current) => ({ ...current, tone }))}
          >
            <SelectTrigger id={`letter-tone-${suffix}`} size="sm" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={UNSET_DIAL}>{t("applications.dialog.letterDialUnset")}</SelectItem>
              {dialOptions(COVER_LETTER_TONES, dials.tone).map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.labelKey ? t(option.labelKey) : option.value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label htmlFor={`letter-length-${suffix}`} className="text-xs">
            {t("coverLetter.length")}
          </Label>
          <Select
            value={dials.length}
            onValueChange={(length) => setDials((current) => ({ ...current, length }))}
          >
            <SelectTrigger id={`letter-length-${suffix}`} size="sm" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={UNSET_DIAL}>{t("applications.dialog.letterDialUnset")}</SelectItem>
              {dialOptions(COVER_LETTER_LENGTHS, dials.length).map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.labelKey ? t(option.labelKey) : option.value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="flex justify-end gap-1.5">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel} disabled={saving}>
          <X aria-hidden />
          {t("applications.dialog.letterCancel")}
        </Button>
        <Button
          type="button"
          variant="primary"
          size="sm"
          loading={saving}
          disabled={!body.trim()}
          onClick={() => onSave(body, dials)}
        >
          <Check aria-hidden />
          {t("applications.dialog.letterSave")}
        </Button>
      </div>
    </div>
  );
}

/** The first non-empty line, so a long letter still has a readable summary. */
function firstLine(letter: CoverLetter): string {
  const line = (letter.body ?? "").split(/\r?\n/).find((part) => part.trim().length > 0);
  return line?.trim() ?? "";
}
