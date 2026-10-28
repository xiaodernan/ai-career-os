import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";

import { applyDocumentLang, LocaleProvider, useLocale } from "./locale-context";

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

/** Reads one key with the variables it is given. */
function InterpolationProbe() {
  const { t } = useLocale();
  return (
    <span>
      {[
        t("applications.dialog.movedTo", { stage: "Offer" }),
        t("applications.dialog.deleteDescription", { title: "Staff Engineer" }),
        // A hole with no value is left alone rather than blanked.
        t("applications.dialog.movedTo"),
        // A key that is not in the table is not filled either.
        t("nav.nope", { stage: "Offer" }),
      ].join("|")}
    </span>
  );
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

  it("fills a hole with the value it is given", () => {
    const html = renderToStaticMarkup(
      <LocaleProvider>
        <InterpolationProbe />
      </LocaleProvider>
    );
    expect(html).toContain("Moved to Offer");
    expect(html).toContain("&quot;Staff Engineer&quot; and its history");
  });

  it("leaves a hole alone when there is no value for it", () => {
    // A missing value should read as missing, not as a sentence with a gap
    // in it -- and an unknown key should not gain one.
    const html = renderToStaticMarkup(
      <LocaleProvider>
        <InterpolationProbe />
      </LocaleProvider>
    );
    expect(html).toContain("{stage}");
    expect(html).toContain("nav.nope");
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

  it("takes the server's locale on the first render, without an effect", () => {
    // The shell is rendered on the server from the cookie. If the first render were "en"
    // while that HTML said zh, the reader would read English until an effect ran -- and a
    // client first render that disagreed with the server's markup would have to tear it
    // down to hydrate it.
    const html = renderToStaticMarkup(
      <LocaleProvider initialLocale="zh">
        <Probe />
      </LocaleProvider>
    );
    expect(html).toContain("zh|仪表盘");
  });
});

describe("the document's lang attribute", () => {
  it("follows the reader, and is a no-op where there is no document", () => {
    // The server render has no document; the guard is what keeps the provider safe there.
    expect(() => applyDocumentLang("zh")).not.toThrow();

    const element = { lang: "en" };
    const scope = globalThis as unknown as { document?: { documentElement: typeof element } };
    const real = scope.document;
    scope.document = { documentElement: element };
    try {
      applyDocumentLang("zh");
      expect(
        element.lang,
        "a Chinese page marked lang=en is read aloud with English phonetics"
      ).toBe("zh");
    } finally {
      if (real === undefined) delete scope.document;
      else scope.document = real;
    }
  });
});
