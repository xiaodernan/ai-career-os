import { describe, expect, it } from "vitest";
import { safeHref } from "./safe-href";

/**
 * The eight anchors that open something the app did not build -- a pasted posting URL, a
 * company's site, a crawler source, a study link, a resume's own links and repo, and the
 * markdown link the analyst emits -- all come here with the reader's string. What the
 * renderer actually does with an ungarded one is measured below, with real relative-path
 * arithmetic against this app's own origin, so the rule is graded on the bug rather than
 * on taste.
 */

const APP_PAGE = "https://careeros.example.com/jobs/6f1c0d2e-1111-2222-3333-444455556666";

/** Where the reader actually lands if the value is dropped into an href unguarded. */
const landingOf = (href: string) => new URL(href, APP_PAGE).href;

describe("the bug the guard exists for", () => {
  it("a scheme-less link is a path, so the button navigates inside the app", () => {
    // The reader pastes "www.acme.com/careers/123" from an address bar and the analyst
    // writes a company site the same way; the anchor then resolves under /jobs/.
    expect(landingOf("www.acme.com/careers/123")).toContain("/jobs/www.acme.com");
    expect(landingOf("acme.com"), "a bare host swallows the job's own id").toBe(
      "https://careeros.example.com/jobs/acme.com"
    );

    for (const value of ["www.acme.com/careers/123", "acme.com", "localhost:3000/careers"]) {
      const href = safeHref(value);
      expect(href, `${value} is still not an absolute URL`).toBeTypeOf("string");
      expect(new URL(href as string).hostname, `${value} opens the app, not the posting`).not.toBe(
        "careeros.example.com"
      );
      expect(landingOf(href as string)).not.toContain("/jobs/");
    }
  });

  it("every refused scheme leaves no anchor to click, in each spelling that reaches a browser", () => {
    const refused = [
      "javascript:alert(1)",
      "JaVaScRiPt:alert(1)",
      "  javascript:alert(1)",
      "\njavascript:alert(1)",
      "java\tscript:alert(1)",
      "data:text/html,<script>alert(1)</script>",
      "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
      "file:///C:/Users/victim/Desktop/notes.txt",
      "tg://msg?text=hi",
      "intent://scan/#Intent;scheme=zxing;end",
      "mailto:hr@acme.com",
      "tel:+15551234",
      "view-source:https://careeros.example.com",
      "blob:https://careeros.example.com/1e4a0c1c-2b3d-4e5f-6a7b-8c9d0e1f2a3b",
      "https://careeros.example.com@evil.test/phish",
      "http://",
      "https://exa mple.com",
      "   ",
    ];
    for (const value of refused) {
      expect(safeHref(value), `${JSON.stringify(value)} should not be a link`).toBeUndefined();
    }
    expect(safeHref(null)).toBeUndefined();
    expect(safeHref(undefined)).toBeUndefined();
  });
});

describe("what the guard passes through", () => {
  it("keeps a page URL exactly as the reader wrote it", () => {
    for (const value of [
      "https://boards.example.com/senior-backend-engineer",
      "http://intranet.example.com/job/9",
      "https://ACME.com/Careers?q=1#top",
      "https://acme.com/jobs/123?utm_source=linkedin",
    ]) {
      expect(safeHref(value), `${value} was rewritten`).toBe(value);
    }
  });

  it("keeps the in-app spellings the surfaces actually pass", () => {
    expect(safeHref("/knowledge?src=4f2a")).toBe("/knowledge?src=4f2a");
    expect(safeHref("#tailor")).toBe("#tailor");
    expect(safeHref("/jobs")).toBe("/jobs");
    // A protocol-relative value means the same host over the page's own scheme.
    expect(safeHref("//cdn.acme.com/posting")).toBe("https://cdn.acme.com/posting");
  });

  it("adds the scheme a bare host is missing, and nothing else", () => {
    expect(safeHref("www.acme.com/careers/123")).toBe("https://www.acme.com/careers/123");
    expect(safeHref("acme.com")).toBe("https://acme.com");
    expect(safeHref("  boards.example.com/j  ")).toBe("https://boards.example.com/j");
    // A colon before the first slash is a port here, not a scheme.
    expect(safeHref("localhost:3000/careers")).toBe("https://localhost:3000/careers");
    expect(safeHref("acme.com:8443/jobs")).toBe("https://acme.com:8443/jobs");
  });

  it("a value that is not a link at all costs the reader the link, not the page", () => {
    for (const value of ["", " ", "not a url", "just text", "https://", "//"]) {
      expect(safeHref(value), `${JSON.stringify(value)} became a link`).toBeUndefined();
    }
  });

  it("the returned href is always one the browser can only resolve as http(s)", () => {
    const values = [
      "www.acme.com/x",
      "https://acme.com",
      "//acme.com",
      "/jobs",
      "#tailor",
      "javascript:alert(1)",
      "data:text/html,x",
      "acme.com:8443/jobs",
    ];
    for (const value of values) {
      const href = safeHref(value);
      if (href === undefined || href.startsWith("#") || href.startsWith("/")) continue;
      expect(["http:", "https:"], `${href} is not a page scheme`).toContain(new URL(href).protocol);
    }
  });
});
