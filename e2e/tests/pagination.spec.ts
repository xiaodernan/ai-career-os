import { expect, test } from "./fixtures";

/**
 * The paging contract, watched from the browser.
 *
 * #219-#231 paged every board and closed the ordering holes behind them, and every one of
 * those changes was proven by unit gates that read source text and by ITs that talk to
 * Postgres. None of them watched the thing a user actually does: click "Next" on one screen
 * and see a different slice of the same set. This spec drives the knowledge page's notes
 * list -- the one board whose rows are plain writes, so 25 of them cost 25 POSTs and no AI
 * call -- and asserts the two properties the whole effort exists for:
 *
 * 1. the two pages *partition* the set: every seeded note appears exactly once across the
 *    pages. A missing ORDER BY tie-break shows up here as a duplicated or vanished row, and
 *    no other layer of the suite would notice.
 * 2. a past-the-end URL corrects itself to the last page that exists (#219), and the pager
 *    never prints a range that does not exist while it corrects.
 *
 * Notes are seeded through the real API and read through the real UI, so the URL key
 * (`?npage=`, the notes list's own index beside the sources list's `?page=`) is exercised
 * exactly as a shared link would exercise it.
 */

const NOTE_COUNT = 25;
const PAGE_SIZE = 20;

/** Every title this run seeded, and the pager's own wording for a window over them. */
function seedTitles(): string[] {
  return Array.from({ length: NOTE_COUNT }, (_, i) => `e2e-note-${String(i + 1).padStart(2, "0")}`);
}

// toHaveText normalises whitespace, so a plain string is the whole assertion.
const FIRST_WINDOW = `1\u2013${PAGE_SIZE} of ${NOTE_COUNT} notes`;
const LAST_WINDOW = `${PAGE_SIZE + 1}\u2013${NOTE_COUNT} of ${NOTE_COUNT} notes`;

test("the two pages of a list partition the set, each row exactly once", async ({ api, authedPage }) => {
  const titles = seedTitles();
  for (const title of titles) {
    const res = await api.post("/knowledge/notes", { title, content: `body of ${title}` });
    expect(res.status(), `create ${title} -> ${await res.text()}`).toBe(201);
  }

  await authedPage.goto("/knowledge");
  const notes = authedPage.locator('section[aria-label="Notes"]');
  const pager = notes.locator('p[aria-live="polite"]');
  await expect(pager).toHaveText(FIRST_WINDOW);

  // Every row carries an Edit button named after its title, so the visible set is readable
  // without depending on card markup.
  const titlesOnPage = async () => {
    const buttons = notes.getByRole("button", { name: /^Edit e2e-note-/ });
    await expect(buttons.first()).toBeVisible();
    const count = await buttons.count();
    const names: string[] = [];
    for (let i = 0; i < count; i++) {
      const label = await buttons.nth(i).getAttribute("aria-label");
      if (label) names.push(label.replace(/^Edit /, ""));
    }
    return names;
  };

  const first = await titlesOnPage();
  expect(first.length).toBe(PAGE_SIZE);

  await notes.getByRole("button", { name: "Next page" }).click();
  await expect(authedPage).toHaveURL(/npage=1/);
  await expect(pager).toHaveText(LAST_WINDOW);

  const second = await titlesOnPage();
  expect(second.length).toBe(NOTE_COUNT - PAGE_SIZE);

  // The partition property itself: no row twice, no row skipped.
  const seen = [...first, ...second];
  expect(new Set(seen).size).toBe(NOTE_COUNT);
  expect([...seen].sort()).toEqual([...titles].sort());
});

test("a past-the-end URL corrects itself, and the pager never prints a window that is not there", async ({
  api,
  authedPage,
}) => {
  const titles = seedTitles();
  for (const title of titles) {
    const res = await api.post("/knowledge/notes", { title, content: `body of ${title}` });
    expect(res.status()).toBe(201);
  }

  // ?npage=9 over 25 rows: the answer is an empty window with a real total. The screen
  // rewrites the URL to the last page that exists, and the pager reports that page's rows
  // rather than "501-525 of 25" for the frame in between.
  await authedPage.goto("/knowledge?npage=9");
  await expect(authedPage).toHaveURL(/npage=1/, { timeout: 20_000 });

  const notes = authedPage.locator('section[aria-label="Notes"]');
  await expect(notes.locator('p[aria-live="polite"]')).toHaveText(LAST_WINDOW);
  await expect(notes.getByRole("button", { name: /^Edit e2e-note-/ })).toHaveCount(
    NOTE_COUNT - PAGE_SIZE
  );
  await expect(notes.getByRole("button", { name: "Next page" })).toBeDisabled();
  await expect(notes.getByRole("button", { name: "Previous page" })).toBeEnabled();
});
