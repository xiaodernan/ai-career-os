import { expect, test } from "./fixtures";
import { unwrap } from "./fixtures";

/**
 * The timeline, watched by a browser.
 *
 * The page renders the engine's own ordered merge — the fold happens server side, and
 * this suite is the only place that proves the browser actually draws it: the kinds are
 * named, the chips narrow, the deep links land on the screens that own the facts they
 * carry, and the URL remembers the narrowing. The rows here are written by the real
 * write paths; nothing is seeded as a fixture shape.
 */
test("the timeline shows the account's own events in order, narrows by kind, and links to the screens", async ({
  api,
  authedPage,
}) => {
  await unwrap(
    await api.post("/applications", {
      title: "Timeline Engineer",
      company_name: "Acme Labs",
      status: "applied",
    })
  );
  await unwrap(
    await api.post("/knowledge/notes", {
      title: "Follow-up plan",
      content: "Pitch the referral ask before the weekend.",
      tags: ["networking"],
    })
  );
  await unwrap(await api.post("/contacts", { name: "Ada Timeline", relation: "referrer" }));

  await authedPage.goto("/timeline");

  // The fold renders through the real locale default (en): heading and all three rows, in order.
  await expect(authedPage.getByRole("heading", { level: 1, name: "Timeline" })).toBeVisible({ timeout: 20_000 });

  const appRow = authedPage.getByRole("link", { name: /Timeline Engineer/ });
  await expect(appRow).toBeVisible({ timeout: 20_000 });
  await expect(authedPage.getByText("Added Ada Timeline")).toBeVisible();
  await expect(authedPage.getByText("Follow-up plan")).toBeVisible();
  await expect(appRow).toHaveAttribute("href", /\/applications\?application=[0-9a-f-]{36}/);

  // One chip narrows the page to applications only — the contact's row is gone.
  const narrowGroup = authedPage.getByRole("group", { name: "Narrow the timeline by kind" });
  await expect(narrowGroup).toBeVisible();
  await narrowGroup.getByRole("button", { name: /Application/ }).click();
  await expect(authedPage).toHaveURL(/[?&]kind=application($|&)/);
  await expect(authedPage.getByText("Added Ada Timeline")).not.toBeVisible();
  await expect(authedPage.getByText("Follow-up plan")).not.toBeVisible();
  await expect(authedPage.getByRole("link", { name: /Timeline Engineer/ })).toBeVisible();

  // All kinds takes the narrowing out of the URL and the rows come back.
  await narrowGroup.getByRole("button", { name: "All kinds" }).click();
  await expect(authedPage).not.toHaveURL(/[?&]kind=/);
  await expect(authedPage.getByText("Added Ada Timeline")).toBeVisible();
  await expect(authedPage.getByText("Follow-up plan")).toBeVisible();

  // A narrowing with nothing behind it — reachable only by pasting the URL — shows the
  // page's own honest empty sentence, not the workspace's default empty state.
  await authedPage.goto("/timeline?kind=interview");
  await expect(authedPage).toHaveURL(/[?&]kind=interview($|&)/);
  await expect(
    authedPage.getByText(/rows yet for this account/i)
  ).toBeVisible();
  await expect(authedPage.getByText("Nothing written down yet")).not.toBeVisible();
});
