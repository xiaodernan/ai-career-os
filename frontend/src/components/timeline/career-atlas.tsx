"use client";

import * as React from "react";
import Link from "next/link";
import { Compass, MapPin, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SectionHeading } from "@/components/common/export-buttons";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatDate } from "@/lib/format";
import type { TimelineEntry } from "@/lib/api/types";

/**
 * Epic 357 — the Career Atlas.
 *
 * The ledger is already a world: every application, rehearsal, contact and note is
 * a place the reader actually went. This card draws that world instead of inventing
 * one. Regions are the timeline's own kinds, sites are the reader's own events, and
 * the only way the map grows is for the workspace to write another fact.
 *
 * The coordinates are a stable projection of ORDER, not a random decoration: the
 * first event of a region sits due north, later events wind outward. A reload puts
 * every site back where it was, so the map can be learned. Unknown kinds get their
 * own region rather than being dropped — a fact the engine cannot name is still a
 * fact the reader can visit.
 */

const REGION_ORDER = [
  "application",
  "interview",
  "match",
  "contact",
  "resume_version",
  "note",
  "unknown",
] as const;

const LABEL_KEYS: Record<string, string> = {
  application: "timeline.kinds.application",
  interview: "timeline.kinds.interview",
  match: "timeline.kinds.match",
  contact: "timeline.kinds.contact",
  resume_version: "timeline.kinds.resume_version",
  note: "timeline.kinds.note",
  unknown: "timeline.kinds.unknown",
};

/** The map stays readable on a power user's ledger; the count stays honest. */
const SITES_PER_REGION = 24;

export interface AtlasSite {
  id: string;
  title: string;
  summary: string;
  at: string;
  x: number;
  y: number;
}

export interface AtlasRegion {
  kind: string;
  labelKey: string;
  count: number;
  hidden: number;
  sites: AtlasSite[];
}

export function buildAtlas(events: TimelineEntry[]): AtlasRegion[] {
  const grouped = new Map<string, TimelineEntry[]>();
  for (const event of events) {
    const kind = (REGION_ORDER as readonly string[]).includes(event.kind)
      ? event.kind
      : "unknown";
    const bucket = grouped.get(kind);
    if (bucket) bucket.push(event);
    else grouped.set(kind, [event]);
  }

  return REGION_ORDER.flatMap((kind, regionIndex) => {
    const rows = grouped.get(kind);
    if (!rows || rows.length === 0) return [];
    const ordered = [...rows].sort((a, b) => a.at.localeCompare(b.at));
    const sites = ordered.slice(0, SITES_PER_REGION).map((event, index) => {
      const angle = (index / ordered.length) * 2 * Math.PI - Math.PI / 2 + regionIndex * 0.35;
      const radius = 13 + (regionIndex % 3) * 9 + (index % 4) * 4;
      const round = (n: number) => Math.round(n * 100) / 100;
      return {
        id: `${event.kind}:${event.refId}:${event.at}`,
        title: event.title,
        summary: event.summary,
        at: event.at,
        x: round(50 + radius * Math.cos(angle)),
        y: round(50 + radius * Math.sin(angle)),
      };
    });
    return [{
      kind,
      labelKey: LABEL_KEYS[kind],
      count: ordered.length,
      hidden: Math.max(0, ordered.length - sites.length),
      sites,
    }];
  });
}

const FRONTIERS = [
  { key: "timeline.atlasFrontierJobs", href: "/jobs" },
  { key: "timeline.atlasFrontierApplications", href: "/applications" },
  { key: "timeline.atlasFrontierInterviews", href: "/interviews" },
  { key: "timeline.atlasFrontierNetworking", href: "/networking" },
] as const;

