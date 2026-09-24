/** Formatting helpers shared by every surface — no per-page date/currency code. */

export function formatDate(value?: string | null, opts?: Intl.DateTimeFormatOptions): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, opts ?? { month: "short", day: "numeric", year: "numeric" });
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function relativeTime(value?: string | null): string {
  if (!value) return "";
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return value;
  const diff = Date.now() - then;
  const min = Math.round(diff / 60_000);
  if (Math.abs(diff) < 60_000) return "just now";
  if (min < 60) return `${min}m ago`;
  const hours = Math.round(min / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.round(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.round(months / 12)}y ago`;
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
  currency?: string | null,
  text?: string | null
): string | null {
  if (text) return text;
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

const DEPTH_LABELS = ["Warm-up", "Standard", "Solid", "Deep", "Expert"];

export function depthLabel(value: number): string {
  return DEPTH_LABELS[depthLevel(value) - 1] ?? String(depthLevel(value));
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
  const blob = new Blob([text], { type: mime });
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
