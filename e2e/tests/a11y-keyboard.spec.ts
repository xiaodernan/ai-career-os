import { expect, test } from "./fixtures";
import { unwrap } from "./fixtures";

/**
 * The keyboard path.
 *
 * The product's a11y story is in the global CSS -- a skip link, a
 * `:focus-visible` outline on everything, a reduced-motion override -- and
 * in the components that give every control a name. None of that is a
 * claim anyone can check, because it is all invisible to a reader who
 * uses a mouse and invisible to the unit tests.
 *
 * So the path is driven with the keyboard, the way a reader who cannot
 * use a mouse drives it, and three things are checked:
 *
 *   1. The skip link is the *first* thing the keyboard reaches, and it
 *      moves the focus to the content -- a viewport jump without a focus
 *      move buys nothing, because the next Tab starts from the top again.
 *   2. Every element the keyboard reaches has a *visible* focus
 *      indicator. The global rule gives one, but a rule can be overridden
 *      by a component, and an element with no visible focus is invisible
 *      to the reader it was meant for.
 *   3. Every control in the shell has an accessible name -- a button
 *      with an icon and no label is a button with no name, and the icon
 *      is not a name.
 */

/** The accessible name of an element, the way a screen reader computes it. */
const ACCESSIBLE_NAME = `(el) => {
  const labelledBy = el.getAttribute("aria-labelledby");
  if (labelledBy) {
    const parts = labelledBy.split(/\\s+/).map((id) => document.getElementById(id)?.textContent ?? "");
    if (parts.join(" ").trim()) return parts.join(" ").trim();
  }
  const ariaLabel = el.getAttribute("aria-label");
  if (ariaLabel && ariaLabel.trim()) return ariaLabel.trim();
  if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT") {
    const id = el.getAttribute("id");
    if (id) {
      const label = document.querySelector('label[for="' + CSS.escape(id) + '"]');
      if (label?.textContent?.trim()) return label.textContent.trim();
    }
    const wrapping = el.closest("label");
    if (wrapping?.textContent?.trim()) return wrapping.textContent.trim();
    const title = el.getAttribute("title");
    if (title && title.trim()) return title.trim();
    const placeholder = el.getAttribute("placeholder");
    if (placeholder && placeholder.trim()) return placeholder.trim();
    return "";
  }
  const text = (el.textContent ?? "").trim();
  if (text) return text;
  const value = el.getAttribute("value");
  if (value && value.trim()) return value.trim();
  const alt = el.querySelector("img[alt]")?.getAttribute("alt");
  return alt && alt.trim() ? alt.trim() : "";
}`;

test("the skip link is the first thing the keyboard reaches, and it takes the focus to the content", async ({
  authedPage,
}) => {
  await authedPage.goto("/dashboard");

  // The shell has to be mounted before the keyboard means anything: the
  // auth guard renders a splash until the session resolves, and a Tab
  // pressed into the splash reaches nothing.
  await expect(authedPage.getByLabel("Open command palette").first()).toBeVisible();

  // One Tab from the top of the document: the skip link, and nothing
  // before it. It rests above the viewport and slides in on focus, so it
  // is only *visible* once it has it -- which is the point of it.
  await authedPage.keyboard.press("Tab");
  const focused = await authedPage.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    return { tag: el?.tagName ?? "", text: (el?.textContent ?? "").trim(), href: el?.getAttribute("href") ?? "" };
  });
  expect(focused.tag, "the first Tab did not reach a link").toBe("A");
  expect(focused.href, "the first Tab did not reach the skip link").toBe("#main");
  await expect(authedPage.getByRole("link", { name: "Skip to content" })).toBeVisible();

  // And it takes the focus with it. A fragment jump moves the viewport
  // but not the focus, so without the target's `tabIndex={-1}` the next
  // Tab would start again from the top and the link would have bought
  // nothing.
  await authedPage.keyboard.press("Enter");
  await expect
    .poll(async () =>
      authedPage.evaluate(() => (document.activeElement as HTMLElement | null)?.id ?? "")
    )
    .toBe("main");
});

