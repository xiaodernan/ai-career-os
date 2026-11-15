import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `[${key}|${Object.values(vars).join(",")}]` : `[${key}]`,
    setLocale: () => undefined,
  }),
}));

import { NineQuestsCard } from "./nine-quests-card";

describe("NineQuestsCard", () => {
  it("renders the tour with nine rooms, the progress rail, and the reset path", () => {
    const html = renderToStaticMarkup(<NineQuestsCard />);
    expect(html).toContain('data-testid="nine-quests-card"');
    expect(html).toContain("[dashboard.nineQuestsTitle]");
    expect(html).toContain("[dashboard.nineQuestsIntro]");
    expect(html).toContain("[dashboard.nineQuestsProgress|0,9]");
    expect(html).toContain('role="progressbar"');
    expect(html).toContain('href="/resumes"');
    expect(html).toContain('href="/studio"');
    expect(html).toContain('href="/growth"');
    expect(html).toContain('href="/letters"');
    expect(html).toContain('href="/interviews"');
    expect(html).toContain('href="/applications"');
    expect(html).toContain('href="/replies"');
    expect(html).toContain('href="/offers"');
    expect(html).toContain('href="/ceremony"');
  });
});