export function CareerAtlas({ events }: { events: TimelineEntry[] }) {
  const { t, locale } = useLocale();
  const regions = React.useMemo(() => buildAtlas(events), [events]);
  const [selected, setSelected] = React.useState<string | null>(null);
  const [openSite, setOpenSite] = React.useState<string | null>(null);
  const active = regions.find((region) => region.kind === selected) ?? regions[0];
  const site = active?.sites.find((row) => row.id === openSite) ?? active?.sites[active.sites.length - 1];

  return (
    <Card className="border-primary/20 shadow-card">
      <CardHeader className="pb-3">
        <SectionHeading
          eyebrow={t("eyebrows.reviewerAgent")}
          icon={<Compass className="size-4" aria-hidden />}
          title={t("timeline.atlasTitle")}
          description={t("timeline.atlasDescription")}
        />
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs leading-relaxed text-muted-foreground">{t("timeline.atlasLede")}</p>

        {regions.length === 0 ? (
          <p className="rounded-xl border border-border/60 bg-muted/30 p-4 text-xs leading-relaxed text-muted-foreground">
            {t("timeline.atlasEmpty")}
          </p>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-[minmax(10rem,14rem)_1fr]">
              <div className="space-y-1.5" role="group" aria-label={t("timeline.atlasRegionsLabel")}>
                {regions.map((region) => (
                  <Button
                    key={region.kind}
                    type="button"
                    variant={region.kind === active?.kind ? "secondary" : "ghost"}
                    size="sm"
                    className="w-full justify-between"
                    aria-pressed={region.kind === active?.kind}
                    onClick={() => {
                      setSelected(region.kind);
                      setOpenSite(null);
                    }}
                  >
                    <span className="truncate">{t(region.labelKey)}</span>
                    <Badge variant="outline" className="shrink-0 text-2xs tabular-nums">
                      {region.count}
                    </Badge>
                  </Button>
                ))}
              </div>

              {active && (
                <div className="space-y-3">
                  <svg
                    viewBox="0 0 100 100"
                    role="img"
                    aria-label={t("timeline.atlasMapLabel")}
                    className="h-44 w-full rounded-xl border hairline bg-muted/20 text-muted-foreground"
                  >
                    <circle cx="50" cy="50" r="46" fill="none" stroke="currentColor" strokeOpacity="0.35" />
                    <circle cx="50" cy="50" r="30" fill="none" stroke="currentColor" strokeOpacity="0.2" />
                    <line x1="50" y1="4" x2="50" y2="96" stroke="currentColor" strokeOpacity="0.12" />
                    <line x1="4" y1="50" x2="96" y2="50" stroke="currentColor" strokeOpacity="0.12" />
                    {active.sites.map((row) => (
                      <circle
                        key={row.id}
                        cx={row.x}
                        cy={row.y}
                        r={row.id === site?.id ? 2.8 : 1.7}
                        className={row.id === site?.id ? "fill-primary" : "fill-primary/50"}
                      >
                        <title>{row.title}</title>
                      </circle>
                    ))}
                  </svg>
                  <p className="text-xs text-muted-foreground">
                    {t("timeline.atlasSiteCount", { count: active.count })}
                    {active.hidden > 0 ? ` · ${t("timeline.atlasHiddenSites", { count: active.hidden })}` : ""}
                  </p>
                  <ul className="flex flex-wrap gap-1.5">
                    {active.sites.map((row) => (
                      <li key={row.id}>
                        <Button
                          type="button"
                          size="sm"
                          variant={row.id === site?.id ? "secondary" : "ghost"}
                          title={row.title}
                          onClick={() => setOpenSite(row.id)}
                        >
                          <MapPin aria-hidden className="size-3" />
                          <span className="max-w-[10rem] truncate">{row.title}</span>
                        </Button>
                      </li>
                    ))}
                  </ul>
                  {site && (
                    <div className="rounded-xl border border-border/60 bg-card p-3">
                      <p className="truncate text-sm font-medium">{site.title}</p>
                      {site.summary ? (
                        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{site.summary}</p>
                      ) : null}
                      <time dateTime={site.at} className="mt-2 block text-2xs tabular-nums text-muted-foreground">
                        {formatDate(site.at, locale)}
                      </time>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}

        <div className="rounded-xl border border-border/60 bg-muted/20 p-3">
          <p className="flex items-center gap-2 text-xs font-medium">
            <Sparkles aria-hidden className="size-3.5 text-primary" />
            {t("timeline.atlasFrontierTitle")}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            {t("timeline.atlasFrontierDescription")}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {FRONTIERS.map((frontier) => (
              <Button key={frontier.href} asChild size="sm" variant="outline">
                <Link href={frontier.href}>{t(frontier.key)}</Link>
              </Button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
