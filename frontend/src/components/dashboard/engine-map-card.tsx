"use client";

/**
 * The engine, made visible (Epic 278) — the state graph the copilot actually runs.
 *
 * The playbook teaches the machine in chapter 11; this card is where the machine
 * lives every day — one screen under the numbers on the dashboard, so the reader
 * who watches their agents work also sees the shape of the instrument those
 * agents are. The four node names are the literals in the source
 * (`retrieve → draft → verify → render`), the bound is `max_steps=8` as the
 * constructor of the real StateGraph enforces it, and the ledger line names
 * the `graph_node` trace the copilot writes into AI Activity.
 *
 * Nothing here is invented telemetry: the card renders the compiled topology
 * the engine ships with, not a simulation. It performs no fetch, reads no list
 * endpoint, and holds no user data — it is a map, not a meter.
 */

import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  PenLine,
  RotateCcw,
  Search,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLocale } from "@/lib/i18n/locale-context";

interface NodeSpec {
  // The node names are the literals in the source — not translated, in either language.
  key: "retrieve" | "draft" | "verify" | "render";
  Icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  bodyKey: string;
}

const NODES: NodeSpec[] = [
  { key: "retrieve", Icon: Search, bodyKey: "dashboard.engineRetrieveBody" },
  { key: "draft", Icon: PenLine, bodyKey: "dashboard.engineDraftBody" },
  { key: "verify", Icon: ShieldCheck, bodyKey: "dashboard.engineVerifyBody" },
  { key: "render", Icon: CheckCircle2, bodyKey: "dashboard.engineRenderBody" },
];

export function EngineMapCard() {
  const { t } = useLocale();

  return (
    <Card className="relative overflow-hidden border-primary/20 bg-gradient-to-br from-indigo-50/50 via-card to-card shadow-card print:break-inside-avoid">
      <CardContent className="relative space-y-6 p-6 sm:p-8">
        <span
          aria-hidden
          className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full print:hidden"
          style={{
            background:
              "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 16%, transparent), transparent)",
          }}
        />

        <div className="relative">
          <p className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-widest text-primary">
            <Workflow aria-hidden className="size-3.5" />
            {t("dashboard.engineEyebrow")}
          </p>
          <h3 className="mt-1 font-serif text-2xl font-semibold tracking-tight sm:text-3xl">
            {t("dashboard.engineTitle")}
          </h3>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
            {t("dashboard.engineIntro")}
          </p>
        </div>

        {/* The compiled topology: four nodes, left to right, one bounded loop. */}
        <ol className="relative grid gap-3 lg:grid-cols-4">
          {NODES.map(({ key, Icon, bodyKey }, index) => (
            <li
              key={key}
              className="relative flex flex-col gap-2 rounded-2xl border border-border/60 bg-card/70 p-4 backdrop-blur-sm"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="tabular-nums text-2xs font-semibold text-muted-foreground">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="flex size-9 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
                  <Icon aria-hidden className="size-5" />
                </span>
              </div>
              <span className="font-mono text-sm font-semibold tracking-tight">{key}</span>
              <span className="text-2xs leading-relaxed text-muted-foreground">{t(bodyKey)}</span>
            </li>
          ))}
        </ol>

        {/* The veto edge: verify refuses, the draft goes back — bounded. */}
        <div className="relative flex items-start gap-2 rounded-xl border border-dashed border-primary/30 bg-primary/[0.05] px-4 py-3">
          <RotateCcw aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
          <p className="text-2xs leading-relaxed text-foreground/90">{t("dashboard.engineRetryLabel")}</p>
        </div>

        {/* The bound, the ledger, and where to read more. */}
        <div className="relative grid gap-3 border-t border-border/60 pt-5 sm:grid-cols-2">
          <div className="space-y-1.5">
            <p className="font-mono text-2xs font-semibold text-foreground/80">
              {t("dashboard.engineBoundValue")}
            </p>
            <p className="text-2xs leading-relaxed text-muted-foreground">{t("dashboard.engineBound")}</p>
          </div>
          <div className="space-y-1.5">
            <p className="font-mono text-2xs font-semibold text-foreground/80">
              {t("dashboard.engineLedgerValue")}
            </p>
            <p className="text-2xs leading-relaxed text-muted-foreground">{t("dashboard.engineLedger")}</p>
          </div>
        </div>

        <div className="relative flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href="/playbook#stategraph">
              <BookOpen aria-hidden className="size-4" />
              {t("dashboard.engineBookLink")}
              <ArrowRight aria-hidden className="size-4" />
            </Link>
          </Button>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/activity">
              {t("dashboard.engineActivityLink")}
              <ArrowRight aria-hidden className="size-4" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
