/**
 * First-run quick start (Epic 347) — a one-time, in-app guided hello.
 *
 * The product already HAS the teaching material (the /tour beats, the /playbook
 * manual, the nine quests, the seeded job corpus). What it lacked was a single
 * moment on first open that actually walks a new reader through the real UI.
 * This module owns only the persisted "seen" flag: the tutorial is shown once,
 * skip/done persists it, and a Replay action can clear it to see it again.
 *
 * localStorage-only, like tour.ts — nothing here scores the person or reaches
 * the server. A browser with storage disabled simply sees the guide every visit,
 * which is the honest failure mode (show the teaching, never hide it silently).
 */

const ONBOARD_KEY = "careeros.onboard.v1";

function storage(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

/** True until the reader has seen (or skipped) the quick start once. */
export function needsQuickStart(replica: Storage | null = storage()): boolean {
  if (!replica) return true;
  try {
    return replica.getItem(ONBOARD_KEY) !== "seen";
  } catch {
    return true;
  }
}

/** Persist that the quick start has been shown; a later visit will not auto-open it. */
export function markQuickStartSeen(replica: Storage | null = storage()): void {
  if (!replica) return;
  try {
    replica.setItem(ONBOARD_KEY, "seen");
  } catch {
    // best effort — storage disabled means it simply shows again next time
  }
}

/** Clear the flag so the Replay action can walk the reader through it again. */
export function resetQuickStart(replica: Storage | null = storage()): void {
  if (!replica) return;
  try {
    replica.removeItem(ONBOARD_KEY);
  } catch {
    // ignore
  }
}
