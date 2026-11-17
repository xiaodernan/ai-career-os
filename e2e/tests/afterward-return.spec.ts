import { expect, test } from "./fixtures";

/**
 * The manual's closing pointer, traced for real.
 *
 * The last chapter of /playbook no longer ends at the empty room: the
 * afterward walks the reader back to the dashboard, where the loop is
 * waiting (Epic 298). A pointer on the last page of the book that does not
 * land where it says is a worse dead end than no pointer at all — so the
 * trace goes all the way: read the rendered chapter, find the pointer,
 * follow it, and count the landing.
 */
test.describe("the afterward's return pointer", () => {
  test("lands the reader on the dashboard", async ({ authedPage: page }) => {
    await page.goto("/playbook#afterward");
    const pointer = page.getByRole("link", {
      name: "the dashboard, where the loop is waiting",
    });
    await expect(pointer, "the afterward chapter renders its return pointer").toBeVisible({
      timeout: 20_000,
    });
    await pointer.click();
    await expect(page, "the pointer lands on the dashboard").toHaveURL(/\/dashboard/, {
      timeout: 30_000,
    });
  });
});
