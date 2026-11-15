"use client";

import * as React from "react";
import { Activity, CheckCircle2, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n/locale-context";

const ROWS = [
  { key: "health", value: "/health — 300/300 · 62.9 rps", measured: "2026-11-15" },
  { key: "jobs", value: "/jobs — 200/200 · 87.7 rps", measured: "2026-11-15" },
  { key: "applications", value: "/applications — 200/200 · 103.7 rps", measured: "2026-11-15" },
  { key: "knowledge", value: "/knowledge/sources — 200/200 · 33.9 rps", measured: "2026-11-15" },
] as const;

/**
 * The operator's ledger (Epic 241) — measured, not guessed.
 *
 * Everything on this card was read off a terminal on 2026-11-15 and
 * 2026-11-16 during development of this install: the burst test of this
 * exact deployment, the load-shaped rounds against the gateway's shared
 * Redis budget, the relay's own cache accounting. It is not a live metric
 * and not marketing copy; it is an operator's note taped to the door —
 * every number here is dated, because a number without a date is not a
 * measurement, it is a story.
 */
const FINDINGS = [
  { key: "deterministic", copyKey: "monitoring.ledgerFinding1" },
  { key: "stream", copyKey: "monitoring.ledgerFinding2" },
  { key: "prefix", copyKey: "monitoring.ledgerFinding3" },
] as const;

export function OperatorLedgerCard() {
  const { t } = useLocale();
  return (
    <Card data-testid="operator-ledger-card" className="border-success/20 shadow-card">
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-success/25 bg-success/10 text-success">
          <Activity aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{t("monitoring.ledgerTitle")}</CardTitle>
          <CardDescription>{t("monitoring.ledgerDescription")}</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="grid gap-2 sm:grid-cols-2">
          {ROWS.map((row) => (
            <li
              key={row.key}
              className="flex items-center gap-2 rounded-lg border border-success/15 bg-success/[0.06] px-3 py-2 text-xs"
            >
              <CheckCircle2 aria-hidden className="size-4 shrink-0 text-success" />
              <span className="font-medium tabular-nums">{row.value}</span>
            </li>
          ))}
        </ul>
        <ol className="space-y-1.5 border-t border-border/50 pt-3 text-2xs leading-relaxed text-muted-foreground">
          {FINDINGS.map((finding) => (
            <li key={finding.key} className="flex gap-2">
              <span aria-hidden className="font-mono tabular-nums text-primary/70">{finding.key}</span>
              <span>{t(finding.copyKey)}</span>
            </li>
          ))}
        </ol>
        <div className="flex items-start gap-2 rounded-xl border border-border/60 bg-muted/40 px-4 py-3 text-xs leading-relaxed">
          <ShieldCheck aria-hidden className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <p className="text-muted-foreground">{t("monitoring.ledgerBody")}</p>
        </div>
        <p className="text-2xs text-muted-foreground">{t("monitoring.ledgerDateLine")}</p>
      </CardContent>
    </Card>
  );
}
