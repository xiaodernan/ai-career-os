import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import {
  APPLICATION_STAGES,
  isTerminal,
  pickerStages,
  STAGE_ORDER,
  stageBlurb,
  stageLabel,
  stageMeta,
  stageShort,
} from "./pipeline";
import { translations } from "./i18n/translations";

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

/**
 * The pipeline's seven names are the product's central vocabulary -- they
 * appear on the board, in the drawer, on the dashboard and in every status
 * picker. They are translated once, in one table, and read back through the
 * locale; these hold that there is one table, that it has both languages, and
 * that a stage the table has never heard of still keeps its own name.
 */
describe("the stage names are read through the locale", () => {
  /** The same lookup the locale provider does: the key back when it misses. */
  const reader = (locale: "en" | "zh") => (key: string): string => {
    let value: unknown = translations[locale];
    for (const part of key.split(".")) {
      if (value == null || typeof value !== "object") return key;
      value = (value as Record<string, unknown>)[part];
    }
    return typeof value === "string" ? value : key;
  };

  it("has a label, a short name and a blurb for every stage, in both languages", () => {
    for (const locale of ["en", "zh"] as const) {
      for (const stage of APPLICATION_STAGES) {
        const t = reader(locale);
        for (const part of ["label", "short", "blurb"] as const) {
          const value = t(`stages.${stage.value}.${part}`);
          expect(value, `${locale}.${stage.value}.${part} is missing`).not.toBe(
            `stages.${stage.value}.${part}`
          );
          expect(value.length).toBeGreaterThan(0);
        }
      }
    }
  });

  it("says something different in each language", () => {
    // A stage whose two names are the same string is a stage nobody translated.
    const same = APPLICATION_STAGES.filter(
      (stage) => reader("en")(`stages.${stage.value}.label`) === reader("zh")(`stages.${stage.value}.label`)
    );
    expect(same.map((s) => s.value)).toEqual([]);
  });

  it("reads the stage's name in the reader's language", () => {
    expect(stageLabel(reader("en"), "offer")).toBe("Offer");
    expect(stageLabel(reader("zh"), "offer")).toBe("录用");
    expect(stageLabel(reader("zh"), "final_round")).toBe("终面");
  });

  it("keeps a stage the table has never heard of under its own name", () => {
    // `stageMeta` labels a stranger instead of hiding it, and the locale
    // reader must not swallow it: a stage the backend added before this
    // ladder was updated should still say what it is.
    expect(stageLabel(reader("zh"), "screening")).toBe("screening");
    expect(stageShort(reader("zh"), "screening")).toBe("screening");
  });

  it("falls back to the English name when the table has no translation", () => {
    // A reader that misses returns the key it was asked for -- which is what
    // the real one does, and what the fallback is written against.
    const empty = (key: string) => key;
    expect(stageLabel(empty, "offer")).toBe("Offer");
    expect(stageShort(empty, "offer")).toBe("Offer");
    expect(stageBlurb(empty, "offer")).toBe("Offer extended — decide or negotiate.");
  });

  it("offers the picker's ladder in the reader's language", () => {
    const options = pickerStages("oa", reader("zh"));
    expect(options.map((o) => o.value)).toEqual([...STAGE_ORDER]);
    expect(options.find((o) => o.value === "oa")!.label).toBe("在线测评");
    // And a stage the ladder does not know keeps its own name at the front.
    const stranger = pickerStages("screening", reader("zh"));
    expect(stranger[0]).toEqual({ value: "screening", label: "screening" });
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
    // The handle's label reads from the locale table now, so the gate asserts
    // the key rather than the English copy.
    expect(kanbanSource).toContain('t("applications.dragToReorder")');
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
