import { describe, expect, it } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { StreamingText } from "./streaming-text";

/**
 * The analyst writes markdown links, so this renderer is where model text becomes a
 * clickable destination. react-markdown's own transform already removes the protocols a
 * browser would run (`javascript:`, `data:`, `file:`) and even one whose scheme is
 * upper-cased, which the assertions below record rather than repeat; what it passes
 * through untouched is a scheme-less host, and that is the one that used to walk the
 * reader to a route inside this app.
 */

const hrefsOf = (html: string) => [...html.matchAll(/<a\b[^>]*href="([^"]*)"[^>]*>/g)].map((m) => m[1]);

describe("the markdown renderer's links", () => {
  it("opens a bare host off-app instead of under the current route", () => {
    const html = renderToStaticMarkup(<StreamingText content="[DDIA](ddia.gg/ch9)" />);
    expect(hrefsOf(html)).toEqual(["https://ddia.gg/ch9"]);
    // Unguarded, the same value resolves to /jobs/ddia.gg under whatever page shows it.
    expect(new URL("ddia.gg/ch9", "https://careeros.example.com/jobs/1").pathname).toContain("ddia.gg");
  });

  it("keeps a real URL and an in-app link exactly as written (control)", () => {
    expect(hrefsOf(renderToStaticMarkup(<StreamingText content="[job](https://acme.com/j/1)" />))).toEqual([
      "https://acme.com/j/1",
    ]);
    expect(hrefsOf(renderToStaticMarkup(<StreamingText content="[note](/knowledge?src=4f2a)" />))).toEqual([
      "/knowledge?src=4f2a",
    ]);
  });

  it("hands the reader a link that stays outside the app", () => {
    const html = renderToStaticMarkup(<StreamingText content="[acme](https://acme.com/j)" />);
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer nofollow"');
  });

  it("renders no anchor for a destination that is not a page", () => {
    // react-markdown itself refuses these, so the renderer never even sees them: the
    // assertion is that the hole stays shut, whichever of the two gates closes it.
    for (const link of ["javascript:alert(1)", "data:text/html,x", "file:///C:/secrets.txt"]) {
      expect(hrefsOf(renderToStaticMarkup(<StreamingText content={`[x](${link})`} />)), link).toEqual([]);
    }
    // What react-markdown does pass on, the guard answers: a mail handler is not a page,
    // so the words stay readable and the click goes nowhere.
    const mail = renderToStaticMarkup(<StreamingText content="[hr](mailto:hr@acme.com)" />);
    expect(hrefsOf(mail)).toEqual([]);
    expect(mail).toContain(">hr<");
  });
});
