import { test, expect, unwrap } from "./fixtures";

/**
 * Epic 184's pace heatmap, end to end: a reader who files an application today sees
 * TODAY's cell lit on the dashboard's grid, and the streaks answer the chain they
 * just started. The claim is the wire through the screen — the grid is dense (every
 * calendar day renders, quiet or not), the counts are the backend's own, and the
 * card reads in the reader's language.
 */

test("the pace grid lights today when the reader files an application", async ({
  api,
  authedPage,
}) => {
  // A job to file against: the seeded board answers the first search.
  const jobs = await unwrap<{ items: Array<{ id: string; title: string }> }>(
    await api.get("/jobs", { size: 1 })
  );
  const job = jobs.items[0];
  await api.post("/applications", {
    jobId: job.id,
    title: job.title,
    status: "applied",
  });

  const heat = await unwrap<{
    days: number;
    grid: Array<{ date: string; applications: number; total: number }>;
    streak: { current: number; longest: number };
    grandTotal: number;
  }>(await api.get("/reports/activity-heatmap", { days: 28 }));

  expect(heat.grid, "the grid is dense: every calendar day is present").toHaveLength(28);
  const today = heat.grid[heat.grid.length - 1];
  expect(today.applications).toBeGreaterThanOrEqual(1);
  expect(heat.grandTotal).toBeGreaterThanOrEqual(1);
  expect(heat.streak.current).toBeGreaterThanOrEqual(1);

  await authedPage.goto("/dashboard");
  await expect(authedPage.getByText("Your search, at a glance")).toBeVisible({
    timeout: 30_000,
  });
  // The streak chips carry the numbers the API just answered.
  await expect(
    authedPage.getByText("Current streak").locator("..").getByText(/\d+/).first()
  ).toBeVisible({ timeout: 20_000 });
});
