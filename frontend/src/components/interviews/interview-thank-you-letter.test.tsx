import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string) => `[${key}]`,
    setLocale: () => undefined,
  }),
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), info: vi.fn(), error: vi.fn() } }));

const writer = vi.fn();
vi.mock("@/lib/hooks/actions", () => ({
  useInterviewThankYouLetter: () => ({ mutate: writer, isPending: false }),
}));

import { InterviewThankYouLetter } from "./interview-thank-you-letter";

describe("InterviewThankYouLetter", () => {
  it("renders the eyebrow, the teaching hint and the ask-first button — nothing is written on mount", () => {
    const html = renderToStaticMarkup(<InterviewThankYouLetter sessionId="session-1" />);
    expect(html).toContain("[interviews.thankYouLetter.eyebrow]");
    expect(html).toContain("[interviews.thankYouLetter.hint]");
    expect(html).toContain("[interviews.thankYouLetter.button]");
    expect(writer).not.toHaveBeenCalled();
  });
});
