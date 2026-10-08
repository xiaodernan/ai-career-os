import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/**
 * The design system animates, and until now it never asked whether the reader wanted it to.
 *
 * `globals.css` declares five `--animate-*` tokens, the app pulls in `tw-animate-css`'s
 * enter/exit pair and Tailwind's own `animate-pulse`, and the components add a dozen
 * `transition-*` classes on top of that. A slide-in card, a shimmering skeleton and a smooth
 * scroll are each pleasant once and unpleasant forever to a reader with a vestibular disorder
 * or a motion-sensitivity setting -- and the Definition of Done lists both "Animations" and
 * "Accessibility", which is only true together if the animations can be switched off.
 *
 * So the stylesheet carries a `prefers-reduced-motion: reduce` block, and this test holds its
 * shape rather than re-deriving it: a blanket rule over every element so a fourth animation
 * library cannot slip past it, the properties that actually move things, `scroll-behavior` on
 * the one element that declares it, and exactly one survivor -- the spinner, which is the only
 * animation here carrying information nothing else does.
 */

const CSS = readFileSync(new URL("./globals.css", import.meta.url), "utf8");
const SRC = fileURLToPath(new URL("../", import.meta.url));

/**
 * The stylesheet with its comments removed. Without this the gate reads a block that has been
 * commented out as a live one -- the `@media` line survives inside the comment and every
 * assertion below still passes -- which is the difference between a gate and a spelling check.
 */
const LIVE = CSS.replace(/\/\*[\s\S]*?\*\//g, "");

/** The body of a `@media (...)` block, brace-matched rather than regex-matched. */
function mediaBlock(query: string): string {
  const at = LIVE.indexOf(`@media (${query})`);
  if (at < 0) {
    return "";
  }
  const open = LIVE.indexOf("{", at);
  let depth = 0;
  for (let i = open; i < LIVE.length; i += 1) {
    if (LIVE[i] === "{") {
      depth += 1;
    } else if (LIVE[i] === "}") {
      depth -= 1;
      if (depth === 0) {
        return LIVE.slice(open + 1, i);
      }
    }
  }
  return "";
}

/** The body of one rule inside a block, found by its selector. */
function ruleBody(block: string, selector: string): string {
  const start = block.indexOf(selector);
  if (start < 0) {
    return "";
  }
  const open = block.indexOf("{", start);
  const close = block.indexOf("}", open);
  return block.slice(open + 1, close);
}

/** A rule's declarations, whitespace-normalised, so they can be compared as strings. */
function declarations(rule: string): string[] {
  return rule
    .split(";")
    .map((part) => part.replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

function sources(): string[] {
  const out: string[] = [];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = `${dir}/${entry.name}`;
      if (entry.isDirectory()) {
        walk(full);
      } else if (/\.tsx?$/.test(entry.name)) {
        out.push(readFileSync(full, "utf8"));
      }
    }
  };
  walk(SRC);
  return out;
}

const REDUCED = mediaBlock("prefers-reduced-motion: reduce");
const FLAT = REDUCED.replace(/\s+/g, " ");
const BLANKET = declarations(ruleBody(REDUCED, "*::after"));
const SPINNER = declarations(ruleBody(REDUCED, ".animate-spin"));

describe("globals.css under prefers-reduced-motion", () => {
  it("declares the block at all", () => {
    expect(REDUCED, "globals.css has no live prefers-reduced-motion: reduce block").not.toBe("");
  });

  it("neutralises, in the blanket rule, the properties that move things", () => {
    expect(BLANKET.length, "the blanket rule is missing, so nothing is covered").toBeGreaterThan(0);
    for (const prop of ["animation-duration", "animation-iteration-count", "transition-duration"]) {
      const found = BLANKET.filter((line) => line.startsWith(`${prop}:`));
      expect(found, `${prop} is not overridden in the blanket rule, so it keeps animating`)
        .toHaveLength(1);
      expect(found[0], `${prop} needs !important to beat a utility class`).toContain("!important");
    }
  });

  it("covers every element, so a new animation library cannot slip past it", () => {
    expect(FLAT, "the override is not a blanket rule over every element")
      .toContain("*, *::before, *::after {");
  });

  it("overrides scroll-behavior on html, the element that declares it", () => {
    expect(CSS).toContain("scroll-behavior: smooth");
    expect(FLAT).toContain("scroll-behavior: auto !important");
  });

  it("keeps exactly one animation alive, and it is one the app really uses", () => {
    expect(SPINNER.length, "no survivor is named, so a loading state has no motion left")
      .toBeGreaterThan(0);
    expect(SPINNER).toContain("animation-iteration-count: infinite !important");
    const users = sources().filter((source) => source.includes("animate-spin"));
    expect(users.length, "the spinner exception is dead code -- nothing uses it").toBeGreaterThan(0);
  });

  it("covers the animations the theme itself declares", () => {
    const tokens = CSS.split("--animate-").length - 1;
    expect(tokens, "the theme stopped declaring animations").toBeGreaterThanOrEqual(5);
    // The blanket rule is what reaches them: a token no rule covers would still animate.
    expect(BLANKET.some((line) => line.startsWith("animation-duration:"))).toBe(true);
  });
});
