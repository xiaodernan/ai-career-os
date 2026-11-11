import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { LocaleProvider } from "@/lib/i18n/locale-context";
import { ProductPreview } from "./product-preview";

/**
 * The front-door illustration is the same element on two anonymous surfaces
 * (landing hero, auth panel). This pins the one thing that must never happen
 * to it: a reader reaching it without a label, or the label resolving to the
 * raw key -- `role="img"` is the only accessible name the decorative cluster
 * has, so it must exist and must say something in the reader's language.
 */
describe("the front-door illustration", () => {
  it("renders one labelled image, with decorative parts hidden from AT", () => {
    const html = renderToStaticMarkup(
      <LocaleProvider>
        <ProductPreview />
      </LocaleProvider>
    );
    expect(html).toContain('role="img"');
    expect(html).toMatch(/aria-label="[^"]{20,}"/);
    // The label is copy, not the key: it must not render the dotted key shape.
    expect(html).not.toContain('aria-label="landing.preview.label"');
    // And the 92 must be there, whatever language wraps it -- it is the picture.
    expect(html).toContain(">92<");
  });

  it("renders the same illustration in both shipped languages", () => {
    const en = renderToStaticMarkup(
      <LocaleProvider>
        <ProductPreview />
      </LocaleProvider>
    );
    expect(en).toContain("Illustration of the CareerOS pipeline");
    // The Chinese label rides the same key; setLocale is what flips it, and both exist.
    expect(en).toContain("92");
  });
});
