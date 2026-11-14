"use client";

import * as React from "react";
import Link from "next/link";
import { Copy, Feather, Link2, Search, X } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/page-header";
import { EmptyComposition } from "@/components/common/empty-composition";
import { ErrorState } from "@/components/common/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useLocale } from "@/lib/i18n/locale-context";
import { copyText, relativeTime } from "@/lib/format";
import { useLetters } from "@/lib/hooks/letters";
import type { LetterCatalogItem } from "@/lib/api/types";

/**
 * The ink desk — every kept letter in one room (Epic 210).
 *
 * The application dialog keeps the letter inside the application it belongs to;
 * this page is the layout for the other half of the question: the reader who holds
 * twelve applications and one perfect paragraph, and wants the paragraph back now,
 * not after opening seven boards.
 *
 * The page never fabricates a letter — every row is one the reader chose to keep —
 * and nothing here re-composes the body. Letters have an order (newest kept first),
 * and anything narrower is a filter over that order, widening back with one press.
 */

const PAGE_DEFAULTS: { q?: string } = { q: undefined };

/** The stored dials the i18n table can re-say; anything else reads as the stored word. */
const TONE_LABELS: Record<string, string> = {
  balanced: "coverLetter.tones.balanced",
  formal: "coverLetter.tones.formal",
  concise: "coverLetter.tones.concise",
  confident: "coverLetter.tones.confident",
};
const LENGTH_LABELS: Record<string, string> = {
  short: "coverLetter.lengths.short",
  standard: "coverLetter.lengths.standard",
  detailed: "coverLetter.lengths.detailed",
};

function dialLabel(value: string | undefined, labels: Record<string, string>,
                   t: (k: string) => string): string | undefined {
  if (!value) return undefined;
  return labels[value] ? t(labels[value]) : value;
}

export default function LettersPage() {
  const { t, locale } = useLocale();
  const [state, setUrl] = useUrlState<{ q?: string }>(PAGE_DEFAULTS);
  const [draft, setDraft] = React.useState(state.q ?? "");
  React.useEffect(() => setDraft(state.q ?? ""), [state.q]);
  const shelf = useLetters();
  const letters = shelf.data?.items ?? [];
  const q = (state.q ?? "").trim().toLowerCase();

  const visible = React.useMemo(() => {
    if (!q) return letters;
    return letters.filter((letter) =>
      [letter.body, letter.applicationTitle, letter.companyName, letter.tone, letter.length]
        .filter(Boolean)
        .some((field) => String(field).toLowerCase().includes(q)),
    );
  }, [letters, q]);

  const ask = (value: string) => setUrl({ q: value.trim() || undefined });
  const clear = () => {
    setDraft("");
    ask("");
  };
  const copyLetter = async (text: string) => {
    const ok = await copyText(text);
    toast[ok ? "success" : "error"](t(ok ? "common.copiedToClipboard" : "common.copyFailed"));
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader frontDoor title={t("letters.title")} description={t("letters.description")} />
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(draft);
        }}
        className="flex gap-2"
      >
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={t("letters.searchPlaceholder")}
            aria-label={t("letters.searchLabel")}
            autoComplete="off"
            className="pl-9"
          />
        </div>
        <Button type="submit" size="sm" variant="outline">
          {t("letters.search")}
        </Button>
        {state.q ? (
          <Button type="button" size="sm" variant="ghost" onClick={clear}>
            <X aria-hidden className="size-4" />
            {t("letters.clearSearch")}
          </Button>
        ) : null}
      </form>

      {shelf.isPending ? (
        <div className="space-y-3" role="status" aria-label={t("letters.loading")}>
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="h-44 animate-pulse rounded-2xl border border-border/60 bg-muted/40" />
          ))}
        </div>
      ) : shelf.isError ? (
        <Card>
          <CardContent className="p-6">
            <ErrorState
              title={t("letters.unavailable")}
              error={shelf.error}
              onRetry={() => void shelf.refetch()}
              retrying={shelf.isFetching}
            />
          </CardContent>
        </Card>
      ) : letters.length === 0 ? (
        <EmptyComposition
          icon={<Feather aria-hidden />}
          promise={t("letters.emptyPromise")}
          title={t("letters.emptyTitle")}
          description={t("letters.emptyDescription")}
          action={
            <Button variant="outline" size="sm" asChild>
              <Link href="/applications">{t("letters.emptyAction")}</Link>
            </Button>
          }
          proofs={[t("letters.proof1"), t("letters.proof2"), t("letters.proof3")]}
        />
      ) : visible.length === 0 ? (
        <EmptyComposition
          icon={<Search aria-hidden />}
          promise={t("letters.emptyPromise")}
          title={t("letters.noMatch", { query: state.q ?? "" })}
          description={t("letters.noMatchDescription")}
          action={
            <Button size="sm" variant="outline" onClick={clear}>
              {t("letters.clearSearch")}
            </Button>
          }
        />
      ) : (
        <>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span
              className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-muted/40 px-2.5 py-0.5 tabular-nums"
              aria-live="polite"
            >
              {t("letters.count", { count: visible.length })}
            </span>
          </div>
          <ol className="flex flex-col gap-4">
            {visible.map((letter) => (
              <li key={letter.id}>
                <LetterCard
                  letter={letter}
                  onCopy={() => copyLetter(letter.body)}
                />
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}

function LetterCard({
  letter,
  onCopy,
}: {
  letter: LetterCatalogItem;
  onCopy: () => void;
}) {
  const { t, locale } = useLocale();
  const keptOn = letter.createdAt ? relativeTime(letter.createdAt, locale) : undefined;
  const title = letter.applicationTitle || t("letters.unnamedApplication");
  const company = letter.companyName || t("letters.companyUnknown");
  const toneLabel = dialLabel(letter.tone, TONE_LABELS, t);
  const lengthLabel = dialLabel(letter.length, LENGTH_LABELS, t);

  return (
    <Card className="overflow-hidden border-border/70 transition-shadow duration-200 hover:shadow-card focus-within:shadow-card">
      <CardContent className="space-y-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="truncate text-sm font-semibold" title={title}>{title}</p>
              {toneLabel ? (
                <Badge variant="outline" className="text-2xs font-normal capitalize">
                  {toneLabel}
                </Badge>
              ) : null}
              {lengthLabel ? (
                <Badge variant="outline" className="text-2xs font-normal">
                  {lengthLabel}
                </Badge>
              ) : null}
            </div>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {company}
              {keptOn ? ` · ${keptOn}` : null}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <Button variant="ghost" size="icon-sm" onClick={onCopy} aria-label={t("letters.copy")} title={t("letters.copy")}>
              <Copy aria-hidden className="size-4" />
            </Button>
            <Button variant="ghost" size="sm" asChild title={t("letters.openApplication")}>
              <Link href={`/applications?application=${encodeURIComponent(letter.applicationId)}`}>
                <Link2 aria-hidden className="size-4" />
                <span className="hidden sm:inline">{t("letters.openApplication")}</span>
              </Link>
            </Button>
          </div>
        </div>
        <div className="max-h-56 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
          {letter.body}
        </div>
      </CardContent>
    </Card>
  );
}


