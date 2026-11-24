import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, string | number>) =>
      vars?.count !== undefined ? `${key}=${vars.count}` : key,
  }),
}));

import { KanbanBoard } from "./kanban";
import type { Application } from "@/lib/api/types";

const app = (extra: Partial<Application>): Application => ({
  id: "app-1",
  title: "Staff Backend Engineer",
  status: "applied",
  companyName: "Northwind",
  ...extra,
});

const render = (application: Application) =>
  renderToStaticMarkup(
    <KanbanBoard
      applications={[application]}
      onReorder={() => {}}
      onOpen={() => {}}
      isPending={false}
    />
  );

const BOARD = readFileSync(fileURLToPath(new URL("./kanban.tsx", import.meta.url)), "utf8");

function buttonMarkup(html: string, marker: string): string {
  const start = html.lastIndexOf("<button", html.indexOf(marker));
  return html.slice(start, html.indexOf("</button>", start));
}

describe("KanbanBoard teaching hints", () => {
  it("teaches both ways to act on a card without changing either control", () => {
    const html = render(app({}));
    const title = buttonMarkup(html, ">Staff Backend Engineer</button>");
    const stage = buttonMarkup(html, 'data-slot="select-trigger"');

    expect(title).toContain('data-slot="tooltip-trigger"');
    expect(stage).toContain('data-slot="select-trigger"');
    expect(stage).not.toContain('data-slot="tooltip-trigger"');
    expect(stage).toContain('data-state="closed"');
    const wrapper = html.slice(
      html.lastIndexOf('<span class="contents"', html.indexOf('data-slot="select-trigger"')),
      html.indexOf('data-slot="select-trigger"'),
    );
    expect(wrapper).toContain('data-slot="tooltip-trigger"');
  });

  it("keeps every board sentence in both locale tables", () => {
    const en = readFileSync(
      fileURLToPath(new URL("../../lib/i18n/en.ts", import.meta.url)),
      "utf8",
    );
    const zh = readFileSync(
      fileURLToPath(new URL("../../lib/i18n/zh.ts", import.meta.url)),
      "utf8",
    );
    for (const key of ["dragHint", "hintOpenCard", "hintChangeStage"]) {
      expect(BOARD).toContain(`t("applications.${key}")`);
      expect(en).toContain(`${key}:`);
      expect(zh).toContain(`${key}:`);
    }
    expect(BOARD).toContain('anchor="span" label={t("applications.hintChangeStage")}');
    expect(BOARD).not.toMatch(/label="[A-Z][a-z]+ [a-z]/);
  });
});

describe("KanbanBoard letter badge", () => {
  it("says how many letters a card holds", () => {
    const html = render(app({ letters: 3 }));
    expect(html).toContain("applications.letterBadge=3");
    expect(html).toContain("applications.letterBadgeTitle=3");
  });

  it("draws no letter badge when the card holds none", () => {
    const html = render(app({ letters: 0 }));
    expect(html).not.toContain("applications.letterBadge");
  });
});