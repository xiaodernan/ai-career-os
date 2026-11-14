/**
 * The pocket (Epic 223) — the browser-local half of the reader's work.
 *
 * Four things the person wrote in their browser live nowhere else:
 *
 *   careeros.ledger.v1     the decision ledger — criteria, weights, per-offer scores
 *   careeros.quarter.*     the first-quarter plan's ticks, keyed by the accepted offer row
 *   careeros.dayone.*      the day-one packet's ticks, same shape
 *   careeros.debrief.*     the after-action debriefs, keyed by interview session id
 *
 * The server cannot see them by design (they never left the browser), so
 * the export bundle omits them. This module is their suitcase — the one
 * file the reader owns that carries the browser's side of the story.
 * Pure functions with an injectable storage port, so the round trip is
 * unit-testable; the UI is a card on /data.
 */

const SCHEMA = "careeros-pocket/1";

export const POCKET_PREFIXES = [
  "careeros.ledger.",
  "careeros.quarter.",
  "careeros.dayone.",
  "careeros.debrief.",
] as const;

export interface PocketFamily {
  prefix: string;
  count: number;
  /** Characters across the family's values — a hint of how much this carries. */
  characters: number;
}

export interface PocketManifest {
  schema: typeof SCHEMA;
  exportedAt: string;
  entries: Record<string, string>;
}

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem" | "length" | "key"> & {
  readonly length: number;
  key(index: number): string | null;
};

function defaultStorage(): StorageLike | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

/** Every pocket key in the given storage, in a stable order. */
export function collectPocket(storage: StorageLike | null = defaultStorage()): PocketManifest {
  const entries: Record<string, string> = {};
  if (storage) {
    for (let i = 0; i < storage.length; i += 1) {
      const key = storage.key(i);
      if (!key) continue;
      if (!POCKET_PREFIXES.some((prefix) => key.startsWith(prefix))) continue;
      const value = storage.getItem(key);
      if (value !== null) entries[key] = value;
    }
  }
  return { schema: SCHEMA, exportedAt: new Date().toISOString(), entries };
}

export function pocketSummary(manifest: PocketManifest): { families: PocketFamily[]; total: number; characters: number } {
  const families = POCKET_PREFIXES.map((prefix) => {
    const keys = Object.keys(manifest.entries).filter((k) => k.startsWith(prefix));
    return {
      prefix,
      count: keys.length,
      characters: keys.reduce((sum, k) => sum + (manifest.entries[k]?.length ?? 0), 0),
    };
  });
  return {
    families,
    total: families.reduce((sum, f) => sum + f.count, 0),
    characters: families.reduce((sum, f) => sum + f.characters, 0),
  };
}

export function serializePocket(manifest: PocketManifest): string {
  return JSON.stringify(manifest, null, 2);
}

export function parsePocket(text: string): PocketManifest | null {
  try {
    const parsed = JSON.parse(text) as Record<string, unknown>;
    if (parsed?.schema !== SCHEMA) return null;
    const raw = parsed?.entries;
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
    const entries: Record<string, string> = {};
    for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
      if (typeof value === "string") entries[key] = value;
    }
    return { schema: SCHEMA, exportedAt: typeof parsed.exportedAt === "string" ? parsed.exportedAt : new Date(0).toISOString(), entries };
  } catch {
    return null;
  }
}

export interface RestoreResult {
  restored: number;
  skipped: string[];
}

/** Write back only keys the product itself wrote — nothing else rides along. */
export function restorePocket(manifest: PocketManifest, storage: StorageLike | null = defaultStorage()): RestoreResult {
  const skipped: string[] = [];
  let restored = 0;
  if (!storage) return { restored: 0, skipped: Object.keys(manifest.entries) };
  for (const [key, value] of Object.entries(manifest.entries)) {
    if (!POCKET_PREFIXES.some((prefix) => key.startsWith(prefix))) {
      skipped.push(key);
      continue;
    }
    try {
      storage.setItem(key, value);
      restored += 1;
    } catch {
      skipped.push(key);
    }
  }
  return { restored, skipped };
}

/** A short human sentence for the family line, exported so callers cannot drift. */
export function familyLabelKey(prefix: string): string {
  switch (prefix) {
    case "careeros.ledger.":
      return "data.pocketFamilyLedger";
    case "careeros.quarter.":
      return "data.pocketFamilyQuarter";
    case "careeros.dayone.":
      return "data.pocketFamilyDayOne";
    case "careeros.debrief.":
      return "data.pocketFamilyDebrief";
    default:
      return "data.pocketFamilyLedger";
  }
}
