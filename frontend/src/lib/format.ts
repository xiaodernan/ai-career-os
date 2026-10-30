/** Formatting helpers shared by every surface — no per-page date/currency code. */

import type { Locale } from "@/lib/i18n/translations";

/**
 * "Oct 28, 2026" / "2026年10月28日" — the reader's language, not the machine's.
 *
 * `toLocaleDateString(undefined, ...)` reads the *browser's* locale, so an English reader on a
 * zh-CN machine read "2026年10月28日" inside English sentences, and a Chinese reader on an en-US
 * machine read the mirror image. `locale` is required, like `relativeTime`'s, so no surface can
 * quietly fall back to the machine.
 */
export function formatDate(value: string | null | undefined, locale: Locale): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(locale, { month: "short", day: "numeric", year: "numeric" });
}

/**
 * A calendar date, formatted in the reader's language without touching a timezone.
 *
 * `formatDate` converts through the reader's zone, which is right for a moment and wrong
 * for a date: "2026-10-26" parsed as UTC midnight is Oct 25 for a reader in Los Angeles. A
 * week starts on a date, so it is formatted as one. A value that is not date-shaped falls
 * back to `formatDate`, which is what a moment-shaped value deserves.
 */
export function formatDateOnly(value: string | null | undefined, locale: Locale): string {
  if (!value) return "";
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return formatDate(value, locale);
  const d = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  return d.toLocaleDateString(locale, {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** "Oct 28, 02:05 PM" / "10月28日 14:05" — the same rule as formatDate, with the clock. */
export function formatDateTime(value: string | null | undefined, locale: Locale): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(locale, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const narrowFormatters = new Map<string, Intl.RelativeTimeFormat>();

function narrow(locale: Locale, numeric: "auto" | "always"): Intl.RelativeTimeFormat {
  const key = `${locale}:${numeric}`;
  let formatter = narrowFormatters.get(key);
  if (!formatter) {
    formatter = new Intl.RelativeTimeFormat(locale, { numeric, style: "narrow" });
    narrowFormatters.set(key, formatter);
  }
  return formatter;
}

/**
 * "3m ago" / "3分钟前" — the reader's language, and the right direction.
 *
 * The stamp sits inside translated sentences ("收藏于 {date}", "最近一步：{when}"), so an
 * English unit read as "收藏于 3d ago"; `locale` is required rather than defaulted so every
 * call site has to say whose language it is speaking. `narrow` + `always` reproduces the
 * compact English the hand-rolled formatter shipped ("5m ago", "1d ago", "1y ago"); `auto`
 * is used only for the under-a-minute bucket, where ICU's word is "now"/"现在" and the
 * rounded "0s ago" would read as a mis-signed value.
 *
 * A future value — `reminderAt` usually is one — formats forward ("in 3h"/"3小时后"); the
 * old subtract-and-divide kept the sign in the divisor and printed "-1440m ago" for a
 * reminder set for tomorrow.
 */
export function relativeTime(value: string | null | undefined, locale: Locale): string {
  if (!value) return "";
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return value;
  const diff = Date.now() - then;
  if (Math.abs(diff) < 60_000) return narrow(locale, "auto").format(0, "second");
  const sign = diff > 0 ? -1 : 1;
  const minutes = Math.round(Math.abs(diff) / 60_000);
  if (minutes < 60) return narrow(locale, "always").format(sign * minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (hours < 24) return narrow(locale, "always").format(sign * hours, "hour");
  const days = Math.round(hours / 24);
  if (days < 30) return narrow(locale, "always").format(sign * days, "day");
  const months = Math.round(days / 30);
  if (months < 12) return narrow(locale, "always").format(sign * months, "month");
  return narrow(locale, "always").format(sign * Math.round(months / 12), "year");
}

const CURRENCY_SYMBOL: Record<string, string> = {
  USD: "$",
  CNY: "¥",
  RMB: "¥",
  EUR: "€",
  GBP: "£",
  HKD: "HK$",
  SGD: "S$",
};

function compact(n: number): string {
  if (Math.abs(n) >= 1000) return `${Math.round(n / 1000)}k`;
  return String(Math.round(n));
}

/** Salary band, e.g. "$40k–$60k" / "¥30–45万". Missing parts are dropped. */
export function formatSalary(
  min?: number | null,
  max?: number | null,
  currency?: string | null
): string | null {
  if (min == null && max == null) return null;
  const cur = (currency ?? "USD").toUpperCase();
  const symbol = CURRENCY_SYMBOL[cur] ?? `${cur} `;
  const perYear = cur === "CNY" || cur === "RMB";
  const fmt = (n: number) => (perYear ? `${Math.round(n / 10_000)}万` : `${symbol}${compact(n)}`);
  if (min != null && max != null && min !== max) return `${fmt(min)}–${fmt(max)}`;
  if (min != null) return `${fmt(min)}+`;
  return `up to ${fmt(max as number)}`;
}

export function formatNumber(n?: number | null): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toLocaleString();
}

export function formatCompact(n?: number | null): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

export function formatUsd(n?: number | null): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n < 0.01 ? `$${n.toFixed(4)}` : `$${n.toFixed(2)}`;
}

export function formatDuration(ms?: number | null): string {
  if (ms == null || !Number.isFinite(ms)) return "";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s < 10 ? s.toFixed(1) : Math.round(s)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

export function pluralize(count: number, one: string, many?: string): string {
  return `${count} ${count === 1 ? one : (many ?? `${one}s`)}`;
}

export function titleCase(value?: string | null): string {
  if (!value) return "";
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * The interview agent's own difficulty number, projected onto the 1–5 ladder every
 * depth surface draws. The pipeline sends 0..1 (`decide_next` clamps to 0.1–0.95) and
 * the trajectory rows send 0/1 follow-up flags; printing either raw put a fraction on
 * a badge that reads "depth".
 *
 * The scales collide at exactly 1, which reads as the top of the 0–1 scale here. Only
 * session/question difficulty goes through this function; the trajectory's 1–5 ladder
 * is folded to run lengths in `normalizeTrajectory` and drawn as-is, so a ladder-1
 * "Warm-up" can never be re-projected into "Expert".
 */
export function depthLevel(value: number): number {
  const level = value <= 1 ? Math.round(value * 5) : Math.round(Math.min(5, Math.max(1, value)));
  return Math.min(5, Math.max(1, level));
}

/** The five rungs `depthLevel` draws, as band tokens; the words come from the locale table. */
export const DEPTH_BANDS = ["warmup", "standard", "solid", "deep", "expert"] as const;

export type DepthBand = (typeof DEPTH_BANDS)[number];

export function depthBand(value: number): DepthBand {
  return DEPTH_BANDS[depthLevel(value) - 1] ?? "standard";
}

/** Memory importance → the band the editor offers; the words come from the locale table. */
export type WeightBand = "low" | "normal" | "high";

/** Memory importance → band for the memory card. */
export function weightBand(importance: number): WeightBand {
  if (importance >= 0.85) return "high";
  if (importance <= 0.35) return "low";
  return "normal";
}

/** Beyond this the number is a parse artifact, not a requirement: no role asks for a
 *  40-year career. The JD importer stores whatever the model answered verbatim. */
const MAX_EXPERIENCE_YEARS = 30;

/**
 * `jobs.experience_years` → the number the seniority chip draws, or undefined when the
 * chip hides. 0 is a real answer ("no experience required") and must not read as
 * missing; null means the posting never said, so the chip hides instead of inventing
 * "0+".
 *
 * The number is the wire fact; the words are the reader's. This function used to mint
 * the English phrase itself ("3+ years experience"), which the job detail printed
 * verbatim on a Chinese page — and the copy census could not see it, because the
 * sentence lived in the data layer rather than in a page. `seniorityWord` picks the
 * words from the table from this number.
 */
export function seniorityYears(
  years: number | null | undefined
): number | undefined {
  if (typeof years !== "number" || !Number.isFinite(years)) return undefined;
  const y = Math.trunc(years);
  if (y < 0 || y > MAX_EXPERIENCE_YEARS) return undefined;
  return y;
}

export function initialsOf(...parts: (string | undefined | null)[]): string {
  const letters = parts
    .filter(Boolean)
    .join(" ")
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
  return letters || "?";
}

/** Copy text to the clipboard with a legacy fallback (http/insecure origins). */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* fall through to the textarea trick */
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

/** Client-side download for AI artifacts (tailored resume, cover letter, report). */
export function downloadText(filename: string, text: string, mime = "text/plain;charset=utf-8") {
  downloadBlob(filename, new Blob([text], { type: mime }));
}

/**
 * Save a blob the browser would otherwise only preview: object URL, programmatic click, revoke.
 * The caller names the file — usually the name the server's Content-Disposition carried.
 */
export function downloadBlob(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "document";
}
