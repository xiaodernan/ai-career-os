import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";

import { LocaleProvider, useLocale } from "./locale-context";

/**
 * The locale context's own contract.
 *
 * Two things matter: a key the table does not carry answers with the key
 * itself rather than an empty string (a blank label is an invisible button),
 * and the provider is safe to read from a server render where `localStorage`
 * does not exist.
 */

function Probe() {
  const { locale, t } = useLocale();
  return <span>{`${locale}|${t("nav.dashboard")}|${t("nav.nope")}|${t("no.such.key")}`}</span>;
}

describe("useLocale", () => {
  it("answers English by default and falls back to the key for an unknown name", () => {
    const html = renderToStaticMarkup(
      <LocaleProvider>
        <Probe />
      </LocaleProvider>
    );
    expect(html).toContain("en|Dashboard|nav.nope|no.such.key");
  });

  it("renders on a server, where there is no localStorage to read", () => {
    // The provider reads the stored locale in an effect, so a server render
    // must not touch `window` at all — a read there would throw in the
    // server-rendered shell.
    expect(() =>
      renderToStaticMarkup(
        <LocaleProvider>
          <Probe />
        </LocaleProvider>
      )
    ).not.toThrow();
  });
});
