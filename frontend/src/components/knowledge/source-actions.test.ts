import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

import {
  ACCEPTED_EXTENSIONS,
  MAX_DOCUMENT_BYTES,
  SOURCE_KINDS,
  batchProgress,
  batchRunning,
  buildDocumentForm,
  planBatch,
  validateDocumentFile,
} from "@/components/knowledge/source-actions";
import type { UploadRow } from "@/components/knowledge/source-actions";

/**
 * Knowledge upload gates. The kind list is a cross-language contract: the backend
 * `validateKind` throws VALIDATION_FAILED on anything outside `KINDS`, so a value the
 * selector can send but the service doesn't name is a 400 the moment it's picked.
 */

const kindsFromJava = () => {
  const java = readFileSync(
    new URL(
      "../../../../backend/src/main/java/com/careeros/knowledge/service/KnowledgeService.java",
      import.meta.url
    ),
    "utf8"
  );
  const declared = java.slice(java.indexOf("KINDS ="), java.indexOf("STATUS_RETIRED"));
  const found = [...declared.matchAll(/"([a-z_]+)"/g)].map((m) => m[1]);
  expect(found.length).toBeGreaterThan(0);
  return found;
};

describe("SOURCE_KINDS", () => {
  it("offers exactly the kinds KnowledgeService.KINDS binds, defaulting to its blank fallback", () => {
    // Same set, no `document` (never in KINDS) and no drift a new value would miss.
    expect([...SOURCE_KINDS].map((k) => k.value).sort()).toEqual([...kindsFromJava()].sort());
    // `uploadDocument` falls back to "note" for a blank kind — the selector's own default.
    expect(SOURCE_KINDS[0].value).toBe("note");
    // Labels stay human-readable next to the snake_case wire values.
    for (const k of SOURCE_KINDS) expect(k.label).toBeTruthy();
  });
});

describe("validateDocumentFile", () => {
  it("accepts an in-cap PDF and rejects the three cases the server would 400", () => {
    expect(validateDocumentFile({ name: "resume.pdf", size: 1024 })).toBeNull();
    expect(validateDocumentFile({ name: "notes.docx", size: 1024 })).toBeNull();
    expect(validateDocumentFile({ name: "notes.txt", size: 1024 })).toBeNull();
    expect(validateDocumentFile({ name: "resume.PDF", size: 1024 })).toBeNull();

    const wrongExt = validateDocumentFile({ name: "resume.exe", size: 1024 });
    expect(wrongExt).toContain(ACCEPTED_EXTENSIONS.join(", "));
    expect(validateDocumentFile({ name: "big.pdf", size: MAX_DOCUMENT_BYTES + 1 })).toMatch(
      /20 MB/
    );
    expect(validateDocumentFile({ name: "empty.txt", size: 0 })).toMatch(/empty/);
  });
});

describe("buildDocumentForm", () => {
  it("sends file + kind as parts and only sends a title the user typed", () => {
    const file = new File(["hi"], "cv.pdf", { type: "application/pdf" });
    const withTitle = buildDocumentForm(file, "  My CV  ", "resume");
    expect(withTitle.get("file")).toBe(file);
    expect(withTitle.get("kind")).toBe("resume");
    expect(withTitle.get("title")).toBe("My CV");

    const blank = buildDocumentForm(file, "   ", "note");
    expect(blank.get("title")).toBeNull();
    expect(blank.get("kind")).toBe("note");
  });
});

/**
 * The batch planner. Its one job is to decide, before anything is sent, which of the
 * picked files the server would refuse — so a seven-file selection with three .zips reads
 * as four queued and three rejected with a reason, not as a silent four.
 */

/**
 * A File whose reported size is the one asked for. `new File([content])` sizes itself from
 * the content, so the bytes are written out rather than passed as an argument the
 * constructor does not take — a size over the cap has to be *real* for the validator to
 * see it.
 */
const file = (name: string, size = 1024) => {
  const blob = new Blob([new Uint8Array(size)]);
  return new File([blob], name, { type: "text/plain" });
};

describe("planBatch", () => {
  it("accepts valid files and rejects the ones the server would 400, naming each", () => {
    const plan = planBatch([file("a.pdf"), file("b.zip"), file("c.txt"), file("d.pdf", 21 * 1024 * 1024)]);
    expect(plan.accepted.map((p) => p.row.name).sort()).toEqual(["a.pdf", "c.txt"]);
    expect(plan.rejected.map((r) => r.name).sort()).toEqual(["b.zip", "d.pdf"]);
    // The pairs are the planner's own: a row is matched to its File at planning time, so
    // an upload can never be attributed to the wrong entry.
    expect(plan.accepted.map((p) => p.file.name).sort()).toEqual(["a.pdf", "c.txt"]);
  });

  it("gives two same-named files distinct keys, because the row is what React tracks", () => {
    const plan = planBatch([file("dup.pdf"), file("dup.pdf")]);
    expect(plan.accepted.map((p) => p.row.key)).toEqual(["dup.pdf", "dup.pdf (2)"]);
    expect(new Set(plan.accepted.map((p) => p.row.key)).size).toBe(2);
  });

  it("does not collide with keys a previous batch already used", () => {
    const plan = planBatch([file("dup.pdf")], ["dup.pdf", "dup.pdf (2)"]);
    expect(plan.accepted[0].row.key).toBe("dup.pdf (3)");
  });

  it("returns empty accepted for a selection the server would refuse entirely", () => {
    const plan = planBatch([file("a.zip"), file("b.zip")]);
    expect(plan.accepted).toEqual([]);
    expect(plan.rejected).toHaveLength(2);
  });
});

