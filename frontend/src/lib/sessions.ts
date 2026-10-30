import { ApiError } from "@/lib/api/client";

/**
 * The settings card's two decisions, held apart from the screen.
 *
 * The backend stores the raw user-agent, because that is the only name a device offers;
 * the reader needs a name they recognise. And a close that answers `LOGIN_SESSION_NOT_FOUND`
 * is not a failure the reader can act on — the door is already shut — so the screen
 * refreshes instead of showing a refusal. Both rules are arithmetic, not markup.
 */

const BROWSERS: Array<[RegExp, string]> = [
  [/Edg(e|A|iOS)?\//, "Edge"],
  [/OPR\//, "Opera"],
  [/CriOS\//, "Chrome"],
  [/FxiOS\//, "Firefox"],
  [/Chrome\//, "Chrome"],
  [/Firefox\//, "Firefox"],
  [/Safari\//, "Safari"],
];

const SYSTEMS: Array<[RegExp, string]> = [
  [/Windows/, "Windows"],
  [/iPhone|iPad|iPod/, "iOS"],
  [/Android/, "Android"],
  [/Mac OS X|Macintosh/, "macOS"],
  [/CrOS/, "ChromeOS"],
  [/Linux/, "Linux"],
];

/**
 * "Chrome · Windows" from a user-agent. An agent that names neither a browser nor a
 * system is shown as itself — a deployment's own client ("JUnit/laptop") is the most
 * recognisable name it has — and a missing agent gets the caller's fallback sentence.
 */
export function deviceLabel(userAgent: string | null | undefined, fallback: string): string {
  if (!userAgent || !userAgent.trim()) return fallback;
  const browser = BROWSERS.find(([pattern]) => pattern.test(userAgent))?.[1];
  const system = SYSTEMS.find(([pattern]) => pattern.test(userAgent))?.[1];
  if (browser && system) return `${browser} · ${system}`;
  return browser ?? system ?? userAgent.trim();
}

/**
 * What a failed close means. `gone` is the backend's one 404 for a family that is not
 * live for this account (a neighbour's or one already closed) — the screen refreshes and
 * says the door was already shut. Every other failure is the caller's to report.
 */
export function sessionCloseRefusal(err: unknown): "gone" | null {
  return err instanceof ApiError && err.code === "LOGIN_SESSION_NOT_FOUND" ? "gone" : null;
}
