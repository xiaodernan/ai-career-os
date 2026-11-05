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

import { StudyNoteButton } from "./study-note-button";

describe("StudyNoteButton", () => {
  it("offers the study item as a note, not a link away", () => {
    const html = renderToStaticMarkup(
      <StudyNoteButton item={{ title: "Consistent hashing", why: "asked twice" }} />
    );
    expect(html).toContain("interviews.report.keepAsNote");
    expect(html).not.toContain("<a ");
    // The class string mentions `disabled:` variants; the attribute is what matters.
    expect(html).not.toContain('disabled=""');
  });

  it("keeps an untitled item saveable rather than dropping it", () => {
    const html = renderToStaticMarkup(<StudyNoteButton item={{ why: "no topic given" }} />);
    expect(html).toContain("interviews.report.keepAsNote");
  });
});
