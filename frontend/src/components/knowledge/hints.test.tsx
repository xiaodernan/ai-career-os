import * as React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { KnowledgeNote } from "@/lib/api/types";

const state = vi.hoisted(() => ({
  url: { npage: 0, ntag: undefined as string | undefined },
  notes: {
    data: undefined as
      | { items: KnowledgeNote[]; total: number; page: number; size: number }
      | undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null as unknown,
    refetch: () => undefined,
  },
  tagCounts: [] as { tag: string; count: number }[],
}));

vi.mock("@/lib/hooks/resources", () => ({
  useSourceStatus: () => ({ data: undefined }),
  useKnowledgeNotes: () => state.notes,
  useKnowledgeNoteTagCounts: () => ({ data: state.tagCounts }),
}));

vi.mock("@/lib/hooks/actions", () => ({
  useNoteMutations: () => ({
    create: { mutate: () => undefined, isPending: false },
    update: { mutate: () => undefined, isPending: false },
    remove: { mutate: () => undefined, isPending: false },
  }),
}));

vi.mock("@/lib/hooks/use-url-state", () => ({
  useUrlState: () => [state.url, () => undefined],
}));

import { NoteCreateCard, NotesPanel } from "./notes-panel";
import { SourceDeleteButton, SourceUploadCard } from "./source-actions";
import { LocaleProvider } from "@/lib/i18n/locale-context";
import { lookup } from "@/lib/i18n/locale-context";
import { translations, type Locale } from "@/lib/i18n/translations";

const SOURCE_KEYS = [
  "knowledge.sources.hintChooseFiles",
  "knowledge.sources.hintTitle",
  "knowledge.sources.hintKind",
  "knowledge.sources.hintClearBatch",
  "knowledge.sources.hintDelete",
];
const NOTE_KEYS = [
  "knowledge.notes.hintSaveNote",
  "knowledge.notes.hintAllTags",
  "knowledge.notes.hintTag",
  "knowledge.notes.hintEditNote",
  "knowledge.notes.hintDeleteNote",
  "knowledge.notes.hintCancelEdit",
  "knowledge.notes.hintSaveChanges",
];

function render(element: React.ReactNode, locale: Locale = "en"): string {
  return renderToStaticMarkup(
    <QueryClientProvider client={new QueryClient()}>
      <LocaleProvider initialLocale={locale} table={translations[locale]}>
        {element}
      </LocaleProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  state.url = { npage: 0, ntag: undefined };
  state.notes = {
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => undefined,
  };
  state.tagCounts = [];
});

describe("knowledge teaching hints", () => {
  it("names every source and note consequence in both locale tables", () => {
    for (const locale of ["en", "zh"] as const) {
      for (const key of [...SOURCE_KEYS, ...NOTE_KEYS]) {
        expect(lookup(translations[locale], key), `${key} missing from ${locale}`).toBeTruthy();
      }
    }
  });

  it("attaches upload, title and kind hints without taking over the Select trigger", () => {
    const html = render(<SourceUploadCard />);
    expect(html).toContain("Choose files");
    expect(html).toContain('id="kb-title"');
    expect(html).toContain('id="kb-kind"');
    expect(html.match(/data-slot="tooltip-trigger"/g)).toHaveLength(3);

    const kind = html.slice(html.indexOf('<span class="contents"', html.indexOf('id="kb-title"')), html.indexOf("</span>", html.indexOf('id="kb-kind"')) + 7);
    expect(kind).toContain('data-slot="tooltip-trigger"');
    expect(kind).toContain('data-slot="select-trigger"');
    expect(kind).toContain('data-state="closed"');
    expect(kind).not.toContain('data-slot="select-trigger" data-state="closed" data-slot="tooltip-trigger"');
  });

  it("gives source deletion its own irreversible-action hint", () => {
    const html = render(<SourceDeleteButton id="source-1" title="Resume" />);
    expect(html).toContain('aria-label="Delete Resume"');
    expect(html).toContain('data-slot="tooltip-trigger"');
    const source = readFileSync(new URL("./source-actions.tsx", import.meta.url), "utf8");
    expect(source).toContain('label={t("knowledge.sources.hintDelete")}');
    expect(source).toContain('label={t("knowledge.sources.hintClearBatch")}');
  });

  it("teaches note creation, tag filtering, editing and deletion on the live rows", () => {
    state.tagCounts = [
      { tag: "interview", count: 2 },
      { tag: "study", count: 1 },
    ];
    state.notes.data = {
      items: [{ id: "note-1", title: "Talking points", content: "Own the follow-up.", tags: ["interview"] }],
      total: 1,
      page: 0,
      size: 20,
    };
    const html = render(<NotesPanel />);
    expect(html).toContain("Save note");
    expect(html).toContain("Talking points");
    expect(html).toContain('aria-label="Edit Talking points"');
    expect(html).toContain('aria-label="Delete Talking points"');
    expect(html).toContain('aria-pressed="false"');
    expect(html.match(/data-slot="tooltip-trigger"/g)?.length).toBeGreaterThanOrEqual(5);

    const source = readFileSync(new URL("./notes-panel.tsx", import.meta.url), "utf8");
    for (const key of NOTE_KEYS) {
      expect(source).toContain(`t("${key}"`);
    }
  });

  it("keeps the creation hint attached in Chinese", () => {
    const html = render(<NoteCreateCard />, "zh");
    expect(html).toContain("保存笔记");
    expect(html).toContain('data-slot="tooltip-trigger"');
    expect(html).not.toContain("Save note");
  });
});
