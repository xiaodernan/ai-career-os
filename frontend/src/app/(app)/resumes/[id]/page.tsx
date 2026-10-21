"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Award,
  Briefcase,
  Check,
  Download,
  ExternalLink,
  FolderGit2,
  GraduationCap,
  Hammer,
  Link2,
  MapPin,
  ScanSearch,
  Sparkles,
  Target,
  Wrench,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SectionHeading } from "@/components/common/export-buttons";
import { DiffView } from "@/components/common/diff-view";
import { DimensionBars } from "@/components/common/skill-chips";
import { MatchRing } from "@/components/ai/match-ring";
import { TaskProgress } from "@/components/ai/task-stream";
import { useParseResume, useSetCurrentResume } from "@/lib/hooks/actions";
import { useResume, useResumeVersions } from "@/lib/hooks/resources";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { normalizeStructuredResume, normalizeTailorDiff, str } from "@/lib/api/normalize";
import { formatDate, downloadBlob, downloadText } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";
import type { ResumeProject, ResumeScore, StructuredResume } from "@/lib/api/types";

const PARSE_STAGE_KEYS = [
  "resumes.detail.stages.reading",
  "resumes.detail.stages.extracting",
  "resumes.detail.stages.structuring",
  "resumes.detail.stages.grading",
];

