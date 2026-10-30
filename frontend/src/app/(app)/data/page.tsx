"use client";

import * as React from "react";
import { toast } from "sonner";
import { Download, FileJson, FileText, Shield, Upload } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { useExportBundle, useImportApply, useImportPlan, useRedactBundle, useRenderBundle } from "@/lib/hooks/data-portability";
import { useLocale } from "@/lib/i18n/locale-context";
import { downloadText } from "@/lib/format";
import type { ExportBundle } from "@/lib/api/types";

/**
 * The data portability page (13.1-13.3): export everything, preview a re-import,
 * and redact sections before sharing.
 *
 * Every number here is read from the bundle the server built — the content hash
 * and the section counts are the server's, not recomputed in the browser.
 */

const SECTIONS = [
  { key: "profile", labelKey: "data.sections.profile" },
  { key: "resumes", labelKey: "data.sections.resumes" },
  { key: "knowledge", labelKey: "data.sections.knowledge" },
  { key: "job_descriptions", labelKey: "data.sections.jobDescriptions" },
  { key: "interviews", labelKey: "data.sections.interviews" },
  { key: "memories", labelKey: "data.sections.memories" },
  // The sections the BACKEND owns: it writes the applications, the stored
  // growth runs, the notes, the people the reader knows and the copilot
  // chats, so the bridge reads them and hands them into the bundle. Without
  // them an export is a reading list and not a record of the search.
  { key: "applications", labelKey: "data.sections.applications" },
  { key: "growth_plans", labelKey: "data.sections.growthRuns" },
  // The two the reader typed into: their own notes and the people they know.
  // They were the first things a reader lost when they left, because the
  // bundle used to carry every table the engines read and neither table the
  // reader wrote in.
  { key: "notes", labelKey: "data.sections.notes" },
  { key: "contacts", labelKey: "data.sections.contacts" },
  // And the chats: what the reader asked and what the assistant answered.
  { key: "conversations", labelKey: "data.sections.conversations" },
  // The standing choices: the question the morning sweep speaks for and the
  // sources the ingester is pointed at. A restore that leaves them behind
  // leaves the next morning silent.
  { key: "saved_searches", labelKey: "data.sections.savedSearches" },
  { key: "ingestion_feeds", labelKey: "data.sections.ingestionFeeds" },
  // The two ends of the pipeline: the postings the reader flagged and the
  // letters recruiters wrote back. One is what they want to remember, the
  // other is what the search answered.
  { key: "saved_jobs", labelKey: "data.sections.savedJobs" },
  { key: "inbound_mails", labelKey: "data.sections.inboundMails" },
] as const;

