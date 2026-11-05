import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: "en", t: (key: string) => key, setLocale: () => {} }),
}));

const mutate = vi.fn();
vi.mock("@/lib/hooks/actions", () => ({
  useNoteMutations: () => ({ create: { mutate, isPending: false } }),
}));

import { BetterAnswerNoteButton } from "./better-answer-note-button";

describe("BetterAnswerNoteButton", () => {
  it("offers the rewrite as a note of its own", () => {
    const html = renderToStaticMarkup(
      <BetterAnswerNoteButton item={{ question: "Why Redis?", answer: "Name the failure mode." }} />
    );
    expect(html).toContain("interviews.report.keepAsNote");
    expect(html).not.toContain('disabled=""');
  });
});
