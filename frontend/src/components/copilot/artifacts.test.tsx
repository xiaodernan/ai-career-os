import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";

import { ArtifactCard } from "./artifacts";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * The four growth-engine artifact cards (Epics 10.x, 12.x).
 *
 * The copilot can now answer "how ready am I for this role" and "which of these
 * offers leads" — and the answer is a card, not a paragraph. A card that renders
 * nothing is the failure this holds: the orchestrator's artifact made it to the
 * browser and the browser drew an empty panel, which reads as "the agent had
 * nothing to say".
 *
 * The cards are rendered inside the real locale provider, because that is how
 * they render in the product: a card that needed a provider to draw is a card
 * that throws on the screen.
 */

function render(artifact: { type: string; data?: unknown }): string {
  return renderToStaticMarkup(
    <LocaleProvider>
      <ArtifactCard artifact={artifact} />
    </LocaleProvider>
  );
}

describe("the growth artifact cards", () => {
  it("draws the gap report with its coverage and the missing skills", () => {
    // The card is handed the engine's own answer: `normalizeArtifacts` passes the
    // orchestrator's `payload` through as `data`, and `analyze_gap` puts `gaps` at
    // the top level with `{skill, importance, category}` rows. A fixture that
    // invented its own keys would keep this suite green while the product painted
    // empty badges.
    const html = render({
      type: "gap_report",
      data: {
        targetRole: "Senior Backend Engineer (Java)",
        coverage: 0.42,
        gaps: [
          { skill: "Kubernetes", importance: "must", category: "devops" },
          { skill: "Kafka", importance: "should", category: "data" },
        ],
      },
    });
    expect(html).toContain("Gap analysis");
    expect(html).toContain("Senior Backend Engineer (Java)");
    // The coverage is printed as a number, not only drawn as a bar.
    expect(html).toContain("42%");
    expect(html).toContain("Kubernetes");
    expect(html).not.toContain("[object Object]");
  });

  it("draws the market band with its percentiles", () => {
    const html = render({
      type: "salary_band",
      data: { salary: { role: "Backend Engineer", percentiles: { p25: 300000, p50: 420000, p75: 560000 } } },
    });
    expect(html).toContain("Market band");
    expect(html).toContain("p50");
  });

  it("draws the offer comparison with every offer's total compensation", () => {
    const html = render({
      type: "offer_comparison",
      data: {
        comparison: {
          rows: [
            { label: "Offer A", totalComp: 520000 },
            { label: "Offer B", totalComp: 480000 },
          ],
        },
      },
    });
    expect(html).toContain("Offer comparison");
    expect(html).toContain("Offer A");
    expect(html).toContain("Offer B");
  });

  it("draws the learning order", () => {
    // `plan_learning_priority` answers `prioritizedGaps`, not `priorities` -- the
    // card read the invented name and drew nothing at all.
    const html = render({
      type: "learning_priority",
      data: {
        targetRole: "Senior Backend Engineer (Java)",
        prioritizedGaps: [
          { skill: "Kubernetes", priority: "must", marketShare: 0.31 },
        ],
      },
    });
    expect(html).toContain("Learning priority");
    expect(html).toContain("Kubernetes");
    expect(html).toContain("must");
    expect(html).not.toContain("[object Object]");
  });

  it("draws nothing for an answer with no content in it", () => {
    // An empty payload is not a card with zeroes in it: it is an answer the
    // engine did not produce, and the reader should see nothing rather than a
    // panel of empty bars.
    expect(render({ type: "gap_report", data: {} })).toBe("");
    expect(render({ type: "salary_band", data: {} })).toBe("");
    expect(render({ type: "offer_comparison", data: {} })).toBe("");
    expect(render({ type: "learning_priority", data: {} })).toBe("");
  });
});
