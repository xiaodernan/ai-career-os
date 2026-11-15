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

import { OperatorLedgerCard } from "./operator-ledger-card";

describe("OperatorLedgerCard", () => {
  it("renders the four measured burst results with their guard rail", () => {
    const html = renderToStaticMarkup(<OperatorLedgerCard />);
    expect(html).toContain('data-testid="operator-ledger-card"');
    expect(html).toContain("/health — 300/300");
    expect(html).toContain("/jobs — 200/200");
    expect(html).toContain("/applications — 200/200");
    expect(html).toContain("/knowledge/sources — 200/200");
    expect(html).toContain("[monitoring.ledgerBody]");
    expect(html).toContain("[monitoring.ledgerDateLine]");
  });
});
