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

import { JobsPulseCard } from "./pulse-card";

describe("JobsPulseCard", () => {
  it("renders the five measured stats and the date line", () => {
    const html = renderToStaticMarkup(<JobsPulseCard />);
    expect(html).toContain('data-testid="jobs-pulse-card"');
    expect(html).toContain("[jobs.pulseTitle]");
    expect(html).toContain("[jobs.pulseCompanies]");
    expect(html).toContain("[jobs.pulseRoles]");
    expect(html).toContain("[jobs.pulseSessions]");
    expect(html).toContain("[jobs.pulseApplications]");
    expect(html).toContain("[jobs.pulseNotes]");
    expect(html).toContain("[jobs.pulseDated]");
    expect(html).toContain("[jobs.pulseCount|16]");
    expect(html).toContain("[jobs.pulseCount|5052]");
  });
});
