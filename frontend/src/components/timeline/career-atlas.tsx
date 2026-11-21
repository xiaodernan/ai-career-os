"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpRight, Compass, MapPin, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Hint } from "@/components/ui/hint";
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

/**
 * 365: the route the reader actually walked, in the order they walked it.
 *
 * A map that says where you have been is half a map; the other half is how one
 * room led to the next. This reads the ledger in its own time order and keeps the
 * first moment each region appeared, so the path is the reader's own sequence --
 * resume first, then a posting, then the match, then the interview -- and never an
 * invented one. A region that only ever appeared once still gets its stop.
 */
export interface AtlasLeg {
  from: string;
  to: string;
}

export function buildRoute(events: TimelineEntry[]): string[] {
  const ordered = [...events].sort((a, b) => a.at.localeCompare(b.at));
  const seen: string[] = [];
  for (const event of ordered) {
    const kind = (REGION_ORDER as readonly string[]).includes(event.kind)
      ? event.kind
      : "unknown";
    if (!seen.includes(kind)) seen.push(kind);
  }
  return seen;
}

export interface AtlasRegion {
  kind: string;
  labelKey: string;
  count: number;
  hidden: number;
  firstAt: string;
  lastAt: string;
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
      // 361: the region's span -- when the first and the newest fact in it were
      // written. A count says how much is here; a span says how long the reader
      // has been building it, which is the thing a map is for.
      firstAt: ordered[0].at,
      lastAt: ordered[ordered.length - 1].at,
      sites,
    }];
  });
}

/**
 * 364: where each region's facts are written.
 *
 * The map names every room the reader has been; these are the rooms themselves. A
 * region with no screen of its own (the engine's own `unknown` bucket) carries no
 * door rather than a link that would answer 404 -- an honest gap beats a dead one.
 */
const REGION_DOORS: Record<string, { href: string; key: string } | undefined> = {
  application: { href: "/applications", key: "timeline.atlasDoorApplications" },
  interview: { href: "/interviews", key: "timeline.atlasDoorInterviews" },
  match: { href: "/jobs", key: "timeline.atlasDoorJobs" },
  contact: { href: "/networking", key: "timeline.atlasDoorNetworking" },
  resume_version: { href: "/resumes", key: "timeline.atlasDoorResumes" },
  note: { href: "/knowledge", key: "timeline.atlasDoorNotes" },
};

/** A door is offered only while its region is still uncharted. */
const FRONTIERS = [
  { kind: "match", key: "timeline.atlasFrontierJobs", href: "/jobs" },
  { kind: "application", key: "timeline.atlasFrontierApplications", href: "/applications" },
  { kind: "interview", key: "timeline.atlasFrontierInterviews", href: "/interviews" },
  { kind: "contact", key: "timeline.atlasFrontierNetworking", href: "/networking" },
  { kind: "resume_version", key: "timeline.atlasFrontierResumes", href: "/resumes" },
] as const;

