import { test, expect } from "./fixtures";

/**
 * Epic 185's offer shelf, driven through the screen: add two offers, the shelf ranks
 * them by total comp and crowns the best; edit one; remove it; the shelf agrees at
 * every step. The decision the offers page exists for finally has rows behind it.
 */

test("the shelf ranks the reader's offers and answers every write", async ({ authedPage }) => {
  const page = authedPage;
  await page.goto("/offers");

  await expect(page.getByText("Your offer shelf")).toBeVisible({ timeout: 30_000 });
  await expect(
    page.getByText("The shelf is empty — add your first offer below and the comparison starts there.")
  ).toBeVisible();

  // Offer A — the richer one.
  await page.getByRole("textbox", { name: "Offer", exact: true }).fill("Acme — Senior Backend");
  await page.getByRole("textbox", { name: "Base salary", exact: true }).fill("210000");
  await page.getByRole("textbox", { name: "Bonus", exact: true }).fill("15000");
  await page.getByRole("textbox", { name: "Equity / yr", exact: true }).fill("30000");
  await page.getByRole("button", { name: "Add offer" }).click();
  await expect(page.getByText("Acme — Senior Backend")).toBeVisible({ timeout: 20_000 });

  // Offer B — the cheaper one with equity but no bonus.
  await page.getByRole("textbox", { name: "Offer", exact: true }).fill("Globex — Platform");
  await page.getByRole("textbox", { name: "Base salary", exact: true }).fill("195000");
  await page.getByRole("textbox", { name: "Equity / yr", exact: true }).fill("10000");
  await page.getByRole("button", { name: "Add offer" }).click();
  await expect(page.getByText("Globex — Platform")).toBeVisible({ timeout: 20_000 });

  // The shelf lists newest first; scope to Globex's row so the order assumption
  // can never silently point the edit at the wrong offer.
  const acmeRow = page.locator("li", { hasText: "Acme" });
  const globexRow = page.locator("li", { hasText: "Globex" });

  // A is the richest (255,000 vs 205,000) and wears the trophy.
  await expect(acmeRow.getByText("Best total comp")).toBeVisible();
  await expect(page.getByText("$255,000").first()).toBeVisible();
  await expect(page.getByText("$205,000").first()).toBeVisible();
  await expect(page.getByText("2 on the shelf")).toBeVisible();

  // Edit Globex's base up to 246,000 (total 256,000): the crown moves because the
  // shelf ranks by the rows it holds rather than remembering a verdict.
  await globexRow.getByLabel("Edit this offer").click();
  await page.getByRole("textbox", { name: "Base salary", exact: true }).fill("246000");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(globexRow.getByText("$256,000")).toBeVisible({ timeout: 20_000 });
  await expect(globexRow.getByText("Best total comp")).toBeVisible();
  await expect(acmeRow.getByText("Best total comp")).toHaveCount(0);

  // Remove it: the shelf is back to one row, and the trophy is suppressed on a
  // single-offer shelf (the badge only competes one offer against another).
  await globexRow.getByLabel("Remove this offer").click();
  await expect(page.getByText("Globex — Platform")).toHaveCount(0, { timeout: 20_000 });
  await expect(acmeRow.getByText("Best total comp")).toHaveCount(0);

  // The decision strip is the endgame: default to On hold, flip to Taking it, and
  // the commit moment fires — the one finish line for a preference turned into an
  // answer; dismiss it, the banner names the row the reader has decided on; flip
  // back to On hold and the banner is gone.
  const acme = page.locator("li", { hasText: "Acme" });
  await expect(acme.getByRole("button", { name: "On hold" })).toHaveAttribute("aria-pressed", "true");
  await acme.getByRole("button", { name: "Taking it" }).click();
  await expect(page.getByText("The call is made.")).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: "Keep going" }).click();
  await expect(acme.getByRole("button", { name: "Taking it" })).toHaveAttribute("aria-pressed", "true", { timeout: 20_000 });
  await expect(page.getByText("Acme — Senior Backend — this is yours.")).toBeVisible({ timeout: 20_000 });
  await acme.getByRole("button", { name: "On hold" }).click();
  await expect(page.getByText("Acme — Senior Backend — this is yours.")).toHaveCount(0, { timeout: 20_000 });
});