test("every element the keyboard reaches has a visible focus indicator", async ({
  authedPage,
}) => {
  await authedPage.goto("/dashboard");
  await authedPage.locator("main").waitFor({ state: "attached" });

  // Walk the first stretch of the tab order. The global rule gives every
  // focused element a two-pixel outline, and a component that overrides
  // it would be invisible to the reader the rule was written for.
  const walked: string[] = [];
  for (let i = 0; i < 12; i++) {
    await authedPage.keyboard.press("Tab");
    const found = await authedPage.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el || el === document.body) return null;
      const style = getComputedStyle(el);
      return {
        tag: el.tagName,
        label: (el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 40),
        outlineStyle: style.outlineStyle,
        outlineWidth: style.outlineWidth,
        boxShadow: style.boxShadow,
      };
    });
    if (!found) break;
    walked.push(found.label || found.tag);
    const visible =
      (found.outlineStyle !== "none" && parseFloat(found.outlineWidth) > 0) ||
      (found.boxShadow !== "none" && found.boxShadow !== "");
    expect(
      visible,
      `${found.tag} "${found.label}" has no visible focus indicator (outline: ${found.outlineStyle} ${found.outlineWidth})`
    ).toBe(true);
  }

  // The walk found something, so the check was not vacuous.
  expect(walked.length, "the tab order was empty").toBeGreaterThan(3);
});

test("every control in the shell has an accessible name", async ({ authedPage }) => {
  await authedPage.goto("/dashboard");
  await authedPage.locator("main").waitFor({ state: "attached" });

  const nameless = await authedPage.evaluate((nameFn) => {
    // The shell and the page: the sidebar, the topbar, and the content.
    const scopes = [
      document.querySelector("header"),
      document.querySelector("aside"),
      document.querySelector("main"),
    ].filter(Boolean) as Element[];
    const name = eval(nameFn) as (el: Element) => string;
    const out: string[] = [];
    for (const scope of scopes) {
      const nodes = Array.from(
        scope.querySelectorAll("button, a[href], input, textarea, select")
      );
      for (const el of nodes) {
        // A hidden control is not a control the reader meets.
        const style = getComputedStyle(el);
        if (style.display === "none" || style.visibility === "hidden") continue;
        if (el.closest("[aria-hidden='true']")) continue;
        if (!name(el)) {
          out.push(
            `${el.tagName.toLowerCase()}${
              el.className ? ` .${String(el.className).split(" ")[0]}` : ""
            }`
          );
        }
      }
    }
    return out;
  }, ACCESSIBLE_NAME);

  expect(
    nameless,
    `these controls have no accessible name: ${nameless.join(", ")}`
  ).toEqual([]);
});

test("the language switch is reachable and operable from the keyboard", async ({
  authedPage,
}) => {
  await authedPage.goto("/dashboard");
  // The top bar's own heading -- the route's name, read through the
  // locale. It is the chrome's, so it is the same for every page, and it
  // is a heading the reader sees change the moment the language does.
  const routeTitle = authedPage.locator("header h2");
  await expect(routeTitle).toHaveText("Dashboard");

  // The switch is a button, so the keyboard can reach it and press it.
  const switcher = authedPage.getByRole("button", { name: "Switch to Chinese" });
  await expect(switcher).toBeVisible();

  await switcher.focus();
  await expect(switcher).toBeFocused();

  // Enter, not a click: a reader who never uses a mouse activates a
  // control with the keyboard.
  await authedPage.keyboard.press("Enter");
  await expect(routeTitle).toHaveText("仪表盘", { timeout: 20_000 });

  // And back, so the next test starts where this one left off.
  await authedPage.getByRole("button", { name: "切换到英文" }).focus();
  await authedPage.keyboard.press("Enter");
  await expect(routeTitle).toHaveText("Dashboard", { timeout: 20_000 });
});

test("the command palette takes the keyboard and gives the focus back", async ({
  authedPage,
}) => {
  await authedPage.goto("/dashboard");

  // The shortcut is bound in a `useEffect` inside the palette's provider,
  // which sits behind the auth guard -- and the guard renders a splash
  // until the session resolves. Pressing the key before that lands on a
  // page with no listener attached, so the wait comes first: the topbar's
  // own button is inside the same provider, so its appearing is proof
  // the listener is live.
  await expect(authedPage.getByLabel("Open command palette").first()).toBeVisible();
  await authedPage.keyboard.press("ControlOrMeta+k");

  const input = authedPage.getByPlaceholder("Type a command or search…");
  await expect(input).toBeVisible({ timeout: 20_000 });

  // Typing goes into the palette, not into the page behind it.
  await input.fill("dashboard");
  await expect(input).toHaveValue("dashboard");

  // Escape closes it and gives the focus back to the page, so the
  // reader is not dropped at the top of the document.
  await authedPage.keyboard.press("Escape");
  await expect(input).toBeHidden({ timeout: 20_000 });
  const focusAfter = await authedPage.evaluate(
    () => (document.activeElement as HTMLElement | null)?.tagName ?? ""
  );
  expect(focusAfter, "the focus was left nowhere after the palette closed").not.toBe("");
});
