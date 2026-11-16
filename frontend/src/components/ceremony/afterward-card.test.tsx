import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `{${key}|${Object.entries(vars).map(([k, v]) => `${k}=${v}`).join(",")}}` : `{${key}}`,
    setLocale: () => undefined,
  }),
}));

vi.mock("@/lib/hooks/resources", () => ({
  useApplications: () => ({ data: { total: 37 }, isPending: false, isError: false }),
  useInterviewSessions: () => ({ data: { total: 12 }, isPending: false, isError: false }),
}));

vi.mock("@/lib/hooks/monitoring", () => ({
  useActivityHeatmap: () => ({
    data: {
      grandTotal: 418,
      grid: [
        { applications: 1, interviews: 0, replies: 0, aiCalls: 1 },
        { applications: 0, interviews: 0, replies: 0, aiCalls: 0 },
        { applications: 2, interviews: 0, replies: 1, aiCalls: 3 },
      ],
    },
  }),
}));

import { AfterwardCard } from "./afterward-card";

describe("AfterwardCard", () => {
  const html = renderToStaticMarkup(<AfterwardCard />);

  it("renders three honest numbers, each bound to the caller's own data", () => {
    expect(html).toContain("{ceremony.afterwardK1Label}");
    expect(html).toContain("{ceremony.afterwardK2Label}");
    expect(html).toContain("{ceremony.afterwardK3Label}");
    expect(html).toContain(">37<");
    expect(html).toContain(">12<");
    // 2 active days (grid[0] and grid[2])
    expect(html).toContain(">2<");
  });

  it("carries the closing honest sentence in the reader's language", () => {
    expect(html).toContain("{ceremony.afterwardFootnote}");
  });

  it("renders the eyebrow and headline in accessible position", () => {
    expect(html).toContain("{ceremony.afterwardEyebrow}");
    expect(html).toContain("{ceremony.afterwardTitle}");
  });
});