export default function DataPortabilityPage() {
  const { t } = useLocale();
  const exportBundle = useExportBundle();
  const importPlan = useImportPlan();
  const applyImport = useImportApply();
  const redactBundle = useRedactBundle();
  const renderBundle = useRenderBundle();

  // The bundle the last export produced — the input the redaction and the
  // import preview both read. Never fetched from anywhere else.
  const [bundle, setBundle] = React.useState<ExportBundle | null>(null);
  const [dropped, setDropped] = React.useState<string[]>([]);
  const [importText, setImportText] = React.useState("");

  const runExport = React.useCallback(
    (anonymized: boolean) => {
      exportBundle.mutate(anonymized, {
        onSuccess: (out) => {
          setBundle(out);
          setDropped([]);
          toast.success(t("data.exportReady"));
        },
      });
    },
    [exportBundle, t]
  );

  const download = React.useCallback(() => {
    if (!bundle) return;
    downloadText(
      "career-os-export.json",
      JSON.stringify(bundle, null, 2),
      "application/json;charset=utf-8"
    );
    toast.success(t("data.fileSaved"));
  }, [bundle, t]);

  const downloadMarkdown = React.useCallback(() => {
    if (!bundle) return;
    // The quick look: the same sections and the same words as the print-ready
    // document, in the form a diff tool reads. It was a library function
    // nothing called -- the route serves the Markdown now, so the reader gets
    // the affordance too.
    renderBundle.mutate(
      { bundle, format: "markdown" },
      {
        onSuccess: (out) => {
          downloadText(
            "career-os-export.md",
            out.markdown ?? "",
            "text/markdown;charset=utf-8"
          );
          toast.success(t("data.fileSaved"));
        },
      }
    );
  }, [bundle, renderBundle, t]);

  const runRedact = React.useCallback(() => {
    if (!bundle) return;
    redactBundle.mutate(
      { bundle, drop: dropped },
      {
        onSuccess: (out) => {
          setBundle(out);
          setDropped([]);
          toast.success(t("data.sectionsRemoved"));
        },
      }
    );
  }, [bundle, dropped, redactBundle, t]);

  const runPlan = React.useCallback(() => {
    if (!importText.trim()) return;
    let parsed: unknown;
    try {
      parsed = JSON.parse(importText);
    } catch {
      toast.error(t("data.notValidJson"));
      return;
    }
    importPlan.mutate(
      { bundle: parsed },
      {
        onSuccess: (plan) => {
          const counts = plan.op_counts;
          // The skip count is not a footnote: it is the row the copy under the
          // title promises, and a plan that hid it would leave the reader
          // unable to tell "nothing to do" from "nothing found".
          toast.success(
            counts
              ? t("data.planWithCounts", {
                  create: counts.create ?? 0,
                  update: counts.update ?? 0,
                  delete: counts.delete ?? 0,
                  skip: counts.skip ?? 0,
                })
              : t("data.planReady")
          );
        },
      }
    );
  }, [importText, importPlan, t]);

  const runApply = React.useCallback(() => {
    if (!importText.trim()) return;
    let parsed: unknown;
    try {
      parsed = JSON.parse(importText);
    } catch {
      toast.error(t("data.notJson"));
      return;
    }
    applyImport.mutate(parsed, {
      onSuccess: (out) => {
        const skipped = (out.skipped ?? []).length;
        toast.success(
          skipped > 0
            ? t("data.appliedWithSkipped")
            : t("data.appliedClean")
        );
      },
    });
  }, [importText, applyImport, t]);

  const runRender = React.useCallback(() => {
    if (!bundle) return;
    renderBundle.mutate(
      { bundle, format: "html" },
      {
        onSuccess: (out) => {
          // The rendered document is self-contained, so a new window with it is
          // a print-ready page: the browser's own "save as PDF" is the PDF.
          const win = window.open("", "_blank");
          if (!win) {
            toast.error(t("data.popupBlocked"));
            return;
          }
          win.document.write(out.html ?? "");
          win.document.close();
          win.focus();
        },
      }
    );
  }, [bundle, renderBundle, t]);

  const toggleDrop = (key: string) =>
    setDropped((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <PageHeader
        title={t("data.title")}
        description={t("data.description")}
      />

      {/* Export */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("data.export")}</CardTitle>
          <CardDescription>{t("data.exportDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button
              variant="ai"
              size="sm"
              loading={exportBundle.isPending}
              onClick={() => runExport(false)}
            >
              <FileJson aria-hidden />
              {t("data.exportEverything")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              loading={exportBundle.isPending}
              onClick={() => runExport(true)}
            >
              <Shield aria-hidden />
              {t("data.exportAnonymized")}
            </Button>
            {bundle && (
              <Button variant="outline" size="sm" onClick={download}>
                <Download aria-hidden />
                {t("data.downloadJson")}
              </Button>
            )}
            {bundle && (
              <Button
                variant="outline"
                size="sm"
                loading={renderBundle.isPending}
                onClick={runRender}
              >
                <FileText aria-hidden />
                {t("data.printView")}
              </Button>
            )}
            {bundle && (
              <Button
                variant="outline"
                size="sm"
                loading={renderBundle.isPending}
                onClick={downloadMarkdown}
              >
                <FileText aria-hidden />
                {t("data.downloadMarkdown")}
              </Button>
            )}
          </div>

          {bundle?.manifest && (
            <>
              <Separator />
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
                    {t("data.contentHash")}
                  </p>
                  <p className="mt-1 font-mono text-xs break-all">
                    {bundle.manifest.content_hash ?? "—"}
                  </p>
                </div>
                <div>
                  <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
                    {t("data.generated")}
                  </p>
                  <p className="mt-1 text-xs">{bundle.generated_at ?? "—"}</p>
                </div>
              </div>
              <ul className="flex flex-wrap gap-1.5">
                {Object.entries(bundle.manifest.counts ?? {}).map(([section, count]) => (
                  <li key={section}>
                    <Badge variant="outline" className="capitalize">
                      {section.replace(/_/g, " ")}: {count}
                    </Badge>
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardContent>
      </Card>

      {/* Redact */}
      {bundle && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("data.redactBeforeSharing")}</CardTitle>
            <CardDescription>{t("data.redactDescription")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {SECTIONS.map((s) => (
                <li key={s.key}>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={dropped.includes(s.key)}
                      onChange={() => toggleDrop(s.key)}
                      className="size-4 rounded border-border"
                    />
                    {t(s.labelKey)}
                  </label>
                </li>
              ))}
            </ul>
            <Button
              variant="outline"
              size="sm"
              loading={redactBundle.isPending}
              disabled={dropped.length === 0}
              onClick={runRedact}
            >
              {t("data.redactSelected")}
            </Button>
            {bundle.manifest?.redacted_sections?.length ? (
              <p className="text-xs text-muted-foreground">
                {t("data.removedSoFar")} {bundle.manifest.redacted_sections.join(", ")}.
              </p>
            ) : null}
          </CardContent>
        </Card>
      )}

      {/* Import plan */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("data.previewRestore")}</CardTitle>
          <CardDescription>{t("data.restoreDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="import-bundle">{t("data.bundleJson")}</Label>
            <Textarea
              id="import-bundle"
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              placeholder='{ "schema_version": "1.0.0", "manifest": { … }, "data": { … } }'
              rows={6}
              className="font-mono text-xs"
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            loading={importPlan.isPending}
            disabled={!importText.trim()}
            onClick={runPlan}
          >
            <Upload aria-hidden />
            {t("data.buildThePlan")}
          </Button>

          {importPlan.data && (
            <div className="space-y-2 rounded-lg border border-border/60 p-3">
              <p className="text-sm font-medium">{t("data.plan")}</p>
              <dl className="grid grid-cols-5 gap-2 text-center">
                <div>
                  <dt className="text-2xs text-muted-foreground uppercase">
                    {t("data.opCreate")}
                  </dt>
                  <dd className="text-lg font-semibold tabular-nums">
                    {importPlan.data.op_counts?.create ?? 0}
                  </dd>
                </div>
                <div>
                  <dt className="text-2xs text-muted-foreground uppercase">
                    {t("data.opUpdate")}
                  </dt>
                  <dd className="text-lg font-semibold tabular-nums">
                    {importPlan.data.op_counts?.update ?? 0}
                  </dd>
                </div>
                <div>
                  <dt className="text-2xs text-muted-foreground uppercase">
                    {t("data.opDelete")}
                  </dt>
                  <dd className="text-lg font-semibold tabular-nums">
                    {importPlan.data.op_counts?.delete ?? 0}
                  </dd>
                </div>
                <div>
                  <dt className="text-2xs text-muted-foreground uppercase">
                    {t("data.opSkip")}
                  </dt>
                  <dd className="text-lg font-semibold tabular-nums">
                    {importPlan.data.op_counts?.skip ?? 0}
                  </dd>
                </div>
                <div>
                  <dt className="text-2xs text-muted-foreground uppercase">
                    {t("data.opTotal")}
                  </dt>
                  <dd className="text-lg font-semibold tabular-nums">
                    {importPlan.data.op_counts?.total ?? 0}
                  </dd>
                </div>
              </dl>
              {/* The plan is a preview; the apply is the write. They are two
                  buttons because a restore that half-applied would be worse
                  than one the user could read first. */}
              <Button
                variant="ai"
                size="sm"
                loading={applyImport.isPending}
                disabled={!importText.trim()}
                onClick={runApply}
              >
                <Upload aria-hidden />
                {t("data.applyTheRestore")}
              </Button>
            </div>
          )}

          {applyImport.data && (
            <div className="space-y-2 rounded-lg border border-border/60 p-3">
              <p className="text-sm font-medium">{t("data.applied")}</p>
              <ul className="space-y-1 text-sm">
                {Object.entries(applyImport.data.applied ?? {}).map(([section, counts]) => (
                  <li key={section} className="flex items-center justify-between gap-2">
                    <span className="capitalize">{section.replace(/_/g, " ")}</span>
                    <span className="text-xs text-muted-foreground">
                      {t("data.appliedCounts", {
                        created: counts.created ?? 0,
                        updated: counts.updated ?? 0,
                        deleted: counts.deleted ?? 0,
                        unchanged: counts.unchanged ?? 0,
                      })}
                    </span>
                  </li>
                ))}
              </ul>
              {/* The skipped sections are named with their reason: a partial
                  restore the user cannot see is a lie the user finds out about
                  later. */}
              {(applyImport.data.skipped ?? []).length > 0 && (
                <ul className="space-y-1 border-t border-border/60 pt-2 text-xs text-muted-foreground">
                  {(applyImport.data.skipped ?? []).map((s) => (
                    <li key={s.section}>
                      <span className="font-medium capitalize">{s.section.replace(/_/g, " ")}</span>
                      {" — "}
                      {s.reason}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
