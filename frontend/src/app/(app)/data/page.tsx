"use client";

import * as React from "react";
import { toast } from "sonner";
import { Download, FileJson, Shield, Upload } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { useExportBundle, useImportPlan, useRedactBundle } from "@/lib/hooks/data-portability";
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
  { key: "profile", label: "Profile" },
  { key: "resumes", label: "Resumes" },
  { key: "knowledge", label: "Knowledge base" },
  { key: "job_descriptions", label: "Job descriptions" },
  { key: "interviews", label: "Interview sessions" },
  { key: "memories", label: "Long-term memories" },
  // The two the BACKEND owns: it writes the applications and the stored growth
  // runs, so the bridge reads them and hands them into the bundle. Without them
  // an export is a reading list and not a record of the search.
  { key: "applications", label: "Applications" },
  { key: "growth_plans", label: "Growth runs" },
] as const;

export default function DataPortabilityPage() {
  const { t } = useLocale();
  const exportBundle = useExportBundle();
  const importPlan = useImportPlan();
  const redactBundle = useRedactBundle();

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
          toast.success("Export ready.");
        },
      });
    },
    [exportBundle]
  );

  const download = React.useCallback(() => {
    if (!bundle) return;
    downloadText(
      "career-os-export.json",
      JSON.stringify(bundle, null, 2),
      "application/json;charset=utf-8"
    );
    toast.success("File saved to your downloads.");
  }, [bundle]);

  const runRedact = React.useCallback(() => {
    if (!bundle) return;
    redactBundle.mutate(
      { bundle, drop: dropped },
      {
        onSuccess: (out) => {
          setBundle(out);
          setDropped([]);
          toast.success("Sections removed and the content hash recomputed.");
        },
      }
    );
  }, [bundle, dropped, redactBundle]);

  const runPlan = React.useCallback(() => {
    if (!importText.trim()) return;
    let parsed: unknown;
    try {
      parsed = JSON.parse(importText);
    } catch {
      toast.error("That is not valid JSON.");
      return;
    }
    importPlan.mutate(
      { bundle: parsed },
      {
        onSuccess: (plan) => {
          const counts = plan.op_counts;
          toast.success(
            counts
              ? `Plan ready: ${counts.create} to create, ${counts.update} to update, ${counts.delete} to delete.`
              : "Plan ready."
          );
        },
      }
    );
  }, [importText, importPlan]);

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
                    {s.label}
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
              <dl className="grid grid-cols-4 gap-2 text-center">
                <div>
                  <dt className="text-2xs text-muted-foreground uppercase">Create</dt>
                  <dd className="text-lg font-semibold tabular-nums">
                    {importPlan.data.op_counts?.create ?? 0}
                  </dd>
                </div>
                <div>
                  <dt className="text-2xs text-muted-foreground uppercase">Update</dt>
                  <dd className="text-lg font-semibold tabular-nums">
                    {importPlan.data.op_counts?.update ?? 0}
                  </dd>
                </div>
                <div>
                  <dt className="text-2xs text-muted-foreground uppercase">Delete</dt>
                  <dd className="text-lg font-semibold tabular-nums">
                    {importPlan.data.op_counts?.delete ?? 0}
                  </dd>
                </div>
                <div>
                  <dt className="text-2xs text-muted-foreground uppercase">Total</dt>
                  <dd className="text-lg font-semibold tabular-nums">
                    {importPlan.data.op_counts?.total ?? 0}
                  </dd>
                </div>
              </dl>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