/**
 * The counter's rule, which is the whole point of it: the upload returning is not the
 * document being usable. A row still ingesting counts as *not* done, so "3 of 5" keeps
 * moving after the last request has already returned.
 */
describe("batchProgress", () => {
  const row = (name: string, stage: Parameters<typeof batchProgress>[0][number]["stage"]) => ({
    key: name, name, size: 1, stage,
  });

  it("counts only ready and failed, never the rows still ingesting", () => {
    const rows = [row("a", "ready"), row("b", "failed"), row("c", "ingesting"), row("d", "queued")];
    expect(batchProgress(rows)).toEqual({ done: 2, total: 4 });
  });

  it("does not report a batch as done while its last rows are still being chunked", () => {
    // The shape this whole rule is for: every request has returned, nothing is ready.
    const rows = [row("a", "ingesting"), row("b", "ingesting")];
    expect(batchProgress(rows)).toEqual({ done: 0, total: 2 });
  });

  it("reports 0 of 0 for an empty batch rather than dividing by anything", () => {
    expect(batchProgress([])).toEqual({ done: 0, total: 0 });
  });
});

describe("batchRunning", () => {
  const row = (name: string, stage: Parameters<typeof batchProgress>[0][number]["stage"]) => ({
    key: name, name, size: 1, stage,
  });

  it("is true while a file is either uploading or ingesting", () => {
    expect(batchRunning([row("a", "uploading"), row("b", "queued")])).toBe(true);
    expect(batchRunning([row("a", "ingesting"), row("b", "ready")])).toBe(true);
  });

  it("is false once every row has settled, so a finished batch can be cleared", () => {
    expect(batchRunning([row("a", "ready"), row("b", "failed"), row("c", "rejected")])).toBe(false);
    expect(batchRunning([])).toBe(false);
  });
});

describe("the settle lifecycle", () => {
  const ingesting: UploadRow[] = [
    { key: "a", name: "a.pdf", size: 1, stage: "ready" },
    { key: "b", name: "b.pdf", size: 1, stage: "ingesting", sourceId: "s1" },
  ];

  it("an ingesting row holds the spinner until the poll settles it, and releases it after", () => {
    // Before the poll answers: one of two done, panel still running.
    expect(batchProgress(ingesting)).toEqual({ done: 1, total: 2 });
    expect(batchRunning(ingesting)).toBe(true);
    // The settle is the patch `onRowSettled` applies, addressed by the row's key.
    const settled: UploadRow[] = ingesting.map((r) =>
      r.key === "b" ? { ...r, stage: "ready" } : r
    );
    expect(batchProgress(settled)).toEqual({ done: 2, total: 2 });
    expect(batchRunning(settled)).toBe(false);
  });
});

/**
 * The ingestion progress stream is wired to the row list. `IngestStageText` was once
 * declared and never rendered — the progress display existed as dead code while the
 * panel spun forever after an upload — so the mount itself is asserted, not just the
 * component's internals.
 */
describe("the ingestion settle wiring", () => {
  const source = () =>
    readFileSync(
      new URL("./source-actions.tsx", import.meta.url),
      "utf8"
    );

  it("renders IngestStageText per row, handing it the batch's key-addressed settle", () => {
    const text = source();
    expect(text).toContain("<IngestStageText row={r} onSettled={batch.onRowSettled} />");
    // `onRowSettled` settles by key, never by index: a file renamed mid-run cannot
    // make one update land on the wrong entry.
    expect(text).toMatch(/const onRowSettled = React\.useCallback\(\s*\(key: string,/);
    expect(text).toMatch(/patch\(key, outcome\)/);
  });

  it("arms the poll only for an ingesting row that has an id to ask about", () => {
    expect(source()).toContain(
      'useSourceStatus(row.stage === "ingesting" ? (row.sourceId ?? null) : null)'
    );
  });

  it("reports the terminal answer once, guarded, and never on an intermediate tick", () => {
    const text = source();
    // The once-only guard, before either terminal branch.
    expect(text).toContain("if (settled.current) return;");
    // Both terminal branches flip the guard before calling out.
    expect(text).toMatch(/settled\.current = true;\s*onSettled\(row\.key, \{ stage: "ready" \}\)/);
    expect(text).toMatch(
      /settled\.current = true;\s*onSettled\(row\.key, \{ stage: "failed", message: failure \?\? t\("knowledge\.sources\.ingestionFailed"\) \}\)/
    );
    // No other call site: a second `onSettled(` outside these two would be a path that
    // settles without flipping the guard.
    expect(text.match(/onSettled\(row\.key,/g)).toHaveLength(2);
  });
});
