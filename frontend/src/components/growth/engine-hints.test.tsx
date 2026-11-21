import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

vi.mock("@/lib/hooks/growth", () => {
  const idle = () => ({
    data: undefined,
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: undefined,
  });
  return {
    useGapAnalysis: () => idle(),
    useGapNote: () => idle(),
    useInterviewPrep: () => idle(),
    useLearningPlan: () => idle(),
    useLearningPriority: () => idle(),
    useProgression: () => idle(),
    useRoleSuggestions: () => idle(),
    useSkillDemand: () => idle(),
    useSkillProgress: () => idle(),
    useStoryBank: () => idle(),
  };
});

vi.mock("@/lib/hooks/actions", () => ({
  useCreateInterviewSession: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { GrowthEnginesPanel } from "./growth-engines-panel";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * 359: every engine button says what it is for, in the reader's language.
 *
 * Nine engines on one panel are nine questions, and their labels are one word
 * each -- a reader who has not read the manual cannot tell a snapshot from a
 * trend. The hint is the sentence the engine answers plus what it needs typed
 * in, and the run button's own hint swaps to the "type the role first" sentence
 * while the field is still too short, which is exactly when the reader is
 * wondering why the button will not answer.
 *
 * Radix mounts a tooltip's content only while it is open, so the sentence
 * itself is not in the static markup -- what IS in the markup is the trigger
 * the tooltip is attached to. So this file pins the two halves separately: the
 * rendered markup proves every control is a tooltip trigger (nothing was left
 * bare), and the source walk proves every engine has a sentence and that the
 * sentence is a translation key rather than prose in a component.
 */

const HINT_KEYS = [
  "hintGap", "hintDemand", "hintPriority", "hintPlan", "hintPrep",
  "hintProgression", "hintStories", "hintRoles", "hintProgress",
];

const PANEL = readFileSync(
  fileURLToPath(new URL("./growth-engines-panel.tsx", import.meta.url)),
  "utf8",
);

function render(locale: "en" | "zh"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <GrowthEnginesPanel />
      </LocaleProvider>,
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

describe("every control on the panel carries a hint", () => {
  it("puts all nine engine buttons behind a tooltip trigger", () => {
    // A bare button is a reader guessing. Nine engines, nine triggers.
    const en = render("en");
    const triggers = en.match(/data-slot="tooltip-trigger"/g) ?? [];
    expect(triggers.length).toBeGreaterThanOrEqual(10);
  });

  it("puts the run button behind a tooltip trigger too", () => {
    // The run button is the one that costs a click, so it is the one that most
    // needs to say what it is about to ask for.
    const en = render("en");
    const run = en.slice(Math.max(0, en.indexOf("Run Gap analysis") - 900));
    expect(run).toContain('data-slot="tooltip-trigger"');
  });

  it("keeps the panel bilingual -- the markup does not change with the language", () => {
    // The hint is a translation key resolved at render, so both languages draw
    // the same controls; what differs is the string inside the tooltip.
    const en = render("en");
    const zh = render("zh");
    expect(en).toContain("Gap analysis");
    expect(zh).toContain("差距分析");
    expect((zh.match(/data-slot="tooltip-trigger"/g) ?? []).length).toBe(
      (en.match(/data-slot="tooltip-trigger"/g) ?? []).length,
    );
  });
});

describe("the sentences themselves", () => {
  it("gives every engine a hint key, with none left over", () => {
    for (const key of HINT_KEYS) {
      expect(PANEL, key).toContain(key);
    }
    // The table is the whole vocabulary: a key added to the copy and never wired
    // here would be a sentence no reader ever sees.
    const wired = PANEL.match(/growthEngines\.hint(\w+)/g) ?? [];
    expect(new Set(wired).size).toBe(HINT_KEYS.length + 1); // + hintNeedsRole
  });

  it("swaps the run button's hint while the role is too short to run", () => {
    expect(PANEL).toContain("NEEDS_ROLE[engine] && !roleOk");
    expect(PANEL).toContain('t("growthEngines.hintNeedsRole")');
  });

  it("resolves the sentence through the locale, never as prose in the component", () => {
    // Prose in a component is copy the census cannot see and a translator
    // cannot reach; every sentence goes through t() with a key.
    expect(PANEL).toContain("t(ENGINE_HINT[e.key])");
    expect(PANEL).not.toMatch(/label="[A-Z][a-z]+ [a-z]/);
  });

  it("declares which engines need no role, so the reader is not sent to type one", () => {
    expect(PANEL).toContain("stories: false");
    expect(PANEL).toContain("roles: false");
  });
});

describe("the copy is in both tables", () => {
  it("carries all ten sentences in English and in Chinese", () => {
    const en = readFileSync(
      fileURLToPath(new URL("../../lib/i18n/en.ts", import.meta.url)),
      "utf8",
    );
    const zh = readFileSync(
      fileURLToPath(new URL("../../lib/i18n/zh.ts", import.meta.url)),
      "utf8",
    );
    for (const key of [...HINT_KEYS, "hintNeedsRole"]) {
      expect(en, key).toContain(key + ":");
      expect(zh, key).toContain(key + ":");
    }
  });
});
