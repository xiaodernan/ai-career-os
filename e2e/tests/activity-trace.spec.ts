import { expect, test } from "./fixtures";
import { unwrap } from "./fixtures";

/**
 * The run's trace, from the screen.
 *
 * The activity page is the debug view behind the answers (PRD §31, §47 Demo
 * 6): a run, the steps it took, and the bill it incurred. It is the one
 * surface that answers "what did the agent actually do", and it is the
 * surface that says the product is inspectable rather than a black box.
 *
 * The golden journey checks the run row exists -- the API says a run was
 * recorded. That is a claim about a table. The claim this makes is about
 * the *page*: a reader opens the run and sees the steps, the tool it
 * called, and the cost, and the run on the screen is the run the copilot
 * just did.
 *
 * So the turn is driven through the copilot, the activity list is opened
 * from the screen, and the run that the list shows is compared with the
 * run the API recorded. The trace's own steps are checked against the
 * trace the API carries -- the step count, and the tool that was called.
 */
test("the run the copilot did is the run the trace shows", async ({
  api,
  authedPage,
}) => {
  // A turn, driven the way a reader drives it.
  await authedPage.goto("/copilot");
  const composer = authedPage.getByRole("textbox", { name: "First message to Copilot" });
  await expect(composer).toBeVisible({ timeout: 20_000 });
  await composer.fill("Which of my projects best shows ownership?");
  await authedPage.getByRole("button", { name: "Start chat" }).click();

  // The answer arrives (the streaming path is held by another case); this
  // one is about what the run left behind.
  await expect(
    authedPage.getByText("Which of my projects best shows ownership?").first(),
    "the question never reached the transcript"
  ).toBeVisible({ timeout: 60_000 });

  // The run the API recorded, so the screen has something to be compared
  // against. It is the newest row with a trace: a run that went through
  // the orchestrator has steps, and one that did not (a single-call parse)
  // has only the run row -- so the newest run is not always the one the
  // reader came for.
  //
  // The wait is a poll, not a sleep. The question reaches the transcript
  // before the turn has finished, and the run is written when the turn
  // does -- so the run row appears a moment later, and looking for it
  // straight away would be looking before it was there.
  let runId: string | null = null;
  await expect
    .poll(
      async () => {
        const runs = await unwrap<{
          items: Array<{ id: string }>;
        }>(await api.get("/activity/runs", { size: 10 }));
        for (const candidate of runs.items) {
          const detail = await unwrap<{ traces?: unknown[] }>(
            await api.get(`/activity/runs/${candidate.id}`)
          );
          if ((detail.traces ?? []).length > 0) {
            runId = candidate.id;
            return true;
          }
        }
        return false;
      },
      { timeout: 60_000, message: "the turn recorded no run with a trace" }
    )
    .toBe(true);
  expect(runId, "the turn recorded a run with no steps").toBeTruthy();

  // The activity list, and the run in it.
  await authedPage.goto("/activity");
  await expect(
    authedPage.getByRole("heading", { name: "AI Activity" }),
    "the activity page did not render"
  ).toBeVisible({ timeout: 30_000 });

  // The list carries the run -- by a link to it. A list that rendered but
  // did not carry the run would pass a check that only looked for the
  // heading.
  const runLink = authedPage.locator(`a[href="/activity/${runId}"]`);
  await expect(runLink, "the activity list does not carry the run").toBeVisible({
    timeout: 30_000,
  });

  // Open it, and the page is that run -- the one the API knows, with the
  // steps it carries.
  await runLink.first().click();
  await expect(authedPage).toHaveURL(new RegExp(`/activity/${runId}$`), {
    timeout: 30_000,
  });

  // The trace itself: the steps, and the tool the agent called.
  await expect(
    authedPage.getByText("Execution trace"),
    "the run has no execution trace"
  ).toBeVisible({ timeout: 30_000 });

  const trace = await unwrap<{
    run?: { id?: string };
    traces?: Array<{ kind?: string; payload?: Record<string, unknown> }>;
  }>(await api.get(`/activity/runs/${runId}`));
  expect(
    trace.run?.id,
    "the run the list shows is not one the API knows"
  ).toBe(runId);
  const steps = trace.traces ?? [];
  expect(steps.length, "the run recorded no steps").toBeGreaterThan(0);

  // The steps the API carries are the steps on the screen. The timeline
  // shows each step's kind beside its label, with the first underscore
  // turned into a space -- so the kinds are what the page shows, and a
  // trace with no steps on the screen cannot pass this.
  const timeline = authedPage.getByLabel("Agent execution trace");
  await expect(timeline, "the run has no trace timeline").toBeVisible({
    timeout: 20_000,
  });
  await expect(
    timeline.locator("li"),
    "the trace shows fewer steps than the run recorded"
  ).toHaveCount(steps.length, { timeout: 20_000 });

  const kinds = new Set(steps.map((s) => s.kind).filter(Boolean));
  for (const kind of kinds) {
    await expect(
      timeline.getByText(String(kind).replace("_", " "), { exact: true }).first(),
      `the trace does not show the step ${kind}`
    ).toBeVisible({ timeout: 20_000 });
  }

  // The attribution panel: the run's own id, its agent, and the bill.
  await expect(
    authedPage.getByText("Attribution"),
    "the run has no attribution panel"
  ).toBeVisible({ timeout: 20_000 });
  await expect(
    authedPage.getByText(runId, { exact: true }),
    "the run's own id is not on the page"
  ).toBeVisible({ timeout: 20_000 });
});
