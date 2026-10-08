import { expect, test } from "./fixtures";

/**
 * The ⌘K palette, watched from the browser.
 *
 * `command-palette.test.ts` guards this component by reading its source, and the
 * unit tests around it stub the search function out. Neither watches the thing a user
 * actually does: press the shortcut, watch the dialog appear, type, and land somewhere.
 * Three properties only a real browser can prove:
 *
 * 1. the keyboard shortcut is bound at all. It lives in a `useEffect` on `window`, which
 *    is exactly the kind of wiring a refactor drops silently -- nothing else in the suite
 *    presses a key.
 * 2. navigation filtering is client-side and still works, so a query that matches a
 *    section narrows the "Go to" group and selecting it navigates.
 * 3. the palette's rows come from the real `GET /search`. The unit test replaces that
 *    call, so "the server answered and the palette rendered it" has never been observed
 *    end to end -- and the subtitle is the proof, because it is a column the server
 *    returns and the client never invents.
 *
 * The note is written through the real API rather than seeded by a fixture, so the row
 * the palette shows is one this run created and can name exactly.
 */

const ELLIPSIS_PLACEHOLDER = "Type a command or search\u2026";

/**
 * Open the palette the way a user does, and wait for the dialog to be there.
 *
 * The wait comes first and it is not optional. The shortcut is bound in a `useEffect`
 * inside `CommandPaletteProvider`, which sits behind `AuthGuard` -- and AuthGuard renders
 * a splash until `useUser()` resolves. Pressing the key before that lands on a page with
 * no listener attached, the event goes nowhere, and the test fails 15 seconds later with
 * "element not found" while looking like a broken component. The topbar's own "Open
 * command palette" button is inside the provider, so it appearing is proof the listener
 * is live; it is the same hook, rendered by the same tree.
 */
async function openPalette(page: import("@playwright/test").Page) {
  await expect(page.getByLabel("Open command palette").first()).toBeVisible();
  await page.keyboard.press("ControlOrMeta+k");
  await expect(page.getByPlaceholder(ELLIPSIS_PLACEHOLDER)).toBeVisible();
}

test("the keyboard shortcut opens the palette, and Escape closes it", async ({ authedPage }) => {
  await authedPage.goto("/dashboard");
  await openPalette(authedPage);

  // The capability line is generated from the same table that decodes the response, so it
  // names every group /search answers with -- and it is only rendered before a query.
  await expect(
    authedPage.getByText(/Search jobs, companies, resumes, notes, conversations and applications/)
  ).toBeVisible();

  // "Go to" is the client-side group: it is on screen before any request has been made.
  const goTo = authedPage.locator("[cmdk-group]").filter({ hasText: "Go to" });
  await expect(goTo.getByRole("option", { name: /Dashboard/ })).toBeVisible();
  await expect(goTo.getByRole("option", { name: /Settings/ })).toBeVisible();

  await authedPage.keyboard.press("Escape");
  await expect(authedPage.getByPlaceholder(ELLIPSIS_PLACEHOLDER)).toBeHidden();
});

test("the palette filters navigation locally and navigates to what it kept", async ({
  authedPage,
}) => {
  await authedPage.goto("/dashboard");
  await openPalette(authedPage);

  const goTo = authedPage.locator("[cmdk-group]").filter({ hasText: "Go to" });
  await expect(goTo.getByRole("option", { name: /Dashboard/ })).toBeVisible();

  await authedPage.getByPlaceholder(ELLIPSIS_PLACEHOLDER).fill("settings");
  await expect(goTo.getByRole("option", { name: /Settings/ })).toBeVisible();
  await expect(goTo.getByRole("option", { name: /Dashboard/ })).toHaveCount(0);

  await goTo.getByRole("option", { name: /Settings/ }).click();
  await expect(authedPage).toHaveURL(/\/settings$/);
  await expect(authedPage.getByPlaceholder(ELLIPSIS_PLACEHOLDER)).toBeHidden();
});

test("a note written through the API is found by the palette's real search", async ({
  api,
  authedPage,
}) => {
  // The snippet below is the assertion's backbone: it is a column /search returns and
  // the client never invents, so seeing it proves the server answered.
  const title = `e2e-palette-${Date.now().toString(36)}`;
  const snippet = "palette probe body pgvector";
  const created = await api.post("/knowledge/notes", { title, content: snippet });
  expect(created.status(), `create note -> ${await created.text()}`).toBe(201);

  await authedPage.goto("/dashboard");
  await openPalette(authedPage);
  await authedPage.getByPlaceholder(ELLIPSIS_PLACEHOLDER).fill(title);

  const hit = authedPage.locator("[cmdk-item]", { hasText: title });
  await expect(hit).toBeVisible();
  await expect(hit).toContainText(snippet);

  // Notes navigate to the knowledge page -- the deepest route that really exists for a
  // note, per the group table that maps entity types to hrefs.
  await hit.click();
  await expect(authedPage).toHaveURL(/\/knowledge$/);
});
