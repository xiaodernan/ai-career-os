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

import AdminPage from "./admin-page";

describe("AdminPage", () => {
  it("renders the locked gate before the passphrase; the SSR surface never shows the ledger", () => {
    const html = renderToStaticMarkup(<AdminPage />);
    expect(html).toContain("[admin.passphraseLabel]");
    expect(html).toContain("[admin.unlock]");
    expect(html).toContain("[admin.adminTitle]");
    expect(html).not.toContain("[admin.journeyTitle]");
    expect(html).not.toContain("[admin.optimizationsTitle]");
  });
});
