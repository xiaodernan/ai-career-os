"use client";

import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  Briefcase,
  CalendarClock,
  Library,
  MessageSquare,
  Sparkles,
  Trophy,
} from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingListSkeleton, LoadingMetricGridSkeleton } from "@/components/common/loading-skeletons";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MatchRing } from "@/components/ai/match-ring";
import { ApiError } from "@/lib/api/client";
import { useUser } from "@/lib/hooks/auth";
import {
  useActivity,
  useApplications,
  useDashboard,
  useKnowledgeSources,
} from "@/lib/hooks/resources";
import { scoreBand } from "@/components/ai/match-ring";

function useGreeting(): string {
  const [greeting, setGreeting] = React.useState("Hello");
  React.useEffect(() => {
    const h = new Date().getHours();
    setGreeting(h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening");
  }, []);
  return greeting;
}

/** Standard async-surface contract: skeleton → content | designed empty-state (with retry). */
function StateNotice({ error, onRetry, title, empty }: { error: unknown; onRetry: () => void; title: string; empty?: boolean }) {
  const notLive = !empty && error instanceof ApiError && error.isNotFound;
  if (empty) {
    return (
      <EmptyState
        icon={<Sparkles aria-hidden />}
        title={`No ${title.toLowerCase()} yet`}
        description="This is yours — nothing shows up here until real activity happens. Copilot can start building it now."
        action={
          <Button variant="outline" size="sm" asChild>
            <Link href="/copilot">Open Copilot</Link>
          </Button>
        }
      />
    );
  }
  return (
    <EmptyState
      icon={<Library aria-hidden />}
      title={notLive ? `${title} isn't connected yet` : `Couldn't load ${title.toLowerCase()}`}
      description={
        notLive
          ? "The backend endpoint for this surface isn't live yet. It will appear here as soon as the API serves it — no placeholder data until then."
          : error instanceof ApiError
            ? error.message
            : "Network unavailable. Check the API server."
      }
      action={
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      }
    />
  );
}

export default function DashboardPage() {
  const greeting = useGreeting();
  const { data: user } = useUser();
  const metrics = useDashboard();
  const applications = useApplications({ size: 5 });
  const sources = useKnowledgeSources();
  const activity = useActivity();

  const m = metrics.data;

  return (
    <div className="space-y-8">
      <PageHeader
        title={
          <>
            {greeting},{" "}
            <span className="italic text-primary">{user?.displayName?.split(" ")[0] ?? "welcome"}</span>
          </>
        }
        description="Your pipeline at a glance — every number here comes from the live API."
        actions={
          <>
            <Button variant="ai" asChild>
              <Link href="/copilot">
                <Sparkles aria-hidden />
                Ask Copilot
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/applications">
                Open pipeline
                <ArrowRight aria-hidden />
              </Link>
            </Button>
          </>
        }
      />

      {/* Metrics */}
      {metrics.isPending ? (
        <LoadingMetricGridSkeleton />
      ) : metrics.isError || !m ? (
        <Card>
          <CardContent>
            <StateNotice error={metrics.error ?? new Error("No data")} onRetry={() => metrics.refetch()} title="Dashboard stats" />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Card>
            <CardHeader>
              <CardDescription>Applications</CardDescription>
              <CardTitle className="text-2xl font-semibold tabular-nums">{m.applications ?? "—"}</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              <CalendarClock className="mr-1 inline size-3.5" aria-hidden /> in your pipeline
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardDescription>Interviews</CardDescription>
              <CardTitle className="text-2xl font-semibold tabular-nums">{m.interviews ?? "—"}</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              <MessageSquare className="mr-1 inline size-3.5" aria-hidden /> scheduled or practiced
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardDescription>Offers</CardDescription>
              <CardTitle className="text-2xl font-semibold tabular-nums">{m.offers ?? "—"}</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              <Trophy className="mr-1 inline size-3.5" aria-hidden /> ready for decision
            </CardContent>
          </Card>
          <Card className="items-center justify-center sm:items-start">
            <CardHeader className="w-full">
              <CardDescription>Avg match score</CardDescription>
            </CardHeader>
            <CardContent className="flex w-full items-center gap-3">
              {typeof m.avgMatch === "number" ? (
                <MatchRing value={m.avgMatch} size={56} thickness={5} label="Average match" />
              ) : (
                <span className="text-2xl font-semibold">—</span>
              )}
              <p className="text-xs text-muted-foreground">
                across saved jobs, computed from your resume evidence
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Recent applications */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent applications</CardTitle>
            <CardDescription>Freshest rows from /applications</CardDescription>
          </CardHeader>
          <CardContent className="px-3">
            {applications.isPending ? (
              <LoadingListSkeleton rows={3} />
            ) : applications.isError || !applications.data?.items.length ? (
              <StateNotice
                error={applications.error ?? new Error("No data")}
                onRetry={() => applications.refetch()}
                title="Applications"
                empty={!applications.error && !applications.data?.items.length}
              />
            ) : (
              <ul>
                {applications.data.items.map((app) => (
                  <li key={app.id} className="flex items-center gap-3 border-b border-border/50 px-3 py-2.5 last:border-0">
                    <span className="flex size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                      <Briefcase className="size-4" aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{app.title}</p>
                      <p className="truncate text-xs text-muted-foreground">{app.company?.name}</p>
                    </div>
                    <Badge variant="outline" className="capitalize">{app.status.replace("_", " ")}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Knowledge sources */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Knowledge base</CardTitle>
            <CardDescription>What the agents can cite</CardDescription>
          </CardHeader>
          <CardContent className="px-3">
            {sources.isPending ? (
              <LoadingListSkeleton rows={3} />
            ) : sources.isError || !sources.data?.items.length ? (
              <StateNotice
                error={sources.error ?? new Error("No data")}
                onRetry={() => sources.refetch()}
                title="Knowledge sources"
                empty={!sources.error && !sources.data?.items.length}
              />
            ) : (
              <ul>
                {sources.data.items.slice(0, 5).map((src) => (
                  <li key={src.id} className="flex items-center gap-3 border-b border-border/50 px-3 py-2.5 last:border-0">
                    <span className="flex size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                      <Library className="size-4" aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{src.title}</p>
                      <p className="truncate text-xs text-muted-foreground capitalize">{src.kind.replace("_", " ")}</p>
                    </div>
                    <Badge variant={src.status === "ready" ? "success" : src.status === "failed" ? "destructive" : "secondary"} className="capitalize">
                      {src.status}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* AI activity */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">AI activity</CardTitle>
            <CardDescription>Latest agent runs across your workspace</CardDescription>
          </CardHeader>
          <CardContent className="px-3">
            {activity.isPending ? (
              <LoadingListSkeleton rows={3} />
            ) : activity.isError || !activity.data?.items.length ? (
              <StateNotice
                error={activity.error ?? new Error("No data")}
                onRetry={() => activity.refetch()}
                title="AI activity"
                empty={!activity.error && !activity.data?.items.length}
              />
            ) : (
              <ul className="grid gap-1 sm:grid-cols-2">
                {activity.data.items.slice(0, 6).map((evt) => (
                  <li key={evt.id} className="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-accent/50">
                    <span
                      className={`size-1.5 shrink-0 rounded-full ${
                        scoreBand(evt.status === "ok" || evt.status === "completed" ? 100 : 30) === "strong"
                          ? "bg-success"
                          : "bg-warning"
                      }`}
                      aria-hidden
                    />
                    <p className="min-w-0 flex-1 truncate text-sm">{evt.summary ?? evt.kind}</p>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {evt.agent ?? evt.kind} · {new Date(evt.createdAt).toLocaleDateString()}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
