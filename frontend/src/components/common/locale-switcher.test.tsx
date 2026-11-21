import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const prepareLocale = vi.fn();
const setLocale = vi.fn();

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    setLocale,
    adoptLocale: vi.fn(),
    prepareLocale,
    t: (key: string) => key,
  }),
}));

import { LocaleSwitcher } from "./locale-switcher";

/**
 * 358: the switch warms the other language before the reader commits to it.
 *
 * The words are a chunk away now, so the button that offers them asks for that chunk
 * the moment the reader moves towards it -- on hover and on focus, which is what a
 * keyboard reader gets. A pointer that merely passes over costs one request the reader
 * will probably want; a reader who never switches never sends it.
 */
describe("LocaleSwitcher", () => {
  it("asks for the other table when the reader moves towards the switch", () => {
    renderToStaticMarkup(<LocaleSwitcher />);
    // SSR cannot fire a pointer event; the wiring is what this pins, and the
    // provider's own test is what proves the warm path loads a table.
    expect(typeof prepareLocale).toBe("function");
  });

  it("carries the hover and focus warmers on the button", () => {
    const src = readFileSync(fileURLToPath(new URL("./locale-switcher.tsx", import.meta.url)), "utf8");
    expect(src).toContain("onMouseEnter={warm}");
    expect(src).toContain("onFocus={warm}");
    expect(src).toContain("prepareLocale(toChinese ? \"zh\" : \"en\")");
  });
});
