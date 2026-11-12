"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Briefcase, CalendarClock, FileBarChart, MessagesSquare, Plus, Search, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { GradientText } from "@/components/ui/gradient-text";
import { Pagination } from "@/components/common/pagination";
import { lastPageOf } from "@/lib/page-window";
import { QueryBoundary } from "@/components/common/query-boundary";
import { LoadingListSkeleton } from "@/components/common/loading-skeletons";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { useCreateInterviewSession, useDeleteInterviewSession } from "@/lib/hooks/actions";
import { useInterviewSessions } from "@/lib/hooks/resources";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useLocale } from "@/lib/i18n/locale-context";
import { str } from "@/lib/api/normalize";
import { formatDateTime, relativeTime } from "@/lib/format";
import { INTERVIEW_MODES } from "@/lib/interview-modes";
import { interviewModeHint, interviewModeName } from "@/lib/status-words";
import { interviewApplicationHref } from "@/lib/interview-target";
import { stageLabel } from "@/lib/pipeline";

// The route's own default window: `GET /interview/sessions` binds `size` with
// `defaultValue = "20"`, so this number asks for exactly what the server would have
// chosen anyway -- the hook's own 50 literal never reaches the wire on this path.
const PAGE_SIZE = 20;

// Module-level so `setUrl` (a `useCallback` keyed on this object) is stable across renders.
// Both optional keys are declared here even though they are usually absent: `hydrateState` walks
// the union of these keys and the numeric ones, so a key left out of the defaults is a filter a
// pasted link cannot restore -- which is how `/interviews?application=<id>` used to open the whole
// history on reload, under a chip the drawer had just written (70.2's rule, now this board's too).
const PAGE_DEFAULTS: { page: number; application?: string; q?: string } = {
  page: 0,
  application: undefined,
  q: undefined,
};

