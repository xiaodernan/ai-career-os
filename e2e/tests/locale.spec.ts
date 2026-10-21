import { expect, test } from "./fixtures";

/**
 * The locale switch reaches the browser.
 *
 * The copy census (`frontend/src/lib/i18n/copy-census.test.ts`) proves that
 * no screen carries a hardcoded English string any more -- it walks the
 * browser's own sources and fails on one. That is a claim about the code.
 *
 * This is the claim about the product: a reader who switches the language
 * gets a product in that language. The census cannot prove it, because a
 * table full of keys and a context nobody reads still passes the census.
 *
 * So the switch is driven for real -- the sidebar's button, the same one a
 * reader clicks -- and the page is checked before and after. The heading is
 * the assertion because it is the one word on every screen that names the
 * screen; the sort control is the assertion because it is a label rather
 * than a heading, and a heading can be translated while a label is not.
 *
 * The switch lives in the locale table and persists in `localStorage`
 * (`careeros.locale`), so the test switches back at the end: the account
 * it provisions is fresh, but the browser profile the next test gets is not
 * necessarily.
 */

test("the language switch translates the screen in place", async ({ authedPage }) => {
  await authedPage.goto("/jobs");

  // Before: the English heading and the English sort label.
  await expect(
    authedPage.getByRole("heading", { level: 1, name: "Jobs" })
  ).toBeVisible({ timeout: 20_000 });
  await expect(authedPage.getByText("Sort", { exact: true })).toBeVisible();

  // The switch itself, in the sidebar. Its accessible name is the sentence
  // that says what the button will do, so the test finds the button by what
  // it promises rather than by the two characters it shows.
  const toChinese = authedPage.getByRole("button", { name: "Switch to Chinese" });
  await expect(toChinese).toBeVisible();
  await toChinese.click();

  // After: the same screen, in the reader's language.
  await expect(
    authedPage.getByRole("heading", { level: 1, name: "职位" })
  ).toBeVisible({ timeout: 20_000 });
  await expect(authedPage.getByText("排序", { exact: true })).toBeVisible();

  // The switch reads the language it is switching *to*, so a second click
  // goes back -- and the reader can get back to the language they started
  // in without reloading.
  const toEnglish = authedPage.getByRole("button", { name: "切换到英文" });
  await expect(toEnglish).toBeVisible();
  await toEnglish.click();
  await expect(
    authedPage.getByRole("heading", { level: 1, name: "Jobs" })
  ).toBeVisible({ timeout: 20_000 });
});

/**
 * The choice survives a reload.
 *
 * The switch writes to `localStorage`, so the reader's language is a
 * property of their browser and not of the page they happen to be on. A
 * switch that reset on every navigation would be a switch nobody keeps.
 */
test("the chosen language survives a reload", async ({ authedPage }) => {
  await authedPage.goto("/jobs");
  const toChinese = authedPage.getByRole("button", { name: "Switch to Chinese" });
  await expect(toChinese).toBeVisible();
  await toChinese.click();
  await expect(
    authedPage.getByRole("heading", { level: 1, name: "职位" })
  ).toBeVisible({ timeout: 20_000 });

  await authedPage.reload();
  await expect(
    authedPage.getByRole("heading", { level: 1, name: "职位" })
  ).toBeVisible({ timeout: 20_000 });

  // And the reader can go back.
  await authedPage.getByRole("button", { name: "切换到英文" }).click();
  await expect(
    authedPage.getByRole("heading", { level: 1, name: "Jobs" })
  ).toBeVisible({ timeout: 20_000 });
});

/**
 * Every navigation item is named in the reader's language.
 *
 * The sidebar is the one piece of the product that is on every screen, so it
 * is the one piece a reader is guaranteed to meet -- and it is the one piece
 * built out of a *table* rather than out of the screen. An item in that
 * table with no translation key renders its English name on every language,
 * and nothing about it looks broken: the item is there, it is in the right
 * place, and only its name is in the wrong language.
 *
 * Two items were exactly that for a while. The gate that claimed to catch it
 * checked the translation table's keys rather than the table's *items*, so it
 * never looked at them -- and the copy census cannot see the file at all,
 * because a table of fallbacks is a `.ts` module and the census reads `.tsx`.
 *
 * So the names are read off the screen rather than written into the test: the
 * English sidebar is measured, the reader switches, and the Chinese sidebar
 * must not show any of the English names. A list written into the test would
 * be a list that goes stale -- a new item would simply not be checked.
 */
test("every navigation item is named in the reader's language", async ({ authedPage }) => {
  await authedPage.goto("/jobs");

  const nav = authedPage.locator("nav[aria-label]").first();

  // The English names, measured.
  const english = (await nav.locator("a").allInnerTexts())
    .map((text) => text.trim())
    .filter(Boolean);
  expect(english.length, "the sidebar rendered no items at all").toBeGreaterThan(0);

  await authedPage.getByRole("button", { name: "Switch to Chinese" }).click();
  await expect(
    authedPage.getByRole("heading", { level: 1, name: "职位" })
  ).toBeVisible({ timeout: 20_000 });

  // The Chinese names, measured.
  const chinese = (await nav.locator("a").allInnerTexts())
    .map((text) => text.trim())
    .filter(Boolean);
  expect(chinese.length, "the sidebar rendered no items at all").toBeGreaterThan(0);

  // Not one of them is still the English name.
  for (const label of english) {
    expect(
      chinese,
      `the sidebar still shows the English name "${label}" on a Chinese page`
    ).not.toContain(label);
  }

  // And back, so the next test gets the browser it expects.
  await authedPage.getByRole("button", { name: "切换到英文" }).click();
  await expect(
    authedPage.getByRole("heading", { level: 1, name: "Jobs" })
  ).toBeVisible({ timeout: 20_000 });
});
