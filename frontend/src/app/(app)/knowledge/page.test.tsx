import * as React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";

const state = vi.hoisted(() => ({
  url: { src: undefined as string | undefined, page: 0 },
  params: undefined as Record<string, unknown> | undefined,
  sources: {
    data: undefined as
      | { items: { id: string; title: string; kind: string; status: string }[]; total: number; page: number; size: number }
      | undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null as unknown,
    refetch: () => undefined,
  },
}));

vi.mock("@/lib/hooks/resources", () => ({
  useKnowledgeSources: (live: boolean, src?: string, params?: Record<string, unknown>) => {
    state.params = { live, src, ...params };
    return state.sources;
  },
}));

vi.mock("@/lib/hooks/use-url-state", () => ({
  useUrlState: () => [state.url, () => undefined],
}));

vi.mock("@/components/knowledge/source-actions", () => ({
  SourceUploadCard: () => <div data-testid="source-upload" />,
  SourceDeleteButton: () => <button type="button">Delete source</button>,
}));

vi.mock("@/components/knowledge/notes-panel", () => ({
  NotesPanel: () => <div data-testid="notes-panel" />,
}));

vi.mock("@/components/knowledge/ask-knowledge-card", () => ({
  AskKnowledgeCard: () => <div data-testid="ask-knowledge" />,
}));

import KnowledgePage from "./page";
import { LocaleProvider, lookup } from "@/lib/i18n/locale-context";
import { translations, type Locale } from "@/lib/i18n/translations";

const HINT_KEYS = [
  "knowledge.hintShowAllSources",
  "knowledge.hintAskCopilotToIngest",
];

function render(locale: Locale = "en"): string {
  return renderToStaticMarkup(
    <LocaleProvider initialLocale={locale} table={translations[locale]}>
      <KnowledgePage />
    </LocaleProvider>
  );
}

beforeEach(() => {
  state.url = { src: undefined, page: 0 };
  state.params = undefined;
  state.sources = {
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => undefined,
  };
});

describe("the knowledge page teaching hints", () => {
  it("explains the empty-board Copilot route without replacing its destination", () => {
    state.sources.data = { items: [], total: 0, page: 0, size: 20 };
    const html = render();
    expect(state.params).toEqual({ live: true, src: undefined, page: 0, size: 20 });
    expect(html).toContain('href="/copilot"');
    expect(html).toContain("Ask Copilot to ingest");
    expect(html).toContain('data-slot="tooltip-trigger"');
    expect(html).toContain('data-testid="source-upload"');
    expect(html).toContain('data-testid="ask-knowledge"');
    expect(html).toContain('data-testid="notes-panel"');
  });

  it("uses the same show-all teaching action in a focused populated list", () => {
    state.url = { src: "doc-1", page: 2 };
    state.sources.data = {
      items: [{ id: "source-1", title: "Resume", kind: "resume", status: "ready" }],
      total: 41,
      page: 2,
      size: 20,
    };
    const html = render();
    expect(state.params).toEqual({ live: true, src: "doc-1", page: 2, size: 20 });
    expect(html).toContain("Show all sources");
    expect(html).toContain('data-slot="tooltip-trigger"');
    expect(html).not.toContain('data-testid="source-upload"');
    expect(html).not.toContain('data-testid="ask-knowledge"');
    expect(html).not.toContain('data-testid="notes-panel"');
  });

  it("keeps the way back when a cited document no longer matches", () => {
    state.url = { src: "gone-document", page: 0 };
    state.sources.data = { items: [], total: 0, page: 0, size: 20 };
    const html = render("zh");
    expect(html).toContain("没有来源匹配这条引用");
    expect(html).toContain("显示全部来源");
    expect(html).not.toContain("让副驾驶摄取");
  });

  it("wires both page-level hints to complete bilingual copy", () => {
    const source = readFileSync(new URL("./page.tsx", import.meta.url), "utf8");
    for (const locale of ["en", "zh"] as const) {
      for (const key of HINT_KEYS) {
        expect(lookup(translations[locale], key), `${key} missing from ${locale}`).toBeTruthy();
        expect(source).toContain(`t("${key}")`);
      }
    }
    expect(source.match(/t\("knowledge\.hintShowAllSources"\)/g)).toHaveLength(1);
  });
});
