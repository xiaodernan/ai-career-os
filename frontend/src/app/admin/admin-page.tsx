"use client";

import * as React from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Database,
  Lock,
  Sparkles,
  Users,
  Waves,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatNumber, relativeTime } from "@/lib/format";
import { seriesTotal, projectedSparkline } from "@/lib/admin-trend";
import { funnelReading } from "@/lib/admin-funnel";

interface AdminStats {
  users?: number;
  resumes?: number;
  applications?: number;
  interviewsPracticed?: number;
  interviewTurns?: number;
  agentRuns?: number;
  agentTraces?: number;
  aiUsageEvents?: number;
  knowledgeSources?: number;
  notesKept?: number;
  coverLetters?: number;
  contacts?: number;
  memories?: number;
  companies?: number;
  jobs?: number;
  matches?: number;
  conversations?: number;
  messages?: number;
  savedSearches?: number;
  offers?: number;
}

interface AdminTrends {
  weeks?: string[];
  series?: Record<string, number[] | undefined>;
  weeksRequested?: number;
}

interface AdminFreshness {
  flows?: Array<{ id: string; table: string; newest: string | null }>;
}

interface AdminFunnel {
  stages?: Array<{ id: string; readers: number }>;
  matchedReaders?: number;
}

interface AdminCohort {
  cohort?: Array<{ week: string; registered: number; active: number }>;
  weeksRequested?: number;
}

const SECRET = "123"; // the install's one passphrase, by the operator's own choosing

const STATIONS = [
  { name: "register", p50: 950, p95: 950 },
  { name: "who am I", p50: 46, p95: 46 },
  { name: "save profile", p50: 466, p95: 466 },
  { name: "upload resume", p50: 1428, p95: 1428 },
  { name: "resume detail", p50: 227, p95: 227 },
  { name: "ingest text", p50: 931, p95: 931 },
  { name: "list knowledge", p50: 50, p95: 50 },
  { name: "search jobs", p50: 15226, p95: 15226 },
  { name: "job match", p50: 39604, p95: 39604 },
] as const;

const RECOMMENDATIONS = [
  { titleKey: "admin.recFeedTitle", bodyKey: "admin.recFeedBody" },
  { titleKey: "admin.recFirstVisitTitle", bodyKey: "admin.recFirstVisitBody" },
  { titleKey: "admin.recCacheTitle", bodyKey: "admin.recCacheBody" },
  { titleKey: "admin.recMatchTitle", bodyKey: "admin.recMatchBody" },
  { titleKey: "admin.recCorpusTitle", bodyKey: "admin.recCorpusBody" },
] as const;

const FUNNEL_STAGE_KEYS: Record<string, string> = {
  registered: "admin.funnelStageRegistered",
  uploaded: "admin.funnelStageUploaded",
  applied: "admin.funnelStageApplied",
  interviewed: "admin.funnelStageInterviewed",
  offered: "admin.funnelStageOffered",
};

const TREND_SERIES = [
  { key: "users", labelKey: "admin.usersLabel", icon: Users },
  { key: "applications", labelKey: "admin.applicationsLabel", icon: BarChart3 },
  { key: "interviewsPracticed", labelKey: "admin.interviewLabel", icon: Activity },
  { key: "agentRuns", labelKey: "admin.agentRunsLabel", icon: Sparkles },
  { key: "aiUsageEvents", labelKey: "admin.aiEventsLabel", icon: Database },
] as const;

/**
 * /admin — the overseer's ledger (Epics 250, 251).
 *
 * The operator's door, behind one passphrase this deployment already carries
 * (123): the one guard the install's one operator asked for, and the ceiling
 * of what it is. Counts only — no name, no content, no per-user row.
 */
