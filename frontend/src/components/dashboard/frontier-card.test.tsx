import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

const applications = vi.hoisted(() => ({ items: [] as unknown[] }));
const sessions = vi.hoisted(() => ({ items: [] as unknown[] }));

vi.mock("@/lib/hooks/resources", () => ({
  useApplications: () => ({ data: applications, isPending: false }),
  useInterviewSessions: () => ({ data: sessions, isPending: false }),
}));

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: "en", t: (key: string, vars?: Record<string, unknown>) =>
    key + (vars ? ":" + JSON.stringify(vars) : "") }),
}));

import { FrontierCard } from "./frontier-card";

/**
 * 369: the card reads the ledgers it says it reads.
 *
 * The first browser probe of this card found a rule written against a vocabulary the
 * backend does not speak (`started` / `in_progress`), so it never fired: the card stayed
 * silent forever while looking correct. The backend spells "still open" as `active` and
 * `paused`, and these tests pin that mapping so the mistake cannot come back.
 */

describe("FrontierCard", () => {
  it("names an open rehearsal — the backend spells it `active`", () => {
    applications.items = [];
    sessions.items = [{ id: "s-1", status: "active" }];
    const html = renderToStaticMarkup(<FrontierCard />);
    expect(html).toContain("frontier.finishRehearsalTitle");
    expect(html).toContain('href="/interviews"');
  });

  it("counts a paused rehearsal as open too", () => {
    applications.items = [];
    sessions.items = [{ id: "s-1", status: "paused" }];
    const html = renderToStaticMarkup(<FrontierCard />);
    expect(html).toContain("frontier.finishRehearsalTitle");
  });

  it("stays silent for a finished or abandoned rehearsal", () => {
    // A completed rehearsal has its report; an abandoned one chose to end. Neither is
    // something the world should point at.
    for (const status of ["completed", "abandoned"]) {
      applications.items = [];
      sessions.items = [{ id: "s-1", status }];
      expect(renderToStaticMarkup(<FrontierCard />)).toBe("");
    }
  });

  it("falls to the board when only applications are waiting on the reader", () => {
    sessions.items = [];
    applications.items = [{ id: "a-1", status: "applied" }, { id: "a-2", status: "offer" }];
    const html = renderToStaticMarkup(<FrontierCard />);
    expect(html).toContain("frontier.moveApplicationTitle");
    expect(html).toContain('href="/applications"');
  });

  it("draws nothing at all when nothing is waiting", () => {
    applications.items = [{ id: "a-1", status: "rejected" }];
    sessions.items = [{ id: "s-1", status: "completed" }];
    expect(renderToStaticMarkup(<FrontierCard />)).toBe("");
  });
});
