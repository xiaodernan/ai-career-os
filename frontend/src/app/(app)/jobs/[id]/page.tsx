"use client";

import * as React from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Briefcase,
  Building2,
  CalendarClock,
  ExternalLink,
  MapPin,
  MessageSquare,
  Plus,
  Quote,
  Sparkles,
  Target,
  Wallet,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { safeHref } from "@/lib/safe-href";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SectionHeading } from "@/components/common/export-buttons";
import { EvidenceList } from "@/components/ai/evidence-list";
import { AIBadge } from "@/components/ai/ai-badge";
import { SaveToggle } from "@/components/jobs/save-toggle";
import {
  InterviewTopicsCard,
  JdCard,
  MatchPanel,
  PreparationCard,
  SkillGapCard,
} from "@/components/jobs/match-panel";
// The two AI writing panels are the heaviest things the job detail ships;
// they only matter once the reader asks for the tailor or the letter, so
// they leave the first-load path (the bundle budget holds the line at 310 kB).
const TailorPanel = dynamic(() =>
  import("@/components/jobs/tailor-panel").then((m) => m.TailorPanel),
);
const CoverLetterPanel = dynamic(() =>
  import("@/components/jobs/cover-letter-panel").then((m) => m.CoverLetterPanel),
);
import { useApplications, useJob } from "@/lib/hooks/resources";
import { useCreateApplication, useCreateInterviewSession, useRunJobMatch } from "@/lib/hooks/actions";
import { list as listOf, pick, rec, str } from "@/lib/api/normalize";
import { remoteTypeWord, interviewModeName, seniorityWord, salaryBandWord, requirementPriorityWord } from "@/lib/status-words";
import { useLocale } from "@/lib/i18n/locale-context";
import type { Evidence, JdRequirement, PreparationItem, SkillGap } from "@/lib/api/types";
import { normalizeJdParsed } from "@/lib/api/normalize";
import { INTERVIEW_MODES } from "@/lib/interview-modes";
import { pipelineApplication, stageLabel } from "@/lib/pipeline";

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const { t } = useLocale();
  const id = params?.id ?? null;
  const router = useRouter();
  const query = useJob(id);
  const matchRun = useRunJobMatch(id ?? "");
  const addApplication = useCreateApplication();
  const startInterview = useCreateInterviewSession();
  // The action bar's Add button is a promise that pressing it adds something. If this posting is
  // already on the board, the promise is false -- pressing it a second time would file a duplicate
  // card -- so the button becomes a link to the card that already exists.
  const pipeline = useApplications(id ? { jobId: id, size: 1 } : undefined);

  const data = query.data;
  const job = data?.job;
  const match = data?.match ?? null;
  const inPipeline = pipelineApplication(pipeline.data?.items, job?.id);

  /* JD extraction may arrive as a structured object or free text.
   * JobDetail.jd is a JdItem — the extracted dict is nested under `parsed`,
   * so read skills/topics/responsibilities from there, not the JdItem top level. */
  const jd = data?.jd;
  const jdBody = rec(pick(jd, "parsed")) ?? jd;
  const jdText = str(jd, "rawText", "raw_text", "text", "content") ?? job?.description ?? null;
  const jdParsed = normalizeJdParsed(jd);
  const required = jdParsed.requiredSkills;
  const preferred = jdParsed.preferredSkills;
  const responsibilities = jdParsed.responsibilities;
  // A gap belongs to the match, not to the JD: a required skill is only a gap for *this* resume,
  // so there is no analysis-side list to fall back to and the card stays hidden before a match. The
  // citations under it work the same way — #151 measured that `JdItem.parsed` carries no evidence
  // list on any path, so the `normalizeEvidence(jdBody)` fallback here could only ever answer [].
  const gaps: SkillGap[] = match?.skillGaps ?? [];
  const evidence: Evidence[] = match?.evidence ?? [];
  const topics: string[] = match?.interviewTopics?.length ? match.interviewTopics : jdParsed.interviewTopics;
  const prep: PreparationItem[] = match?.preparation ?? [];
  const reqRow = (r: unknown, requiredFlag: boolean): JdRequirement => ({
    skill: str(r, "name", "skill", "text") ?? (typeof r === "string" ? r : undefined),
    required: requiredFlag,
    priority: str(r, "priority", "level") ?? (requiredFlag ? undefined : "nice"),
    evidence: str(r, "evidence_phrase", "evidence", "quote"),
  });
  const requirementRows: JdRequirement[] = [
    ...listOf(jdBody, "requiredSkills", "required_skills", "requirements").map((r) => reqRow(r, true)),
    ...listOf(jdBody, "preferredSkills", "preferred_skills", "criteria").map((r) => reqRow(r, false)),
  ];

  const resumeVersionId = null; // the backend resolves the current version when omitted

  if (query.isPending) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-4 w-24" />
        <Card>
          <CardHeader className="gap-3">
            <Skeleton className="h-7 w-2/5" />
            <Skeleton className="h-4 w-1/4" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-9 w-full max-w-md rounded-lg" />
          </CardContent>
        </Card>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="h-64 rounded-xl" />
        </div>
        <span className="sr-only">{t("jobs.detail.loading")}</span>
      </div>
    );
  }

  if (query.isError || !job) {
    const notFound = (query.error as { isNotFound?: boolean } | null)?.isNotFound;
    return (
      <div className="space-y-6">
        <BackLink />
        <Card>
          <CardContent>
            {notFound ? (
              <EmptyState
                icon={<Briefcase aria-hidden />}
                title={t("jobs.detail.notInSystem")}
                description={t("jobs.detail.notInSystemDescription")}
                action={
                  <Button variant="ai" size="sm" asChild>
                    <Link href="/jobs">{t("jobs.detail.backToJobs")}</Link>
                  </Button>
                }
              />
            ) : (
              <ErrorState
                title={t("jobs.detail.loadFailed")}
                error={query.error}
                onRetry={() => void query.refetch()}
                retrying={query.isFetching}
              />
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  const salary = salaryBandWord(t, job.salaryMin, job.salaryMax, job.salaryCurrency);
  // The reader pasted this link; it is only worth a button if it opens a page.
  const postingHref = safeHref(job.externalUrl);

  return (
    <div className="space-y-6">
      <BackLink />

      {/* Hero */}
      <Card className="gap-4 relative overflow-hidden border-hairline shadow-card">
        {/* Decorative radial wash, masked to the top edge -- an app-surface accent, not a landing */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-40 opacity-70"
          style={{
            background:
              "radial-gradient(120% 100% at 50% 0%, color-mix(in oklch, var(--primary) 12%, transparent), transparent 70%)",
          }}
        />
        {/* Quiet shimmer hairline on the rim (app-surface voice) */}
        <span aria-hidden className="shimmer-rule absolute inset-x-0 top-0 block h-px" />
        <CardHeader className="relative">
          <div className="flex items-start gap-3">
            <span className="flex size-11 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-primary/15 bg-primary/5 text-primary shadow-soft">
              {job.company?.logoUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={job.company.logoUrl} alt="" className="size-full object-contain p-1.5" />
              ) : (
                <Building2 className="size-5" aria-hidden />
              )}
            </span>
            <div className="min-w-0 flex-1">
              <h1
                className="animate-fade-up font-serif text-display-sm font-medium text-balance"
                style={{ animationDelay: "80ms" }}
              >
                {job.title}
              </h1>
              <p
                className="animate-fade-up mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground"
                style={{ animationDelay: "150ms" }}
              >
                {job.company?.name || job.companyName ? (
                  job.companyId ? (
                    <Link href={`/companies/${job.companyId}`} className="flex items-center gap-1 hover:text-foreground">
                      <Building2 className="size-3.5" aria-hidden />
                      {job.company?.name || job.companyName}
                    </Link>
                  ) : (
                    <span>{job.company?.name || job.companyName}</span>
                  )
                ) : (
                  <span>{t("jobs.detail.companyNotResearched")}</span>
                )}
                {job.location && (
                  <span className="flex items-center gap-1">
                    <MapPin className="size-3.5" aria-hidden />
                    {job.location}
                  </span>
                )}
                {salary && (
                  <span className="flex items-center gap-1">
                    <Wallet className="size-3.5" aria-hidden />
                    {salary}
                  </span>
                )}
                {job.remoteType && (
                  <Badge variant="outline" className="text-2xs font-normal">
                    {remoteTypeWord(t, job.remoteType)}
                  </Badge>
                )}
                {job.experienceYears !== undefined && (
                  <Badge variant="outline" className="text-2xs font-normal">
                    {seniorityWord(t, job.experienceYears)}
                  </Badge>
                )}
              </p>
            </div>
            {match && (
              <div
                className={
                  "hidden shrink-0 flex-col items-center gap-1 sm:flex" +
                  (match.overall >= 80 ? " rounded-2xl p-1 glow-halo" : "")
                }
                title={t("jobs.match.scoreAria", { score: Math.round(match.overall) })}
              >
                <MatchMini value={match.overall} />
                <span className="text-2xs text-muted-foreground">AI match</span>
              </div>
            )}
          </div>
        </CardHeader>

        <CardContent>
          {/* Action bar */}
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="ai"
              size="sm"
              loading={matchRun.isPending}
              onClick={() => matchRun.mutate(resumeVersionId)}
            >
              <Target aria-hidden />
              {match ? t("jobs.detail.reAnalyze") : t("jobs.detail.analyze")}
            </Button>

            <Button variant="outline" size="sm" asChild>
              <a href="#tailor">
                <Sparkles aria-hidden />
                {t("jobs.detail.tailorResume")}
              </a>
            </Button>

            <Button variant="outline" size="sm" asChild>
              <a href="#cover-letter">
                <MessageSquare aria-hidden />
                {t("jobs.detail.coverLetter")}
              </a>
            </Button>

            <SaveToggle jobId={job.id} saved={job.saved} withLabel />

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" loading={startInterview.isPending}>
                  <CalendarClock aria-hidden />
                  {t("jobs.detail.interviewPrep")}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-48">
                <DropdownMenuLabel>{t("jobs.detail.mockInterviewMode")}</DropdownMenuLabel>
                {INTERVIEW_MODES.map((m) => (
                  <DropdownMenuItem
                    key={m.value}
                    onClick={() =>
                      startInterview.mutate(
                        { jobId: job.id, mode: m.value },
                        {
                          onSuccess: (res) => {
                            const sid = str(res, "id", "session_id", "sessionId") ?? str(pick(res, "session"), "id");
                            if (sid) router.push(`/interviews/${sid}`);
                          },
                        }
                      )
                    }
                  >
                    {interviewModeName(t, m.value)}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {inPipeline ? (
              <Button
                variant="outline"
                size="sm"
                asChild
                title={t("jobs.detail.inPipelineHint")}
              >
                <Link href={`/applications?application=${inPipeline.id}`}>
                  <Briefcase aria-hidden />
                  {t("jobs.detail.inPipeline", { stage: stageLabel(t, inPipeline.status) })}
                </Link>
              </Button>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                loading={addApplication.isPending}
                onClick={() =>
                  addApplication.mutate({
                    jobId: job.id,
                    companyId: job.companyId || undefined,
                    companyName: job.company?.name ?? job.companyName ?? undefined,
                    title: job.title,
                    status: "applied",
                  })
                }
              >
                <Plus aria-hidden />
                {t("jobs.detail.addToPipeline")}
              </Button>
            )}

            {postingHref && (
              <Button variant="link" size="sm" asChild className="ml-auto">
                <a href={postingHref} target="_blank" rel="noopener noreferrer nofollow">
                  {t("jobs.detail.originalPosting")}
                  <ExternalLink aria-hidden />
                </a>
              </Button>
            )}
          </div>

          {matchRun.error != null && (
            <p role="alert" className="mt-3 text-xs text-destructive">
              {t("jobs.detail.matchRunFailed")}{" "}
              {matchRun.error instanceof Error
                ? matchRun.error.message
                : t("jobs.detail.unknownError")}
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0 space-y-4">
          <JdCard
            rawText={jdText}
            requiredSkills={required}
            preferredSkills={preferred}
            responsibilities={responsibilities}
          />

          {requirementRows.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t("jobs.detail.requirementsBreakdown")}</CardTitle>
                <CardDescription>{t("jobs.detail.requirementsBreakdownDescription")}</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="divide-y divide-border/60">
                  {requirementRows.map((r, i) => (
                    <li key={i} className="flex items-center gap-3 py-2 text-sm first:pt-0 last:pb-0">
                      <span className="min-w-0 flex-1 truncate">{r.skill}</span>
                      <Badge variant={r.required ? "ai" : "outline"} className="shrink-0 text-2xs font-normal">
                        {requirementPriorityWord(t, r.priority ?? (r.required ? "must" : "nice"))}
                      </Badge>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <SectionHeading
                eyebrow={t("eyebrows.explainability")}
                icon={<Quote className="size-4" aria-hidden />}
                title={t("jobs.detail.resumeEvidence")}
                description={t("jobs.detail.resumeEvidenceDescription")}
              />
            </CardHeader>
            <CardContent>
              {evidence.length ? (
                <EvidenceList items={evidence} limit={5} hrefFor={(e) => (e.source?.docId ? `/knowledge?src=${e.source.docId}` : undefined)} />
              ) : match ? (
                <p className="text-sm text-muted-foreground">
                  {t("jobs.detail.noCitations")}
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t("jobs.detail.noAnalysis")}
                </p>
              )}
            </CardContent>
          </Card>

          <div id="tailor" className="scroll-mt-20">
            <TailorPanel jobId={job.id} resumeVersionId={resumeVersionId} />
          </div>
          <div id="cover-letter" className="scroll-mt-20">
            <CoverLetterPanel
              jobId={job.id}
              resumeVersionId={resumeVersionId}
              applicationId={inPipeline?.id ?? null}
            />
          </div>
        </div>

        <aside className="space-y-4">
          <MatchPanel
            match={match}
            analyzing={matchRun.isPending}
            onAnalyze={() => matchRun.mutate(resumeVersionId)}
          />
          <SkillGapCard gaps={gaps} />
          <InterviewTopicsCard topics={topics} />
          <PreparationCard items={prep} />

          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("jobs.detail.sources")}</CardTitle>
              <CardDescription>{t("jobs.detail.sourcesDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-muted-foreground">
              <p className="flex items-center gap-2">
                <AIBadge label={t("jobs.detail.sourceBadgeJob")} />
                {job.source === "user_paste" ? t("jobs.detail.pastedByYou") : job.source === "agent_research" ? t("jobs.detail.foundByResearch") : t("jobs.detail.seededBoard")}
              </p>
              <Separator className="my-1" />
              <p>
                {t("jobs.detail.scoreFrom")}{" "}
                <span className="font-mono text-foreground">/jobs/{job.id}/match</span> ·{" "}
                {t("jobs.detail.evidenceFrom")}
              </p>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}

/* ------------------------------- fragments -------------------------------- */

function BackLink() {
  const { t } = useLocale();
  return (
    <Link
      href="/jobs"
      className="-ml-1 inline-flex w-fit items-center gap-1.5 rounded-md px-1 text-sm text-muted-foreground hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-primary/30"
    >
      <ArrowLeft className="size-4" aria-hidden />
      {t("jobs.detail.backToJobs")}
    </Link>
  );
}

function MatchMini({ value }: { value: number }) {
  const { t } = useLocale();
  return (
    <span
      className={cn(
        "flex size-12 items-center justify-center rounded-full border-4 text-sm font-semibold tabular-nums",
        value >= 80
          ? "border-success/40 text-success"
          : value >= 60
            ? "border-primary/40 text-primary"
            : value >= 40
              ? "border-warning/40 text-warning"
              : "border-destructive/40 text-destructive"
      )}
      aria-label={t("jobs.match.scoreAria", { score: value })}
    >
      {Math.round(value)}
    </span>
  );
}