export default function AdminPage() {
  const { t, locale } = useLocale();
  const [unlocked, setUnlocked] = React.useState(false);
  const [phrase, setPhrase] = React.useState("");
  const [wrong, setWrong] = React.useState(false);
  const [stats, setStats] = React.useState<AdminStats | null>(null);
  const [trends, setTrends] = React.useState<AdminTrends | null>(null);
  const [freshness, setFreshness] = React.useState<AdminFreshness | null>(null);
  const [funnel, setFunnel] = React.useState<AdminFunnel | null>(null);
  const [cohort, setCohort] = React.useState<AdminCohort | null>(null);

  React.useEffect(() => {
    if (!unlocked) return;
    let cancelled = false;
    // the shared client unwraps the {success,data,error} envelope and carries the
    // correlation id; failures degrade to the em-dash, never to a fabricated number
    api.get<AdminStats>(endpoints.admin.stats)
      .then((data) => { if (!cancelled) setStats(data); })
      .catch(() => { /* the gate is happy without the database — the operator can probe HTTP by hand if the door flakes */ });
    api.get<AdminTrends>(endpoints.admin.trends, { weeks: 12 })
      .then((data) => { if (!cancelled) setTrends(data); })
      .catch(() => { /* as above */ });
    api.get<AdminFreshness>(endpoints.admin.freshness)
      .then((data) => { if (!cancelled) setFreshness(data); })
      .catch(() => { /* as above — instants are a courtesy, never a blocker */ });
    api.get<AdminFunnel>(endpoints.admin.funnel)
      .then((data) => { if (!cancelled) setFunnel(data); })
      .catch(() => { /* as above — a reader count is a courtesy, never a blocker */ });
    api.get<AdminCohort>(endpoints.admin.cohort)
      .then((data) => { if (!cancelled) setCohort(data); })
      .catch(() => { /* as above — a signup cohort is a courtesy, never a blocker */ });
    return () => { cancelled = true; };
  }, [unlocked]);

  if (!unlocked) {
    return (
      <div className="relative grid min-h-dvh place-items-center overflow-hidden bg-background px-4">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(60%_50%_at_50%_0%,color-mix(in_oklch,var(--primary)_14%,transparent),transparent)]" />
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (phrase.trim() === SECRET) {
              setUnlocked(true);
              setWrong(false);
            } else {
              setWrong(true);
            }
          }}
          className="w-full max-w-md space-y-6 rounded-3xl border border-border/70 bg-card/80 p-8 shadow-pop backdrop-blur"
        >
          <div className="flex items-center gap-3">
            <span aria-hidden className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-inset ring-primary/15">
              <Lock className="size-5" />
            </span>
            <div>
              <p className="text-2xs font-semibold uppercase tracking-widest text-primary">
                {t("admin.adminEyebrow")}
              </p>
              <h1 className="font-serif text-2xl font-semibold tracking-tight">
                {t("admin.adminTitle")}
              </h1>
            </div>
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">{t("admin.intro")}</p>
          <div className="space-y-2">
            <Label htmlFor="admin-pass">{t("admin.passphraseLabel")}</Label>
            <Input
              id="admin-pass"
              type="password"
              autoComplete="off"
              autoFocus
              placeholder={t("admin.passphrasePlaceholder")}
              value={phrase}
              onChange={(event) => {
                setPhrase(event.target.value);
                setWrong(false);
              }}
              aria-invalid={wrong || undefined}
              aria-describedby={wrong ? "admin-wrong" : undefined}
            />
            {wrong && (
              <p id="admin-wrong" role="alert" className="text-2xs text-destructive">
                {t("admin.wrong")}
              </p>
            )}
          </div>
          <Button type="submit" variant="ai" size="lg" className="w-full glow-on-hover">
            {t("admin.unlock")}
            <ArrowRight className="size-4" aria-hidden />
          </Button>
        </form>
      </div>
    );
  }

  const tiles = [
    { icon: Users, labelKey: "admin.usersLabel", value: stats?.users },
    { icon: Database, labelKey: "admin.resumesLabel", value: stats?.resumes },
    { icon: BarChart3, labelKey: "admin.applicationsLabel", value: stats?.applications },
    { icon: Activity, labelKey: "admin.interviewLabel", value: stats?.interviewsPracticed },
    { icon: Sparkles, labelKey: "admin.agentRunsLabel", value: stats?.agentRuns },
    { icon: Database, labelKey: "admin.notesLabel", value: stats?.notesKept },
    { icon: Database, labelKey: "admin.jobsLabel", value: stats?.jobs },
    { icon: Sparkles, labelKey: "admin.messagesLabel", value: stats?.messages },
  ] as const;

  const trendWeeks = trends?.weeks;
  const reading = funnel ? funnelReading(funnel.stages ?? [], funnel.matchedReaders) : null;
  const readingStageLabel = reading?.bottleneckStageId
    ? (FUNNEL_STAGE_KEYS[reading.bottleneckStageId]
        ? t(FUNNEL_STAGE_KEYS[reading.bottleneckStageId])
        : reading.bottleneckStageId)
    : "";

  return (
    <div className="mx-auto max-w-6xl space-y-10 px-4 py-10">
      <div className="border-b border-border/60 pb-6">
        <p className="text-2xs font-semibold uppercase tracking-widest text-primary">
          {t("admin.adminEyebrow")}
        </p>
        <h1 className="mt-2 font-serif text-4xl font-semibold tracking-tight">
          {t("admin.adminTitle")}
        </h1>
        <p className="mt-2 max-w-3xl text-base leading-relaxed text-muted-foreground">
          {t("admin.loreLede")}
        </p>
      </div>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map((tile, index) => {
          const Icon = tile.icon;
          return (
            <div key={index} className="rounded-2xl border border-border/60 bg-card/60 p-4">
              <div className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-widest text-muted-foreground">
                <Icon aria-hidden className="size-3.5" />
                <span>{t(tile.labelKey)}</span>
              </div>
              <p className="mt-2 font-serif text-3xl font-semibold tabular-nums">
                {tile.value === undefined ? "—" : formatNumber(tile.value)}
              </p>
            </div>
          );
        })}
      </section>

      <section aria-label={t("admin.flowTitle")}>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 rounded-2xl border border-border/60 bg-card/40 px-4 py-3 text-xs">
          <span className="flex items-center gap-2 font-semibold text-muted-foreground">
            <Waves aria-hidden className="size-3.5" />
            {t("admin.flowTitle")}
          </span>
          {(freshness?.flows ?? []).map((flow) => (
            <span key={flow.id} className="flex items-baseline gap-1.5">
              <span className="text-muted-foreground">{flow.id}</span>
              <span className="tabular-nums text-foreground">
                {flow.newest ? relativeTime(flow.newest, locale) : "—"}
              </span>
            </span>
          ))}
          {freshness && freshness.flows?.length === 0 && (
            <span className="text-muted-foreground">—</span>
          )}
        </div>
      </section>

      <section aria-label={t("admin.funnelTitle")}>
        <h2 className="font-serif text-xl font-semibold tracking-tight">{t("admin.funnelTitle")}</h2>
        <p className="mt-1 max-w-4xl text-sm leading-relaxed text-muted-foreground">{t("admin.funnelLede")}</p>
        <div className="mt-4 overflow-hidden rounded-2xl border border-border/60 bg-card/40">
          {(funnel?.stages ?? []).map((stage, index) => {
            const stages = funnel?.stages ?? [];
            const first = stages[0]?.readers ?? 0;
            const previous = index > 0 ? stages[index - 1]?.readers : undefined;
            const share = previous && previous > 0 ? Math.round((stage.readers / previous) * 100) : null;
            const width = first > 0 ? Math.max(2, Math.round((stage.readers / first) * 100)) : 0;
            return (
              <div key={stage.id} className="flex items-center gap-3 border-b border-border/40 px-4 py-2.5 last:border-b-0">
                <span className="w-28 shrink-0 text-xs font-medium text-muted-foreground">
                  {FUNNEL_STAGE_KEYS[stage.id] ? t(FUNNEL_STAGE_KEYS[stage.id]) : stage.id}
                </span>
                <div className="relative h-5 min-w-0 flex-1 overflow-hidden rounded-full bg-muted/60">
                  <div
                    className="h-5 rounded-full bg-gradient-to-r from-primary/60 to-primary transition-[width] duration-500"
                    style={{ width: `${width}%` }}
                  />
                </div>
                <span className="w-16 shrink-0 text-right font-mono text-xs tabular-nums">
                  {formatNumber(stage.readers)}
                </span>
                <span className="w-12 shrink-0 text-right text-2xs tabular-nums text-muted-foreground">
                  {share === null ? "" : `${share}%`}
                </span>
              </div>
            );
          })}
          {!funnel && (
            <div className="px-4 py-4 text-2xs text-muted-foreground">—</div>
          )}
        </div>
        <p className="mt-2 text-2xs text-muted-foreground">
          {t("admin.funnelMatchedNote", { count: formatNumber(funnel?.matchedReaders ?? 0) })}
          {" "}{t("admin.funnelFootnote")}
        </p>
        {reading?.bottleneckStageId && (
          <p className="mt-1.5 flex flex-wrap items-center gap-1.5 text-2xs font-medium text-primary">
            <Sparkles aria-hidden className="size-3.5" />
            {t("admin.funnelReadingLine", { stage: readingStageLabel, percent: `${reading.bottleneckPercent}%` })}
          </p>
        )}
      </section>

      <section aria-label={t("admin.cohortTitle")}>
        <h2 className="font-serif text-xl font-semibold tracking-tight">{t("admin.cohortTitle")}</h2>
        <p className="mt-1 max-w-4xl text-sm leading-relaxed text-muted-foreground">{t("admin.cohortLede")}</p>
        {(() => {
          const rows = cohort?.cohort ?? [];
          const totalRegistered = rows.reduce((sum, r) => sum + r.registered, 0);
          const totalActive = rows.reduce((sum, r) => sum + r.active, 0);
          const totalShare = totalRegistered > 0 ? Math.round((totalActive / totalRegistered) * 100) : 0;
          return (
            <>
              {rows.length > 0 && (
                <p className="mt-3 text-xs font-medium text-foreground">
                  {t("admin.cohortTotal", { active: formatNumber(totalActive), registered: formatNumber(totalRegistered), percent: String(totalShare) })}
                </p>
              )}
              <div className="mt-4 overflow-x-auto rounded-2xl border border-border/60">
                <table className="min-w-[520px] w-full text-sm">
                  <thead className="border-b border-border/60 bg-muted/40 text-left text-2xs uppercase tracking-widest text-muted-foreground">
                    <tr>
                      <th className="px-4 py-2.5">{t("admin.cohortHeaderWeek")}</th>
                      <th className="px-4 py-2.5 text-right">{t("admin.cohortHeaderRegistered")}</th>
                      <th className="px-4 py-2.5 text-right">{t("admin.cohortHeaderActive")}</th>
                      <th className="px-4 py-2.5 text-right">{t("admin.cohortHeaderShare")}</th>
                      <th className="px-4 py-2.5 w-48" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {rows.map((row) => {
                      const share = row.registered > 0 ? Math.round((row.active / row.registered) * 100) : 0;
                      return (
                        <tr key={row.week}>
                          <td className="px-4 py-2 font-mono text-2xs tabular-nums text-muted-foreground">{row.week}</td>
                          <td className="px-4 py-2 text-right tabular-nums">{formatNumber(row.registered)}</td>
                          <td className="px-4 py-2 text-right tabular-nums">{formatNumber(row.active)}</td>
                          <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">{share}%</td>
                          <td className="px-4 py-2">
                            <div className="h-2 w-full overflow-hidden rounded-full bg-muted/60">
                              <div className="h-2 rounded-full bg-primary/70" style={{ width: `${share}%` }} />
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {rows.length === 0 && (
                      <tr><td colSpan={5} className="px-4 py-4 text-center text-2xs text-muted-foreground">—</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-2xs leading-relaxed text-muted-foreground">{t("admin.cohortQuietNote")}</p>
            </>
          );
        })()}
      </section>

      <section>
        <h2 className="font-serif text-xl font-semibold tracking-tight">{t("admin.trendTitle")}</h2>
        <p className="mt-1 max-w-4xl text-sm leading-relaxed text-muted-foreground">{t("admin.trendLede")}</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {TREND_SERIES.map((serie) => {
            const values = trends?.series?.[serie.key];
            const spark = values ? projectedSparkline(values, 4, 120, 36, 3) : null;
            const total = values ? seriesTotal(values) : undefined;
            const peak = values && values.length > 0 ? Math.max(...values) : undefined;
            const Icon = serie.icon;
            return (
              <div key={serie.key} className="rounded-2xl border border-border/60 bg-card/60 p-4">
                <div className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-widest text-muted-foreground">
                  <Icon aria-hidden className="size-3.5" />
                  <span>{t(serie.labelKey)}</span>
                </div>
                <div className="mt-2 flex items-end justify-between gap-2">
                  <p className="font-serif text-2xl font-semibold tabular-nums">
                    {total === undefined ? "—" : formatNumber(total)}
                  </p>
                  <svg viewBox="0 0 120 36" className="h-9 w-24 text-primary" aria-hidden="true">
                    {spark && (
                      <>
                        <polyline
                          points={spark.points}
                          fill="none"
                          stroke="currentColor"
                          strokeWidth={1.5}
                          strokeLinejoin="round"
                          strokeLinecap="round"
                        />
                        <polyline
                          points={spark.projectionPoints}
                          fill="none"
                          stroke="currentColor"
                          strokeWidth={1.5}
                          strokeDasharray="3 2"
                          strokeLinecap="round"
                          opacity={0.65}
                        />
                        <circle cx={spark.last.x} cy={spark.last.y} r={1.6} fill="currentColor" />
                      </>
                    )}
                  </svg>
                </div>
                <p className="mt-1 text-2xs tabular-nums text-muted-foreground">
                  {trendWeeks ? t("admin.trendAcrossWeeks", { count: trendWeeks.length }) : "—"}
                  {peak !== undefined && peak > 0 ? ` · ${t("admin.trendPeak", { count: formatNumber(peak) })}` : ""}
                </p>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-2xs leading-relaxed text-muted-foreground">{t("admin.trendProjection")}</p>
        <p className="mt-1 text-2xs leading-relaxed text-muted-foreground">{t("admin.trendFootnote")}</p>
      </section>

      <section>
        <h2 className="font-serif text-xl font-semibold tracking-tight">{t("admin.journeyTitle")}</h2>
        <p className="mt-1 max-w-4xl text-sm leading-relaxed text-muted-foreground">{t("admin.journeyLede")}</p>
        <div className="mt-4 overflow-hidden rounded-2xl border border-border/60">
          <table className="w-full text-sm">
            <thead className="border-b border-border/60 bg-muted/40 text-left text-2xs uppercase tracking-widest text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5">{t("admin.journeyStation")}</th>
                <th className="px-4 py-2.5 text-right">{t("admin.journeyP50")}</th>
                <th className="px-4 py-2.5 text-right">{t("admin.journeyP95")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {STATIONS.map((station) => (
                <tr key={station.name}>
                  <td className="px-4 py-2 font-medium">{station.name}</td>
                  <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">{station.p50.toLocaleString()} ms</td>
                  <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">{station.p95.toLocaleString()} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="font-serif text-xl font-semibold tracking-tight">{t("admin.optimizationsTitle")}</h2>
        <p className="mt-1 max-w-4xl text-sm leading-relaxed text-muted-foreground">{t("admin.optimizationsLede")}</p>
        <ol className="mt-4 grid gap-2">
          {RECOMMENDATIONS.map((rec, index) => (
            <li key={index} className="flex gap-3 rounded-xl border border-primary/10 bg-primary/5 p-4">
              <span aria-hidden className="font-mono text-2xs tabular-nums text-primary">{String(index + 1).padStart(2, "0")}</span>
              <div className="min-w-0">
                <p className="text-sm font-semibold">{t(rec.titleKey)}</p>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{t(rec.bodyKey)}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <div className="border-t border-border/60 pt-6 text-2xs text-muted-foreground">
        <p>{t("admin.footnote")}</p>
        <Link href="/" className="mt-2 inline-block hover:text-foreground">
          ← {t("admin.backToProduct")}
        </Link>
      </div>
    </div>
  );
}