export default function ResumeDetailPage() {
  const params = useParams<{ id: string }>();
  const { t } = useLocale();
  const id = params?.id ?? null;
  const resume = useResume(id);
  const versionsQ = useResumeVersions(id);
  const parse = useParseResume(id ?? "");
  const setCurrent = useSetCurrentResume(id ?? "");
  const [parseTask, setParseTask] = React.useState<string | null>(null);
  const [downloading, setDownloading] = React.useState(false);

  // The original upload's bytes, saved the way the other artifacts are: blob, click, revoke.
  // The name comes from the server — the route that read the document row knows it.
  const downloadOriginal = React.useCallback((resumeId: string, done: () => void) => {
    setDownloading(true);
    api
      .download(endpoints.resumeFile(resumeId))
      .then(({ blob, name }) => {
        downloadBlob(name ?? "original-file", blob);
        done();
      })
      .catch((e) => toast.error(e instanceof Error ? e.message : "Download failed."))
      .finally(() => setDownloading(false));
  }, []);

  const r = resume.data;

  if (resume.isPending) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-24 rounded-xl" />
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <Skeleton className="h-96 rounded-xl" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
        <span className="sr-only">{t("resumes.detail.loading")}</span>
      </div>
    );
  }

  if (resume.isError || !r) {
    return (
      <div className="space-y-6">
        <BackLink />
        <Card>
          <CardContent>
            {resume.isError && (resume.error as { isNotFound?: boolean })?.isNotFound ? (
              <EmptyState
                icon={<FolderGit2 aria-hidden />}
                title={t("resumes.detail.notInWorkspace")}
                description={t("resumes.detail.notInWorkspaceDescription")}
                action={
                  <Button variant="ai" size="sm" asChild>
                    <Link href="/resumes">{t("resumes.detail.backToResumes")}</Link>
                  </Button>
                }
              />
            ) : (
              <ErrorState
                title={t("resumes.detail.loadFailed")}
                error={resume.error}
                onRetry={() => void resume.refetch()}
                retrying={resume.isFetching}
              />
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  const structured = normalizeStructuredResume(r.structured);

  return (
    <div className="space-y-6">
      <BackLink />

      {/* Header + actions */}
      <Card className="gap-4">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h1 className="font-serif text-display-sm font-medium text-balance">{r.title}</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                added {r.createdAt ? formatDate(r.createdAt) : "—"} ·{" "}
                <StatusBadge status={r.status} />
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {/* Live when the detail body carries sourceFileKey, which the backend produces from
                  the resume.source_file_key column and gates the download route. */}
              {r.sourceFileKey && (
                <Button
                  variant="outline"
                  size="sm"
                  loading={downloading}
                  onClick={() =>
                    downloadOriginal(r.id, () => {
                      toast.success(t("resumes.detail.originalDownloaded"));
                    })
                  }
                >
                  <Download aria-hidden />
                  {t("resumes.detail.originalFile")}
                </Button>
              )}
              <Button
                variant="ai"
                size="sm"
                loading={parse.isPending}
                onClick={() =>
                  parse.mutate(undefined, {
                    onSuccess: (res) => {
                      const task = str(res, "taskId", "task_id");
                      if (task) setParseTask(task);
                      else toast.success("Parsed — structured profile updated.");
                    },
                  })
                }
              >
                <ScanSearch aria-hidden />
                {structured ? "Re-parse" : "Parse now"}
              </Button>
            </div>
          </div>

          {(parse.isPending || parseTask) && (
            <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
              {parseTask ? (
                <TaskProgress
                  taskId={parseTask}
                  seed={PARSE_STAGE_KEYS.map((k) => ({ id: k, label: t(k) }))}
                  title={t("resumes.detail.parsing")}
                  onDone={() => {
                    setParseTask(null);
                    void resume.refetch();
                  }}
                />
              ) : (
                <TaskProgress
                  pending
                  title={t("resumes.detail.parsing")}
                  steps={PARSE_STAGE_KEYS.map((k, i) => ({
                    id: k,
                    label: t(k),
                    status: (i === 0 ? "active" : "pending") as "active" | "pending",
                  }))}
                  pendingLabel={t("resumes.detail.submitting")}
                />
              )}
            </div>
          )}
        </CardHeader>

        <CardContent>
          {parse.error != null && (
            <p role="alert" className="text-xs text-destructive">
              {t("resumes.detail.parseFailed")}{" "}
              {parse.error instanceof Error
                ? parse.error.message
                : t("jobs.detail.unknownError")}
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_21rem]">
        {/* Structured profile */}
        <div className="min-w-0 space-y-4">
          {structured ? (
            <StructuredProfileView structured={structured} />
          ) : (
            <Card>
              <CardContent>
                <EmptyState
                  icon={<ScanSearch aria-hidden />}
                  title={t("resumes.detail.notParsedYet")}
                  description={
                    r.status === "parsing" || r.status === "ingesting"
                      ? "The extraction agent is working through this document — the structured profile appears automatically when it's done."
                      : "Run the parse above to turn this file into a queryable profile: experience, projects, education and skills with citations back to the document."
                  }
                />
              </CardContent>
            </Card>
          )}
        </div>

        <aside className="space-y-4">
          {/* Score widget */}
          <Card>
            <CardHeader className="pb-3">
              <SectionHeading
                eyebrow="Reviewer agent"
                icon={<Target className="size-4" aria-hidden />}
                title={t("resumes.detail.quality")}
                description={t("resumes.detail.qualityDescription")}
              />
            </CardHeader>
            <CardContent>
              <ScorePanel score={r.score ?? null} />
            </CardContent>
          </Card>

          {/* Versions */}
          <Card>
            <CardHeader className="pb-3">
              <SectionHeading
                eyebrow="History"
                icon={<FolderGit2 className="size-4" aria-hidden />}
                title={t("resumes.detail.versions")}
                description={t("resumes.detail.versionsDescription")}
              />
            </CardHeader>
            <CardContent className="space-y-3">
              {versionsQ.isPending ? (
                <Skeleton className="h-16 w-full" />
              ) : versionsQ.isError ? (
                <ErrorState
                  className="px-0 py-6"
                  title={t("resumes.detail.versionsLoadFailed")}
                  error={versionsQ.error}
                  onRetry={() => void versionsQ.refetch()}
                  retrying={versionsQ.isFetching}
                />
              ) : (versionsQ.data ?? []).length ? (
                (versionsQ.data ?? []).map((v) => {
                  const isCurrent = v.isCurrent || v.id === r.currentVersionId;
                  const diff = v.diff ? normalizeTailorDiff(v.diff) : null;
                  return (
                    <div
                      key={v.id}
                      className={cn(
                        "rounded-lg border p-3",
                        isCurrent ? "border-primary/40 bg-primary/5" : "border-border/70"
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <p className="min-w-0 flex-1 truncate text-sm font-medium">
                          {v.label ?? `Version ${v.versionNo ?? v.id.slice(0, 8)}`}
                        </p>
                        {isCurrent ? (
                          <Badge variant="success" className="gap-1 text-2xs font-normal">
                            <Check className="size-3" aria-hidden />
                            Current
                          </Badge>
                        ) : (
                          <Button
                            variant="ghost"
                            size="xs"
                            loading={setCurrent.isPending && setCurrent.variables === v.id}
                            onClick={() => setCurrent.mutate(v.id)}
                          >
                            {t("resumes.detail.setCurrent")}
                          </Button>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {v.source ? `${v.source.replace(/_/g, " ")} · ` : ""}
                        {v.createdAt ? formatDate(v.createdAt) : "date unavailable"}
                        {typeof v.score?.overall === "number" ? ` · score ${v.score.overall}` : ""}
                      </p>
                      {diff && (diff.accepted.length > 0 || diff.rejected.length > 0) && (
                        <div className="mt-2 border-t border-border/60 pt-2">
                          <p className="mb-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
                            {t("resumes.detail.diffVsPrevious")}
                          </p>
                          <DiffView accepted={diff.accepted} rejected={diff.rejected} />
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <p className="text-sm text-muted-foreground">
                  No stored versions yet — each parse of this resume stores a new one.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <SectionHeading
                eyebrow="Data sources"
                icon={<Sparkles className="size-4" aria-hidden />}
                title={t("resumes.detail.whereFrom")}
              />
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-muted-foreground">
              <p>
                {t("resumes.detail.profileFrom")}{" "}
                <span className="font-mono text-foreground">/resumes/{r.id}</span>{" "}
                {t("resumes.detail.structuredJson")}
              </p>
              <p>
                {t("resumes.detail.scoreFrom")}{" "}
                <Link href="/knowledge" className="font-medium text-primary underline-offset-4 hover:underline">
                  {t("resumes.detail.knowledge")}
                </Link>
                .
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
      href="/resumes"
      className="-ml-1 inline-flex w-fit items-center gap-1.5 rounded-md px-1 text-sm text-muted-foreground hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-primary/30"
    >
      <ArrowLeft className="size-4" aria-hidden />
      {t("resumes.detail.backToResumes")}
    </Link>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "parsed"
      ? "success"
      : status === "failed"
        ? "destructive"
        : status === "parsing" || status === "ingesting"
          ? "warning"
          : "secondary";
  return (
    <Badge variant={variant} className="text-2xs font-normal capitalize">
      {status}
    </Badge>
  );
}

function ScorePanel({ score }: { score: ResumeScore | null }) {
  const { t } = useLocale();
  if (!score || score.overall == null) {
    return (
      <p className="text-sm text-muted-foreground">
        No review score yet. It is produced by the parsing run — trigger a re-parse above to
        generate one.
      </p>
    );
  }
  const dims = [
    { key: "bullets", label: "Bullets & metric density" },
    { key: "structure", label: "Structure & scannability" },
    { key: "impact", label: "Impact wording" },
    { key: "clarity", label: "Clarity" },
    { key: "keywords", label: "Keyword coverage" },
  ]
    .map((d) => ({
      ...d,
      score: (score as unknown as Record<string, number | undefined>)[d.key],
    }))
    .filter((d): d is { key: string; label: string; score: number } => typeof d.score === "number");

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <MatchRing
          value={score.overall}
          size={64}
          thickness={6}
          label={t("resumes.detail.scoreRing")}
        />
        <div className="min-w-0 text-sm">
          <p className="font-medium">
            {t("resumes.detail.overall")} {score.overall}/100
          </p>
        </div>
      </div>
      {dims.length > 0 && <DimensionBars dimensions={dims} dense />}
      {score.gaps && score.gaps.length > 0 && (
        <div>
          <p className="mb-1 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
            {t("resumes.detail.gapsFound")}
          </p>
          <ul className="ml-4 list-disc space-y-1 text-xs text-muted-foreground">
            {score.gaps.slice(0, 6).map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function StructuredProfileView({ structured }: { structured: StructuredResume }) {
  const { t } = useLocale();
  const profile = structured.profile;
  const hasAny =
    profile ||
    structured.summary ||
    structured.experience?.length ||
    structured.projects?.length ||
    structured.education?.length ||
    structured.skills?.length ||
    structured.achievements?.length;

  if (!hasAny) {
    return (
      <Card>
        <CardContent>
          <EmptyState
            icon={<ScanSearch aria-hidden />}
            title={t("resumes.detail.profileEmpty")}
            description={t("resumes.detail.profileEmptyDescription")}
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      {/* Contact / summary */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <CardTitle className="font-serif text-lg">
                {profile?.name ?? structured.profile?.headline ?? "Profile"}
              </CardTitle>
              {profile?.headline && (
                <CardDescription className="mt-0.5">{profile.headline}</CardDescription>
              )}
              <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                {profile?.location && (
                  <span className="flex items-center gap-1">
                    <MapPin className="size-3" aria-hidden />
                    {profile.location}
                  </span>
                )}
                {profile?.email && <span>{profile.email}</span>}
                {profile?.phone && <span>{profile.phone}</span>}
                {profile?.links?.slice(0, 3).map((l, i) => (
                  <a
                    key={i}
                    href={/^https?:/.test(l) ? l : `https://${l}`}
                    target="_blank"
                    rel="noopener noreferrer nofollow"
                    className="flex items-center gap-1 font-medium text-primary underline-offset-4 hover:underline"
                  >
                    <Link2 className="size-3" aria-hidden />
                    {l.replace(/^https?:\/\//, "").slice(0, 28)}
                  </a>
                ))}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                downloadText(
                  "resume-profile.json",
                  JSON.stringify(structured, null, 2),
                  "application/json"
                );
                toast.success("Structured profile exported.");
              }}
            >
              <Download aria-hidden />
              {t("resumes.detail.exportJson")}
            </Button>
          </div>
        </CardHeader>
        {structured.summary && (
          <CardContent>
            <p className="text-sm leading-relaxed text-foreground/90">{structured.summary}</p>
          </CardContent>
        )}
      </Card>

      {/* Experience */}
      {(structured.experience?.length ?? 0) > 0 && (
        <SectionCard
          icon={<Briefcase className="size-4" aria-hidden />}
          eyebrow="Work history"
          title={`${structured.experience!.length} role${structured.experience!.length === 1 ? "" : "s"}`}
        >
          <ol className="space-y-5">
            {structured.experience!.map((exp, i) => (
              <li key={i} className="relative pl-5">
                <span
                  className="absolute left-0 top-1.5 h-full w-px bg-border"
                  aria-hidden
                  style={i === structured.experience!.length - 1 ? { display: "none" } : undefined}
                />
                <span className="absolute -left-[3px] top-1.5 size-1.5 rounded-full bg-primary" aria-hidden />
                <p className="text-sm font-semibold">{exp.role ?? "Role"}</p>
                <p className="text-xs text-muted-foreground">
                  {[exp.company, exp.location].filter(Boolean).join(" · ")}{" "}
                  {[
                    exp.start,
                    exp.end,
                  ]
                    .filter(Boolean)
                    .join(" → ")}
                </p>
                <BulletList items={exp.bullets} className="mt-2" />
              </li>
            ))}
          </ol>
        </SectionCard>
      )}

      {/* Projects */}
      {(structured.projects?.length ?? 0) > 0 && (
        <SectionCard
          icon={<Hammer className="size-4" aria-hidden />}
          eyebrow="Projects"
          title={`${structured.projects!.length} project${structured.projects!.length === 1 ? "" : "s"}`}
        >
          <ul className="space-y-4">
            {structured.projects!.map((p: ResumeProject, i) => (
              <li key={i} className="rounded-lg border border-border/70 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="min-w-0 flex-1 text-sm font-semibold">{p.name}</p>
                  {p.period && <span className="text-xs text-muted-foreground">{p.period}</span>}
                  {p.url && (
                    <a
                      href={p.url}
                      target="_blank"
                      rel="noopener noreferrer nofollow"
                      className="flex items-center gap-1 text-xs font-medium text-primary underline-offset-4 hover:underline"
                    >
                      <ExternalLink className="size-3" aria-hidden />
                      {t("resumes.detail.repo")}
                    </a>
                  )}
                </div>
                <BulletList items={p.bullets} />
                {(p.techStack?.length ?? 0) > 0 && <TechLine items={p.techStack!} />}
              </li>
            ))}
          </ul>
        </SectionCard>
      )}

      {/* Education */}
      {(structured.education?.length ?? 0) > 0 && (
        <SectionCard
          icon={<GraduationCap className="size-4" aria-hidden />}
          eyebrow="Education"
          title={t("resumes.detail.schools")}
        >
          <ul className="space-y-3">
            {structured.education!.map((ed, i) => (
              <li key={i} className="flex flex-wrap items-baseline gap-x-2 text-sm">
                <span className="font-semibold">{ed.school}</span>
                <span className="text-muted-foreground">
                  {[ed.degree, ed.major].filter(Boolean).join(" · ")}
                </span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {[ed.start, ed.end].filter(Boolean).join(" → ")}
                  {ed.gpa ? ` · GPA ${ed.gpa}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </SectionCard>
      )}

      {/* Skills */}
      {(structured.skills?.length ?? 0) > 0 && (
        <SectionCard
          icon={<Wrench className="size-4" aria-hidden />}
          eyebrow="Skills"
          title={t("resumes.detail.inventory")}
        >
          <ul className="space-y-3">
            {structured.skills!.map((g, i) => (
              <li key={i}>
                <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
                  {g.group ?? `Group ${i + 1}`}
                </p>
                <ul className="mt-1 flex flex-wrap gap-1.5">
                  {(g.skills ?? []).map((s) => (
                    <li key={s}>
                      <Badge variant="outline" className="text-2xs font-normal">
                        {s}
                      </Badge>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </SectionCard>
      )}

      {/* Goals & preferences */}
      {((structured.careerGoals?.length ?? 0) > 0 ||
        (structured.preferredRoles?.length ?? 0) > 0 ||
        (structured.preferredLocations?.length ?? 0) > 0 ||
        (structured.achievements?.length ?? 0) > 0) && (
        <SectionCard
          icon={<Award className="size-4" aria-hidden />}
          eyebrow="Goals"
          title={t("resumes.detail.direction")}
        >
          <div className="space-y-3 text-sm">
            {structured.preferredRoles && structured.preferredRoles.length > 0 && (
              <Labelled label={t("resumes.detail.targetRoles")} items={structured.preferredRoles} />
            )}
            {structured.preferredLocations && structured.preferredLocations.length > 0 && (
              <Labelled
                label={t("resumes.detail.preferredLocations")}
                items={structured.preferredLocations}
              />
            )}
            {structured.careerGoals && structured.careerGoals.length > 0 && (
              <Labelled label={t("resumes.detail.careerGoals")} items={structured.careerGoals} />
            )}
            {(structured.achievements?.length ?? 0) > 0 && (
              <div>
                <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
                  {t("resumes.detail.achievements")}
                </p>
                <BulletList items={structured.achievements!} />
              </div>
            )}
          </div>
        </SectionCard>
      )}
    </>
  );
}

function SectionCard({
  icon,
  eyebrow,
  title,
  children,
}: {
  icon: React.ReactNode;
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <SectionHeading eyebrow={eyebrow} icon={icon} title={title} />
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function BulletList({ items, className }: { items?: string[]; className?: string }) {
  if (!items?.length) return null;
  return (
    <ul className={cn("ml-4 list-disc space-y-1 text-sm text-foreground/90 marker:text-muted-foreground", className)}>
      {items.map((b, i) => (
        <li key={i}>{b}</li>
      ))}
    </ul>
  );
}

function TechLine({ items }: { items: string[] }) {
  return (
    <p className="mt-1.5 flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
      <Wrench className="size-3" aria-hidden />
      {items.join(" · ")}
    </p>
  );
}

function Labelled({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">{label}</p>
      <p className="mt-0.5 text-sm text-foreground/90">{items.join(" · ")}</p>
    </div>
  );
}
