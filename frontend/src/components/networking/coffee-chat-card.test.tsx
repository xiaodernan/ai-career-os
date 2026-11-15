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

import { CoffeeChatCard } from "./coffee-chat-card";

describe("CoffeeChatCard", () => {
  it("renders the three moments with the ask on the table first", () => {
    const html = renderToStaticMarkup(<CoffeeChatCard />);
    expect(html).toContain('data-testid="coffee-chat-card"');
    expect(html).toContain("[networking.coffeeTitle]");
    expect(html).toContain("[networking.coffeeDescription]");
    expect(html).toContain("[networking.coffeeStep|1]");
    expect(html).toContain("[networking.coffeePush_ask]");
    expect(html).toContain("[networking.coffeeReply_ask_burden]");
    expect(html).toContain("[networking.coffeeReply_ask_generic]");
    expect(html).toContain("[networking.coffeeReply_ask_specific]");
  });
});
