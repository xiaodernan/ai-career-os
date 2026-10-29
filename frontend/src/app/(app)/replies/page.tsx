"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpRight, Inbox } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/page-header";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { Pagination } from "@/components/common/pagination";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { relativeTime } from "@/lib/format";
import { stageLabel } from "@/lib/pipeline";
import { lastPageOf } from "@/lib/page-window";
import { useLocale } from "@/lib/i18n/locale-context";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useApplications } from "@/lib/hooks/resources";
import { useFileInboundMail, useInboundMails } from "@/lib/hooks/replies";
import { useUpdateApplication } from "@/lib/hooks/actions";
import type { ApplicationStatus, InboundMail } from "@/lib/api/types";

/**
 * The replies page (roadmap 37.4).
 *
 * Every row is a letter a recruiter sent back to the account's forwarding address. The
 * page's one promise is that a letter either names the application it answers or asks the
 * reader to pick one: the match is made by the server against the letter's own words, and
 * when it cannot narrow to a single card the letter waits here rather than landing on the
 * wrong timeline.
 *
 * The suggested stage is advice, not a decision. It comes from the reading, it is shown on
 * the card the letter is actually filed on, and it moves nothing until the reader confirms
 * -- the same confirmation every other stage change goes through.
 */

type Translate = (key: string, vars?: Record<string, string | number>) => string;

const PAGE_SIZE = 20;
// Module-level so `setUrl` (a `useCallback` keyed on this object) is stable across renders.
const PAGE_DEFAULTS: { mail?: string; page: number } = { mail: undefined, page: 0 };

function intentKey(intent: string | null): string {
  switch (intent) {
    case "rejection":
      return "replies.intents.rejection";
    case "interview":
      return "replies.intents.interview";
    case "offer":
      return "replies.intents.offer";
    case "info":
      return "replies.intents.info";
    case "other":
      return "replies.intents.other";
    default:
      return "replies.intents.unread";
  }
}

function intentVariant(intent: string | null): "warning" | "outline" | "destructive" | "success" | "ai" {
  switch (intent) {
    case "rejection":
      return "destructive";
    case "offer":
      return "success";
    case "interview":
      return "ai";
    case "info":
      return "outline";
    default:
      return "outline";
  }
}

function titleOf(mail: InboundMail, t: Translate): string {
  return mail.subject || t("replies.unnamed");
}

