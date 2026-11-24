import { afterEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";

vi.mock("@/lib/i18n/locale-context", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/i18n/locale-context")>()),
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `[${key}|${Object.values(vars).join(",")}]` : `[${key}]`,
    setLocale: () => undefined,
  }),
}));

import { CoffeeChatCard } from "./coffee-chat-card";
import { lookup } from "@/lib/i18n/locale-context";
import { translations } from "@/lib/i18n/translations";

const HINT_KEYS = [
  "networking.coffeeHintReply",
  "networking.coffeeHintNext",
  "networking.coffeeHintVerdict",
  "networking.coffeeHintKeep",
  "networking.coffeeHintReset",
];

afterEach(() => vi.unstubAllGlobals());

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

  it("attaches one teaching trigger to every reply without replacing radio state", () => {
    const html = renderToStaticMarkup(<CoffeeChatCard />);
    expect(html.match(/role="radio"/g)).toHaveLength(3);
    expect(html.match(/data-slot="tooltip-trigger"/g)).toHaveLength(3);
    expect(html.match(/aria-checked="false"/g)).toHaveLength(3);
    const source = readFileSync(new URL("./coffee-chat-card.tsx", import.meta.url), "utf8");
    expect(source.match(/label=\{t\("networking\.coffeeHintReply"\)\}/g)).toHaveLength(1);
  });

  it("teaches the kept sentence and reset after all three choices", () => {
    vi.stubGlobal("window", {
      localStorage: {
        getItem: () =>
          JSON.stringify({
            scores: { ask: "specific", middle: "lead", close: "forward" },
            sentence: "One question and fifteen minutes.",
          }),
        setItem: () => {},
        removeItem: () => {},
      },
    });
    const html = renderToStaticMarkup(<CoffeeChatCard />);

    expect(html).toContain('id="coffee-keep"');
    expect(html).toContain('data-slot="textarea"');
    expect(html.match(/data-slot="tooltip-trigger"/g)).toHaveLength(2);
    expect(html).not.toContain("chrome.resetHint");
    const source = readFileSync(new URL("./coffee-chat-card.tsx", import.meta.url), "utf8");
    expect(source).toContain('label={t("networking.coffeeHintKeep")}');
    expect(source).toContain('label={t("networking.coffeeHintReset")}');
  });

  it("defines all five coffee consequences in both languages and wires both advance paths", () => {
    for (const locale of ["en", "zh"] as const) {
      for (const key of HINT_KEYS) {
        expect(lookup(translations[locale], key), `${locale}: ${key}`).toBeTruthy();
      }
    }
    const source = readFileSync(new URL("./coffee-chat-card.tsx", import.meta.url), "utf8");
    expect(source).toContain(
      't(isLast ? "networking.coffeeHintVerdict" : "networking.coffeeHintNext")'
    );
    expect(source).toContain('t("networking.coffeeHintReply")');
    expect(source).toContain("const done = verdictOpen && coffeeAnswered(state);");
    expect(source).toContain("setVerdictOpen(true);");
  });
});
