import { expect, test } from "./fixtures";

/**
 * The page's title, in the reader's language.
 *
 * The title is rendered into the document's head, and the head is the
 * browser's first paint and the crawler's whole view. So it has to be
 * right in the HTML the *server* sends -- and the server does not know
 * which language the reader chose, because the product keeps the locale
 * in the browser's own storage.
 *
 * The locale therefore travels in a cookie as well, and the server reads
 * it. That is the whole design, and it is worth stating because the
 * obvious alternative does not work: a `useEffect` that writes
 * `document.title` runs, and the title does change, and then React's own
 * metadata reconciliation resets it -- the `<title>` element is part of
 * the tree it just hydrated. The write is undone a moment after it
 * happens, and the reader sees the server's English title for the whole
 * visit. A test that only looked at the DOM would not see it; a test that
 * reads the title after the page has settled does.
 *
 * So these read the title after the page has settled, in both languages.
 */
test("the page's title is in the reader's language", async ({ page }) => {
  // English to begin with: the account is fresh, but the browser profile
  // the next test gets is not necessarily, so the test says which
  // language it is reading rather than assuming one.
  await page.goto("/login");
  await expect(page).toHaveTitle(/Sign in · AI Career OS/, { timeout: 20_000 });

  // The switch on the public page, driven for real.
  await page.getByRole("button", { name: "Switch to Chinese" }).first().click();

  // The title follows -- and it is the *server's* title, so the page has
  // to be fetched again to see it, which is what a navigation does.
  await page.goto("/login");
  await expect(page).toHaveTitle(/登录 · AI Career OS/, { timeout: 20_000 });

  // And the 404, which is the one page the server names itself: the
  // browser cannot tell a bad route from a good one -- it sees the path
  // that was asked for -- so only the server can say "not found".
  await page.goto("/definitely-not-a-route");
  await expect(page).toHaveTitle(/页面不存在 · AI Career OS/, { timeout: 20_000 });

  // Back to English, so the next test starts where this one left off.
  await page.goto("/login");
  await page.getByRole("button", { name: "切换到英文" }).first().click();
  await page.goto("/login");
  await expect(page).toHaveTitle(/Sign in · AI Career OS/, { timeout: 20_000 });
});
