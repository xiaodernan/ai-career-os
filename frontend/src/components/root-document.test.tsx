import { describe, expect, it } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { RootDocument } from "./root-document";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * The first HTML a reader receives.
 *
 * The locale cookie is written on every switch and read by the page's metadata, but the
 * body and `<html lang>` never saw it: the provider initialized to "en" on the server and
 * the layout hardcoded `lang="en"`. So a zh reader's first paint was an English document
 * (marked as English for a screen reader, too), which flipped to Chinese after hydration.
 *
 * The layout now reads the cookie and hands the locale here; this renders the shipped shell
 * and reads both facts off the markup: the `lang` attribute and the language of the words.
 */

function Probe() {
  const { locale, t } = useLocale();
  return <span>{`${locale}|${t("nav.dashboard")}`}</span>;
}

describe("the document shell", () => {
  it("sends the reader's language in the first HTML, in lang and in the body", () => {
    const html = renderToStaticMarkup(
      <RootDocument locale="zh" bodyClassName="shell">
        <Probe />
      </RootDocument>
    );
    expect(html, "the shell's markup").toMatch(/^<html lang="zh"/);
    expect(html, `the zh shell rendered: ${html.slice(0, 240)}`).toContain("zh|仪表盘");
    expect(html, "a zh reader's first paint was English").not.toContain("en|Dashboard");
  });

  it("keeps English for an English reader (control)", () => {
    const html = renderToStaticMarkup(
      <RootDocument locale="en" bodyClassName="shell">
        <Probe />
      </RootDocument>
    );
    expect(html).toMatch(/^<html lang="en"/);
    expect(html).toContain("en|Dashboard");
  });
});
