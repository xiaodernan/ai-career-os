import { describe, expect, it } from "vitest";
import { INBOX_KINDS, asInboxKind, kindsPresent, rowsUnder } from "@/lib/inbox-filter";
import type { NotificationItem } from "@/lib/api/types";

function item(kind: string, key = `${kind}:1`): NotificationItem {
  return {
    key,
    kind,
    title: "Acme",
    subject: "",
    status: "",
    count: null,
    note: null,
    link: "/notifications",
    read: false,
  };
}

describe("the inbox's own filter", () => {
  it("adopts only a kind the page can name", () => {
    for (const kind of INBOX_KINDS) {
      expect(asInboxKind(kind)).toBe(kind);
    }
    // Anything else is no filter at all: an empty list would look like a quiet morning.
    expect(asInboxKind(undefined)).toBeNull();
    expect(asInboxKind("")).toBeNull();
    expect(asInboxKind("replied")).toBeNull();
    expect(asInboxKind("all")).toBeNull();
  });

  it("lists the kinds present in the server's order, never the absent ones", () => {
    const items = [
      item("reply"),
      item("reminder"),
      item("reply"),
      item("saved_search"),
    ];
    expect(kindsPresent(items)).toEqual([
      { kind: "reminder", count: 1 },
      { kind: "saved_search", count: 1 },
      { kind: "reply", count: 2 },
    ]);
  });

  it("counts every row of a kind, read or not", () => {
    const items = [item("stale", "a"), { ...item("stale", "b"), read: true }, item("reply")];
    expect(kindsPresent(items)).toEqual([
      { kind: "stale", count: 2 },
      { kind: "reply", count: 1 },
    ]);
  });

  it("leaves a kind nobody named out of the chips", () => {
    // The server can grow a seventh kind before this screen learns its name.
    const items = [item("reminder"), item("interview_invite")];
    expect(kindsPresent(items)).toEqual([{ kind: "reminder", count: 1 }]);
    // It is still an inbox row, so the unfiltered view keeps it.
    expect(rowsUnder(items, null)).toHaveLength(2);
  });

  it("shows every row under no filter and only that kind's rows under one", () => {
    const items = [item("reminder", "a"), item("reply", "b"), item("reply", "c")];
    const all = rowsUnder(items, null);
    expect(all.map((row) => row.key)).toEqual(["a", "b", "c"]);
    // The list is a copy, so a caller sorting it cannot reorder the inbox's own array.
    expect(all).not.toBe(items);
    expect(rowsUnder(items, "reply").map((row) => row.key)).toEqual(["b", "c"]);
    expect(rowsUnder(items, "stale")).toEqual([]);
  });
});
