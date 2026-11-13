"use client";

import * as React from "react";
import { useLocale } from "@/lib/i18n/locale-context";
import { Copy, Loader2, Sparkles } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { FitBreakdown } from "@/components/ai/fit-breakdown";
import { useAnalyzeJd } from "@/lib/hooks/actions";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { field } from "@/lib/api/body";
import { normalizeMatch, normalizeTailor, pick } from "@/lib/api/normalize";
import type { JobMatch } from "@/lib/api/types";
import { toast } from "sonner";

type Phase = "idle" | "analyzing" | "matching" | "tailoring";

/**
 * Match Studio — paste a job description, the engine analyzes it, matches it
 * against your most recent resume, and lays the fit out as a ring + dimensions
 * + skill split + traced evidence. One button later it tailors the resume to
 * the posting. Built to be the page a candidate opens the moment a posting
 * lands in their inbox.
 */
export default function StudioPage() {
  const { t } = useLocale();
  const [jd, setJd] = React.useState("");
  const [resumeVersionId, setResumeVersionId] = React.useState("");
  const [match, setMatch] = React.useState<JobMatch | null>(null);
  const [tailored, setTailored] = React.useState<string | null>(null);
  const [copied, setCopied] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [phase, setPhase] = React.useState<Phase>("idle");

  const analyze = useAnalyzeJd();
  const rv = resumeVersionId.trim() || null;
  const busy = phase !== "idle";

  async function onAnalyze() {
    if (!jd.trim() || busy) return;
    setError(null);
    setMatch(null);
    setTailored(null);
    setCopied(false);
    setPhase("analyzing");
    try {
      const jdRes = await analyze.mutateAsync(jd);
      const id = (jdRes as { id?: string }).id;
      if (!id) throw new Error(t("studio.analysisFailed"));
      setPhase("matching");
      const raw = await api.request<unknown>(endpoints.jobMatch(id), {
        method: "POST",
        body: field("resumeVersionId", rv),
      });
      const m = normalizeMatch(pick(raw, "match") ?? raw);
      if (!m) throw new Error(t("studio.analysisFailed"));
      setMatch(m);
      setPhase("idle");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("studio.analysisFailed"));
      setPhase("idle");
    }
  }

  async function onTailor() {
    if (!match || busy) return;
    const id = match.jobId;
    if (!id) {
      setError(t("studio.analysisFailed"));
      return;
    }
    setError(null);
    setPhase("tailoring");
    try {
      const raw = await api.request<unknown>(endpoints.jobTailor(id), {
        method: "POST",
        body: field("resumeVersionId", rv),
      });
      setTailored(normalizeTailor(raw).tailored?.markdown ?? null);
      toast.success(t("studio.tailoredReady"));
      setPhase("idle");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("studio.tailoringFailed"));
      setPhase("idle");
    }
  }

  async function onCopy() {
    if (!tailored) return;
    try {
      await navigator.clipboard.writeText(tailored);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard may be unavailable; the text is still on screen to select */
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6">
      <header className="space-y-1">
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <Sparkles className="size-5 text-primary" aria-hidden />
          {t("studio.title")}
        </h1>
        <p className="text-sm text-muted-foreground">
          {t("studio.description")}
        </p>
      </header>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">{t("studio.jdLabel")}</CardTitle>
          <CardDescription>
            {t("studio.jdHint")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder={t("studio.jdPlaceholder")}
            className="min-h-44 resize-y text-sm leading-relaxed"
            aria-label={t("studio.jdLabel")}
          />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1 space-y-1.5">
              <label
                htmlFor="rvid"
                className="text-2xs font-medium uppercase tracking-wide text-muted-foreground"
              >
                {t("studio.resumeVersionLabel")}
              </label>
              <Input
                id="rvid"
                value={resumeVersionId}
                onChange={(e) => setResumeVersionId(e.target.value)}
                placeholder={t("studio.resumeVersionDefault")}
                className="text-sm"
              />
            </div>
            <Button onClick={onAnalyze} disabled={busy || !jd.trim()} className="sm:w-40">
              {busy ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                  {phase === "matching" ? t("studio.matching") : t("studio.analyzing")}
                </>
              ) : (
                t("studio.analyze")
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error ? (
        <p
          role="alert"
          className="rounded-lg border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive"
        >
          {error}
        </p>
      ) : null}

      {match ? (
        <FitBreakdown match={match} />
      ) : busy ? (
        <Card>
          <CardContent className="flex items-center gap-2 py-10 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            {phase === "matching" ? t("studio.scoringFit") : t("studio.readingPosting")}
          </CardContent>
        </Card>
      ) : null}

      {match ? (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">{t("studio.tailorTitle")}</CardTitle>
            <CardDescription>
              {t("studio.tailorDescription")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button variant="outline" onClick={onTailor} disabled={busy}>
              {phase === "tailoring" ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                  {t("studio.tailoring")}
                </>
              ) : (
                t("studio.tailorAction")
              )}
            </Button>
            {tailored ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    <span>{t("studio.tailorTitle")}</span>
                  </span>
                  <Button variant="ghost" size="sm" onClick={onCopy} className="text-xs">
                    <Copy className="size-3.5" aria-hidden />
                    {copied ? t("studio.copied") : t("common.copy")}
                  </Button>
                </div>
                <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-border/70 bg-muted/30 p-4 text-xs leading-relaxed">
                  {tailored}
                </pre>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
