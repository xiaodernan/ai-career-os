"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Briefcase, CalendarClock, FileBarChart, MessagesSquare, Plus } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { Pagination } from "@/components/common/pagination";
import { lastPageOf } from "@/lib/page-window";
import { QueryBoundary } from "@/components/common/query-boundary";
import { LoadingListSkeleton } from "@/components/common/loading-skeletons";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useCreateInterviewSession } from "@/lib/hooks/actions";
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
const PAGE_DEFAULTS: { page: number; application?: string } = { page: 0 };

export default function InterviewsPage() {
  const { t, locale } = useLocale();
  // The page index lives in the URL, so a reload or a shared list link opens the same window.
  const [state, setUrl] = useUrlState<{ page: number; application?: string }>(
    PAGE_DEFAULTS,
    { numericKeys: ["page"] }
  );
  // 57.1: the drawer's rehearsals link names a card, so the list narrows to it.
  // The filter travels in the URL like the page does, so the narrowed list is
  // shareable and a reload does not silently widen it back to everything.
  const applicationId = state.application;
  const sessions = useInterviewSessions({
    page: state.page,
    size: PAGE_SIZE,
    applicationId,
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
      <PageHeader
        title={t("interviews.title")}
        description={t("interviews.description")}
        actions={
          <div className="flex items-center gap-2">
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
              <Button variant="ai" loading={create.isPending}>
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