export default function InterviewsPage() {
  const { t, locale } = useLocale();
  // The page index and the word both live in the URL, so a reload or a shared list link opens the
  // same page of the same question -- the rule the replies (49.1), company (58.2), pipeline (70.2)
  // and registry (70.3) boards follow.
  const [state, setUrl] = useUrlState<{ page: number; application?: string; q?: string }>(
    PAGE_DEFAULTS,
    { numericKeys: ["page"] }
  );
  // 57.1: the drawer's rehearsals link names a card, so the list narrows to it.
  // The filter travels in the URL like the page does, so the narrowed list is
  // shareable and a reload does not silently widen it back to everything.
  const applicationId = state.application;
  // The box holds what the reader is typing; the URL holds what was asked. Binding the box straight
  // to the URL would make every character a new question: six keystrokes would be six requests and
  // six cache entries, and the board would answer a word nobody had finished.
  const [word, setWord] = React.useState(state.q ?? "");
  React.useEffect(() => setWord(state.q ?? ""), [state.q]);
  // Asking a new question starts at its first page: a word typed on page 4 must not leave the
  // reader on a page the new, narrower answer does not have.
  const ask = (value: string) => setUrl({ q: value.trim() || undefined, page: 0 });
  const sessions = useInterviewSessions({
    page: state.page,
    size: PAGE_SIZE,
    applicationId,
    q: state.q,
  });
  const create = useCreateInterviewSession();
  const router = useRouter();

  const total = sessions.data?.total ?? 0;
  // A past-the-end page is an empty window over a real total, not an empty list: the answer's
  // own window is the divisor (`data.size`), so the URL is corrected to the last page that
  // exists -- `lastPageOf` (lib/page-window.ts) is that rule in one place. A layout effect,
  // because the stale commit paints its empty copy first -- React flushes this update before
  // the browser paints, so the wrong screen is replaced, not seen.
  const lastPage = sessions.data ? lastPageOf(total, sessions.data.size) : 0;
  React.useLayoutEffect(() => {
    if (sessions.data && state.page > lastPage) setUrl({ page: lastPage });
  }, [sessions.data, state.page, lastPage, setUrl]);

  const start = (mode: string) =>
    create.mutate(
      // 57.3: on a card's narrowed list, a new rehearsal is for that card.
      // The button used to start a free session and then drop the reader on a
      // list it was not on -- the filter is the context the reader chose, so
      // the create reads it too.
      { mode, ...(applicationId ? { applicationId } : {}) },
      {
        onSuccess: (res) => {
          const id = str(res, "id", "session_id", "sessionId") ?? str((res as { session?: unknown }).session, "id");
          if (id) router.push(`/interviews/${id}`);
          else void sessions.refetch();
        },
      }
    );

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* The interview rehearsal board is a headline action for every candidate, so its header
          carries the same front-door band the dashboard, jobs board, inbox and resume manager
          established: static light-theme washes, a dark-only aurora (screen-blend over a light
          Card would wash it white -- the trap Epic 137 documented), a shimmer hairline and a
          CSS-only staggered entrance. Every layer is a plain decorated span/div, so the band adds
          zero client JS and leaves the route budget untouched; all motion is decorative and
          `prefers-reduced-motion` stays authoritative via globals.css. The search box, filter and
          start CTA below are real controls and are untouched -- only their entrance and the primary
          CTA's affordance gain the designed language. */}
      <section className="animate-fade-up relative overflow-hidden rounded-2xl border hairline bg-card/60 shadow-card">
        {/* Light-theme ambient washes: static gradients, zero per-frame cost. */}
        <div
          aria-hidden
          className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full"
          style={{
            background:
              "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 16%, transparent), transparent)",
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-28 -left-24 h-64 w-64 rounded-full"
          style={{
            background:
              "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 9%, transparent), transparent)",
          }}
        />
        {/* Dark-theme aurora: screen-blend light only ever composited over a dark surface. */}
        <div aria-hidden className="pointer-events-none absolute inset-0 hidden overflow-hidden dark:block">
          <span className="aurora-blob aurora-blob-1 opacity-30" />
          <span className="aurora-blob aurora-blob-2 opacity-30" />
          <div className="aurora-grid opacity-30" />
        </div>
        {/* Shimmer hairline crowns the band -- the same premium separator the dashboard uses. */}
        <span aria-hidden className="shimmer-rule absolute inset-x-0 top-0 block h-px" />
        <div className="relative px-6 py-6">
          <PageHeader
            title={<GradientText className="italic">{t("interviews.title")}</GradientText>}
            description={
              <span className="animate-fade-up block" style={{ animationDelay: "90ms" }}>
                {t("interviews.description")}
              </span>
            }
            actions={
              <div className="animate-fade-up flex flex-wrap items-center justify-end gap-2" style={{ animationDelay: "160ms" }}>
            {/* The question 70.4 gave this route and this board never asked. It is the server's
                search, not a filter over the rows in hand: the pager counts the matches, so page
                two of a word is the second page of the matches -- and the characters are read as
                characters, which is what lets a rehearsal at a company that really carries an
                underscore be found by spelling the underscore. */}
            <form
              role="search"
              className="flex items-center gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                ask(word);
              }}
            >
              <div className="relative">
                <Search
                  aria-hidden
                  className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                />
                <Input
                  value={word}
                  onChange={(event) => setWord(event.target.value)}
                  placeholder={t("interviews.searchPlaceholder")}
                  aria-label={t("interviews.searchLabel")}
                  autoComplete="off"
                  className="w-40 pl-9 sm:w-60"
                />
              </div>
              <Button type="submit" size="sm" variant="outline">
                {t("chrome.search")}
              </Button>
              {state.q ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setWord("");
                    ask("");
                  }}
                >
                  {t("interviews.clearSearch")}
                </Button>
              ) : null}
            </form>
            {applicationId && (
              <Button
                variant="outline"
                onClick={() => setUrl({ page: 0, application: undefined })}
              >
                {t("interviews.detail.allInterviews")}
              </Button>
            )}
            <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ai" className="glow-halo glow-on-hover" loading={create.isPending}>
                <Plus aria-hidden />
                {t("interviews.startInterview")}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-72">
              <DropdownMenuLabel>{t("interviews.mode")}</DropdownMenuLabel>
              {INTERVIEW_MODES.map((m) => (
                <DropdownMenuItem key={m.value} onSelect={() => start(m.value)}>
                  <span className="flex min-w-0 flex-col">
                    <span>{interviewModeName(t, m.value)}</span>
                    <span className="text-xs text-muted-foreground">{interviewModeHint(t, m.value)}</span>
                  </span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
            </DropdownMenu>
          </div>
        }
          />
        </div>
      </section>

      {applicationId && (
        // The chip is the answer to "why is this list short": it names the card
        // the list is scoped to and leads back to it (51.2's deep link).
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
          <Briefcase className="size-4 shrink-0" aria-hidden />
          <span>{t("interviews.filteredToApplication")}</span>
          <Button variant="link" size="sm" className="h-auto p-0" asChild>
            <Link href={interviewApplicationHref(applicationId) ?? "/applications"}>
              {t("interviews.openApplication")}
            </Link>
          </Button>
        </div>
      )}

      <QueryBoundary
        query={sessions}
        skeleton={<LoadingListSkeleton rows={4} />}
        empty={{
          icon: <CalendarClock aria-hidden />,
          // Three different empties (49.2's rule, now three deep). The word is read ahead of the
          // card because it is the narrower of the two: clearing it brings this card's rehearsals
          // back, while widening the card would drop the words the reader was looking for.
          ...(state.q
            ? {
                title: t("interviews.noMatch", { query: state.q }),
                description: t("interviews.noMatchDescription"),
                // The escape is the words, not a create form -- the reader was not trying to
                // start a rehearsal, and a board of them is full.
                action: (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setWord("");
                      ask("");
                    }}
                  >
                    {t("interviews.clearSearch")}
                  </Button>
                ),
              }
            : {
                title: t("interviews.empty"),
                // A card with no rehearsals yet is not "no interviews ever": the
                // narrowed list gets its own action, so the way out is the honest
                // one -- widen the list -- rather than "pick a target job".
                description: applicationId
                  ? t("interviews.filteredToApplication")
                  : t("interviews.emptyDescription"),
                action: applicationId ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setUrl({ page: 0, application: undefined })}
                  >
                    {t("interviews.detail.allInterviews")}
                  </Button>
                ) : (
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/jobs">{t("interviews.pickATargetJob")}</Link>
                  </Button>
                ),
              }),
        }}
        notLive={{
          title: t("common.notLiveTitle"),
          description:
            t("interviews.notLiveDescription"),
        }}
        boxed={false}
      >
        {(page) => (
          <ul className="space-y-3">
            {page.items.map((s) => {
              const done = s.status === "completed";
              const applicationHref = interviewApplicationHref(s.applicationId);
              return (
                <li key={s.id}>
                  <Card className="transition-shadow duration-200 hover:shadow-pop">
                    <CardContent className="flex flex-wrap items-center gap-3">
                      <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground">
                        {done ? (
                          <FileBarChart className="size-5" aria-hidden />
                        ) : (
                          <MessagesSquare className="size-5" aria-hidden />
                        )}
                      </span>
                      <div className="min-w-0 flex-1 basis-52">
                        <p className="truncate text-sm font-medium">
                          {t("interviews.modeInterview", { mode: interviewModeName(t, s.mode) })}
                          {s.jobTitle ? ` · ${s.jobTitle}` : s.companyName ? ` · ${s.companyName}` : ""}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-muted-foreground">
                          {s.questionCount
                            ? t("interviews.questionsInline", {
                                count: s.questionCount,
                                plural: s.questionCount === 1 ? "" : "s",
                              })
                            : ""}
                          {done
                            ? t("interviews.finishedAt", { when: relativeTime(s.finishedAt, locale) })
                            : t("interviews.startedAt", { when: formatDateTime(s.startedAt, locale) })}
                        </p>
                      </div>
                      {!done && s.status === "active" && (
                        <Badge variant="ai" className="shrink-0 text-2xs font-normal">
                          {t("interviews.inProgress")}
                        </Badge>
                      )}
                      {done && typeof s.overall === "number" && (
                        <Badge variant={s.overall >= 75 ? "success" : s.overall >= 50 ? "warning" : "destructive"} className="shrink-0 tabular-nums">
                          {Math.round(s.overall)}/100
                        </Badge>
                      )}
                      {s.applicationStatus && (
                        // 57.4: the card's stage, so the reader knows whether this practice
                        // belongs to an application still in play (or one already decided).
                        <Badge variant="outline" className="shrink-0 font-normal">
                          {stageLabel(t, s.applicationStatus)}
                        </Badge>
                      )}
                      {applicationHref && (
                        <Button variant="ghost" size="sm" asChild className="shrink-0">
                          <Link href={applicationHref}>
                            <Briefcase aria-hidden />
                            {t("interviews.openApplication")}
                          </Link>
                        </Button>
                      )}
                      <Button variant="outline" size="sm" asChild className="shrink-0">
                        <Link href={done ? `/interviews/${s.id}/report` : `/interviews/${s.id}`}>
                          {done ? t("interviews.reportAction") : t("interviews.continueAction")}
                          <ArrowRight aria-hidden />
                        </Link>
                      </Button>
                      <DeleteSessionButton id={s.id} />
                    </CardContent>
                  </Card>
                </li>
              );
            })}
          </ul>
        )}
      </QueryBoundary>
      {total > PAGE_SIZE && (
        <Pagination
          page={sessions.data?.page ?? state.page}
          size={PAGE_SIZE}
          total={total}
          label={t("interviews.paginationLabel")}
          onPageChange={(page) => {
            setUrl({ page });
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        />
      )}
    </div>
  );
}

/**
 * 66.1: the delete verb the endpoint has always had. It sits on the row rather
 * than in a menu because a list of rehearsals is exactly where a mistaken one
 * is noticed; the dialog names what goes, including that the application card
 * and any note kept from the report stay where they are.
 */
function DeleteSessionButton({ id }: { id: string }) {
  const { t } = useLocale();
  const [open, setOpen] = React.useState(false);
  const remove = useDeleteInterviewSession();
  return (
    <>
      <Button
        variant="ghost"
        size="icon-sm"
        className="shrink-0"
        aria-label={t("interviews.deleteAria")}
        onClick={() => setOpen(true)}
      >
        <Trash2 aria-hidden />
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={t("interviews.deleteTitle")}
        description={t("interviews.deleteDescription")}
        confirmLabel={t("interviews.deleteConfirm")}
        destructive
        loading={remove.isPending}
        onConfirm={() => remove.mutate(id, { onSuccess: () => setOpen(false) })}
      />
    </>
  );
}
