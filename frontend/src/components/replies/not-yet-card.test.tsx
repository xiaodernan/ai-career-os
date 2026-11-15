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

import { NotYetCard } from "./not-yet-card";

describe("NotYetCard", () => {
  it("renders the three doors and the kept sentence, collapsed by default", () => {
    const html = renderToStaticMarkup(<NotYetCard />);
    expect(html).toContain('data-testid="not-yet-card"');
    expect(html).toContain("[replies.notYetTitle]");
    expect(html).toContain("[replies.notYetDescription]");
    expect(html).toContain("[replies.notYetDoor_calibrate_quote]");
    expect(html).toContain("[replies.notYetDoor_hold_quote]");
    expect(html).toContain("[replies.notYetDoor_impress_quote]");
    expect(html).toContain("[replies.notYetKeepPlaceholder]");
    expect(html).not.toContain("[replies.notYetDoor_calibrate_decode]");
  });
});
