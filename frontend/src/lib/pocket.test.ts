import { describe, expect, it } from "vitest";
import {
  POCKET_PREFIXES,
  collectPocket,
  parsePocket,
  pocketSummary,
  restorePocket,
  serializePocket,
  type PocketManifest,
} from "./pocket";

function fakeStorage(seed: Record<string, string> = {}) {
  const map = new Map<string, string>(Object.entries(seed));
  return {
    get length() {
      return map.size;
    },
    key(index: number) {
      return [...map.keys()][index] ?? null;
    },
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
    seed,
  };
}

const SAMPLE = {
  "careeros.ledger.v1": JSON.stringify({ criteria: [], scores: { "offer-1": { comp: 9 } } }),
  "careeros.quarter.offer-1": JSON.stringify({ quarterOwn1: true }),
  "careeros.dayone.offer-1": JSON.stringify({ dayOneVest: true }),
  "careeros.debrief.session-9": JSON.stringify({
    whatHappened: "I rambled.",
    differently: "Name the result first.",
  }),
  "careeros.locale": "zh",
  "unrelated.key": "not ours",
};

describe("collectPocket", () => {
  it("collects only the four pocket prefixes, nothing else", () => {
    const manifest = collectPocket(fakeStorage(SAMPLE));
    expect(Object.keys(manifest.entries).sort()).toEqual([
      "careeros.dayone.offer-1",
      "careeros.debrief.session-9",
      "careeros.ledger.v1",
      "careeros.quarter.offer-1",
    ]);
    expect(manifest.schema).toBe("careeros-pocket/1");
  });

  it("returns an empty manifest when the pocket is empty or storage is absent", () => {
    expect(collectPocket(fakeStorage({})).entries).toEqual({});
    expect(collectPocket(null).entries).toEqual({});
  });
});

describe("pocketSummary", () => {
  it("groups counts and characters per family", () => {
    const summary = pocketSummary(collectPocket(fakeStorage(SAMPLE)));
    expect(summary.total).toBe(4);
    const byPrefix = Object.fromEntries(summary.families.map((f) => [f.prefix, f.count]));
    expect(byPrefix["careeros.ledger."]).toBe(1);
    expect(byPrefix["careeros.quarter."]).toBe(1);
    expect(byPrefix["careeros.dayone."]).toBe(1);
    expect(byPrefix["careeros.debrief."]).toBe(1);
    expect(summary.characters).toBeGreaterThan(0);
  });
});

describe("serialize/parse round trip", () => {
  it("survives a save-and-reload cycle", () => {
    const original = collectPocket(fakeStorage(SAMPLE));
    const text = serializePocket(original);
    const parsed = parsePocket(text);
    expect(parsed).not.toBeNull();
    expect(parsed!.entries).toEqual(original.entries);
    expect(parsed!.schema).toBe("careeros-pocket/1");
  });

  it("refuses a foreign schema or broken JSON", () => {
    expect(parsePocket("not json")).toBeNull();
    expect(parsePocket('{"schema":"other/1","entries":{}}')).toBeNull();
    expect(parsePocket('{"schema":"careeros-pocket/1"}')).toBeNull();
    expect(parsePocket('{"schema":"careeros-pocket/1","entries":["x"]}')).toBeNull();
  });

  it("drops non-string values rather than corrupting the storage", () => {
    const parsed = parsePocket('{"schema":"careeros-pocket/1","entries":{"careeros.ledger.v1":42,"careeros.ledger.v2":"ok"}}');
    expect(parsed!.entries).toEqual({ "careeros.ledger.v2": "ok" });
  });
});

describe("restorePocket", () => {
  it("writes back only the pocket prefixes and reports what it skipped", () => {
    const target = fakeStorage({ "careeros.locale": "en" });
    const incoming: PocketManifest = {
      schema: "careeros-pocket/1",
      exportedAt: "2026-11-15T00:00:00.000Z",
      entries: {
        "careeros.ledger.v1": "{}",
        "careeros.quarter.offer-9": "{}",
        "careeros.unknown.thing": "nope",
        "cookies": "nope",
      },
    };
    const result = restorePocket(incoming, target);
    expect(result.restored).toBe(2);
    expect(result.skipped.sort()).toEqual(["careeros.unknown.thing", "cookies"]);
    expect(target.getItem("careeros.ledger.v1")).toBe("{}");
    expect(target.getItem("careeros.locale")).toBe("en"); // untouched
  });

  it("restores exactly what collect picked up", () => {
    const source = fakeStorage(SAMPLE);
    const restored = fakeStorage({});
    const manifest = collectPocket(source);
    const result = restorePocket(manifest, restored);
    expect(result.restored).toBe(4);
    expect(restored.getItem("careeros.ledger.v1")).toBe(SAMPLE["careeros.ledger.v1"]);
    expect(restored.getItem("careeros.debrief.session-9")).toBe(SAMPLE["careeros.debrief.session-9"]);
  });
});
