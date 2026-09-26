import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { APPLICATION_STAGES, isTerminal, pickerStages, STAGE_ORDER, stageMeta } from "./pipeline";

describe("stageMeta", () => {
  it("returns known stage metadata", () => {
    const offer = stageMeta("offer");
    expect(offer.label).toBe("Offer");
    expect(offer.badgeVariant).toBe("success");
  });
  it("falls back gracefully for unknown status", () => {
    const unknown = stageMeta("ghost");
    expect(unknown.badgeVariant).toBe("outline");
    expect(unknown.label).toBe("ghost");
    expect(stageMeta("").label).toBe("Unknown");
  });
});

describe("STAGE_ORDER", () => {
  it("mirrors the declared board order", () => {
    expect(STAGE_ORDER).toEqual(APPLICATION_STAGES.map((s) => s.value));
    expect(STAGE_ORDER[0]).toBe("saved");
    expect(STAGE_ORDER[STAGE_ORDER.length - 1]).toBe("rejected");
  });
});

describe("isTerminal", () => {
  it("treats only offer and rejected as terminal", () => {
    expect(isTerminal("offer")).toBe(true);
    expect(isTerminal("rejected")).toBe(true);
    expect(isTerminal("interview")).toBe(false);
  });
});

describe("pickerStages", () => {
  it("offers the whole ladder in board order for a known stage", () => {
    const opts = pickerStages("oa");
    expect(opts.map((o) => o.value)).toEqual([...STAGE_ORDER]);
    expect(opts.find((o) => o.value === "oa")?.label).toBe("Online assessment");
  });

  it("includes the stage the row already sits in", () => {
    // A control that cannot show its own value has nothing to select back to.
    expect(pickerStages("interview").map((o) => o.value)).toContain("interview");
  });

  it("keeps a status outside the ladder selectable instead of rendering blank", () => {
    // A <select> draws an empty box when its value matches no option, so a stage
    // the backend adds first would erase the one fact the row exists to show.
    const opts = pickerStages("screening");
    expect(opts[0]).toEqual({ value: "screening", label: "screening" });
    expect(opts).toHaveLength(STAGE_ORDER.length + 1);
  });

  it("never offers an option with a blank label", () => {
    for (const status of [...STAGE_ORDER, "screening", ""]) {
      for (const opt of pickerStages(status)) expect(opt.label.trim()).not.toBe("");
    }
  });
});

/**
 * The row is JSX in a node-environment suite, so nothing here can render it. What
 * this can pin is that the page drives the mutation the backend has always had,
 * and that it stopped promising a board it does not ship.
 */
describe("the applications page", () => {
  const source = readFileSync(
    new URL("../app/(app)/applications/page.tsx", import.meta.url),
    "utf8"
  );
  const kanbanSource = readFileSync(
    new URL("../components/common/kanban.tsx", import.meta.url),
    "utf8"
  );

  it("sends a status patch through the shared reorder mutation", () => {
    expect(source).toContain("useReorderApplication");
    expect(source).toMatch(/reorderApp\.mutate\(\{ id, status, order \}\)/);
  });

  it("labels the drag handle for the row it belongs to", () => {
    expect(kanbanSource).toContain("aria-label=\"Drag to reorder\"");
  });

  it("takes its colours from pipeline metadata instead of a local map", () => {
    expect(kanbanSource).toContain("stageMeta(app.status)");
    expect(kanbanSource).toContain("meta.badgeVariant");
    expect(kanbanSource).not.toMatch(/const STAGE_VARIANT/);
  });

  it("renders the Kanban board with drag-and-drop reorder", () => {
    expect(source).toContain("KanbanBoard");
    expect(source).toContain("useReorderApplication");
  });
});

/**
 * The board's stages and the statuses the backend accepts are the same seven words, written
 * twice in two languages with nothing comparing them. Both directions fail quietly: a stage the
 * backend rejects is a control that breaks the moment it is used, and a stage it accepts but the
 * ladder does not know lands outside every column -- `pickerStages` even papers over that by
 * prepending the unknown value as its own stage.
 */
describe("the stage ladder is the set of statuses the backend accepts", () => {
  const service = readFileSync(
    new URL(
      "../../../backend/src/main/java/com/careeros/application/service/ApplicationService.java",
      import.meta.url
    ),
    "utf8"
  );
  const block = service.match(/Set\.of\(([^)]*"saved"[^)]*)\)/);
  const accepted = [...(block?.[1].matchAll(/"([a-z_]+)"/g) ?? [])].map((m) => m[1]);

  it("reads a real list from the backend, not an empty one", () => {
    expect(accepted.length).toBeGreaterThanOrEqual(7);
    expect(accepted).toContain("final_round");
    expect(new Set(accepted).size).toBe(accepted.length);
  });

  it("offers exactly those stages, and no others", () => {
    expect([...APPLICATION_STAGES.map((s) => s.value)].sort()).toEqual([...accepted].sort());
  });

  it("calls only accepted stages terminal", () => {
    const terminal = APPLICATION_STAGES.map((s) => s.value).filter(isTerminal);
    expect(terminal).toEqual(["offer", "rejected"]);
    expect(terminal.every((stage) => accepted.includes(stage))).toBe(true);
  });
});
