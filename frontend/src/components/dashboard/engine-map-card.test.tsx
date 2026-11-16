import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `{${key}|${Object.entries(vars).map(([k, v]) => `${k}=${v}`).join(",")}}` : `{${key}}`,
    setLocale: () => undefined,
  }),
}));

import { EngineMapCard } from "./engine-map-card";

describe("EngineMapCard", () => {
  const html = renderToStaticMarkup(<EngineMapCard />);

  it("renders the four literal node names, in order", () => {
    const retrieve = html.indexOf("retrieve");
    const draft = html.indexOf("draft");
    const verify = html.indexOf("verify");
    const render = html.indexOf("render");
    expect(retrieve).toBeGreaterThanOrEqual(0);
    expect(draft).toBeGreaterThan(retrieve);
    expect(verify).toBeGreaterThan(draft);
    expect(render).toBeGreaterThan(verify);
  });

  it("keeps the node names as the literals in the source, never translated", () => {
    // The engine's own names — an English table and a Chinese table both carry them verbatim.
    for (const name of ["retrieve", "draft", "verify", "render"]) {
      expect(html).toContain(name);
    }
    expect(html).not.toContain("{dashboard.engineRetrieve}");
  });

  it("draws the loop's veto path and the hard bound", () => {
    expect(html).toContain("{dashboard.engineRetryLabel}");
    expect(html).toContain("{dashboard.engineBoundValue}");
    expect(html).toContain("{dashboard.engineBound}");
    expect(html).toContain("{dashboard.engineLedgerValue}");
    expect(html).toContain("{dashboard.engineLedger}");
  });

  it("links to the book's chapter and the activity ledger", () => {
    expect(html).toContain('href="/playbook#stategraph"');
    expect(html).toContain('href="/activity"');
    expect(html).toContain("{dashboard.engineBookLink}");
    expect(html).toContain("{dashboard.engineActivityLink}");
  });

  it("renders the eyebrow, the headline and the intro in the reader's language", () => {
    expect(html).toContain("{dashboard.engineEyebrow}");
    expect(html).toContain("{dashboard.engineTitle}");
    expect(html).toContain("{dashboard.engineIntro}");
  });
});
