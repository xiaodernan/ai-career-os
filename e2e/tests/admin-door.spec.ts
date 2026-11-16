import { API_URL, expect, test, unwrap } from "./fixtures";

const PASSPHRASE = "123";

test.describe("the overseer's door", () => {
  test("opens on the shared passphrase without an account", async ({ page, request }) => {
    await page.goto("/admin");
    const gate = page.locator("#admin-pass");
    await expect(gate).toBeVisible();
    // A wrong word drops you at the gate, not past it.
    await gate.fill("not-the-passphrase");
    await page.getByRole("button", { name: /Open the ledger|打开账簿/i }).click();
    await expect(gate).toBeVisible();
    // The right word opens the ledger.
    await gate.fill(PASSPHRASE);
    await page.getByRole("button", { name: /Open the ledger|打开账簿/i }).click();
    await expect(page.getByRole("heading", { name: /^The overseer's ledger$|^掌管全局的人的账簿$/i })).toBeVisible({
      timeout: 15_000,
    });
    // The attention tile totals at least load, the synthetic door renders.
    await expect(page.locator("#simulate-count")).toBeVisible({ timeout: 15_000 });
    const attention = await unwrap<{ landings: number; dwells: number; acts: number }>(
      await request.get(`${API_URL}/admin/attention`)
    );
    expect(attention.landings).toBeGreaterThanOrEqual(0);
  });

  test("a seeded week moves the attention ledger both ways", async ({ page, request }) => {
    await page.goto("/admin");
    await page.locator("#admin-pass").fill(PASSPHRASE);
    await page.getByRole("button", { name: /Open the ledger|打开账簿/i }).click();
    await expect(page.locator("#simulate-count")).toBeVisible({ timeout: 15_000 });

    const before = await unwrap<{ landings: number; dwells: number; acts: number }>(
      await request.get(`${API_URL}/admin/attention`)
    );

    // Seed three sessions into the ledger via the door.
    await page.locator("#simulate-count").fill("3");
    await page.getByRole("button", { name: /Seed synthetic visitors|注入合成访客/i }).click();
    await expect(page.getByText(/synthetic sessions written|已写入/i)).toBeVisible({
      timeout: 20_000,
    });

    const seeded = await unwrap<{ landings: number; dwells: number; acts: number }>(
      await request.get(`${API_URL}/admin/attention`)
    );
    expect(seeded.landings).toBeGreaterThan(before.landings);

    // Wipe them back, restoring the ledger to its real shape.
    await page.getByRole("button", { name: /Wipe synthetic rows|抹除合成记录/i }).click();
    await expect(page.getByText(/Synthetic rows wiped|合成记录已抹去/i)).toBeVisible({
      timeout: 20_000,
    });

    const wiped = await unwrap<{ landings: number; dwells: number; acts: number }>(
      await request.get(`${API_URL}/admin/attention`)
    );
    expect(wiped.landings).toBeLessThanOrEqual(seeded.landings);
  });
});
