"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, CalendarClock, FileBarChart, MessagesSquare, Plus } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
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
import { str } from "@/lib/api/normalize";
import { formatDateTime, relativeTime, titleCase } from "@/lib/format";
import { INTERVIEW_MODES } from "@/lib/interview-modes";

export default function InterviewsPage() {
  const sessions = useInterviewSessions();
  const create = useCreateInterviewSession();
  const router = useRouter();

  const start = (mode: string) =>
    create.mutate(
      { mode },
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
        title="Interviews"
        description="Adaptive mock interviews: the agent follows up while your answers are strong, moves on when they're not, and pushes deeper as you prove depth. Every evaluation cites your own material."
        actions={
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ai" loading={create.isPending}>
                <Plus aria-hidden />
                Start interview
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-72">
              <DropdownMenuLabel>Mode</DropdownMenuLabel>
              {INTERVIEW_MODES.map((m) => (
                <DropdownMenuItem key={m.value} onSelect={() => start(m.value)}>
                  <span className="flex min-w-0 flex-col">
                    <span>{m.label}</span>
                    <span className="text-xs text-muted-foreground">{m.hint}</span>
                  </span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        }
      />

      <QueryBoundary
        query={sessions}
        skeleton={<LoadingListSkeleton rows={4} />}
        empty={{
          icon: <CalendarClock aria-hidden />,
          title: "No mock interviews yet",
          description:
            "Pick a mode above — the session is built from your resume and the job you're targeting, so answers are graded against evidence, not trivia.",
          action: (
            <Button variant="outline" size="sm" asChild>
              <Link href="/jobs">Pick a target job first</Link>
            </Button>
          ),
        }}
        notLive={{
          title: "This API build has no interview sessions",
          description:
            "GET /interview/sessions answered 404, so this frontend and the backend it is talking to are different versions. The runner is wired and activates as soon as they match.",
        }}
        boxed={false}
      >
        {(page) => (
          <ul className="space-y-3">
            {page.items.map((s) => {
              const done = s.status === "completed";
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
                          {titleCase(s.mode)} interview
                          {s.jobTitle ? ` · ${s.jobTitle}` : s.companyName ? ` · ${s.companyName}` : ""}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-muted-foreground">
                          {s.questionCount ? `${s.questionCount} questions · ` : ""}
                          {done
                            ? `finished ${relativeTime(s.finishedAt)}`
                            : `started ${formatDateTime(s.startedAt)}`}
                        </p>
                      </div>
                      {!done && s.status === "active" && (
                        <Badge variant="ai" className="shrink-0 text-2xs font-normal">
                          In progress
                        </Badge>
                      )}
                      {done && typeof s.overall === "number" && (
                        <Badge variant={s.overall >= 75 ? "success" : s.overall >= 50 ? "warning" : "destructive"} className="shrink-0 tabular-nums">
                          {Math.round(s.overall)}/100
                        </Badge>
                      )}
                      <Button variant="outline" size="sm" asChild className="shrink-0">
                        <Link href={done ? `/interviews/${s.id}/report` : `/interviews/${s.id}`}>
                          {done ? "Report" : "Continue"}
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
    </div>
  );
}
