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

import { FirstWeekGame } from "./first-week-game";

describe("FirstWeekGame", () => {
  it("opens chapter zero on the first scene with its three forks", () => {
    const html = renderToStaticMarkup(<FirstWeekGame />);
    expect(html).toContain('data-testid="first-week-game"');
    expect(html).toContain("[playbook.firstweekTitle]");
    expect(html).toContain("[playbook.firstweekStep|1,6]");
    expect(html).toContain("[playbook.firstweekScene_upload]");
    expect(html).toContain("playbook.firstweekChoice_upload_all");
    expect(html).toContain("playbook.firstweekChoice_upload_recent");
    expect(html).toContain("playbook.firstweekChoice_upload_polish");
  });
});
