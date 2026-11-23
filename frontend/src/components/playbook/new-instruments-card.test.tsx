import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: "en", t: (key: string) => `[${key}]`, setLocale: () => undefined }),
}));

import { NewInstrumentsCard } from "./new-instruments-card";

describe("NewInstrumentsCard", () => {
  it("teaches the three newest instruments, each with a working door", () => {
    const html = renderToStaticMarkup(<NewInstrumentsCard />);
    expect(html).toContain("[playbook.newInstrumentsStoryTitle]");
    expect(html).toContain("[playbook.newInstrumentsAnswerTitle]");
    expect(html).toContain("[playbook.newInstrumentsLostTitle]");
    expect(html).toContain('href="/timeline"');
    expect(html).toContain('href="/knowledge"');
    expect(html).toContain('href="/admin"');
  });
});
