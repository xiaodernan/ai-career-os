import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

/**
 * The browser tab's title.
 *
 * Next.js reads a route's title from the `metadata` export, which is
 * evaluated on the server -- and the server cannot know the language,
 * because this product keeps the locale in the browser's own storage. So
 * every route's title was English, whatever the reader chose, and the
 * title was the one thing on the page that never changed.
 *
 * The component cannot render in the node environment -- it reads the
 * router and the locale -- so these guard the wiring instead: the effect
 * that sets the title, the suffix the root layout's template gives, and
 * the rule that a path the product does not name is left to the server.
 */
const source = readFileSync(
  new URL("./document-title.tsx", import.meta.url),
  "utf8"
);

describe("the document title", () => {
  it("sets the title from the route table, in the reader's language", () => {
    expect(source).toContain("routeTitle(pathname, t)");
    expect(source).toContain("document.title =");
    // The suffix the root layout's `title.template` gives, so the tab reads
    // the same in the client as it did on the server.
    expect(source).toContain("· AI Career OS");
  });

  it("follows the locale, not just the path", () => {
    // A reader who switches language on a page must see the tab follow.
    // The effect's dependencies are the whole claim: without the locale,
    // the title would be set once and never move.
    expect(source).toMatch(/useEffect\(\(\) => \{[\s\S]*?\}, \[pathname, t, locale\]\)/);
  });

  it("leaves a path the product does not name to the server", () => {
    // The server's `metadata` is the right answer for a 404 or a route
    // that does not exist; the client must not overwrite it with a guess.
    expect(source).toMatch(/if \(!title\) return;/);
  });

  it("is mounted once, at the root, so every route is covered", () => {
    const layout = readFileSync(
      new URL("../../app/layout.tsx", import.meta.url),
      "utf8"
    );
    expect(layout).toContain("<DocumentTitle />");
    expect(layout).toContain('from "@/components/layout/document-title"');
  });
});
