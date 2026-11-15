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
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatNumber } from "@/lib/format";

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

/**
 * /admin — the overseer's ledger (Epic 250).
 *
 * The operator's door, behind one passphrase this deployment already carries
 * (123): the one guard the install's one operator asked for, and the ceiling
 * of what it is. Counts only — no name, no content, no per-user row.
 */
export default function AdminPage() {
  const { t } = useLocale();
  const [unlocked, setUnlocked] = React.useState(false);
  const [phrase, setPhrase] = React.useState("");
  const [wrong, setWrong] = React.useState(false);
  const [stats, setStats] = React.useState<AdminStats | null>(null);

  React.useEffect(() => {
    if (!unlocked) return;
    const url = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080/api/v1"}/admin/stats`;
    let cancelled = false;
    fetch(url).then(async (response) => {
      if (!response.ok) return;
      const payload = await response.json();
      if (!cancelled) setStats(payload);
    }).catch(() => {
      /* the gate is happy without the database — the operator can probe HTTP by hand if the door flakes */
    });
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
