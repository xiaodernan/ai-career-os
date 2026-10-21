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
