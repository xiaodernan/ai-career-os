import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

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