import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { KnowledgeNote } from "@/lib/api/types";

const state = vi.hoisted(() => ({ notes: [] as KnowledgeNote[] }));

vi.mock("@/lib/hooks/resources", () => ({
  useKnowledgeNotes: () => ({
    data: { items: state.notes, total: state.notes.length, page: 0, size: 50 },
    isPending: false,
    isError: false,
  }),
}));

vi.mock("@/lib/hooks/actions", () => ({
  useNoteMutations: () => ({
    create: { mutate: () => undefined, isPending: false },
    remove: { mutate: () => undefined, isPending: false },
  }),
}));

import { TimeCapsuleCard } from "./time-capsule-card";
import { LocaleProvider } from "@/lib/i18n/locale-context";

function note(id: string, tags: string[], content: string): KnowledgeNote {
  return { id, title: "", content, tags };
}

// The provider reads the reader's language from localStorage; every assertion below is
// written against the Chinese copy, so the shelf is rendered in that language on purpose.
function render(locale: "en" | "zh" = "zh"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <TimeCapsuleCard />
      </LocaleProvider>,
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

describe("TimeCapsuleCard", () => {
  beforeEach(() => {
    state.notes = [];
  });

  it("shows an envelope, never the prose, while the letter is sealed", () => {
    state.notes = [note("sealed", ["capsule", "capsule-2099-01-01"], "a secret plan")];
    const markup = render();
    expect(markup).toContain("封存中");
    expect(markup).toContain("还要");
    expect(markup).not.toContain("a secret plan");
  });

  it("opens the prose once the date has arrived", () => {
    state.notes = [note("open", ["capsule", "capsule-2020-01-01"], "a visible memory")];
    const markup = render();
    expect(markup).toContain("已开启");
    expect(markup).toContain("a visible memory");
  });

  it("keeps a quiet shelf honest rather than empty", () => {
    const markup = render();
    expect(markup).toContain("还没有信");
  });

  it("ignores a note that wears the tag without a readable date", () => {
    state.notes = [note("broken", ["capsule", "capsule-not-a-date"], "not a capsule")];
    const markup = render();
    expect(markup).not.toContain("not a capsule");
    expect(markup).toContain("还没有信");
  });

  it("speaks English to an English reader, with the same sealed/open split", () => {
    state.notes = [
      note("sealed-en", ["capsule", "capsule-2099-01-01"], "a secret plan"),
      note("open-en", ["capsule", "capsule-2020-01-01"], "a visible memory"),
    ];
    const markup = render("en");
    expect(markup).toContain("Sealed");
    expect(markup).toContain("Opens in");
    expect(markup).toContain("Opened");
    expect(markup).not.toContain("a secret plan");
    expect(markup).toContain("a visible memory");
  });
});
