import { test, expect, apiFor, unwrap } from "./fixtures";

/**
 * The moment the funnel converges: a card crosses to `Offer` and this is the one
 * place in the product allowed to stop and celebrate.
 *
 * Path: an interview-stage application is created through the API, opened via
 * the board's deep link with `?application=<id>`, moved to Offer, and saved —
 * the mutation's onSuccess renders the celebration, not a silent toast.
 */
test("moving a card to Offer stops the board for a celebration", async ({ authedPage, user, request }) => {
  const api = apiFor(request, user);
  const create = await api.post("/applications", {
    title: "Senior Backend Engineer",
    companyName: "Acme",
    status: "interview",
  });
  const app = await unwrap<{ id: string }>(create);

  await authedPage.goto(`/applications?application=${app.id}`);
  // The deep link opens the card's editor; the label "Stage" belongs to the radix select.
  const stage = authedPage.getByLabel("Stage", { exact: true });
  await expect(stage).toBeVisible();
  await stage.click();
  await authedPage.getByRole("option", { name: "Offer", exact: true }).click();
  await authedPage.getByRole("button", { name: "Save changes" }).click();

  await expect(authedPage.getByText("An offer, in hand.")).toBeVisible({ timeout: 20_000 });
  await expect(authedPage.getByText("Senior Backend Engineer — Acme")).toBeVisible();

  // The single ask the screen makes, and the only place it leads: the offers shelf.
  await authedPage.getByRole("link", { name: "Open the offers shelf" }).click();
  await expect(authedPage).toHaveURL(/\/offers(\?.*)?$/);
  await expect(authedPage.getByText("Your offer shelf")).toBeVisible({ timeout: 20_000 });
});
