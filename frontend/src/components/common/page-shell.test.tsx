"use client";

import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { GridSpan, PageGrid, PAGE_WIDTHS } from "@/components/layout/page-grid";
import { PageShell } from "@/components/common/page-shell";
import { PageSection } from "@/components/common/page-section";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: "en", t: (k: string) => k, setLocale: () => undefined }),
}));

describe("PageGrid", () => {
  it("lays out twelve columns and spans bare children across all of them", () => {
    const markup = renderToStaticMarkup(
      <PageGrid>
        <div>one</div>
      </PageGrid>,
    );
    expect(markup).toContain("grid");
    expect(markup).toContain("grid-cols-12");
    // Bare children span all twelve columns via the arbitrary variant — the escape
    // form is React's business, so assert the property, not the spelling.
    expect(/col-span-12/.test(markup)).toBe(true);
  });

  it("exports the width scale the whole app shares", () => {
    expect(PAGE_WIDTHS.form).toBe("max-w-3xl");
    expect(PAGE_WIDTHS.content).toBe("max-w-6xl");
    expect(PAGE_WIDTHS.board).toBe("max-w-[88rem]");
  });
});

describe("GridSpan", () => {
  it("full width on mobile; the asked span at md; clamps out-of-range spans", () => {
    const seven = renderToStaticMarkup(<GridSpan span={7}>x</GridSpan>);
    expect(seven).toContain("col-span-12");
    expect(seven).toContain("md:col-span-7");
    expect(renderToStaticMarkup(<GridSpan span={99}>x</GridSpan>)).toContain("md:col-span-12");
    expect(renderToStaticMarkup(<GridSpan span={0}>x</GridSpan>)).toContain("md:col-span-1");
  });
});

describe("PageShell", () => {
  it("renders the shared heading block and the content width by default", () => {
    const markup = renderToStaticMarkup(
      <PageShell title="Activity" description="Every agent run." actions={<button>Rerun</button>}>
        <div>rows</div>
      </PageShell>,
    );
    expect(markup).toContain("<h1");
    expect(markup).toContain("Activity");
    expect(markup).toContain("Every agent run.");
    expect(markup).toContain("max-w-6xl");
    expect(markup).toContain("Rerun");
  });

  it("honors the form and board widths", () => {
    expect(renderToStaticMarkup(<PageShell width="form" title="x"><div /></PageShell>)).toContain("max-w-3xl");
    expect(renderToStaticMarkup(<PageShell width="board" title="x"><div /></PageShell>)).toContain("max-w-[88rem]");
  });
});

describe("PageSection", () => {
  it("renders a named band with an aria-label from the title", () => {
    const markup = renderToStaticMarkup(
      <PageSection title="Agenda" description="What the week asks for">
        <ul />
      </PageSection>,
    );
    expect(markup).toContain('aria-label="Agenda"');
    expect(markup).toContain("What the week asks for");
    expect(markup).toContain("<section");
  });

  it("renders bare children without heading when no title is given", () => {
    const markup = renderToStaticMarkup(<PageSection><div>plain</div></PageSection>);
    expect(markup).not.toContain("<h2");
    expect(markup).toContain("plain");
  });
});
