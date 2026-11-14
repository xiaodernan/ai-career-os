"use client";

import * as React from "react";
import { Backpack, Download, Upload } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useLocale } from "@/lib/i18n/locale-context";
import { downloadText } from "@/lib/format";
import {
  collectPocket,
  parsePocket,
  pocketSummary,
  restorePocket,
  serializePocket,
  POCKET_PREFIXES,
  familyLabelKey,
} from "@/lib/pocket";

/**
 * The pocket (Epic 223) — the server cannot see what the browser kept.
 *
 * The ledger, the day-one packets, the first-quarter plans and the debriefs
 * all live in localStorage by design: they are the reader's own thinking,
 * not search data. The export bundle cannot carry them, so the /data page
 * used to be one file short of "everything". This card closes the gap: a
 * summary of the four families the browser holds, a download that writes
 * them into one JSON file, and a restore that accepts only the keys the
 * product itself wrote.
 */
export function PocketCard() {
  const { t } = useLocale();
  const fileRef = React.useRef<HTMLInputElement>(null);
  const [manifest, setManifest] = React.useState(() => ({ schema: "careeros-pocket/1" as const, exportedAt: "", entries: {} }));

  const refresh = React.useCallback(() => {
    setManifest(collectPocket(typeof window === "undefined" ? null : window.localStorage));
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const summary = pocketSummary(manifest);
  const today = new Date().toISOString().slice(0, 10);

  const download = () => {
    if (summary.total === 0) {
      toast.info(t("data.pocketEmptyToast"));
      return;
    }
    downloadText(`careeros-pocket-${today}.json`, serializePocket(manifest), "application/json;charset=utf-8");
    toast.success(t("data.pocketSaved"));
  };

  const pick = () => fileRef.current?.click();

  const restoreFromFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    file.text().then((text) => {
      const parsed = parsePocket(text);
      if (!parsed) {
        toast.error(t("data.pocketInvalid"));
        return;
      }
      const result = restorePocket(parsed, typeof window === "undefined" ? null : window.localStorage);
      toast.success(
        result.skipped.length > 0
          ? t("data.pocketRestoredWithSkipped", { count: result.restored, skipped: result.skipped.length })
          : t("data.pocketRestored", { count: result.restored })
      );
      refresh();
    });
  };

  return (
    <Card data-testid="pocket-card">
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <Backpack aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{t("data.pocketTitle")}</CardTitle>
          <CardDescription>{t("data.pocketDescription")}</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="grid gap-2 sm:grid-cols-2">
          {summary.families.map((family) => (
            <li
              key={family.prefix}
              className="flex items-center justify-between gap-3 rounded-lg border border-border/60 px-3 py-2"
            >
              <span className="text-xs text-muted-foreground">{t(familyLabelKey(family.prefix))}</span>
              <span className="text-xs tabular-nums text-foreground">
                {t("data.pocketFamilyCount", { count: family.count })}
              </span>
            </li>
          ))}
        </ul>
        {summary.total === 0 && (
          <p className="text-sm text-muted-foreground">{t("data.pocketEmpty")}</p>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="ai" size="sm" onClick={download}>
            <Download aria-hidden />
            {t("data.pocketDownload")}
          </Button>
          <Button variant="outline" size="sm" onClick={pick}>
            <Upload aria-hidden />
            {t("data.pocketRestore")}
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept=".json,application/json"
            className="sr-only"
            aria-label={t("data.pocketRestoreFile")}
            onChange={restoreFromFile}
          />
          <p className="w-full text-2xs text-muted-foreground">{t("data.pocketHint")}</p>
        </div>
      </CardContent>
    </Card>
  );
}
