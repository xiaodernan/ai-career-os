"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { relativeTime } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";
import type { Application, ApplicationPacket } from "@/lib/api/types";

/**
 * The pipeline packet attached to one application.
 *
 * The application used to show three raw uuids, which is not something a reader can check.
 * This panel resolves each link into the label its owner would recognise -- the resume's title
 * and version, the JD's role and company, the match's score -- and links to the screen that
 * holds it. A linked column whose row can no longer be read is not drawn as "not linked": the
 * two mean different things to someone deciding whether the packet they sent was complete.
 */

type Translate = (key: string, vars?: Record<string, string | number>) => string;

interface PacketRow {
  key: "resume" | "jd" | "match" | "letters" | "rehearsals";
  label: string;
  primary: string;
  secondary?: string;
  href?: string;
  state: "ready" | "unavailable" | "missing";
  /** Set for the two counting rows (letters, rehearsals) instead of a state badge. */
  count?: number;
}

export interface ApplicationPacketPanelProps {
  application: Application;
  packet?: ApplicationPacket | null;
  loading?: boolean;
  failed?: boolean;
}

function resumeRow(
  packet: ApplicationPacket,
  t: Translate,
  locale: "en" | "zh"
): PacketRow {
  const value = packet.resume;
  const secondary = [value?.label, value?.kind !== value?.label ? value?.kind : null]
    .filter(Boolean)
    .join(" · ");
  return {
    key: "resume",
    label: t("applications.dialog.resumeVersionLink"),
    primary: value?.title || t("applications.dialog.packet.untitledResume"),
    secondary: [secondary, value?.createdAt ? relativeTime(value.createdAt, locale) : ""]
      .filter(Boolean)
      .join(" · "),
    href: value?.resumeId ? `/resumes/${encodeURIComponent(value.resumeId)}` : undefined,
    state: !packet.resumeLinked ? "missing" : value ? "ready" : "unavailable",
  };
}

function jdRow(application: Application, packet: ApplicationPacket, t: Translate, locale: "en" | "zh"): PacketRow {
  const value = packet.jd;
  return {
    key: "jd",
    label: t("applications.dialog.jdAnalysis"),
    primary: value?.title || application.title,
    secondary: [value?.companyName, value?.createdAt ? relativeTime(value.createdAt, locale) : ""]
      .filter(Boolean)
      .join(" · "),
    href: value?.jobId ? `/jobs/${encodeURIComponent(value.jobId)}` : undefined,
    state: !packet.jdLinked ? "missing" : value ? "ready" : "unavailable",
  };
}

function matchRow(packet: ApplicationPacket, t: Translate, locale: "en" | "zh"): PacketRow {
  const value = packet.match;
  return {
    key: "match",
    label: t("applications.dialog.match"),
    primary: value?.overall != null
      ? t("applications.dialog.packet.matchScore", { score: Math.round(value.overall * 100) })
      : t("applications.dialog.packet.untitledMatch"),
    secondary: value?.createdAt ? relativeTime(value.createdAt, locale) : undefined,
    href: value?.jobId ? `/jobs/${encodeURIComponent(value.jobId)}` : undefined,
    state: !packet.matchLinked ? "missing" : value ? "ready" : "unavailable",
  };
}

/**
 * The fourth artifact (53.1). It is a count, not a link: a kept letter has no screen of its own
 * and there may be several, so the row answers "how much is here" rather than "which one".
 */
function lettersRow(packet: ApplicationPacket, t: Translate): PacketRow {
  const count = packet.letters ?? 0;
  return {
    key: "letters",
    label: t("applications.dialog.letters"),
    primary:
      count > 0
        ? t("applications.dialog.packet.letterCount", { count })
        : t("applications.dialog.packet.noLetters"),
    state: count > 0 ? "ready" : "missing",
    count,
  };
}

/**
 * The fifth artifact (57.2). Also a count, and the only count that links: the
 * rehearsals are a screen of their own (`/interviews`), narrowed to this card
 * by the filter 57.1 added. A card nobody practised for draws no link -- there
 * is nothing on the other side of it.
 */
function rehearsalsRow(
  application: Application,
  packet: ApplicationPacket,
  t: Translate
): PacketRow {
  const count = packet.rehearsals ?? 0;
  return {
    key: "rehearsals",
    label: t("applications.dialog.rehearsals"),
    primary:
      count > 0
        ? t("applications.dialog.packet.rehearsalCount", {
            count,
            plural: count === 1 ? "" : "s",
          })
        : t("applications.dialog.packet.noRehearsals"),
    href: count > 0 ? `/interviews?application=${encodeURIComponent(application.id)}` : undefined,
    state: count > 0 ? "ready" : "missing",
    count,
  };
}

function Status({ row, t }: { row: PacketRow; t: Translate }) {
  // A count is its own status: printing "Not linked" beside "None kept yet" would say the same
  // thing twice, and "Not linked" would be false for a letter that simply was never written.
  // The rehearsal count keeps its link, though: a count of something that has a screen is a door.
  if (row.count !== undefined && !row.href) return null;
  if (row.href) {
    return (
      <Button asChild size="sm" variant="ghost">
        <Link href={row.href}>
          {t("applications.dialog.packet.open")}
          <ArrowUpRight aria-hidden />
        </Link>
      </Button>
    );
  }
  return (
    <Badge variant={row.state === "unavailable" ? "warning" : "outline"} className="shrink-0">
      {row.state === "unavailable"
        ? t("applications.dialog.packet.unavailable")
        : t("applications.dialog.packet.notLinked")}
    </Badge>
  );
}

export function ApplicationPacketPanel({
  application,
  packet,
  loading = false,
  failed = false,
}: ApplicationPacketPanelProps) {
  const { t, locale } = useLocale();
  const headingId = React.useId();
  const rows = packet
    ? [
        resumeRow(packet, t, locale),
        jdRow(application, packet, t, locale),
        matchRow(packet, t, locale),
        lettersRow(packet, t),
        rehearsalsRow(application, packet, t),
      ]
    : [];
  const allMissing =
    packet != null &&
    !packet.resumeLinked &&
    !packet.jdLinked &&
    !packet.matchLinked &&
    (packet.letters ?? 0) === 0 &&
    (packet.rehearsals ?? 0) === 0;

  return (
    <section className="space-y-2" aria-labelledby={headingId}>
      <h4 id={headingId} className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {t("applications.dialog.pipelineLinks")}
      </h4>
      {loading ? (
        <div className="space-y-2" aria-label={t("applications.dialog.packet.loading")}>
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : failed ? (
        <p role="alert" className="text-sm text-destructive">
          {t("applications.dialog.packet.failed")}
        </p>
      ) : (
        <>
          <ul className="divide-y divide-border/70 rounded-lg border border-border/70">
            {rows.map((row) => (
              <li key={row.key} className="flex items-center gap-3 p-3">
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-muted-foreground">{row.label}</p>
                  <p className="truncate text-sm font-medium">{row.primary}</p>
                  {row.secondary ? (
                    <p className="truncate text-xs text-muted-foreground">{row.secondary}</p>
                  ) : null}
                </div>
                <Status row={row} t={t} />
              </li>
            ))}
          </ul>
          {allMissing ? (
            <p className="text-xs text-muted-foreground">
              {t("applications.dialog.packet.empty")}
            </p>
          ) : null}
        </>
      )}
      <p className="text-xs text-muted-foreground">{t("applications.dialog.pipelineLinksHint")}</p>
    </section>
  );
}
