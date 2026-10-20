import { describe, expect, it } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { BarChart, ShareChart } from "./bar-chart";

/**
 * The chart's contract.
 *
 * A chart is a picture of a number, and the number has to survive the drawing:
 * a bar nobody can read the value of is decoration. These tests hold three
 * things — the value is always printed, the scale is the caller's, and an empty
 * dataset says so rather than drawing an empty axis.
 */

const STAGE = { label: "Applied", value: 12 };
const OA = { label: "Offer", value: 3 };

describe("BarChart", () => {
  it("prints every value beside its bar", () => {
    const html = renderToStaticMarkup(<BarChart data={[STAGE, OA]} />);
    expect(html).toContain("12");
    expect(html).toContain("3");
    // And the bar itself carries the same fact for a screen reader.
    expect(html).toContain("Applied: 12");
  });

  it("scales the bars against the caller's maximum, not the largest row", () => {
    // With a maximum of 100, a value of 25 is a quarter of the width -- and the
    // bar of 3 is narrower still. A chart that scaled to its own largest row
    // would draw both as full width.
    const html = renderToStaticMarkup(<BarChart data={[{ label: "A", value: 25 }]} max={100} />);
    expect(html).toContain("width:25%");
  });

  it("scales against the largest value when the caller names no maximum", () => {
    const html = renderToStaticMarkup(<BarChart data={[STAGE, OA]} />);
    // The 3 is a quarter of the 12.
    expect(html).toContain("width:25%");
  });

  it("draws an empty bar for a zero value rather than a negative one", () => {
    const html = renderToStaticMarkup(<BarChart data={[{ label: "None", value: 0 }]} />);
    expect(html).not.toContain("width:-");
    expect(html).toContain("width:0%");
  });

  it("says so when there is nothing to plot", () => {
    const html = renderToStaticMarkup(<BarChart data={[]} emptyHint="No applications yet." />);
    expect(html).toContain("No applications yet.");
  });

  it("prints the value through the caller's formatter", () => {
    const html = renderToStaticMarkup(
      <BarChart data={[{ label: "Cost", value: 1234 }]} valueFormat={(v) => `$${v.toFixed(2)}`} />
    );
    expect(html).toContain("$1234.00");
  });

  it("keeps the detail line under the label", () => {
    const html = renderToStaticMarkup(
      <BarChart data={[{ label: "Applied", value: 12, detail: "3 last week" }]} />
    );
    expect(html).toContain("3 last week");
  });
});

describe("ShareChart", () => {
  it("draws one segment per row and names every share", () => {
    const html = renderToStaticMarkup(
      <ShareChart data={[{ label: "Applied", value: 3 }, { label: "Rejected", value: 1 }]} />
    );
    // Three quarters and one quarter of the whole.
    expect(html).toContain("width:75%");
    expect(html).toContain("width:25%");
    expect(html).toContain("Applied: 3, Rejected: 1");
  });

  it("skips a zero row's segment rather than drawing an empty one", () => {
    const html = renderToStaticMarkup(
      <ShareChart data={[{ label: "Applied", value: 2 }, { label: "None", value: 0 }]} />
    );
    expect(html).toContain("width:100%");
    expect(html).not.toContain("width:0%");
  });

  it("says so when there is nothing to plot", () => {
    const html = renderToStaticMarkup(<ShareChart data={[]} emptyHint="No stages yet." />);
    expect(html).toContain("No stages yet.");
  });
});