export function CareerAtlas({ events }: { events: TimelineEntry[] }) {
  const { t, locale } = useLocale();
  const regions = React.useMemo(() => buildAtlas(events), [events]);
  const [selected, setSelected] = React.useState<string | null>(null);
  const [openSite, setOpenSite] = React.useState<string | null>(null);
  const active = regions.find((region) => region.kind === selected) ?? regions[0];
  const site = active?.sites.find((row) => row.id === openSite) ?? active?.sites[active.sites.length - 1];
  const charted = React.useMemo(() => new Set(regions.map((region) => region.kind)), [regions]);
  // 365: the reader's own route through the world, in the order they walked it. It
  // is drawn over every region rather than the selected one, because the sequence
  // is a fact about the whole ledger -- narrowing the fold narrows what is drawn,
  // exactly as the sites do.
  const route = React.useMemo(() => buildRoute(events), [events]);
  // Each region's centre is the mean of the sites drawn for it, so a leg joins
  // where the reader's facts actually sit rather than a point invented for the
  // region. A region with no drawn sites contributes no leg.
  const legs = React.useMemo(() => {
    const centre = new Map(regions.map((region) => {
      const rows = region.sites;
      const x = rows.reduce((sum, site) => sum + site.x, 0) / Math.max(1, rows.length);
      const y = rows.reduce((sum, site) => sum + site.y, 0) / Math.max(1, rows.length);
      return [region.kind, { x, y }] as const;
    }));
    const out: Array<{ from: string; to: string; x1: number; y1: number; x2: number; y2: number }> = [];
    for (let i = 1; i < route.length; i += 1) {
      const a = centre.get(route[i - 1]);
      const b = centre.get(route[i]);
      if (!a || !b) continue;
      out.push({ from: route[i - 1], to: route[i], x1: a.x, y1: a.y, x2: b.x, y2: b.y });
    }
    return out;
  }, [regions, route]);
  const openFrontiers = FRONTIERS.filter((frontier) => !charted.has(frontier.kind));

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
                {regions.map((region) => {
                  // 364: a region is a door, not just a lens. The reader who sees
                  // "Interview · 12" wants to stand in that room, and the map is the
                  // one surface that can name every room at once -- so each region
                  // carries the link to the screen that writes its facts, beside the
                  // count of what is already there.
                  const door = REGION_DOORS[region.kind];
                  return (
                    <div key={region.kind} className="flex items-center gap-1">
                      <Button
                        type="button"
                        variant={region.kind === active?.kind ? "secondary" : "ghost"}
                        size="sm"
                        className="min-w-0 flex-1 justify-between"
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
                      {door ? (
                        <Hint label={t("timeline.atlasRegionDoor", { region: t(region.labelKey) })}>
                          <Button asChild size="sm" variant="ghost" className="shrink-0 px-2">
                            <Link href={door.href} aria-label={t(door.key)}>
                              <ArrowUpRight aria-hidden className="size-3.5" />
                            </Link>
                          </Button>
                        </Hint>
                      ) : null}
                    </div>
                  );
                })}
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
                    {/* 365: the route the reader walked. Each leg joins one
                        region's centre to the next region they actually reached,
                        in the order the ledger says they reached it -- a dashed
                        line, because it is a path taken rather than a road that
                        exists. */}
                    {legs.map((leg) => (
                      <line
                        key={`${leg.from}-${leg.to}`}
                        x1={leg.x1}
                        y1={leg.y1}
                        x2={leg.x2}
                        y2={leg.y2}
                        stroke="currentColor"
                        strokeWidth="0.4"
                        strokeDasharray="1.5 1.5"
                        strokeOpacity="0.5"
                      />
                    ))}
                    {/* 361: a site is a door, not a dot. Every circle is inside a
                        focusable button, so the map can be walked with the keyboard
                        and a click lands on the fact itself -- the list below is the
                        same doors in words for a reader who would rather read than
                        point. */}
                    {active.sites.map((row) => (
                      <g key={row.id}>
                        <circle
                          cx={row.x}
                          cy={row.y}
                          r={row.id === site?.id ? 2.8 : 1.7}
                          className={row.id === site?.id ? "fill-primary" : "fill-primary/50"}
                        />
                        <circle
                          cx={row.x}
                          cy={row.y}
                          r={4}
                          fill="transparent"
                          className="cursor-pointer"
                          tabIndex={0}
                          role="button"
                          aria-pressed={row.id === site?.id}
                          aria-label={row.title}
                          onClick={() => setOpenSite(row.id)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              setOpenSite(row.id);
                            }
                          }}
                        >
                          <title>{row.title}</title>
                        </circle>
                      </g>
                    ))}
                  </svg>
                  {/* 365: the dashed line is a path taken, and a path the reader
                      cannot see the shape of is a line they will not trust. */}
                  {legs.length > 0 ? (
                    <p className="text-xs text-muted-foreground">
                      {t("timeline.atlasRouteLength", { count: legs.length })}
                    </p>
                  ) : null}
                  <p className="text-xs text-muted-foreground">
                    {t("timeline.atlasSiteCount", { count: active.count })}
                    {active.hidden > 0 ? ` · ${t("timeline.atlasHiddenSites", { count: active.hidden })}` : ""}
                    {/* 361: how long this stretch of the world took to build. The
                        span is the reader's own, read off the first and newest fact
                        in the region -- never invented. */}
                    <span className="block sm:inline sm:before:content-['_·_']">
                      {t("timeline.atlasSpan", {
                        from: formatDate(active.firstAt, locale),
                        to: formatDate(active.lastAt, locale),
                      })}
                    </span>
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
          {openFrontiers.length === 0 ? (
            <p className="mt-2 text-xs text-muted-foreground">{t("timeline.atlasAllCharted")}</p>
          ) : (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {openFrontiers.map((frontier) => (
                <Button key={frontier.href} asChild size="sm" variant="outline">
                  <Link href={frontier.href} title={t(LABEL_KEYS[frontier.kind])}>
                    {t(frontier.key)}
                  </Link>
                </Button>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
