import { expect, test } from "./fixtures";
import { unwrap } from "./fixtures";

/**
 * The contacts, written by hand.
 *
 * The address book is the reader's own record of who they know, and it is
 * the one screen the suite drove only through the API. The draft flow -- the
 * copilot writing a message to a contact -- was covered; the writing of the
 * contact itself was not, and a screen nobody writes on is a screen nobody
 * checked.
 *
 * It matters more than it did a day ago: the contacts travel in the export
 * bundle now, so a contact the reader cannot write is a contact the reader
 * cannot take with them.
 */
test("a contact is written, edited and deleted on the screen", async ({
  api,
  authedPage,
}) => {
  await authedPage.goto("/networking");

  // Nothing there yet, and the empty state says so.
  await expect(
    authedPage.getByText("No contacts yet", { exact: true })
  ).toBeVisible({ timeout: 20_000 });

  // The form the reader opens.
  await authedPage.getByRole("button", { name: "Add contact" }).click();
  await expect(authedPage.locator("#ct-name")).toBeVisible();

  // Only the name is required, and the rest is what the reader knows.
  await authedPage.locator("#ct-name").fill("Li Ming");
  await authedPage.locator("#ct-company").fill("Acme");
  await authedPage.locator("#ct-relation").fill("Mentor");
  await authedPage.locator("#ct-notes").fill("Met at the conference; happy to review my design.");
  await authedPage.getByRole("button", { name: "Add", exact: true }).click();

  // The row is on the screen, with what the reader typed. The row *is* the
  // edit control -- clicking it opens the form -- so the row is found by
  // the name in it.
  const row = authedPage.getByRole("button", { name: /Li Ming/ });
  await expect(row).toBeVisible({ timeout: 20_000 });

  // And it is in the server's own list -- the screen is not showing a
  // local copy of something the server never received. The route answers a
  // plain list: there is no pager on an address book.
  await expect
    .poll(async () => {
      const contacts = await unwrap<Array<{ name: string; company: string }>>(
        await api.get("/contacts")
      );
      return contacts.map((c) => `${c.name}@${c.company}`).join(",");
    }, { timeout: 20_000 })
    .toContain("Li Ming@Acme");

  // The edit, on the row itself.
  await row.click();
  await expect(authedPage.locator("#ct-name")).toBeVisible();
  await authedPage.locator("#ct-company").fill("Acme Labs");
  await authedPage.getByRole("button", { name: "Save", exact: true }).click();

  await expect
    .poll(async () => {
      const contacts = await unwrap<Array<{ name: string; company: string }>>(
        await api.get("/contacts")
      );
      return contacts.map((c) => `${c.name}@${c.company}`).join(",");
    }, { timeout: 20_000 })
    .toContain("Li Ming@Acme Labs");

  // And the delete, which the form offers and the dialog asks about.
  await authedPage.getByRole("button", { name: /Li Ming/ }).first().click();
  await expect(authedPage.locator("#ct-name")).toBeVisible();
  await authedPage.getByRole("button", { name: "Delete", exact: true }).click();
  const dialog = authedPage.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Delete", exact: true }).click();

  // A fresh account holds no other contacts, so the empty state returning
  // is the strongest proof the delete removed the row.
  await expect(
    authedPage.getByText("No contacts yet", { exact: true })
  ).toBeVisible({ timeout: 20_000 });
});
