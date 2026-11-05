import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: "en", t: (key: string) => key, setLocale: () => {} }),
}));

vi.mock("@/lib/hooks/actions", () => ({
  useNoteMutations: () => ({
    create: { mutate: vi.fn(), isPending: false },
  }),
}));

import { KeepAsNoteButton, KeptNoteLink } from "./keep-as-note-button";

describe("KeepAsNoteButton", () => {
  it("offers one click and no way out before the note exists", () => {
    const html = renderToStaticMarkup(
      <KeepAsNoteButton draft={{ title: "B-trees", content: "why leaves link", tags: ["interview", "study"] }} />
    );
    expect(html).toContain("interviews.report.keepAsNote");
    expect(html).not.toContain("<a ");
  });
});

describe("KeptNoteLink", () => {
  it("is a door to the notes carrying the draft's own kind", () => {
    const html = renderToStaticMarkup(<KeptNoteLink tags={["interview", "study"]} />);
    expect(html).toContain('href="/knowledge?ntag=study"');
    expect(html).toContain("interviews.report.noteKeptOpen");
    expect(html).not.toContain("interviews.report.keepAsNote");
  });

  it("opens the unfiltered list when the draft minted no kind tag", () => {
    const html = renderToStaticMarkup(<KeptNoteLink tags={["interview"]} />);
    expect(html).toContain('href="/knowledge"');
  });
});
