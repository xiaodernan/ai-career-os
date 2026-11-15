import { expect, test } from "./fixtures";

/**
 * Epic 268 — the room you walk into, proven through the real browser.
 * Registering through the API, opening the seeded TechCorp page, sealing one
 * lens, and watching the meter move — no mocks anywhere on this path.
 */
test("the pre-interview kit renders and seals a lens end to end", async ({ authedPage }) => {
  await authedPage.goto("/companies/ebbf5f04-c79c-4a18-a7b3-84130808056c");

  const kit = authedPage.getByTestId("preinterview-kit");
  await expect(kit).toBeVisible({ timeout: 20_000 });

  // The meter starts at zero.
  const meter = kit.getByRole("progressbar");
  await expect(meter).toHaveAttribute("aria-valuenow", "0");

  // Seal one lens at "Evidence" (level 2) and read the meter twice.
  await kit.getByRole("button", { name: "Evidence" }).first().click();
  await expect(meter).toHaveAttribute("aria-valuenow", "2", { timeout: 5_000 });

  // The gate is honest: nothing is synthesized until the reader writes through.
  await expect(kit.getByText(/Seal at least 8 of 10/)).toBeVisible();
  await expect(kit.getByText("Gather into two questions")).toHaveCount(0);
});