export default function RepliesPage() {
  const { t, locale } = useLocale();
  const [state, setUrl] = useUrlState<{ mail?: string; page: number }>(PAGE_DEFAULTS, {
    numericKeys: ["page"],
  });
  const letters = useInboundMails({ page: state.page, size: PAGE_SIZE });
  const applications = useApplications({ size: 100 });
  const file = useFileInboundMail();
  const apply = useUpdateApplication();
  // mail id → the card the reader picked for it; a picked value lives only on this screen.
  const [picked, setPicked] = React.useState<Record<string, string>>({});
  const [applyFor, setApplyFor] = React.useState<InboundMail | null>(null);

  const items = letters.data?.items ?? [];
  const total = letters.data?.total ?? 0;
  // A past-the-end page is an empty window over a real total: correct the URL to the last
  // page that exists, in a layout effect so the stale commit is replaced before it paints.
  const lastPage = letters.data ? lastPageOf(total, letters.data.size) : 0;
  React.useLayoutEffect(() => {
    if (letters.data && state.page > lastPage) setUrl({ page: lastPage });
  }, [letters.data, state.page, lastPage, setUrl]);

  const fileMail = (mail: InboundMail) => {
    const applicationId = picked[mail.id];
    if (!applicationId) return;
    file.mutate(
      { id: mail.id, applicationId },
      {
        onSuccess: () =>
          setPicked((cur) => {
            const next = { ...cur };
            delete next[mail.id];
            return next;
          }),
      }
    );
  };

  const applyStage = () => {
    if (!applyFor?.applicationId || !applyFor.suggestedStage) return;
    apply.mutate(
      {
        id: applyFor.applicationId,
        patch: { status: applyFor.suggestedStage as ApplicationStatus },
      },
      {
        onSettled: () => setApplyFor(null),
        onSuccess: () => toast.success(t("replies.applyStageToast")),
      }
    );
  };

  const applyTitle = applyFor
    ? applyFor.applicationTitle || titleOf(applyFor, t)
    : "";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader title={t("replies.title")} description={t("replies.description")} />

      <Card>
        <CardContent className="p-6">
          {letters.isPending ? (
            <div className="space-y-2" role="status">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-3/4" />
              <span className="sr-only">{t("replies.loading")}</span>
            </div>
          ) : letters.isError ? (
            <ErrorState
              title={t("replies.unavailable")}
              error={letters.error}
              onRetry={() => void letters.refetch()}
              retrying={letters.isFetching}
            />
          ) : items.length ? (
            <ul className="space-y-2">
              {items.map((mail) => {
                const highlighted = state.mail === mail.id;
                const pending = file.isPending && file.variables?.id === mail.id;
                const intended = mail.applicationTitle || titleOf(mail, t);
                return (
                  <li
                    key={mail.id}
                    className={`rounded-lg border p-3 ${
                      highlighted ? "border-primary ring-1 ring-primary/30" : "border-border/70"
                    }`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant={intentVariant(mail.intent)}>
                            {t(intentKey(mail.intent))}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {relativeTime(mail.receivedAt, locale)}
                          </span>
                          {(mail.company || mail.role) && (
                            <span className="text-xs text-muted-foreground">
                              {[mail.company, mail.role].filter(Boolean).join(" · ")}
                            </span>
                          )}
                        </div>
                        <p className="text-sm font-medium">{titleOf(mail, t)}</p>
                        <p className="text-xs text-muted-foreground">
                          {mail.fromAddress || t("replies.senderUnknown")}
                        </p>
                        {mail.bodyText && (
                          <details className="pt-1">
                            <summary className="cursor-pointer text-xs text-muted-foreground">
                              {t("replies.readLetter")}
                            </summary>
                            <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">
                              {mail.bodyText}
                            </p>
                          </details>
                        )}
                      </div>

                      <div className="flex shrink-0 flex-col items-end gap-2">
                        {mail.applicationId ? (
                          <>
                            <span className="text-xs text-muted-foreground">
                              {t("replies.filedOn", { title: intended })}
                            </span>
                            <div className="flex flex-wrap items-center justify-end gap-2">
                              <Button asChild size="sm" variant="ghost">
                                <Link href={`/applications?application=${mail.applicationId}`}>
                                  <ArrowUpRight aria-hidden />
                                  {t("replies.openApplication")}
                                </Link>
                              </Button>
                              {mail.suggestedStage && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => setApplyFor(mail)}
                                >
                                  {t("replies.applyStage", {
                                    stage: stageLabel(t, mail.suggestedStage),
                                  })}
                                </Button>
                              )}
                            </div>
                          </>
                        ) : (
                          <div className="flex flex-col items-end gap-2">
                            {applications.isPending ? null : applications.data?.items.length ? (
                              <div className="flex items-center gap-2">
                                <Select
                                  value={picked[mail.id] ?? ""}
                                  onValueChange={(value) =>
                                    setPicked((cur) => ({ ...cur, [mail.id]: value }))
                                  }
                                >
                                  <SelectTrigger
                                    size="sm"
                                    aria-label={t("replies.pickApplication")}
                                  >
                                    <SelectValue placeholder={t("replies.pickApplication")} />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {applications.data.items.map((app) => (
                                      <SelectItem key={app.id} value={app.id}>
                                        <span>{app.title}</span>
                                        {app.companyName && (
                                          <span className="text-muted-foreground">
                                            · {app.companyName}
                                          </span>
                                        )}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  disabled={!picked[mail.id] || pending}
                                  loading={pending}
                                  onClick={() => fileMail(mail)}
                                >
                                  {t("replies.file")}
                                </Button>
                              </div>
                            ) : (
                              <span className="text-xs text-muted-foreground">
                                {t("replies.notFiled")}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <EmptyState
              icon={<Inbox aria-hidden />}
              title={t("replies.empty")}
              description={t("replies.emptyDescription")}
              action={
                <Button asChild size="sm" variant="outline">
                  <Link href="/settings">{t("replies.getAddress")}</Link>
                </Button>
              }
            />
          )}
        </CardContent>
      </Card>

      {total > PAGE_SIZE && (
        <Pagination
          page={letters.data?.page ?? state.page}
          size={PAGE_SIZE}
          total={total}
          label={t("replies.paginationLabel")}
          onPageChange={(page) => {
            setUrl({ page });
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        />
      )}

      <ConfirmDialog
        open={applyFor !== null}
        onOpenChange={(open) => !open && setApplyFor(null)}
        title={
          applyFor
            ? t("replies.applyStageConfirm", {
                title: applyTitle,
                stage: stageLabel(t, applyFor.suggestedStage ?? ""),
              })
            : ""
        }
        description={
          applyFor
            ? t("replies.applyStageDescription", {
                intent: t(intentKey(applyFor.intent)),
                stage: stageLabel(t, applyFor.suggestedStage ?? ""),
              })
            : undefined
        }
        confirmLabel={
          applyFor
            ? t("replies.applyStage", { stage: stageLabel(t, applyFor.suggestedStage ?? "") })
            : t("common.confirm")
        }
        destructive={applyFor?.suggestedStage === "rejected"}
        loading={apply.isPending}
        onConfirm={applyStage}
      />
    </div>
  );
}
